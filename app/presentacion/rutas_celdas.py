"""Pantallas de gestión de celdas (HU-14 a HU-16)."""
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.negocio.celda_servicio import CeldaServicio
from app.negocio.errores import ReglaNegocioError
from app.presentacion.seguridad import admin_requerido, login_requerido

bp = Blueprint("celdas", __name__)


@bp.route("/celdas")
@login_requerido
def mapa():
    filtros = {k: request.args.get(k, "") for k in ("tipo", "estado")}
    servicio = CeldaServicio()
    return render_template("celdas.html", filtros=filtros, celdas=servicio.mapa(**filtros),
                           resumen=servicio.resumen())


@bp.route("/celdas/nueva", methods=["GET", "POST"])
@admin_requerido
def nueva():
    if request.method == "POST":
        try:
            celda = CeldaServicio().registrar(request.form.get("codigo"), request.form.get("tipo"))
        except ReglaNegocioError as e:
            flash(str(e), "danger")
        else:
            flash(f"Celda {celda.codigo} creada", "success")
            return redirect(url_for("celdas.mapa"))
    return render_template("celda_form.html", celda=None, datos=request.form)


@bp.route("/celdas/<int:id_celda>/editar", methods=["GET", "POST"])
@admin_requerido
def editar(id_celda):
    servicio = CeldaServicio()
    try:
        celda = servicio.obtener(id_celda)
        if request.method == "POST":
            servicio.modificar(id_celda, request.form.get("codigo"), request.form.get("tipo"))
            flash("Celda actualizada", "success")
            return redirect(url_for("celdas.mapa"))
    except ReglaNegocioError as e:
        flash(str(e), "danger")
        if request.method == "GET":
            return redirect(url_for("celdas.mapa"))
    datos = request.form if request.method == "POST" else {"codigo": celda.codigo, "tipo": celda.tipo.value}
    return render_template("celda_form.html", celda=celda, datos=datos)


@bp.route("/celdas/<int:id_celda>/inhabilitar", methods=["POST"])
@admin_requerido
def inhabilitar(id_celda):
    try:
        celda = CeldaServicio().inhabilitar(id_celda, request.form.get("motivo"))
    except ReglaNegocioError as e:
        flash(str(e), "danger")
        return redirect(url_for("celdas.editar", id_celda=id_celda))
    flash(f"Celda {celda.codigo} inhabilitada", "success")
    return redirect(url_for("celdas.mapa"))


@bp.route("/celdas/<int:id_celda>/habilitar", methods=["POST"])
@admin_requerido
def habilitar(id_celda):
    try:
        celda = CeldaServicio().habilitar(id_celda)
    except ReglaNegocioError as e:
        flash(str(e), "danger")
    else:
        flash(f"Celda {celda.codigo} habilitada", "success")
    return redirect(url_for("celdas.mapa"))
