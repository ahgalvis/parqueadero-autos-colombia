"""Pantallas de gestión de pagos (iteración 3, HU-17 a HU-23)."""
from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.modelo.entidades import MedioPago
from app.negocio.errores import ReglaNegocioError
from app.negocio.pago_servicio import SIGUIENTE, PagoServicio
from app.presentacion.seguridad import admin_requerido, login_requerido, operador_actual

bp = Blueprint("pagos", __name__)


@bp.route("/pagos")
@login_requerido
def lista():
    hoy = date.today().isoformat()
    filtros = {"desde": request.args.get("desde", hoy), "hasta": request.args.get("hasta", hoy),
               "texto": request.args.get("texto", ""), "medio": request.args.get("medio", "")}
    return render_template("pagos.html", filtros=filtros, medios=list(MedioPago),
                           resultado=PagoServicio().listar(**filtros))


@bp.route("/pagos/nuevo", methods=["GET", "POST"])
@login_requerido
def nuevo():
    servicio = PagoServicio()
    placa = request.values.get("placa", "")
    cuenta = None
    if request.method == "POST" and request.form.get("accion") == "pagar":
        f = request.form
        try:
            pago = servicio.registrar_pago(placa, f.get("mensualidad"), f.get("medio"), f.get("referencia"),
                                           f.get("valor_recibido"), operador_actual())
        except ReglaNegocioError as e:
            flash(str(e), "danger")
        else:
            flash(f"Pago registrado. Recibo {pago.numero_recibo}", "success")
            return redirect(url_for("pagos.recibo", id_pago=pago.id_pago))
    if placa:
        try:
            cuenta = servicio.cuenta_de_placa(placa)
        except ReglaNegocioError as e:
            if request.form.get("accion") != "pagar":
                flash(str(e), "danger")
    return render_template("pago_form.html", placa=placa, cuenta=cuenta, medios=list(MedioPago),
                           siguiente=SIGUIENTE, datos=request.form)


@bp.route("/pagos/<int:id_pago>")
@login_requerido
def recibo(id_pago):
    try:
        datos = PagoServicio().recibo(id_pago)
    except ReglaNegocioError as e:
        flash(str(e), "danger")
        return redirect(url_for("pagos.lista"))
    return render_template("recibo.html", r=datos)


@bp.route("/pagos/<int:id_pago>/anular", methods=["GET", "POST"])
@admin_requerido
def anular(id_pago):
    servicio = PagoServicio()
    if request.method == "POST":
        try:
            pago = servicio.anular(id_pago, request.form.get("motivo"), operador_actual())
        except ReglaNegocioError as e:
            flash(str(e), "danger")
        else:
            flash(f"Pago {pago.numero_recibo} anulado. La mensualidad quedó pendiente de pago", "success")
            return redirect(url_for("pagos.recibo", id_pago=id_pago))
    try:
        datos = servicio.recibo(id_pago)
    except ReglaNegocioError as e:
        flash(str(e), "danger")
        return redirect(url_for("pagos.lista"))
    return render_template("pago_anular.html", r=datos, motivo=request.form.get("motivo", ""))


@bp.route("/pagos/pendientes")
@login_requerido
def pendientes():
    texto = request.args.get("q", "")
    return render_template("pendientes.html", q=texto, resultado=PagoServicio().pendientes(texto))
