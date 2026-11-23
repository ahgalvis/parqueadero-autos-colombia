"""Repositorios: única capa que escribe SQL."""
from werkzeug.security import generate_password_hash

from app.datos import conexion
from app.modelo.entidades import (
    Celda, EstadoCelda, EstadoPago, MedioPago, Mensualidad, Novedad, Operador, Pago, Registro, Rol, TipoVehiculo,
    Usuario, Vehiculo,
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

    def existe_usuario(self, usuario):
        with _cursor() as c:
            c.execute("SELECT 1 FROM operador WHERE usuario = %s", (usuario,))
            return c.fetchone() is not None

    def listar(self):
        with _cursor() as c:
            c.execute("SELECT * FROM operador ORDER BY nombre")
            return [self._a_entidad(f) for f in c.fetchall()]

    def guardar(self, nombre, usuario, contrasena_hash, rol):
        with _cursor() as c:
            c.execute(
                "INSERT INTO operador (nombre, usuario, contrasena_hash, rol) VALUES (%s, %s, %s, %s)",
                (nombre, usuario, contrasena_hash, rol.value),
            )
            return c.lastrowid

    def actualizar(self, operador):
        with _cursor() as c:
            c.execute(
                "UPDATE operador SET nombre = %s, rol = %s, activo = %s, contrasena_hash = %s "
                "WHERE id_operador = %s",
                (operador.nombre, operador.rol.value, operador.activo, operador.contrasena_hash,
                 operador.id_operador),
            )

    def administradores_activos(self):
        with _cursor() as c:
            c.execute("SELECT COUNT(*) AS n FROM operador WHERE rol = 'ADMINISTRADOR' AND activo")
            return c.fetchone()["n"]

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


class UsuarioRepositorio:
    """Clientes con mensualidad (iteración 2)."""

    def listar(self, texto=None, solo_activos=False):
        sql = ("SELECT u.*, (SELECT COUNT(*) FROM vehiculo v WHERE v.id_usuario = u.id_usuario AND v.activo) "
               "AS vehiculos FROM usuario u WHERE 1 = 1")
        params = []
        if texto:
            sql += " AND (u.documento LIKE %s OR u.nombre LIKE %s)"
            params += [f"%{texto}%", f"%{texto}%"]
        if solo_activos:
            sql += " AND u.activo"
        with _cursor() as c:
            c.execute(sql + " ORDER BY u.nombre", params)
            return c.fetchall()

    def buscar_por_id(self, id_usuario):
        with _cursor() as c:
            c.execute("SELECT * FROM usuario WHERE id_usuario = %s", (id_usuario,))
            f = c.fetchone()
        return self._a_entidad(f) if f else None

    def buscar_por_documento(self, documento):
        with _cursor() as c:
            c.execute("SELECT * FROM usuario WHERE documento = %s", (documento,))
            f = c.fetchone()
        return self._a_entidad(f) if f else None

    def guardar(self, usuario):
        with _cursor() as c:
            c.execute(
                "INSERT INTO usuario (documento, nombre, telefono, correo) VALUES (%s, %s, %s, %s)",
                (usuario.documento, usuario.nombre, usuario.telefono, usuario.correo),
            )
            usuario.id_usuario = c.lastrowid
        return usuario

    def actualizar(self, usuario):
        with _cursor() as c:
            c.execute(
                "UPDATE usuario SET nombre = %s, telefono = %s, correo = %s, activo = %s WHERE id_usuario = %s",
                (usuario.nombre, usuario.telefono, usuario.correo, usuario.activo, usuario.id_usuario),
            )

    @staticmethod
    def _a_entidad(f):
        return Usuario(f["id_usuario"], f["documento"], f["nombre"], f["telefono"], f["correo"], bool(f["activo"]))


class VehiculoRepositorio:
    def buscar_por_placa(self, placa):
        with _cursor() as c:
            c.execute("SELECT * FROM vehiculo WHERE placa = %s", (placa,))
            f = c.fetchone()
        return self._a_entidad(f) if f else None

    def buscar_por_id(self, id_vehiculo):
        with _cursor() as c:
            c.execute("SELECT * FROM vehiculo WHERE id_vehiculo = %s", (id_vehiculo,))
            f = c.fetchone()
        return self._a_entidad(f) if f else None

    def de_usuario(self, id_usuario):
        """Vehículos del usuario con el fin de su última mensualidad y si está dentro del parqueadero."""
        with _cursor() as c:
            c.execute(
                "SELECT v.*, (SELECT MAX(m.fecha_fin) FROM mensualidad m WHERE m.id_vehiculo = v.id_vehiculo) "
                "AS mensualidad_hasta, EXISTS(SELECT 1 FROM registro r WHERE r.id_vehiculo = v.id_vehiculo "
                "AND r.fecha_hora_salida IS NULL) AS dentro FROM vehiculo v WHERE v.id_usuario = %s "
                "ORDER BY v.activo DESC, v.placa",
                (id_usuario,),
            )
            return c.fetchall()

    def guardar(self, vehiculo):
        with _cursor() as c:
            c.execute(
                "INSERT INTO vehiculo (placa, tipo, marca, color, id_usuario) VALUES (%s, %s, %s, %s, %s)",
                (vehiculo.placa, vehiculo.tipo.value, vehiculo.marca, vehiculo.color, vehiculo.id_usuario),
            )
            vehiculo.id_vehiculo = c.lastrowid
        return vehiculo

    def actualizar(self, vehiculo):
        with _cursor() as c:
            c.execute(
                "UPDATE vehiculo SET marca = %s, color = %s, activo = %s WHERE id_vehiculo = %s",
                (vehiculo.marca, vehiculo.color, vehiculo.activo, vehiculo.id_vehiculo),
            )

    def nombre_propietario(self, id_usuario):
        with _cursor() as c:
            c.execute("SELECT nombre FROM usuario WHERE id_usuario = %s", (id_usuario,))
            f = c.fetchone()
        return f["nombre"] if f else ""

    @staticmethod
    def _a_entidad(f):
        return Vehiculo(f["id_vehiculo"], f["placa"], TipoVehiculo(f["tipo"]), f["marca"],
                        f["color"], f["id_usuario"], bool(f["activo"]))


# Subconsulta que dice si una mensualidad tiene un pago válido (iteración 3)
_PAGADA = "EXISTS(SELECT 1 FROM pago p WHERE p.id_mensualidad = m.id_mensualidad AND p.estado = 'VALIDO')"


class MensualidadRepositorio:
    def ultima_de_vehiculo(self, id_vehiculo):
        with _cursor() as c:
            c.execute(
                f"SELECT m.*, {_PAGADA} AS pagada FROM mensualidad m WHERE m.id_vehiculo = %s "
                "ORDER BY m.fecha_fin DESC LIMIT 1",
                (id_vehiculo,),
            )
            f = c.fetchone()
        return self._a_entidad(f) if f else None

    def buscar_por_id(self, id_mensualidad):
        with _cursor() as c:
            c.execute(f"SELECT m.*, {_PAGADA} AS pagada FROM mensualidad m WHERE m.id_mensualidad = %s",
                      (id_mensualidad,))
            f = c.fetchone()
        return self._a_entidad(f) if f else None

    def vigente_de_vehiculo(self, id_vehiculo, fecha):
        """La mensualidad que cubre la fecha; si hay varias, prefiere la que está pagada."""
        with _cursor() as c:
            c.execute(
                f"SELECT m.*, {_PAGADA} AS pagada FROM mensualidad m WHERE m.id_vehiculo = %s "
                "AND m.fecha_inicio <= %s AND m.fecha_fin >= %s ORDER BY pagada DESC, m.fecha_fin DESC LIMIT 1",
                (id_vehiculo, fecha, fecha),
            )
            f = c.fetchone()
        return self._a_entidad(f) if f else None

    def ultima_vencida_de_vehiculo(self, id_vehiculo, fecha):
        with _cursor() as c:
            c.execute(
                f"SELECT m.*, {_PAGADA} AS pagada FROM mensualidad m WHERE m.id_vehiculo = %s "
                "AND m.fecha_fin < %s ORDER BY m.fecha_fin DESC LIMIT 1",
                (id_vehiculo, fecha),
            )
            f = c.fetchone()
        return self._a_entidad(f) if f else None

    def pendientes_de_vehiculo(self, id_vehiculo):
        """Mensualidades sin pago válido, de la más antigua a la más nueva."""
        with _cursor() as c:
            c.execute(
                f"SELECT m.*, {_PAGADA} AS pagada FROM mensualidad m WHERE m.id_vehiculo = %s "
                f"AND NOT {_PAGADA} ORDER BY m.fecha_inicio",
                (id_vehiculo,),
            )
            return [self._a_entidad(f) for f in c.fetchall()]

    def pendientes(self, texto=None):
        """Cartera: mensualidades sin pagar de vehículos y usuarios activos (RF-29)."""
        sql = (
            f"SELECT m.*, {_PAGADA} AS pagada, v.placa, v.tipo, u.id_usuario, u.documento, u.nombre AS propietario, "
            "u.telefono FROM mensualidad m JOIN vehiculo v ON v.id_vehiculo = m.id_vehiculo "
            f"JOIN usuario u ON u.id_usuario = v.id_usuario WHERE v.activo AND u.activo AND NOT {_PAGADA}"
        )
        params = []
        if texto:
            sql += " AND (v.placa LIKE %s OR u.documento LIKE %s OR u.nombre LIKE %s)"
            params += [f"%{texto}%"] * 3
        with _cursor() as c:
            c.execute(sql + " ORDER BY m.fecha_inicio, v.placa", params)
            return c.fetchall()

    def estado_cuenta_usuario(self, id_usuario):
        """Todas las mensualidades de los vehículos del usuario con su pago válido, si lo tiene (RF-31)."""
        with _cursor() as c:
            c.execute(
                "SELECT m.*, v.placa, p.id_pago, p.fecha_hora AS fecha_pago, p.medio_pago, "
                "(p.id_pago IS NOT NULL) AS pagada FROM mensualidad m "
                "JOIN vehiculo v ON v.id_vehiculo = m.id_vehiculo "
                "LEFT JOIN pago p ON p.id_mensualidad = m.id_mensualidad AND p.estado = 'VALIDO' "
                "WHERE v.id_usuario = %s ORDER BY m.fecha_inicio DESC, v.placa",
                (id_usuario,),
            )
            return c.fetchall()

    def guardar(self, mensualidad):
        with _cursor() as c:
            c.execute(
                "INSERT INTO mensualidad (id_vehiculo, fecha_inicio, fecha_fin, valor) VALUES (%s, %s, %s, %s)",
                (mensualidad.id_vehiculo, mensualidad.fecha_inicio, mensualidad.fecha_fin, mensualidad.valor),
            )
            mensualidad.id_mensualidad = c.lastrowid
        return mensualidad

    @staticmethod
    def _a_entidad(f):
        return Mensualidad(f["id_mensualidad"], f["id_vehiculo"], f["fecha_inicio"], f["fecha_fin"], f["valor"],
                           bool(f.get("pagada")))


class PagoRepositorio:
    """Pagos de mensualidades (iteración 3). Nunca se borran: se anulan."""

    _DETALLE = (
        "SELECT p.*, m.fecha_inicio, m.fecha_fin, v.placa, v.tipo, u.id_usuario, u.documento, "
        "u.nombre AS propietario, o.nombre AS operador, oa.nombre AS operador_anulacion "
        "FROM pago p JOIN mensualidad m ON m.id_mensualidad = p.id_mensualidad "
        "JOIN vehiculo v ON v.id_vehiculo = m.id_vehiculo JOIN usuario u ON u.id_usuario = v.id_usuario "
        "JOIN operador o ON o.id_operador = p.id_operador "
        "LEFT JOIN operador oa ON oa.id_operador = p.id_operador_anulacion"
    )

    def guardar(self, pago):
        with _cursor() as c:
            c.execute(
                "INSERT INTO pago (id_mensualidad, fecha_hora, valor, medio_pago, referencia, valor_recibido, "
                "id_operador) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (pago.id_mensualidad, pago.fecha_hora, pago.valor, pago.medio_pago.value, pago.referencia,
                 pago.valor_recibido, pago.id_operador),
            )
            pago.id_pago = c.lastrowid
        return pago

    def buscar_por_id(self, id_pago):
        with _cursor() as c:
            c.execute("SELECT * FROM pago WHERE id_pago = %s", (id_pago,))
            f = c.fetchone()
        return self._a_entidad(f) if f else None

    def detalle(self, id_pago):
        """Datos completos para el recibo."""
        with _cursor() as c:
            c.execute(self._DETALLE + " WHERE p.id_pago = %s", (id_pago,))
            return c.fetchone()

    def anular(self, pago, id_operador, momento):
        with _cursor() as c:
            c.execute(
                "UPDATE pago SET estado = %s, motivo_anulacion = %s, fecha_hora_anulacion = %s, "
                "id_operador_anulacion = %s WHERE id_pago = %s AND estado = 'VALIDO'",
                (pago.estado.value, pago.motivo_anulacion, momento, id_operador, pago.id_pago),
            )
            return c.rowcount

    def listar(self, desde=None, hasta=None, texto=None, medio=None):
        sql = self._DETALLE + " WHERE 1 = 1"
        params = []
        if desde:
            sql += " AND DATE(p.fecha_hora) >= %s"
            params.append(desde)
        if hasta:
            sql += " AND DATE(p.fecha_hora) <= %s"
            params.append(hasta)
        if texto:
            sql += " AND (v.placa LIKE %s OR u.documento LIKE %s OR u.nombre LIKE %s)"
            params += [f"%{texto}%"] * 3
        if medio:
            sql += " AND p.medio_pago = %s"
            params.append(medio)
        with _cursor() as c:
            c.execute(sql + " ORDER BY p.fecha_hora DESC, p.id_pago DESC", params)
            return c.fetchall()

    @staticmethod
    def _a_entidad(f):
        return Pago(f["id_pago"], f["id_mensualidad"], f["fecha_hora"], f["valor"], MedioPago(f["medio_pago"]),
                    f["referencia"], f["valor_recibido"], f["id_operador"], EstadoPago(f["estado"]),
                    f["motivo_anulacion"])


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

    def buscar_por_codigo(self, codigo):
        with _cursor() as c:
            c.execute("SELECT * FROM celda WHERE codigo = %s", (codigo,))
            f = c.fetchone()
        return self._a_entidad(f) if f else None

    def actualizar_estado(self, celda):
        with _cursor() as c:
            c.execute("UPDATE celda SET estado = %s, motivo = %s WHERE id_celda = %s",
                      (celda.estado.value, celda.motivo, celda.id_celda))

    def guardar(self, celda):
        with _cursor() as c:
            c.execute("INSERT INTO celda (codigo, tipo) VALUES (%s, %s)", (celda.codigo, celda.tipo.value))
            celda.id_celda = c.lastrowid
        return celda

    def actualizar(self, celda):
        with _cursor() as c:
            c.execute("UPDATE celda SET codigo = %s, tipo = %s WHERE id_celda = %s",
                      (celda.codigo, celda.tipo.value, celda.id_celda))

    def mapa(self, tipo=None, estado=None):
        """Todas las celdas con la placa del vehículo que la ocupa (si hay uno)."""
        sql = ("SELECT c.*, v.placa, u.nombre AS propietario FROM celda c "
               "LEFT JOIN registro r ON r.id_celda = c.id_celda AND r.fecha_hora_salida IS NULL "
               "LEFT JOIN vehiculo v ON v.id_vehiculo = r.id_vehiculo "
               "LEFT JOIN usuario u ON u.id_usuario = v.id_usuario WHERE 1 = 1")
        params = []
        if tipo:
            sql += " AND c.tipo = %s"
            params.append(tipo)
        if estado:
            sql += " AND c.estado = %s"
            params.append(estado)
        with _cursor() as c:
            c.execute(sql + " ORDER BY c.tipo, c.codigo", params)
            return c.fetchall()

    def resumen(self):
        with _cursor() as c:
            c.execute("SELECT tipo, estado, COUNT(*) AS total FROM celda GROUP BY tipo, estado")
            filas = c.fetchall()
        resumen = {t.value: {e.value: 0 for e in EstadoCelda} for t in TipoVehiculo}
        for f in filas:
            resumen[f["tipo"]][f["estado"]] = f["total"]
        return resumen

    @staticmethod
    def _a_entidad(f):
        return Celda(f["id_celda"], f["codigo"], TipoVehiculo(f["tipo"]), EstadoCelda(f["estado"]),
                     f.get("motivo"))


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
