"""Cuentas del personal que usa el sistema: operadores y administradores (HU-13)."""
import re

from werkzeug.security import generate_password_hash

from app.datos import conexion
from app.datos.repositorios import OperadorRepositorio
from app.modelo.entidades import Rol
from app.negocio.errores import ReglaNegocioError

PATRON_LOGIN = re.compile(r"^[a-z0-9._]{3,30}$")


def _rol(valor):
    try:
        return Rol(valor)
    except ValueError:
        raise ReglaNegocioError("Selecciona un rol válido") from None


def _validar_clave(clave):
    if len(clave or "") < 6:
        raise ReglaNegocioError("La contraseña debe tener al menos 6 caracteres")


class PersonalServicio:
    def __init__(self):
        self.operadores = OperadorRepositorio()

    def listar(self):
        return self.operadores.listar()

    def obtener(self, id_operador):
        operador = self.operadores.buscar_por_id(id_operador)
        if not operador:
            raise ReglaNegocioError("La cuenta no existe")
        return operador

    def registrar(self, nombre, usuario, clave, rol):
        nombre = (nombre or "").strip()[:100]
        usuario = (usuario or "").strip().lower()
        if not nombre:
            raise ReglaNegocioError("El nombre es obligatorio")
        if not PATRON_LOGIN.match(usuario):
            raise ReglaNegocioError("El usuario debe tener de 3 a 30 letras minúsculas, números, punto o guion bajo")
        _validar_clave(clave)
        rol = _rol(rol)
        if self.operadores.existe_usuario(usuario):
            raise ReglaNegocioError("Ese nombre de usuario ya existe")
        nuevo = self.operadores.guardar(nombre, usuario, generate_password_hash(clave), rol)
        conexion.obtener().commit()
        return nuevo

    def actualizar(self, id_operador, nombre, rol, activo, nueva_clave, quien):
        operador = self.obtener(id_operador)
        nombre = (nombre or "").strip()[:100]
        if not nombre:
            raise ReglaNegocioError("El nombre es obligatorio")
        rol = _rol(rol)
        if operador.id_operador == quien.id_operador and (not activo or rol != Rol.ADMINISTRADOR):
            raise ReglaNegocioError("No puedes quitarte el rol de administrador ni inactivar tu propia cuenta")
        era_admin_activo = operador.es_administrador() and operador.activo
        if era_admin_activo and (not activo or rol != Rol.ADMINISTRADOR) \
                and self.operadores.administradores_activos() <= 1:
            raise ReglaNegocioError("Debe quedar al menos un administrador activo")
        if nueva_clave:
            _validar_clave(nueva_clave)
            operador.contrasena_hash = generate_password_hash(nueva_clave)
        operador.nombre, operador.rol, operador.activo = nombre, rol, activo
        self.operadores.actualizar(operador)
        conexion.obtener().commit()
        return operador
