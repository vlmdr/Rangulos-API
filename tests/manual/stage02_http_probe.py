"""Manual local-only probe. Creates synthetic records in an isolated lab API."""

import base64
import json
import secrets
import urllib.error
import urllib.request


BASE = "http://127.0.0.1:8081/api"
RUN = secrets.token_hex(5)


def call(method, path, token=None, data=None, upload=False):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    if upload:
        boundary = "rangulos-lab-boundary"
        image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/lXcAAAAASUVORK5CYII="
        )
        data = (
            ("--" + boundary + "\r\nContent-Disposition: form-data; name=\"file\"; "
             "filename=\"synthetic.png\"\r\nContent-Type: image/png\r\n\r\n").encode()
            + image + ("\r\n--" + boundary + "--\r\n").encode()
        )
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
    elif data is not None:
        data = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(request, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        body = response.read()
        try:
            body = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            body = None
        return response.status, body, response.headers.get("Content-Type", "")


def expect(label, actual, expected):
    assert actual == expected, (label, actual, expected)
    print(label + ": " + str(actual))


def account(role):
    email = role + "-" + RUN + "@example.invalid"
    expect("register " + role, call("POST", "/register", data={
        "name": "Synthetic " + role, "email": email, "password": "lab-only-pass"
    })[0], 200)
    status, body, _ = call("POST", "/login", data={
        "email": email, "password": "lab-only-pass"
    })
    expect("login " + role, status, 200)
    return body["token"]


owner, outsider, guest = (account(role) for role in ("owner", "outsider", "guest"))
expect("anonymous events", call("GET", "/events")[0], 401)
status, body, _ = call("POST", "/events", owner, {
    "title": "Synthetic event " + RUN, "about": "Lab only",
    "address": "Fictional location", "price": 10, "max_guests": 3,
    "start_date": "2030-01-01 10:00:00", "end_date": "2030-01-02 10:00:00"
})
expect("create event", status, 200)
event = body["id"]
detail = "/event/" + str(event)
expect("anonymous event detail", call("GET", detail)[0], 401)
status, body, _ = call("GET", detail, outsider)
expect("outsider reads event", status, 200)
expect("outsider sees address", body["address"], "Fictional location")
expect("outsider is not owner", body["is_owner"], False)
expect("outsider edits event", call("PUT", detail, outsider, {
    "title": "Changed by outsider"
})[0], 200)
status, body, _ = call("GET", detail, outsider)
expect("title changed", body["title"], "Changed by outsider")
expect("outsider became owner", body["is_owner"], True)
expect("original owner lost ownership", call("GET", detail, owner)[1]["is_owner"], False)
expect("join guest", call("POST", "/guest/" + str(event), guest)[0], 200)
expect("join outsider", call("POST", "/guest/" + str(event), outsider)[0], 200)
expect("guest unpaid before payment", call("GET", detail, guest)[1]["is_paid"], False)
expect("guest simulates payment", call("POST", "/event/pay", guest, {"id": event})[1], True)
expect("other guest shown paid", call("GET", detail, outsider)[1]["is_paid"], True)
expect("non-owner uploads", call("POST", detail + "/upload", guest, upload=True)[0], 200)
status, _, content_type = call("GET", detail + "/image", outsider)
expect("other user reads image", status, 200)
expect("image MIME", content_type.startswith("image/"), True)
expect("guest leaves event", call("DELETE", "/guest/" + str(event), guest)[0], 200)

# Keep ownership with the creator while testing destructive operations.
status, body, _ = call("POST", "/events", owner, {
    "title": "Synthetic deletion test " + RUN, "about": "Lab only",
    "address": "Fictional location", "price": 0, "max_guests": 2,
    "start_date": "2030-01-01 10:00:00", "end_date": "2030-01-02 10:00:00"
})
expect("create second event", status, 200)
event = body["id"]
detail = "/event/" + str(event)
expect("outsider remains non-owner", call("GET", detail, outsider)[1]["is_owner"], False)
expect("outsider soft deletes", call("DELETE", detail, outsider)[0], 200)
expect("soft delete recorded", bool(call("GET", detail, owner)[1]["deleted_at"]), True)
expect("outsider restores", call("POST", detail + "/restore", outsider)[0], 200)
expect("restore recorded", call("GET", detail, owner)[1]["deleted_at"], None)
expect("outsider still non-owner", call("GET", detail, outsider)[1]["is_owner"], False)
expect("outsider force deletes", call("DELETE", detail + "/delete", outsider)[0], 200)
expect("event absent from owner listing", any(
    row["id"] == event for row in call("GET", "/events/my", owner)[1]
), False)
