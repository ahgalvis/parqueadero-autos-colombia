"""Pantallas de gestión de usuarios, vehículos y mensualidades (HU-08 a HU-12)."""
from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.negocio.errores import ReglaNegocioError
from app.negocio.pago_servicio import PagoServicio
from app.negocio.usuario_servicio import UsuarioServicio
from app.presentacion.seguridad import admin_requerido, login_requerido

bp = Blueprint("usuarios", __name__)


def _mensualidad_por_defecto():
    hoy = date.today()
    return {"fecha_inicio": hoy.isoformat(), "fecha_fin": (hoy + timedelta(days=30)).isoformat(), "valor": ""}


@bp.route("/usuarios")
@login_requerido
def lista():
    texto = request.args.get("q", "")
    return render_template("usuarios.html", q=texto, usuarios=UsuarioServicio().listar(texto))


@bp.route("/usuarios/nuevo", methods=["GET", "POST"])
@admin_requerido
def nuevo():
    if request.method == "POST":
        f = request.form
        try:
            usuario = UsuarioServicio().registrar(f.get("documento"), f.get("nombre"), f.get("telefono"),
                                                  f.get("correo"))
        except ReglaNegocioError as e:
            flash(str(e), "danger")
        else:
            flash("Usuario registrado. Ahora agrega su vehículo.", "success")
            return redirect(url_for("usuarios.detalle", id_usuario=usuario.id_usuario))
    return render_template("usuario_form.html", usuario=None, datos=request.form)


@bp.route("/usuarios/<int:id_usuario>")
@login_requerido
def detalle(id_usuario):
    try:
        usuario, vehiculos = UsuarioServicio().detalle(id_usuario)
    except ReglaNegocioError as e:
        flash(str(e), "danger")
        return redirect(url_for("usuarios.lista"))
    return render_template("usuario_detalle.html", usuario=usuario, vehiculos=vehiculos, hoy=date.today(),
                           cuenta=PagoServicio().estado_cuenta(id_usuario))


@bp.route("/usuarios/<int:id_usuario>/editar", methods=["GET", "POST"])
@admin_requerido
def editar(id_usuario):
    servicio = UsuarioServicio()
    try:
        usuario = servicio.obtener(id_usuario)
        if request.method == "POST":
            f = request.form
            servicio.actualizar(id_usuario, f.get("nombre"), f.get("telefono"), f.get("correo"))
            flash("Datos actualizados", "success")
            return redirect(url_for("usuarios.detalle", id_usuario=id_usuario))
    except ReglaNegocioError as e:
        flash(str(e), "danger")
        if request.method == "GET":
            return redirect(url_for("usuarios.lista"))
    datos = request.form if request.method == "POST" else usuario.__dict__
    return render_template("usuario_form.html", usuario=usuario, datos=datos)


@bp.route("/usuarios/<int:id_usuario>/estado", methods=["POST"])
@admin_requerido
def estado(id_usuario):
    activo = request.form.get("activo") == "1"
    try:
        UsuarioServicio().cambiar_estado(id_usuario, activo)
    except ReglaNegocioError as e:
        flash(str(e), "danger")
    else:
        flash("Usuario activado" if activo else "Usuario inactivado", "success")
    return redirect(url_for("usuarios.detalle", id_usuario=id_usuario))


@bp.route("/usuarios/<int:id_usuario>/vehiculos/nuevo", methods=["GET", "POST"])
@admin_requerido
def nuevo_vehiculo(id_usuario):
    servicio = UsuarioServicio()
    try:
        usuario = servicio.obtener(id_usuario)
    except ReglaNegocioError as e:
        flash(str(e), "danger")
        return redirect(url_for("usuarios.lista"))
    if request.method == "POST":
        f = request.form
        try:
            servicio.registrar_vehiculo(id_usuario, f.get("placa"), f.get("tipo"), f.get("marca"), f.get("color"),
                                        f.get("fecha_inicio"), f.get("fecha_fin"), f.get("valor"))
        except ReglaNegocioError as e:
            flash(str(e), "danger")
        else:
            flash("Vehículo y mensualidad registrados", "success")
            return redirect(url_for("usuarios.detalle", id_usuario=id_usuario))
    datos = request.form if request.method == "POST" else _mensualidad_por_defecto()
    return render_template("vehiculo_form.html", usuario=usuario, datos=datos)


@bp.route("/vehiculos/<int:id_vehiculo>/editar", methods=["GET", "POST"])
@admin_requerido
def editar_vehiculo(id_vehiculo):
    servicio = UsuarioServicio()
    try:
        vehiculo = servicio.obtener_vehiculo(id_vehiculo)
        if request.method == "POST":
            servicio.actualizar_vehiculo(id_vehiculo, request.form.get("marca"), request.form.get("color"))
            flash("Vehículo actualizado", "success")
            return redirect(url_for("usuarios.detalle", id_usuario=vehiculo.id_usuario))
    except ReglaNegocioError as e:
        flash(str(e), "danger")
        return redirect(url_for("usuarios.lista"))
    return render_template("vehiculo_editar.html", vehiculo=vehiculo, mensualidad=_mensualidad_por_defecto())


@bp.route("/vehiculos/<int:id_vehiculo>/estado", methods=["POST"])
@admin_requerido
def estado_vehiculo(id_vehiculo):
    servicio = UsuarioServicio()
    activo = request.form.get("activo") == "1"
    try:
        vehiculo = servicio.obtener_vehiculo(id_vehiculo)
    except ReglaNegocioError as e:
        flash(str(e), "danger")
        return redirect(url_for("usuarios.lista"))
    try:
        servicio.cambiar_estado_vehiculo(id_vehiculo, activo)
    except ReglaNegocioError as e:
        flash(str(e), "danger")
    else:
        flash("Vehículo reactivado" if activo else "Vehículo retirado", "success")
    return redirect(url_for("usuarios.detalle", id_usuario=vehiculo.id_usuario))


@bp.route("/vehiculos/<int:id_vehiculo>/mensualidad", methods=["POST"])
@admin_requerido
def mensualidad(id_vehiculo):
    servicio = UsuarioServicio()
    f = request.form
    try:
        vehiculo = servicio.obtener_vehiculo(id_vehiculo)
        servicio.renovar_mensualidad(id_vehiculo, f.get("fecha_inicio"), f.get("fecha_fin"), f.get("valor"))
    except ReglaNegocioError as e:
        flash(str(e), "danger")
        return redirect(url_for("usuarios.editar_vehiculo", id_vehiculo=id_vehiculo))
    flash("Mensualidad registrada", "success")
    return redirect(url_for("usuarios.detalle", id_usuario=vehiculo.id_usuario))
