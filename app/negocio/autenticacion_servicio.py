from app.datos.repositorios import OperadorRepositorio
from app.negocio.errores import ReglaNegocioError


class AutenticacionServicio:
    def __init__(self, operadores=None):
        self.operadores = operadores or OperadorRepositorio()

    def iniciar_sesion(self, usuario, clave):
        operador = self.operadores.buscar_por_usuario(usuario.strip())
        if not operador or not operador.verificar_contrasena(clave):
            raise ReglaNegocioError("Usuario o contraseña incorrectos")
        return operador
