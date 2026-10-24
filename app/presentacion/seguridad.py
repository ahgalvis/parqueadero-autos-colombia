from functools import wraps

from flask import flash, g, redirect, session, url_for

from app.datos.repositorios import OperadorRepositorio


def operador_actual():
    if "operador" not in g:
        id_operador = session.get("id_operador")
        g.operador = OperadorRepositorio().buscar_por_id(id_operador) if id_operador else None
    return g.operador


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if not operador_actual():
            return redirect(url_for("auth.login"))
        return vista(*args, **kwargs)
    return envoltura


def admin_requerido(vista):
    @wraps(vista)
    @login_requerido
    def envoltura(*args, **kwargs):
        if not operador_actual().es_administrador():
            flash("Solo el administrador puede ver esta sección", "danger")
            return redirect(url_for("consultas.panel"))
        return vista(*args, **kwargs)
    return envoltura
