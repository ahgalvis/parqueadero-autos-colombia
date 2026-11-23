"""Gestión de usuarios (clientes con mensualidad), sus vehículos y mensualidades (HU-08 a HU-12)."""
from datetime import date
from decimal import Decimal, InvalidOperation

from app.datos import conexion
from app.datos.repositorios import MensualidadRepositorio, UsuarioRepositorio, VehiculoRepositorio
from app.modelo.entidades import (
    PATRON_CORREO, PATRON_DOCUMENTO, PATRON_PLACA, PATRON_TELEFONO, Mensualidad, TipoVehiculo, Usuario, Vehiculo,
)
from app.negocio.errores import ReglaNegocioError
from app.negocio.registro_servicio import normalizar_placa


def _texto(valor, maximo):
    return (valor or "").strip()[:maximo]


def _fecha(valor, nombre):
    try:
        return date.fromisoformat((valor or "").strip())
    except ValueError:
        raise ReglaNegocioError(f"La {nombre} no es válida") from None


class UsuarioServicio:
    def __init__(self):
        self.usuarios = UsuarioRepositorio()
        self.vehiculos = VehiculoRepositorio()
        self.mensualidades = MensualidadRepositorio()

    # ---------- Usuarios ----------
    def listar(self, texto=None):
        return self.usuarios.listar(_texto(texto, 100) or None)

    def obtener(self, id_usuario):
        usuario = self.usuarios.buscar_por_id(id_usuario)
        if not usuario:
            raise ReglaNegocioError("El usuario no existe")
        return usuario

    def detalle(self, id_usuario):
        usuario = self.obtener(id_usuario)
        return usuario, self.vehiculos.de_usuario(id_usuario)

    def _validar_datos(self, nombre, telefono, correo):
        nombre = _texto(nombre, 100)
        telefono = _texto(telefono, 20).replace(" ", "")
        correo = _texto(correo, 100).lower()
        if not nombre:
            raise ReglaNegocioError("El nombre es obligatorio")
        if telefono and not PATRON_TELEFONO.match(telefono):
            raise ReglaNegocioError("El teléfono debe tener entre 7 y 10 dígitos")
        if correo and not PATRON_CORREO.match(correo):
            raise ReglaNegocioError("El correo no tiene un formato válido")
        return nombre, telefono or None, correo or None

    def registrar(self, documento, nombre, telefono=None, correo=None):
        documento = _texto(documento, 20).replace(".", "").replace(" ", "")
        if not PATRON_DOCUMENTO.match(documento):
            raise ReglaNegocioError("El documento debe tener solo números (entre 5 y 15 dígitos)")
        nombre, telefono, correo = self._validar_datos(nombre, telefono, correo)
        if self.usuarios.buscar_por_documento(documento):
            raise ReglaNegocioError("Ya existe un usuario con ese documento")
        usuario = self.usuarios.guardar(Usuario(None, documento, nombre, telefono, correo))
        conexion.obtener().commit()
        return usuario

    def actualizar(self, id_usuario, nombre, telefono=None, correo=None):
        usuario = self.obtener(id_usuario)
        usuario.nombre, usuario.telefono, usuario.correo = self._validar_datos(nombre, telefono, correo)
        self.usuarios.actualizar(usuario)
        conexion.obtener().commit()
        return usuario

    def cambiar_estado(self, id_usuario, activo):
        usuario = self.obtener(id_usuario)
        if not activo and any(v["dentro"] for v in self.vehiculos.de_usuario(id_usuario)):
            raise ReglaNegocioError("No se puede inactivar: el usuario tiene un vehículo dentro del parqueadero")
        usuario.activo = activo
        self.usuarios.actualizar(usuario)
        conexion.obtener().commit()
        return usuario

    # ---------- Vehículos ----------
    def obtener_vehiculo(self, id_vehiculo):
        vehiculo = self.vehiculos.buscar_por_id(id_vehiculo)
        if not vehiculo:
            raise ReglaNegocioError("El vehículo no existe")
        return vehiculo

    def registrar_vehiculo(self, id_usuario, placa, tipo, marca, color, fecha_inicio, fecha_fin, valor):
        usuario = self.obtener(id_usuario)
        if not usuario.activo:
            raise ReglaNegocioError("No se pueden agregar vehículos a un usuario inactivo")
        placa = normalizar_placa(placa)
        try:
            tipo = TipoVehiculo(tipo)
        except ValueError:
            raise ReglaNegocioError("Selecciona el tipo de vehículo") from None
        if not PATRON_PLACA[tipo.value].match(placa):
            formato = "AAA123" if tipo == TipoVehiculo.CARRO else "AAA12A"
            raise ReglaNegocioError(f"La placa no corresponde a un {tipo.value.lower()} (formato {formato})")
        if self.vehiculos.buscar_por_placa(placa):
            raise ReglaNegocioError("La placa ya está registrada")
        mensualidad = self._nueva_mensualidad(fecha_inicio, fecha_fin, valor)
        db = conexion.obtener()
        try:
            vehiculo = self.vehiculos.guardar(
                Vehiculo(None, placa, tipo, _texto(marca, 40) or None, _texto(color, 30) or None, id_usuario))
            mensualidad.id_vehiculo = vehiculo.id_vehiculo
            self.mensualidades.guardar(mensualidad)
            db.commit()
        except Exception:
            db.rollback()
            raise
        return vehiculo

    def actualizar_vehiculo(self, id_vehiculo, marca, color):
        vehiculo = self.obtener_vehiculo(id_vehiculo)
        vehiculo.marca, vehiculo.color = _texto(marca, 40) or None, _texto(color, 30) or None
        self.vehiculos.actualizar(vehiculo)
        conexion.obtener().commit()
        return vehiculo

    def cambiar_estado_vehiculo(self, id_vehiculo, activo):
        vehiculo = self.obtener_vehiculo(id_vehiculo)
        dentro = any(v["dentro"] for v in self.vehiculos.de_usuario(vehiculo.id_usuario)
                     if v["id_vehiculo"] == id_vehiculo)
        if not activo and dentro:
            raise ReglaNegocioError("No se puede retirar: el vehículo está dentro del parqueadero")
        if activo and not self.obtener(vehiculo.id_usuario).activo:
            raise ReglaNegocioError("Primero activa al usuario propietario")
        vehiculo.activo = activo
        self.vehiculos.actualizar(vehiculo)
        conexion.obtener().commit()
        return vehiculo

    def renovar_mensualidad(self, id_vehiculo, fecha_inicio, fecha_fin, valor):
        vehiculo = self.obtener_vehiculo(id_vehiculo)
        mensualidad = self._nueva_mensualidad(fecha_inicio, fecha_fin, valor)
        mensualidad.id_vehiculo = vehiculo.id_vehiculo
        self.mensualidades.guardar(mensualidad)
        conexion.obtener().commit()
        return mensualidad

    @staticmethod
    def _nueva_mensualidad(fecha_inicio, fecha_fin, valor):
        inicio = _fecha(fecha_inicio, "fecha de inicio")
        fin = _fecha(fecha_fin, "fecha de fin")
        if fin < inicio:
            raise ReglaNegocioError("La fecha de fin debe ser posterior a la fecha de inicio")
        try:
            valor = Decimal(str(valor or "").strip())
        except InvalidOperation:
            raise ReglaNegocioError("El valor de la mensualidad no es válido") from None
        if valor <= 0:
            raise ReglaNegocioError("El valor de la mensualidad debe ser mayor que cero")
        return Mensualidad(None, None, inicio, fin, valor)
