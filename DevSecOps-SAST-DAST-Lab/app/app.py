"""Intentionally vulnerable training application. Local lab use only."""
import sqlite3
from flask import Flask, render_template_string, request

app = Flask(__name__)
DB_PATH = "/tmp/devsecops-lab.db"


def get_db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_db():
    with get_db() as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS products "
            "(id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
        )
        connection.execute("DELETE FROM products")
        connection.executemany(
            "INSERT INTO products (name) VALUES (?)",
            [("keyboard",), ("monitor",), ("laptop",)],
        )


@app.get("/")
def index():
    return """
    <h1>DevSecOps Training Store</h1>
    <p>Intentionally vulnerable endpoints for local security training.</p>
    <ul>
      <li><a href="/search?q=keyboard">Search products</a></li>
      <li><a href="/lookup?name=keyboard">Look up a product</a></li>
      <li><a href="/health">Health check</a></li>
    </ul>
    """


@app.get("/health")
def health():
    return {"status": "ok"}, 200


@app.get("/search")
def search():
    # TRAINING VULNERABILITY: untrusted input is inserted into an HTML template.
    query = request.args.get("q", "")
    return render_template_string(
        "<h2>Search results for: " + query + "</h2>"
        "<p>This endpoint is intentionally vulnerable to reflected XSS.</p>"
    )


@app.get("/lookup")
def lookup():
    # TRAINING VULNERABILITY: SQL is assembled using untrusted string input.
    name = request.args.get("name", "")
    with get_db() as connection:
        rows = connection.execute(
            f"SELECT id, name FROM products WHERE name = '{name}'"
        ).fetchall()
    return {"results": [dict(row) for row in rows]}


if __name__ == "__main__":
    initialize_db()
    app.run(host="0.0.0.0", port=5000, debug=False)
