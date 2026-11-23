"""Clases de dominio del parqueadero (ver diagrama de clases)."""
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional

from werkzeug.security import check_password_hash

PATRON_DOCUMENTO = re.compile(r"^[0-9]{5,15}$")
PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PATRON_TELEFONO = re.compile(r"^[0-9]{7,10}$")
PATRON_CODIGO_CELDA = re.compile(r"^[A-Z]{1,3}-[0-9]{1,4}$")

PATRON_PLACA = {
    "CARRO": re.compile(r"^[A-Z]{3}[0-9]{3}$"),
    "MOTO": re.compile(r"^[A-Z]{3}[0-9]{2}[A-Z]$"),
}


class Rol(str, Enum):
    OPERADOR = "OPERADOR"
    ADMINISTRADOR = "ADMINISTRADOR"


class TipoVehiculo(str, Enum):
    CARRO = "CARRO"
    MOTO = "MOTO"


class MedioPago(str, Enum):
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    TRANSFERENCIA = "TRANSFERENCIA"


class EstadoPago(str, Enum):
    VALIDO = "VALIDO"
    ANULADO = "ANULADO"


class EstadoCelda(str, Enum):
    LIBRE = "LIBRE"
    OCUPADA = "OCUPADA"
    INHABILITADA = "INHABILITADA"


def formato_placa_valido(placa: str) -> bool:
    return any(p.match(placa) for p in PATRON_PLACA.values())


@dataclass
class Operador:
    id_operador: int
    nombre: str
    usuario: str
    contrasena_hash: str
    rol: Rol
    activo: bool = True

    def verificar_contrasena(self, clave: str) -> bool:
        return check_password_hash(self.contrasena_hash, clave)

    def es_administrador(self) -> bool:
        return self.rol == Rol.ADMINISTRADOR


@dataclass
class Usuario:
    id_usuario: int
    documento: str
    nombre: str
    telefono: Optional[str] = None
    correo: Optional[str] = None
    activo: bool = True


@dataclass
class Vehiculo:
    id_vehiculo: int
    placa: str
    tipo: TipoVehiculo
    marca: Optional[str]
    color: Optional[str]
    id_usuario: int
    activo: bool = True

    def placa_valida(self) -> bool:
        return bool(PATRON_PLACA[self.tipo.value].match(self.placa))


@dataclass
class Mensualidad:
    id_mensualidad: int
    id_vehiculo: int
    fecha_inicio: date
    fecha_fin: date
    valor: Decimal
    pagada: bool = False  # iteración 3: tiene un pago válido

    def esta_vigente(self, fecha: date) -> bool:
        return self.fecha_inicio <= fecha <= self.fecha_fin

    def estado_pago(self, hoy: date) -> str:
        """Texto que se muestra en el estado de cuenta y en los pendientes."""
        if self.pagada:
            return "Pagada"
        if self.fecha_fin < hoy:
            return "Vencida sin pagar"
        if self.fecha_inicio > hoy:
            return "Por iniciar"
        return "Pendiente de pago"


@dataclass
class Celda:
    id_celda: int
    codigo: str
    tipo: TipoVehiculo
    estado: EstadoCelda
    motivo: Optional[str] = None

    def esta_libre(self) -> bool:
        return self.estado == EstadoCelda.LIBRE

    def ocupar(self):
        self.estado = EstadoCelda.OCUPADA

    def liberar(self):
        self.estado = EstadoCelda.LIBRE

    def inhabilitar(self, motivo: str):
        self.estado = EstadoCelda.INHABILITADA
        self.motivo = motivo

    def habilitar(self):
        self.estado = EstadoCelda.LIBRE
        self.motivo = None


@dataclass
class Registro:
    id_registro: int
    id_vehiculo: int
    id_celda: int
    fecha_hora_entrada: datetime
    fecha_hora_salida: Optional[datetime]
    id_operador_entrada: int
    id_operador_salida: Optional[int] = None

    def esta_abierto(self) -> bool:
        return self.fecha_hora_salida is None

    def registrar_salida(self, operador: Operador, momento: datetime):
        self.fecha_hora_salida = momento
        self.id_operador_salida = operador.id_operador

    def tiempo_permanencia(self) -> timedelta:
        fin = self.fecha_hora_salida or datetime.now()
        return fin - self.fecha_hora_entrada


@dataclass
class Novedad:
    id_novedad: int
    id_registro: int
    descripcion: str
    fecha_hora: datetime
    id_operador: int


@dataclass
class Pago:
    """Pago de una mensualidad (iteración 3). No se borra: se anula (RNF-19)."""
    id_pago: Optional[int]
    id_mensualidad: int
    fecha_hora: datetime
    valor: Decimal
    medio_pago: MedioPago
    referencia: Optional[str]
    valor_recibido: Optional[Decimal]
    id_operador: int
    estado: EstadoPago = EstadoPago.VALIDO
    motivo_anulacion: Optional[str] = None

    @property
    def numero_recibo(self) -> str:
        return numero_recibo(self.id_pago)

    def cambio(self) -> Decimal:
        if self.medio_pago != MedioPago.EFECTIVO or self.valor_recibido is None:
            return Decimal(0)
        return self.valor_recibido - self.valor

    def esta_anulado(self) -> bool:
        return self.estado == EstadoPago.ANULADO

    def anular(self, motivo: str):
        self.estado = EstadoPago.ANULADO
        self.motivo_anulacion = motivo


def numero_recibo(id_pago) -> str:
    """Consecutivo del recibo: RC-000001, RC-000002..."""
    return f"RC-{int(id_pago):06d}"
