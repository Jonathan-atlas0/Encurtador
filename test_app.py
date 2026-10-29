import pytest

from app import OFFSET, create_app, encode, valid_url


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app.test_client()


def test_encode_base62():
    assert encode(0) == "0"
    assert encode(61) == "Z"
    assert encode(62) == "10"


@pytest.mark.parametrize(
    "url,ok",
    [
        ("https://exemplo.com", True),
        ("http://exemplo.com/a?b=1", True),
        ("javascript:alert(1)", False),
        ("ftp://exemplo.com", False),
        ("exemplo.com", False),
        ("", False),
        ("https://" + "a" * 3000, False),
    ],
)
def test_valid_url(url, ok):
    assert valid_url(url) is ok


def test_shorten_and_redirect(client):
    r = client.post("/api/shorten", json={"url": "https://exemplo.com/longo"})
    assert r.status_code == 201
    code = r.get_json()["code"]

    r = client.get(f"/{code}")
    assert r.status_code == 302
    assert r.headers["Location"] == "https://exemplo.com/longo"


def test_codes_are_unique(client):
    codes = {
        client.post(
            "/api/shorten", json={"url": f"https://exemplo.com/{i}"}
        ).get_json()["code"]
        for i in range(20)
    }
    assert len(codes) == 20


def test_custom_alias(client):
    r = client.post(
        "/api/shorten", json={"url": "https://exemplo.com", "alias": "meu-link"}
    )
    assert r.status_code == 201
    assert r.get_json()["code"] == "meu-link"
    assert client.get("/meu-link").status_code == 302


def test_alias_conflict(client):
    client.post("/api/shorten", json={"url": "https://a.com", "alias": "teste"})
    r = client.post("/api/shorten", json={"url": "https://b.com", "alias": "teste"})
    assert r.status_code == 409


def test_invalid_alias_and_reserved(client):
    assert (
        client.post(
            "/api/shorten", json={"url": "https://a.com", "alias": "a b"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/shorten", json={"url": "https://a.com", "alias": "api"}
        ).status_code
        == 400
    )


def test_invalid_url_rejected(client):
    r = client.post("/api/shorten", json={"url": "javascript:alert(1)"})
    assert r.status_code == 400


def test_auto_code_skips_existing_alias(client):
    # reserva exatamente o código que o próximo ID geraria
    reserved = encode(1 + OFFSET)
    client.post("/api/shorten", json={"url": "https://a.com", "alias": reserved})
    r = client.post("/api/shorten", json={"url": "https://b.com"})
    assert r.status_code == 201
    assert r.get_json()["code"] != reserved


def test_click_counter(client):
    code = client.post("/api/shorten", json={"url": "https://exemplo.com"}).get_json()[
        "code"
    ]
    for _ in range(3):
        client.get(f"/{code}")
    stats = client.get(f"/api/stats/{code}").get_json()
    assert stats["clicks"] == 3


def test_not_found(client):
    assert client.get("/naoexiste").status_code == 404
    assert client.get("/api/stats/naoexiste").status_code == 404
