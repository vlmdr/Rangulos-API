# Etapa 02 — reprodução local e validação HTTP da API

Data da repetição: 15/10/2026. Base: `ViniciusRio/Rangulos-API` `d118a5e`. Este relatório combina inspeção estática com requisições reais a uma instância local descartável. Nenhum serviço de produção foi acessado. Dados de contas, endereço e evento foram fictícios. Tokens, chaves e respostas com dados de usuários não foram gravados no relatório.

## Dependências e instruções existentes

- `composer.json` exige PHP `>=7.0`, Laravel `5.5.*`, `tymon/jwt-auth` `1.0.0-rc.4.1` e PHPUnit `~6.0`. O lockfile fixa Laravel `5.5.48` e PHPUnit `6.5.14`. A [documentação oficial do Laravel 5.5](https://laravel.com/framework/docs/5.5) lista OpenSSL, PDO, Mbstring, Tokenizer e XML entre as extensões exigidas.
- O host não oferecia PHP nem Composer. A reprodução usou Docker `29.8.0`, imagem local baseada em `php:7.4-cli` com extensões `pdo_sqlite`, `mbstring`, `xml` e `curl`, mais os utilitários `git` e `unzip`, PHP `7.4.33`, Composer `1.10.27` e SQLite novo. A imagem e o Composer foram recursos de laboratório, sem alteração de arquivos rastreados.
- `README.md` e `readme.md` não fornecem um procedimento completo de bootstrap. `container/docker-compose.yml` e `container/env-example` descrevem Nginx/PHP-FPM/MySQL, mas não há `.env.example` na raiz, embora o script `post-root-package-install` o espere. Há um `database/database.sqlite` rastreado; ele **não foi usado nem aberto** nesta validação.
- `config/database.php`, `config/jwt.php`, `config/auth.php` e `routes/api.php` definem os requisitos de banco, segredo JWT e rotas. O laboratório montou apenas um SQLite vazio fora do repositório, com `APP_KEY` e `JWT_SECRET` aleatórios em arquivo local de permissão `0600`.

## Execução e impedimentos

| Ação | Resultado observado |
| --- | --- |
| `composer install` com Composer 2.2.25 | A primeira execução falhou por falta de utilitários `unzip`/`git` na imagem inicial. Com essas ferramentas, o plugin `kylekatarnls/update-helper` falhou na interface de plugins. `--no-plugins --no-scripts` instalou pacotes, mas o bootstrap Laravel falhou em `PackageManifest` por formato de `installed.json` incompatível. |
| `php .stage02-composer.phar install --no-plugins --no-scripts --no-interaction --prefer-dist` em PHP 7.4/Composer 1.10.27 | Sucesso, 83 pacotes do lockfile. Houve aviso de lockfile desatualizado e de obsolescência do Composer 1. Não foi feito `composer update`. |
| `php artisan migrate --force` com `--network none` | Sucesso: tabela de migrations e cinco migrations aplicadas no SQLite vazio do laboratório. |
| `vendor/bin/phpunit` com `--network none` | Sucesso: `OK (2 tests, 2 assertions)`. São testes de base; não cobrem os contratos nem os riscos abaixo. |
| `php artisan serve --host=0.0.0.0 --port=8081` em container | API publicada somente em `127.0.0.1:8081` no host. |
| `python3 -B tests/manual/stage02_http_probe.py` | Sucesso na repetição. O script exige a API local já inicializada e usa contas `@example.invalid`, localização fictícia e imagem sintética de 1 px. Os asserts documentam cada resposta sem imprimir JWT, e-mail ou IDs. |

Para reproduzir em outro ambiente, crie uma imagem PHP 7.4 com as extensões citadas, `git` e `unzip`; instale com Composer 1.10.27 sem plugins/scripts; gere `APP_KEY` e `JWT_SECRET` aleatórios; aponte `DB_CONNECTION=sqlite` e `DB_DATABASE` para **um arquivo novo fora do checkout**; rode migrations, PHPUnit e servidor com bind do host limitado a `127.0.0.1`; execute o probe manual. O script pressupõe uma instância descartável e cria registros: não o use contra uma API compartilhada. Evite o SQLite versionado.

## Contratos HTTP observados

Todos os caminhos têm prefixo `/api`. O login devolve `token` e `token_type=bearer`; o script manteve o token apenas em memória. Os corpos de sucesso variam entre objeto com mensagem/ID, booleano JSON e recurso serializado. A tabela descreve respostas efetivamente testadas, não uma especificação aprovada.

| Método e rota | Entrada/resultado observado no laboratório |
| --- | --- |
| `POST /register`, `POST /login` | Nome/e-mail/senha fictícios; ambos `200`; login retorna bearer JWT. |
| `GET /events`, `GET /event/{id}` sem token | `401`. |
| `POST /events` | Título, descrição, endereço, preço, limite e datas; `200`, com ID. |
| `GET /event/{id}` como usuário alheio | `200`, inclui endereço e `is_owner=false`. A política de visibilidade do produto não está definida. |
| `PUT /event/{id}` como usuário alheio | `200`; título mudou; `is_owner` passou a `true` para ele e `false` para o criador original. |
| `DELETE /event/{id}` e `POST /event/{id}/restore` como usuário alheio | Em segundo evento, cujo proprietário **permaneceu o criador**, ambos `200`; `deleted_at` foi preenchido e depois removido. |
| `POST /guest/{id}` e `DELETE /guest/{id}` | `200` para entrada e saída do convidado fictício. |
| `POST /event/pay` com `{ "id": <evento> }` | `200` com `true` para convidado; nenhum provedor financeiro foi usado. Antes, outro convidado via `is_paid=false`; depois, `is_paid=true` no detalhe, embora não tivesse feito a operação. |
| `POST /event/{id}/upload` multipart com campo `file` | `200` para usuário sem posse; `GET /event/{id}/image` por outro usuário deu `200` com MIME de imagem. |
| `DELETE /event/{id}/delete` como usuário alheio | No segundo evento, ainda sem posse, `200`; ele deixou de constar em `GET /events/my` do criador original. |

O probe não cobre todas as combinações de perfis, payloads inválidos, concorrência, tamanho/tipo de upload, limite de convidados, expiração do JWT, logout, histórico, avaliação, banco MySQL nem integrações externas. Um `200` para o usuário alheio e a mudança persistida demonstram a falha **neste build local**; não são evidência de exploração em produção.

## Divergências e riscos

| Gravidade | Evidência | Impacto potencial | Recomendação |
| --- | --- | --- | --- |
| Crítica | `EventController::update`, `destroy`, `restore` e `deleteEvent` não comparam o proprietário; probe confirmou edição, troca de `user_creator_id`, exclusão e restauração por usuário alheio. | Alteração e remoção de eventos de terceiros, perda de integridade de propriedade. | Bloquear operações por política de recurso no backend; impedir troca de proprietário por `PUT`; testar `403` e estado inalterado para não proprietário. |
| Alta | `EventController::payEvent` marca `payment_confirmed=true` por requisição do próprio convidado; `show` calcula `is_paid` pela existência de **qualquer** convidado pago. Probe confirmou que outro convidado passou a ver `is_paid=true`. | Estado de pagamento enganoso e liberação incorreta de ações caso o cliente confie nesse campo. | Definir o significado de cobrança; separar estado individual; confirmar pagamento somente por evento confiável de provedor ou fluxo aprovado; testar por usuário. |
| Alta | `EventController::show` retorna endereço a usuário autenticado alheio; `upload`/`getImage` exigem apenas token. Probe confirmou leitura e upload sem posse. | Exposição de localização e alteração/leitura de imagens fora da política desejada. | Definir visibilidade e divulgação do endereço; aplicar autorização por recurso a detalhe, upload e imagem. |
| Alta | `routes/api.php` expõe mutações sem middleware de autorização; `EventController::storeFillEvents` insere dados estáticos com IDs fixos e endereços reais no código. Não foi chamado no laboratório. | Dados inconsistentes e exposição de dados versionados se a rota for acionada. | Desativar/remover a rota de preenchimento após análise; retirar dados reais do código em trabalho específico. |
| Média | `GuestController::store` não checa lotação, duplicidade ou política de participação; inspeção estática. | Inscrições duplicadas ou acima do limite, conforme regras ainda não definidas. | Definir política e adicionar validação e testes transacionais. |

O frontend também transporta JWT na URL da imagem e configura `localhost` como URL de API para produção; esses riscos e a conexão navegador/API estão em `ViniciusRio/Rangulos`, documento `docs/research/stage02-frontend-validation.md`. Nenhuma alteração de aplicação ou migração foi feita nesta etapa.

## Próximas decisões

Corrigir autorização de recursos e integridade de pagamento antes de expor a API fora do laboratório; formalizar política de visibilidade, participação, localização e cobrança. A comparação de estratégias está em [backend-recovery-options.md](backend-recovery-options.md). Nenhuma estratégia de reescrita foi aprovada por esta auditoria.
