"""Repositorios: única capa que escribe SQL."""
from werkzeug.security import generate_password_hash

from app.datos import conexion
from app.modelo.entidades import (
    Celda, EstadoCelda, Mensualidad, Novedad, Operador, Registro, Rol, TipoVehiculo, Vehiculo,
)

CLAVES_INICIALES = {"admin": "admin123", "operador": "operador123"}


def _cursor():
    return conexion.obtener().cursor()


class OperadorRepositorio:
    def buscar_por_usuario(self, usuario):
        with _cursor() as c:
            c.execute("SELECT * FROM operador WHERE usuario = %s AND activo", (usuario,))
            fila = c.fetchone()
        return self._a_entidad(fila) if fila else None

    def buscar_por_id(self, id_operador):
        with _cursor() as c:
            c.execute("SELECT * FROM operador WHERE id_operador = %s", (id_operador,))
            fila = c.fetchone()
        return self._a_entidad(fila) if fila else None

    def inicializar_claves_pendientes(self):
        db = conexion.obtener()
        with db.cursor() as c:
            c.execute("SELECT id_operador, usuario FROM operador WHERE contrasena_hash = 'PENDIENTE'")
            for fila in c.fetchall():
                clave = CLAVES_INICIALES.get(fila["usuario"], fila["usuario"])
                c.execute(
                    "UPDATE operador SET contrasena_hash = %s WHERE id_operador = %s",
                    (generate_password_hash(clave), fila["id_operador"]),
                )
        db.commit()

    @staticmethod
    def _a_entidad(f):
        return Operador(f["id_operador"], f["nombre"], f["usuario"], f["contrasena_hash"],
                        Rol(f["rol"]), bool(f["activo"]))


class VehiculoRepositorio:
    def buscar_por_placa(self, placa):
        with _cursor() as c:
            c.execute("SELECT * FROM vehiculo WHERE placa = %s", (placa,))
            f = c.fetchone()
        if not f:
            return None
        return Vehiculo(f["id_vehiculo"], f["placa"], TipoVehiculo(f["tipo"]), f["marca"],
                        f["color"], f["id_usuario"])

    def nombre_propietario(self, id_usuario):
        with _cursor() as c:
            c.execute("SELECT nombre FROM usuario WHERE id_usuario = %s", (id_usuario,))
            f = c.fetchone()
        return f["nombre"] if f else ""


class MensualidadRepositorio:
    def ultima_de_vehiculo(self, id_vehiculo):
        with _cursor() as c:
            c.execute(
                "SELECT * FROM mensualidad WHERE id_vehiculo = %s ORDER BY fecha_fin DESC LIMIT 1",
                (id_vehiculo,),
            )
            f = c.fetchone()
        if not f:
            return None
        return Mensualidad(f["id_mensualidad"], f["id_vehiculo"], f["fecha_inicio"], f["fecha_fin"],
                           f["valor"])


class CeldaRepositorio:
    def primera_libre_bloqueada(self, tipo):
        """Toma la primera celda libre y la bloquea hasta el commit para que dos operadores no la asignen a la vez."""
        with _cursor() as c:
            c.execute(
                "SELECT * FROM celda WHERE tipo = %s AND estado = 'LIBRE' ORDER BY codigo LIMIT 1 FOR UPDATE",
                (tipo.value,),
            )
            f = c.fetchone()
        return self._a_entidad(f) if f else None

    def buscar_por_id(self, id_celda):
        with _cursor() as c:
            c.execute("SELECT * FROM celda WHERE id_celda = %s", (id_celda,))
            f = c.fetchone()
        return self._a_entidad(f) if f else None

    def actualizar_estado(self, celda):
        with _cursor() as c:
            c.execute("UPDATE celda SET estado = %s WHERE id_celda = %s",
                      (celda.estado.value, celda.id_celda))

    def resumen(self):
        with _cursor() as c:
            c.execute("SELECT tipo, estado, COUNT(*) AS total FROM celda GROUP BY tipo, estado")
            filas = c.fetchall()
        resumen = {t.value: {"LIBRE": 0, "OCUPADA": 0} for t in TipoVehiculo}
        for f in filas:
            resumen[f["tipo"]][f["estado"]] = f["total"]
        return resumen

    @staticmethod
    def _a_entidad(f):
        return Celda(f["id_celda"], f["codigo"], TipoVehiculo(f["tipo"]), EstadoCelda(f["estado"]))


