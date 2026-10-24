from flask import Blueprint, redirect, render_template, request, url_for

from app.negocio.consulta_servicio import ConsultaServicio
from app.presentacion.seguridad import admin_requerido, login_requerido

bp = Blueprint("consultas", __name__)


@bp.route("/")
def inicio():
    return redirect(url_for("consultas.panel"))


@bp.route("/panel")
@login_requerido
def panel():
    return render_template("panel.html", celdas=ConsultaServicio().resumen_celdas())


@bp.route("/vehiculos")
@login_requerido
def vehiculos():
    placa = request.args.get("placa", "")
    return render_template("vehiculos.html", placa=placa, vehiculos=ConsultaServicio().vehiculos_dentro(placa))


@bp.route("/historial")
@admin_requerido
def historial():
    filtros = {k: request.args.get(k, "") for k in ("placa", "desde", "hasta")}
    return render_template("historial.html", filtros=filtros, movimientos=ConsultaServicio().historial(**filtros))
