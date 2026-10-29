import os
import re
import sqlite3
import string
from urllib.parse import urlparse



from flask import Flask, g, jsonify, redirect, render_template, request


ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase
BASE = len(ALPHABET)  # 62
OFFSET = 100_000  # evita códigos muito curtos/óbvios no começo
ALIAS_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
RESERVED = {"api", "static"}
MAX_URL_LEN = 2048


def encode(n: int) -> str:
    """Converte um inteiro para base62."""
    if n == 0:
        return ALPHABET[0]
    out = []
    while n:
        n, r = divmod(n, BASE)
        out.append(ALPHABET[r])
    return "".join(reversed(out))


def valid_url(url: str) -> bool:
    if not url or len(url) > MAX_URL_LEN:
        return False
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def create_app(db_path: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config["DB_PATH"] = db_path or os.environ.get("DB_PATH", "links.db")

    def get_db() -> sqlite3.Connection:
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DB_PATH"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_exc):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    with sqlite3.connect(app.config["DB_PATH"]) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS links (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                code       TEXT UNIQUE,
                url        TEXT NOT NULL,
                clicks     INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/shorten")
    def shorten():
        data = request.get_json(silent=True) or {}
        url = (data.get("url") or "").strip()
        alias = (data.get("alias") or "").strip()

        if not valid_url(url):
            return jsonify(error="URL inválida. Use http:// ou https://"), 400

        db = get_db()

        if alias:
            if not ALIAS_RE.match(alias) or alias.lower() in RESERVED:
                return jsonify(error="Alias inválido (3-32 caracteres: letras, números, - e _)"), 400
            try:
                db.execute("INSERT INTO links (code, url) VALUES (?, ?)", (alias, url))
                db.commit()
            except sqlite3.IntegrityError:
                return jsonify(error="Esse alias já está em uso"), 409
            code = alias
        else:
            cur = db.execute("INSERT INTO links (url) VALUES (?)", (url,))
            row_id = cur.lastrowid
            n = row_id + OFFSET
            while True:
                code = encode(n)
                try:
                    db.execute("UPDATE links SET code = ? WHERE id = ?", (code, row_id))
                    db.commit()
                    break
                except sqlite3.IntegrityError:
                    # colidiu com um alias personalizado; tenta o próximo
                    n += 1

        return jsonify(code=code, short_url=request.host_url + code, url=url), 201

    @app.get("/api/stats/<code>")
    def stats(code):
        row = get_db().execute(
            "SELECT code, url, clicks, created_at FROM links WHERE code = ?", (code,)
        ).fetchone()
        if row is None:
            return jsonify(error="Link não encontrado"), 404
        return jsonify(dict(row))

    @app.get("/<code>")
    def follow(code):
        db = get_db()
        row = db.execute("SELECT url FROM links WHERE code = ?", (code,)).fetchone()
        if row is None:
            return jsonify(error="Link não encontrado"), 404
        db.execute("UPDATE links SET clicks = clicks + 1 WHERE code = ?", (code,))
        db.commit()
        # 302 (e não 301) para o navegador não cachear e todo clique ser contado
        return redirect(row["url"], code=302)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
