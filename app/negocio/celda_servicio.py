"""Gestión de celdas (HU-14 a HU-16)."""
from app.datos import conexion
from app.datos.repositorios import CeldaRepositorio
from app.modelo.entidades import PATRON_CODIGO_CELDA, Celda, EstadoCelda, TipoVehiculo
from app.negocio.errores import ReglaNegocioError


class CeldaServicio:
    def __init__(self):
        self.celdas = CeldaRepositorio()

    def mapa(self, tipo=None, estado=None):
        tipo = tipo if tipo in TipoVehiculo.__members__ else None
        estado = estado if estado in EstadoCelda.__members__ else None
        return self.celdas.mapa(tipo, estado)

    def resumen(self):
        return self.celdas.resumen()

    def obtener(self, id_celda):
        celda = self.celdas.buscar_por_id(id_celda)
        if not celda:
            raise ReglaNegocioError("La celda no existe")
        return celda

    def _validar(self, codigo, tipo, id_actual=None):
        codigo = (codigo or "").strip().upper().replace(" ", "")
        if not PATRON_CODIGO_CELDA.match(codigo):
            raise ReglaNegocioError("Código inválido. Usa letras, guion y número, por ejemplo C-11 o M-06")
        try:
            tipo = TipoVehiculo(tipo)
        except ValueError:
            raise ReglaNegocioError("Selecciona el tipo de celda") from None
        otra = self.celdas.buscar_por_codigo(codigo)
        if otra and otra.id_celda != id_actual:
            raise ReglaNegocioError("Ya existe una celda con ese código")
        return codigo, tipo

    def registrar(self, codigo, tipo):
        codigo, tipo = self._validar(codigo, tipo)
        celda = self.celdas.guardar(Celda(None, codigo, tipo, EstadoCelda.LIBRE))
        conexion.obtener().commit()
        return celda

    def modificar(self, id_celda, codigo, tipo):
        celda = self.obtener(id_celda)
        if celda.estado == EstadoCelda.OCUPADA:
            raise ReglaNegocioError("No se puede modificar una celda ocupada")
        celda.codigo, celda.tipo = self._validar(codigo, tipo, id_celda)
        self.celdas.actualizar(celda)
        conexion.obtener().commit()
        return celda

    def inhabilitar(self, id_celda, motivo):
        celda = self.obtener(id_celda)
        motivo = (motivo or "").strip()[:200]
        if celda.estado == EstadoCelda.OCUPADA:
            raise ReglaNegocioError("No se puede inhabilitar una celda ocupada")
        if not motivo:
            raise ReglaNegocioError("Escribe el motivo para inhabilitar la celda")
        celda.inhabilitar(motivo)
        self.celdas.actualizar_estado(celda)
        conexion.obtener().commit()
        return celda

    def habilitar(self, id_celda):
        celda = self.obtener(id_celda)
        if celda.estado != EstadoCelda.INHABILITADA:
            raise ReglaNegocioError("La celda ya está habilitada")
        celda.habilitar()
        self.celdas.actualizar_estado(celda)
        conexion.obtener().commit()
        return celda
