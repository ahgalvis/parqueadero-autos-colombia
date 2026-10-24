from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.negocio.autenticacion_servicio import AutenticacionServicio
from app.negocio.errores import ReglaNegocioError

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            operador = AutenticacionServicio().iniciar_sesion(request.form["usuario"], request.form["clave"])
        except ReglaNegocioError as e:
            flash(str(e), "danger")
        else:
            session.clear()
            session["id_operador"] = operador.id_operador
            return redirect(url_for("consultas.panel"))
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
