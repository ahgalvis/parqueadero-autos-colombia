"""Configuración leída de variables de entorno, con valores por defecto para desarrollo local."""
import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "cambiar-esta-llave-en-produccion")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "autos_colombia")
