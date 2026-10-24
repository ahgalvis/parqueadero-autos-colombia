"""Reglas de entrada y salida de vehículos (HU-02, HU-03)."""
from datetime import datetime

from app.datos import conexion
from app.datos.repositorios import (
    CeldaRepositorio, MensualidadRepositorio, NovedadRepositorio, RegistroRepositorio, VehiculoRepositorio,
)
from app.modelo.entidades import formato_placa_valido
from app.negocio.errores import ReglaNegocioError


def normalizar_placa(placa):
    placa = (placa or "").strip().upper().replace(" ", "").replace("-", "")
    if not formato_placa_valido(placa):
        raise ReglaNegocioError("Formato de placa inválido. Carro: AAA123, moto: AAA12A")
    return placa


class RegistroServicio:
    def __init__(self):
        self.vehiculos = VehiculoRepositorio()
        self.mensualidades = MensualidadRepositorio()
        self.celdas = CeldaRepositorio()
        self.registros = RegistroRepositorio()
        self.novedades = NovedadRepositorio()

    def validar_entrada(self, placa):
        """Verifica todo lo necesario antes de confirmar; devuelve los datos para mostrar."""
        placa = normalizar_placa(placa)
        vehiculo = self.vehiculos.buscar_por_placa(placa)
        if not vehiculo:
            raise ReglaNegocioError("Vehículo no registrado")
        mensualidad = self._validar_mensualidad(vehiculo)
        if self.registros.abierto_de_vehiculo(vehiculo.id_vehiculo):
            raise ReglaNegocioError("El vehículo ya se encuentra en el parqueadero")
        return {
            "vehiculo": vehiculo,
            "propietario": self.vehiculos.nombre_propietario(vehiculo.id_usuario),
            "mensualidad": mensualidad,
            "celdas_libres": self.celdas.resumen()[vehiculo.tipo.value]["LIBRE"],
        }

    def registrar_entrada(self, placa, operador):
        datos = self.validar_entrada(placa)
        vehiculo = datos["vehiculo"]
        db = conexion.obtener()
        try:
            celda = self._asignar_celda(vehiculo.tipo)
            registro = self.registros.guardar(vehiculo.id_vehiculo, celda.id_celda,
                                              operador.id_operador, datetime.now().replace(microsecond=0))
            celda.ocupar()
            self.celdas.actualizar_estado(celda)
            db.commit()
        except Exception:
            db.rollback()
            raise
        return self._comprobante(registro, vehiculo, celda, datos["propietario"])

    def buscar_estancia(self, placa):
        placa = normalizar_placa(placa)
        vehiculo = self.vehiculos.buscar_por_placa(placa)
        registro = self.registros.abierto_de_vehiculo(vehiculo.id_vehiculo) if vehiculo else None
        if not registro:
            raise ReglaNegocioError("El vehículo no se encuentra en el parqueadero")
        return vehiculo, registro

    def resumen_salida(self, placa):
        vehiculo, registro = self.buscar_estancia(placa)
        celda = self.celdas.buscar_por_id(registro.id_celda)
        datos = self._comprobante(registro, vehiculo, celda, self.vehiculos.nombre_propietario(vehiculo.id_usuario))
        datos["novedades"] = self.novedades.de_registro(registro.id_registro)
        return datos

    def registrar_salida(self, placa, operador):
        vehiculo, registro = self.buscar_estancia(placa)
        db = conexion.obtener()
        try:
            registro.registrar_salida(operador, datetime.now().replace(microsecond=0))
            self.registros.actualizar_salida(registro)
            celda = self.celdas.buscar_por_id(registro.id_celda)
            celda.liberar()
            self.celdas.actualizar_estado(celda)
            db.commit()
        except Exception:
            db.rollback()
            raise
        return self._comprobante(registro, vehiculo, celda, self.vehiculos.nombre_propietario(vehiculo.id_usuario))

    def _validar_mensualidad(self, vehiculo):
        mensualidad = self.mensualidades.ultima_de_vehiculo(vehiculo.id_vehiculo)
        if not mensualidad or not mensualidad.esta_vigente(datetime.now().date()):
            vence = f" (venció el {mensualidad.fecha_fin:%d/%m/%Y})" if mensualidad else ""
            raise ReglaNegocioError("Mensualidad vencida" + vence)
        return mensualidad

    def _asignar_celda(self, tipo):
        celda = self.celdas.primera_libre_bloqueada(tipo)
        if not celda:
            raise ReglaNegocioError("No hay celdas disponibles")
        return celda

    @staticmethod
    def _comprobante(registro, vehiculo, celda, propietario):
        minutos = int(registro.tiempo_permanencia().total_seconds() // 60)
        return {
            "placa": vehiculo.placa,
            "tipo": vehiculo.tipo.value,
            "propietario": propietario,
            "celda": celda.codigo,
            "entrada": registro.fecha_hora_entrada,
            "salida": registro.fecha_hora_salida,
            "permanencia": f"{minutos // 60} h {minutos % 60} min",
        }
