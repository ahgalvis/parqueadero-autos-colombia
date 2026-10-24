"""Conexión a MySQL: una por petición, guardada en flask.g."""
import pymysql
from flask import current_app, g


def obtener():
    if "db" not in g:
        cfg = current_app.config
        g.db = pymysql.connect(
            host=cfg["DB_HOST"],
            port=cfg["DB_PORT"],
            user=cfg["DB_USER"],
            password=cfg["DB_PASSWORD"],
            database=cfg["DB_NAME"],
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
    return g.db


def cerrar(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def iniciar(app):
    app.teardown_appcontext(cerrar)
