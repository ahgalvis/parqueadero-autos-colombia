"""Pruebas de la iteración 2: gestión de usuarios y gestión de celdas (ver plan de pruebas)."""
from datetime import date, timedelta

from tests.conftest import entrar


def html(respuesta):
    return respuesta.get_data(as_text=True)


def mensualidad(dias=30):
    hoy = date.today()
    return {"fecha_inicio": hoy.isoformat(), "fecha_fin": (hoy + timedelta(days=dias)).isoformat(), "valor": "180000"}


def nuevo_usuario(cliente, documento="4040404040", nombre="Pedro Ruiz", **extra):
    datos = {"documento": documento, "nombre": nombre, "telefono": "3011112233", "correo": "pedro@correo.com"}
    datos.update(extra)
    return cliente.post("/usuarios/nuevo", data=datos, follow_redirects=True)


# ---------- Gestión de usuarios ----------

def test_cp01_registrar_usuario_y_vehiculo_permite_entrada(cliente):
    entrar(cliente, "admin", "admin123")
    r = nuevo_usuario(cliente)
    assert "Usuario registrado" in html(r) and "Pedro Ruiz" in html(r)
    r = cliente.post("/usuarios/4/vehiculos/nuevo",
                     data={"placa": "ghi789", "tipo": "CARRO", "marca": "Kia", "color": "Azul", **mensualidad()},
                     follow_redirects=True)
    assert "Vehículo y mensualidad registrados" in html(r) and "GHI789" in html(r)
    # Iteración 3: la mensualidad nueva queda pendiente; se paga antes de entrar
    r = cliente.post("/pagos/nuevo", data={"placa": "GHI789", "mensualidad": "5", "medio": "EFECTIVO",
                                           "valor_recibido": "180000", "accion": "pagar"}, follow_redirects=True)
    assert "Pago registrado" in html(r)
    # El vehículo recién registrado ya puede entrar (antes daba "Vehículo no registrado")
    r = cliente.post("/entrada", data={"placa": "GHI789", "accion": "confirmar"})
    assert "Entrada registrada" in html(r)


def test_cp02_documento_duplicado_o_invalido(cliente):
    entrar(cliente, "admin", "admin123")
    assert "Ya existe un usuario con ese documento" in html(nuevo_usuario(cliente, documento="1010101010"))
    assert "solo números" in html(nuevo_usuario(cliente, documento="12AB"))
    assert "El nombre es obligatorio" in html(nuevo_usuario(cliente, nombre=" "))
    assert "correo no tiene un formato válido" in html(nuevo_usuario(cliente, correo="pedro@"))


def test_cp03_buscar_y_editar_usuario(cliente):
    entrar(cliente, "admin", "admin123")
    r = cliente.get("/usuarios?q=laura")
    assert "Laura Gómez" in html(r) and "Andrés Rojas" not in html(r)
    r = cliente.post("/usuarios/1/editar", data={"nombre": "Laura Gómez Díaz", "telefono": "3000000000", "correo": ""},
                     follow_redirects=True)
    assert "Datos actualizados" in html(r) and "Laura Gómez Díaz" in html(r)


def test_cp04_inactivar_usuario_bloquea_entrada(cliente):
    entrar(cliente, "admin", "admin123")
    r = cliente.post("/usuarios/2/estado", data={"activo": "0"}, follow_redirects=True)
    assert "Usuario inactivado" in html(r)
    r = cliente.post("/entrada", data={"placa": "XYZ789", "accion": "confirmar"})
    assert "El usuario propietario está inactivo" in html(r)


def test_cp05_no_inactivar_usuario_con_vehiculo_dentro(cliente):
    entrar(cliente, "admin", "admin123")
    cliente.post("/entrada", data={"placa": "ABC123", "accion": "confirmar"})
    r = cliente.post("/usuarios/1/estado", data={"activo": "0"}, follow_redirects=True)
    assert "tiene un vehículo dentro del parqueadero" in html(r)
    r = cliente.post("/vehiculos/1/estado", data={"activo": "0"}, follow_redirects=True)
    assert "el vehículo está dentro del parqueadero" in html(r)


def test_cp06_placa_repetida_o_que_no_coincide_con_tipo(cliente):
    entrar(cliente, "admin", "admin123")
    r = cliente.post("/usuarios/1/vehiculos/nuevo", data={"placa": "XYZ789", "tipo": "CARRO", **mensualidad()})
    assert "La placa ya está registrada" in html(r)
    r = cliente.post("/usuarios/1/vehiculos/nuevo", data={"placa": "ABC12D", "tipo": "CARRO", **mensualidad()})
    assert "no corresponde a un carro" in html(r)
    r = cliente.post("/usuarios/1/vehiculos/nuevo", data={"placa": "JKL321", "tipo": "CARRO", **mensualidad(-5)})
    assert "fecha de fin debe ser posterior" in html(r)


