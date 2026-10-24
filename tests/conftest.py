"""Las pruebas recrean la base de datos desde bd/autos_colombia.sql (usa las mismas variables DB_* de la app)."""
from pathlib import Path

import pymysql
import pytest

from app import create_app
from app.config import Config

SCRIPT = Path(__file__).resolve().parent.parent / "bd" / "autos_colombia.sql"


def recrear_bd():
    sentencias = [s.strip() for s in SCRIPT.read_text(encoding="utf-8").split(";") if s.strip()]
    con = pymysql.connect(host=Config.DB_HOST, port=Config.DB_PORT, user=Config.DB_USER,
                          password=Config.DB_PASSWORD, autocommit=True)
    with con.cursor() as c:
        for s in sentencias:
            lineas = [l for l in s.splitlines() if not l.strip().startswith("--")]
            if "".join(lineas).strip():
                c.execute("\n".join(lineas))
    con.close()


@pytest.fixture
def cliente():
    recrear_bd()
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def entrar(cliente, usuario="operador", clave="operador123"):
    return cliente.post("/login", data={"usuario": usuario, "clave": clave}, follow_redirects=True)
