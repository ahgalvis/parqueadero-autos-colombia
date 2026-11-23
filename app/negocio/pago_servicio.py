"""Gestión de pagos de mensualidades (iteración 3, HU-17 a HU-23)."""
import calendar
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

import pymysql

from app.datos import conexion
from app.datos.repositorios import MensualidadRepositorio, PagoRepositorio, UsuarioRepositorio, VehiculoRepositorio
from app.modelo.entidades import MedioPago, Mensualidad, Pago, numero_recibo
from app.negocio.errores import ReglaNegocioError
from app.negocio.registro_servicio import normalizar_placa

PATRON_REFERENCIA = re.compile(r"^[A-Za-z0-9-]{4,40}$")
PATRON_NUMERO_TARJETA = re.compile(r"^[0-9]{13,19}$")
SIGUIENTE = "siguiente"


def sumar_un_mes(inicio):
    """Último día del periodo mensual que empieza en 'inicio' (23/11 -> 22/12; 31/01 -> 28/02)."""
    anio, mes = (inicio.year + 1, 1) if inicio.month == 12 else (inicio.year, inicio.month + 1)
    dia = min(inicio.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia) - timedelta(days=1)


def _dinero(valor, nombre):
    texto = str(valor or "").strip().replace("$", "").replace(".", "").replace(",", "")
    try:
        numero = Decimal(texto)
    except InvalidOperation:
        raise ReglaNegocioError(f"Escribe el {nombre} en pesos, solo números") from None
    if numero <= 0:
        raise ReglaNegocioError(f"El {nombre} debe ser mayor que cero")
    return numero


