"""
Lightweight SQLite data-access layer.

We use Python's built-in sqlite3 module directly (rather than an ORM) to keep
the stack simple and easy for a student to explain. All queries are
parameterized to prevent SQL injection. Because every query here is plain
ANSI-ish SQL, swapping SQLite for MySQL/PostgreSQL later mainly means
swapping this module's connection function and a handful of syntax quirks
(e.g. AUTOINCREMENT -> SERIAL) -- the rest of the app talks to this module,
not to SQLite directly.
"""
import sqlite3
import os
from flask import g, current_app

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "database", "schema.sql")


def get_db():
    """Return a request-scoped SQLite connection."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE_PATH"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app):
    """Create tables from schema.sql. Called explicitly (not on every boot)."""
    with app.app_context():
        db = get_db()
        with open(SCHEMA_PATH, "r") as f:
            db.executescript(f.read())
        db.commit()


def query(sql, args=(), one=False):
    db = get_db()
    cur = db.execute(sql, args)
    rows = cur.fetchall()
    cur.close()
    if one:
        return rows[0] if rows else None
    return rows


def execute(sql, args=()):
    """Run an INSERT/UPDATE/DELETE and commit. Returns the new row id."""
    db = get_db()
    cur = db.execute(sql, args)
    db.commit()
    new_id = cur.lastrowid
    cur.close()
    return new_id


def init_app(app):
    app.teardown_appcontext(close_db)
