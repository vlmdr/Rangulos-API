# Alternativas para recuperar e modernizar a API

Base de decisão: [reprodução e contratos observados](stage02-api-validation.md). O experimento demonstra que o legado executa em laboratório com PHP 7.4 e Composer 1. Ele **não** demonstra aptidão para produção nem determina uma reescrita.

| Alternativa | Benefício | Custo e risco | Evidência necessária antes da escolha |
| --- | --- | --- | --- |
| A. Conter o Laravel 5.5 e corrigir os riscos imediatos | Menor mudança inicial; preserva os contratos que o frontend já usa. A reprodução local foi possível. | Runtime e dependências antigas; Composer 1 já obsoleto; manutenção de segurança e operação é difícil. | Testes de autorização e pagamento, cobertura de fluxos reais, inventário de dados e plano de exposição controlada. Solução transitória, se adotada. |
| B. Evoluir o backend Laravel em passos | Preserva boa parte do domínio e permite revisar contratos progressivamente. | Várias mudanças de PHP, dependências, autenticação e APIs do framework; cada salto exige testes. | Matriz de compatibilidade por versão, baseline de testes de contrato, prova de migração em branch isolada e plano de rollback. |
| C. Substituir seletivamente a API | Permite desenhar autorização e pagamento de forma explícita e remover pontos frágeis. | Maior risco de divergência comportamental e migração de dados; trabalho de operação simultânea. | Especificação validada de domínio, contratos HTTP completos, testes de equivalência e estratégia de migração. |

As [notas de versão e política de suporte do Laravel](https://laravel.com/docs/13.x/releases) e os [guias oficiais de upgrade](https://laravel.com/docs/12.x/upgrade) mostram que saltos de versão envolvem requisitos de PHP e mudanças de compatibilidade. A [documentação de autorização do Laravel 5.5](https://laravel.com/docs/5.5/authorization) já oferece políticas por recurso; a falta de checagem observada é do aplicativo, não uma limitação que exija reescrita. Os detalhes exatos de versões de destino devem ser reavaliados quando houver decisão, pois o suporte muda com o tempo.

**Recomendação para a próxima etapa:** primeiro especificar quem pode ler e modificar cada recurso, corrigir e testar os defeitos reproduzidos, e estabelecer contratos e dados de migração. Em seguida, experimentar B e C em ramos separados com o mesmo conjunto de testes; comparar esforço, segurança, custo operacional e preservação de dados. A decisão fica pendente dessas evidências e da política de produto.