def test_cp07_retirar_vehiculo_y_renovar_mensualidad(cliente):
    entrar(cliente, "admin", "admin123")
    r = cliente.post("/vehiculos/4/mensualidad", data=mensualidad(), follow_redirects=True)
    assert "Mensualidad registrada" in html(r)
    # Iteración 3: la renovación queda pendiente de pago hasta que se cobra
    r = cliente.post("/pagos/nuevo", data={"placa": "DEF456", "mensualidad": "5", "medio": "EFECTIVO",
                                           "valor_recibido": "180000", "accion": "pagar"}, follow_redirects=True)
    assert "Pago registrado" in html(r)
    assert "Entrada registrada" in html(cliente.post("/entrada", data={"placa": "DEF456", "accion": "confirmar"}))
    cliente.post("/salida", data={"placa": "DEF456", "accion": "confirmar"})
    r = cliente.post("/vehiculos/4/estado", data={"activo": "0"}, follow_redirects=True)
    assert "Vehículo retirado" in html(r)
    assert "Vehículo retirado del sistema" in html(cliente.post("/entrada", data={"placa": "DEF456",
                                                                                   "accion": "confirmar"}))


def test_cp08_operador_solo_consulta_usuarios(cliente):
    entrar(cliente)
    assert "Laura Gómez" in html(cliente.get("/usuarios"))
    r = cliente.get("/usuarios/nuevo", follow_redirects=True)
    assert "Solo el administrador" in html(r)


def test_cp09_cuentas_del_personal(cliente):
    entrar(cliente, "admin", "admin123")
    r = cliente.post("/personal/nuevo", data={"nombre": "Sofía León", "usuario": "sofia", "clave": "sofia123",
                                              "rol": "OPERADOR"}, follow_redirects=True)
    assert "Cuenta creada" in html(r)
    r = cliente.post("/personal/1/editar", data={"nombre": "Administrador General", "rol": "OPERADOR",
                                                 "activo": "1"}, follow_redirects=True)
    assert "No puedes quitarte el rol de administrador" in html(r)
    cliente.get("/logout")
    assert "Sofía León" in html(entrar(cliente, "sofia", "sofia123"))


# ---------- Gestión de celdas ----------

def test_cp10_crear_celda_y_codigo_repetido(cliente):
    entrar(cliente, "admin", "admin123")
    r = cliente.post("/celdas/nueva", data={"codigo": "c-11", "tipo": "CARRO"}, follow_redirects=True)
    assert "Celda C-11 creada" in html(r)
    r = cliente.post("/celdas/nueva", data={"codigo": "C-11", "tipo": "CARRO"})
    assert "Ya existe una celda con ese código" in html(r)
    r = cliente.post("/celdas/nueva", data={"codigo": "11", "tipo": "CARRO"})
    assert "Código inválido" in html(r)


def test_cp11_mapa_muestra_placa_de_celda_ocupada(cliente):
    entrar(cliente)
    cliente.post("/entrada", data={"placa": "MOT45A", "accion": "confirmar"})
    r = cliente.get("/celdas?tipo=MOTO&estado=OCUPADA")
    assert "M-01" in html(r) and "MOT45A" in html(r) and "M-02" not in html(r)


def test_cp12_inhabilitar_celda_no_se_asigna(cliente):
    entrar(cliente, "admin", "admin123")
    r = cliente.post("/celdas/1/inhabilitar", data={"motivo": "Piso en reparación"}, follow_redirects=True)
    assert "Celda C-01 inhabilitada" in html(r) and "Piso en reparación" in html(r)
    r = cliente.post("/entrada", data={"placa": "ABC123", "accion": "confirmar"})
    assert "C-02" in html(r)
    assert "1 inhabilitada" in html(cliente.get("/panel"))
    r = cliente.post("/celdas/1/habilitar", follow_redirects=True)
    assert "Celda C-01 habilitada" in html(r)


def test_cp13_no_modificar_ni_inhabilitar_celda_ocupada(cliente):
    entrar(cliente, "admin", "admin123")
    cliente.post("/entrada", data={"placa": "ABC123", "accion": "confirmar"})
    r = cliente.post("/celdas/1/inhabilitar", data={"motivo": "Prueba"}, follow_redirects=True)
    assert "No se puede inhabilitar una celda ocupada" in html(r)
    r = cliente.post("/celdas/1/editar", data={"codigo": "C-01", "tipo": "MOTO"})
    assert "No se puede modificar una celda ocupada" in html(r)
    r = cliente.post("/celdas/2/inhabilitar", data={"motivo": " "}, follow_redirects=True)
    assert "Escribe el motivo" in html(r)


def test_cp14_operador_no_modifica_celdas(cliente):
    entrar(cliente)
    r = cliente.post("/celdas/nueva", data={"codigo": "C-20", "tipo": "CARRO"}, follow_redirects=True)
    assert "Solo el administrador" in html(r)
