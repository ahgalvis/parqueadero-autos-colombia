"""Pantallas de cuentas del personal (HU-13). Solo administrador."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.negocio.errores import ReglaNegocioError
from app.negocio.personal_servicio import PersonalServicio
from app.presentacion.seguridad import admin_requerido, operador_actual

bp = Blueprint("personal", __name__)


@bp.route("/personal")
@admin_requerido
def lista():
    return render_template("personal.html", cuentas=PersonalServicio().listar())


@bp.route("/personal/nuevo", methods=["GET", "POST"])
@admin_requerido
def nuevo():
    if request.method == "POST":
        f = request.form
        try:
            PersonalServicio().registrar(f.get("nombre"), f.get("usuario"), f.get("clave"), f.get("rol"))
        except ReglaNegocioError as e:
            flash(str(e), "danger")
        else:
            flash("Cuenta creada", "success")
            return redirect(url_for("personal.lista"))
    return render_template("personal_form.html", cuenta=None, datos=request.form)


@bp.route("/personal/<int:id_operador>/editar", methods=["GET", "POST"])
@admin_requerido
def editar(id_operador):
    servicio = PersonalServicio()
    try:
        cuenta = servicio.obtener(id_operador)
        if request.method == "POST":
            f = request.form
            servicio.actualizar(id_operador, f.get("nombre"), f.get("rol"), f.get("activo") == "1",
                                f.get("clave"), operador_actual())
            flash("Cuenta actualizada", "success")
            return redirect(url_for("personal.lista"))
    except ReglaNegocioError as e:
        flash(str(e), "danger")
        if request.method == "GET":
            return redirect(url_for("personal.lista"))
    datos = request.form if request.method == "POST" else {
        "nombre": cuenta.nombre, "rol": cuenta.rol.value, "activo": "1" if cuenta.activo else "0"}
    return render_template("personal_form.html", cuenta=cuenta, datos=datos)