class PagoServicio:
    def __init__(self):
        self.vehiculos = VehiculoRepositorio()
        self.usuarios = UsuarioRepositorio()
        self.mensualidades = MensualidadRepositorio()
        self.pagos = PagoRepositorio()

    # ---------- Registrar pago (HU-17, HU-18) ----------
    def cuenta_de_placa(self, placa):
        """Vehículo, propietario, mensualidades pendientes y, si no hay, la siguiente mensualidad propuesta."""
        placa = normalizar_placa(placa)
        vehiculo = self.vehiculos.buscar_por_placa(placa)
        if not vehiculo:
            raise ReglaNegocioError("Vehículo no registrado")
        if not vehiculo.activo:
            raise ReglaNegocioError("Vehículo retirado del sistema")
        propietario = self.usuarios.buscar_por_id(vehiculo.id_usuario)
        if not propietario.activo:
            raise ReglaNegocioError("El usuario propietario está inactivo")
        pendientes = self.mensualidades.pendientes_de_vehiculo(vehiculo.id_vehiculo)
        return {
            "vehiculo": vehiculo,
            "propietario": propietario,
            "pendientes": pendientes,
            "siguiente": None if pendientes else self.siguiente_mensualidad(vehiculo.id_vehiculo),
            "hoy": date.today(),
        }

    def siguiente_mensualidad(self, id_vehiculo):
        """Propone el periodo que sigue a la última mensualidad, con el mismo valor (RF-26)."""
        ultima = self.mensualidades.ultima_de_vehiculo(id_vehiculo)
        if not ultima:
            return None
        inicio = max(ultima.fecha_fin + timedelta(days=1), date.today())
        return Mensualidad(None, id_vehiculo, inicio, sumar_un_mes(inicio), ultima.valor)

    def registrar_pago(self, placa, mensualidad, medio, referencia, valor_recibido, operador):
        cuenta = self.cuenta_de_placa(placa)
        try:
            medio = MedioPago(medio)
        except ValueError:
            raise ReglaNegocioError("Selecciona el medio de pago") from None

        if mensualidad == SIGUIENTE:
            if cuenta["pendientes"]:
                raise ReglaNegocioError("Primero paga la mensualidad pendiente")
            a_pagar = cuenta["siguiente"]
            if not a_pagar:
                raise ReglaNegocioError("El vehículo no tiene mensualidades para renovar")
        else:
            a_pagar = next((m for m in cuenta["pendientes"] if str(m.id_mensualidad) == str(mensualidad)), None)
            if not a_pagar:
                raise ReglaNegocioError("Selecciona una mensualidad pendiente de pago")

        referencia = (referencia or "").strip().replace(" ", "")
        recibido = None
        if medio == MedioPago.EFECTIVO:
            referencia = None
            recibido = _dinero(valor_recibido, "valor recibido")
            if recibido < a_pagar.valor:
                raise ReglaNegocioError("El valor recibido es menor que el valor a pagar")
        else:
            if medio == MedioPago.TARJETA and PATRON_NUMERO_TARJETA.match(referencia):
                raise ReglaNegocioError("No escribas el número de la tarjeta: usa el número de aprobación del datáfono")
            if not PATRON_REFERENCIA.match(referencia):
                raise ReglaNegocioError("Escribe el número de aprobación o de la transferencia (4 a 40 letras o números)")

        db = conexion.obtener()
        try:
            if a_pagar.id_mensualidad is None:  # la siguiente mensualidad se crea junto con su pago
                self.mensualidades.guardar(a_pagar)
            pago = self.pagos.guardar(Pago(None, a_pagar.id_mensualidad, datetime.now().replace(microsecond=0),
                                           a_pagar.valor, medio, referencia or None, recibido,
                                           operador.id_operador))
            db.commit()
        except pymysql.err.IntegrityError:
            db.rollback()
            raise ReglaNegocioError("La mensualidad ya está pagada") from None
        except Exception:
            db.rollback()
            raise
        return pago

    # ---------- Recibo (HU-19) ----------
    def recibo(self, id_pago):
        datos = self.pagos.detalle(id_pago)
        if not datos:
            raise ReglaNegocioError("El pago no existe")
        datos["numero_recibo"] = numero_recibo(datos["id_pago"])
        recibido = datos["valor_recibido"]
        datos["cambio"] = (recibido - datos["valor"]) if recibido is not None else None
        return datos

    # ---------- Consultas (HU-20, HU-21) ----------
    def listar(self, desde=None, hasta=None, texto=None, medio=None):
        texto = (texto or "").strip()[:100] or None
        if medio and medio not in MedioPago.__members__:
            medio = None
        pagos = self.pagos.listar(desde or None, hasta or None, texto, medio or None)
        for p in pagos:
            p["numero_recibo"] = numero_recibo(p["id_pago"])
        validos = [p for p in pagos if p["estado"] == "VALIDO"]
        por_medio = {m.value: sum((p["valor"] for p in validos if p["medio_pago"] == m.value), Decimal(0))
                     for m in MedioPago}
        return {"pagos": pagos, "por_medio": por_medio, "total": sum(por_medio.values(), Decimal(0)),
                "cantidad": len(validos), "anulados": len(pagos) - len(validos)}

    def pendientes(self, texto=None):
        hoy = date.today()
        filas = self.mensualidades.pendientes((texto or "").strip()[:100] or None)
        for f in filas:
            f["estado"] = Mensualidad(f["id_mensualidad"], f["id_vehiculo"], f["fecha_inicio"], f["fecha_fin"],
                                      f["valor"]).estado_pago(hoy)
        return {"filas": filas, "total": sum((f["valor"] for f in filas), Decimal(0))}

    def estado_cuenta(self, id_usuario):
        hoy = date.today()
        filas = self.mensualidades.estado_cuenta_usuario(id_usuario)
        for f in filas:
            f["estado"] = Mensualidad(f["id_mensualidad"], f["id_vehiculo"], f["fecha_inicio"], f["fecha_fin"],
                                      f["valor"], bool(f["pagada"])).estado_pago(hoy)
            f["numero_recibo"] = numero_recibo(f["id_pago"]) if f["id_pago"] else None
        return filas

    # ---------- Anular (HU-22) ----------
    def anular(self, id_pago, motivo, operador):
        pago = self.pagos.buscar_por_id(id_pago)
        if not pago:
            raise ReglaNegocioError("El pago no existe")
        if pago.esta_anulado():
            raise ReglaNegocioError("El pago ya está anulado")
        motivo = (motivo or "").strip()[:200]
        if len(motivo) < 5:
            raise ReglaNegocioError("Escribe el motivo de la anulación (mínimo 5 caracteres)")
        pago.anular(motivo)
        db = conexion.obtener()
        if not self.pagos.anular(pago, operador.id_operador, datetime.now().replace(microsecond=0)):
            db.rollback()
            raise ReglaNegocioError("El pago ya está anulado")
        db.commit()
        return pago