class RegistroRepositorio:
    def abierto_de_vehiculo(self, id_vehiculo):
        with _cursor() as c:
            c.execute(
                "SELECT * FROM registro WHERE id_vehiculo = %s AND fecha_hora_salida IS NULL",
                (id_vehiculo,),
            )
            f = c.fetchone()
        return self._a_entidad(f) if f else None

    def guardar(self, id_vehiculo, id_celda, id_operador, momento):
        with _cursor() as c:
            c.execute(
                "INSERT INTO registro (id_vehiculo, id_celda, fecha_hora_entrada, id_operador_entrada) "
                "VALUES (%s, %s, %s, %s)",
                (id_vehiculo, id_celda, momento, id_operador),
            )
            nuevo_id = c.lastrowid
        return Registro(nuevo_id, id_vehiculo, id_celda, momento, None, id_operador)

    def actualizar_salida(self, registro):
        with _cursor() as c:
            c.execute(
                "UPDATE registro SET fecha_hora_salida = %s, id_operador_salida = %s WHERE id_registro = %s",
                (registro.fecha_hora_salida, registro.id_operador_salida, registro.id_registro),
            )

    def vehiculos_dentro(self, placa=None):
        sql = (
            "SELECT v.placa, v.tipo, u.nombre AS propietario, c.codigo AS celda, r.fecha_hora_entrada "
            "FROM registro r JOIN vehiculo v ON v.id_vehiculo = r.id_vehiculo "
            "JOIN usuario u ON u.id_usuario = v.id_usuario JOIN celda c ON c.id_celda = r.id_celda "
            "WHERE r.fecha_hora_salida IS NULL"
        )
        params = []
        if placa:
            sql += " AND v.placa LIKE %s"
            params.append(f"%{placa}%")
        with _cursor() as c:
            c.execute(sql + " ORDER BY r.fecha_hora_entrada", params)
            return c.fetchall()

    def historial(self, placa=None, desde=None, hasta=None):
        sql = (
            "SELECT r.id_registro, v.placa, c.codigo AS celda, r.fecha_hora_entrada, r.fecha_hora_salida, "
            "oe.nombre AS operador_entrada, os.nombre AS operador_salida, "
            "(SELECT COUNT(*) FROM novedad n WHERE n.id_registro = r.id_registro) AS novedades "
            "FROM registro r JOIN vehiculo v ON v.id_vehiculo = r.id_vehiculo "
            "JOIN celda c ON c.id_celda = r.id_celda "
            "JOIN operador oe ON oe.id_operador = r.id_operador_entrada "
            "LEFT JOIN operador os ON os.id_operador = r.id_operador_salida WHERE 1 = 1"
        )
        params = []
        if placa:
            sql += " AND v.placa LIKE %s"
            params.append(f"%{placa}%")
        if desde:
            sql += " AND DATE(r.fecha_hora_entrada) >= %s"
            params.append(desde)
        if hasta:
            sql += " AND DATE(r.fecha_hora_entrada) <= %s"
            params.append(hasta)
        with _cursor() as c:
            c.execute(sql + " ORDER BY r.fecha_hora_entrada DESC", params)
            return c.fetchall()

    @staticmethod
    def _a_entidad(f):
        return Registro(f["id_registro"], f["id_vehiculo"], f["id_celda"], f["fecha_hora_entrada"],
                        f["fecha_hora_salida"], f["id_operador_entrada"], f["id_operador_salida"])


class NovedadRepositorio:
    def guardar(self, id_registro, descripcion, id_operador, momento):
        with _cursor() as c:
            c.execute(
                "INSERT INTO novedad (id_registro, descripcion, fecha_hora, id_operador) VALUES (%s, %s, %s, %s)",
                (id_registro, descripcion, momento, id_operador),
            )
            nuevo_id = c.lastrowid
        return Novedad(nuevo_id, id_registro, descripcion, momento, id_operador)

    def de_registro(self, id_registro):
        with _cursor() as c:
            c.execute(
                "SELECT n.descripcion, n.fecha_hora, o.nombre AS operador FROM novedad n "
                "JOIN operador o ON o.id_operador = n.id_operador WHERE n.id_registro = %s "
                "ORDER BY n.fecha_hora",
                (id_registro,),
            )
            return c.fetchall()
