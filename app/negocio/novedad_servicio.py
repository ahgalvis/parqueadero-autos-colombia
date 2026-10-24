from datetime import datetime

from app.datos import conexion
from app.datos.repositorios import NovedadRepositorio
from app.negocio.errores import ReglaNegocioError
from app.negocio.registro_servicio import RegistroServicio


class NovedadServicio:
    def __init__(self):
        self.novedades = NovedadRepositorio()
        self.registro_servicio = RegistroServicio()

    def registrar_novedad(self, placa, descripcion, operador):
        descripcion = (descripcion or "").strip()
        if not descripcion:
            raise ReglaNegocioError("La descripción es obligatoria")
        _, registro = self.registro_servicio.buscar_estancia(placa)
        novedad = self.novedades.guardar(registro.id_registro, descripcion[:500], operador.id_operador,
                                         datetime.now().replace(microsecond=0))
        conexion.obtener().commit()
        return novedad
