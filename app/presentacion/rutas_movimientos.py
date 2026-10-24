from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.negocio.errores import ReglaNegocioError
from app.negocio.novedad_servicio import NovedadServicio
from app.negocio.registro_servicio import RegistroServicio
from app.presentacion.seguridad import login_requerido, operador_actual

bp = Blueprint("movimientos", __name__)


@bp.route("/entrada", methods=["GET", "POST"])
@login_requerido
def entrada():
    datos = comprobante = None
    placa = request.form.get("placa", "")
    if request.method == "POST":
        servicio = RegistroServicio()
        try:
            if request.form.get("accion") == "confirmar":
                comprobante = servicio.registrar_entrada(placa, operador_actual())
                flash("Entrada registrada", "success")
            else:
                datos = servicio.validar_entrada(placa)
        except ReglaNegocioError as e:
            flash(str(e), "danger")
    return render_template("entrada.html", placa=placa, datos=datos, comprobante=comprobante)


@bp.route("/salida", methods=["GET", "POST"])
@login_requerido
def salida():
    datos = comprobante = None
    placa = request.form.get("placa", "")
    if request.method == "POST":
        servicio = RegistroServicio()
        try:
            if request.form.get("accion") == "confirmar":
                comprobante = servicio.registrar_salida(placa, operador_actual())
                flash("Salida registrada", "success")
            else:
                datos = servicio.resumen_salida(placa)
        except ReglaNegocioError as e:
            flash(str(e), "danger")
    return render_template("salida.html", placa=placa, datos=datos, comprobante=comprobante)


@bp.route("/novedad", methods=["GET", "POST"])
@login_requerido
def novedad():
    placa = request.values.get("placa", "")
    if request.method == "POST":
        try:
            NovedadServicio().registrar_novedad(placa, request.form.get("descripcion"), operador_actual())
        except ReglaNegocioError as e:
            flash(str(e), "danger")
        else:
            flash("Novedad registrada", "success")
            return redirect(url_for("movimientos.novedad"))
    return render_template("novedad.html", placa=placa)
