"""Pruebas de la iteración 3: gestión de pagos (casos CP-15 a CP-26 del plan de pruebas)."""
from datetime import date, timedelta

from app.negocio.pago_servicio import sumar_un_mes
from tests.conftest import entrar


def html(respuesta):
    return respuesta.get_data(as_text=True)


def pagar(cliente, placa, mensualidad, medio="EFECTIVO", recibido="", referencia=""):
    return cliente.post("/pagos/nuevo", data={"placa": placa, "mensualidad": mensualidad, "medio": medio,
                                              "valor_recibido": recibido, "referencia": referencia,
                                              "accion": "pagar"}, follow_redirects=True)


def test_cp15_pagar_en_efectivo_calcula_cambio_y_permite_entrada(cliente):
    entrar(cliente)
    r = cliente.get("/pagos/nuevo?placa=xyz789")
    assert "Andrés Rojas" in html(r) and "$180.000" in html(r) and "Pendiente de pago" in html(r)
    r = pagar(cliente, "XYZ789", "2", recibido="200000")
    assert "Pago registrado. Recibo RC-000004" in html(r)
    assert "Cambio" in html(r) and "$20.000" in html(r) and "Carlos Pérez" in html(r)
    assert "Entrada registrada" in html(cliente.post("/entrada", data={"placa": "XYZ789", "accion": "confirmar"}))


def test_cp16_entrada_rechazada_si_la_mensualidad_no_esta_pagada(cliente):
    entrar(cliente)
    r = cliente.post("/entrada", data={"placa": "XYZ789", "accion": "validar"})
    assert "La mensualidad está pendiente de pago" in html(r)
    assert "Mensualidad vencida" in html(cliente.post("/entrada", data={"placa": "DEF456", "accion": "validar"}))


def test_cp17_validaciones_del_pago(cliente):
    entrar(cliente)
    assert "menor que el valor a pagar" in html(pagar(cliente, "XYZ789", "2", recibido="100000"))
    assert "Escribe el valor recibido" in html(pagar(cliente, "XYZ789", "2", recibido="cien"))
    assert "número de aprobación" in html(pagar(cliente, "XYZ789", "2", medio="TARJETA"))
    assert "No escribas el número de la tarjeta" in html(
        pagar(cliente, "XYZ789", "2", medio="TARJETA", referencia="4111111111111111"))
    assert "Selecciona el medio de pago" in html(pagar(cliente, "XYZ789", "2", medio="CHEQUE"))
    assert "Pendiente de pago" in html(cliente.get("/pagos/pendientes"))  # nada se guardó


def test_cp18_pagar_con_tarjeta_o_transferencia(cliente):
    entrar(cliente)
    r = pagar(cliente, "XYZ789", "2", medio="TARJETA", referencia="APR 7781")
    assert "Recibo RC-000004" in html(r) and "aprobación APR7781" in html(r) and "Cambio" not in html(r)


def test_cp19_cobrar_la_siguiente_mensualidad(cliente):
    entrar(cliente)
    fin_actual = date.today() + timedelta(days=20)
    inicio = fin_actual + timedelta(days=1)
    r = cliente.get("/pagos/nuevo?placa=ABC123")
    assert "siguiente mensualidad" in html(r) and inicio.strftime("%d/%m/%Y") in html(r)
    assert sumar_un_mes(inicio).strftime("%d/%m/%Y") in html(r)
    r = pagar(cliente, "ABC123", "siguiente", medio="TRANSFERENCIA", referencia="NEQ99001")
    assert "Pago registrado" in html(r) and inicio.strftime("%d/%m/%Y") in html(r)
    r = cliente.get("/usuarios/1")
    assert html(r).count(">Pagada<") == 2


def test_cp20_no_se_paga_dos_veces_la_misma_mensualidad(cliente):
    entrar(cliente)
    pagar(cliente, "XYZ789", "2", recibido="180000")
    assert "Selecciona una mensualidad pendiente" in html(pagar(cliente, "XYZ789", "2", recibido="180000"))
    assert "Selecciona una mensualidad pendiente" in html(pagar(cliente, "ABC123", "1", recibido="180000"))


def test_cp21_pago_rechazado_para_vehiculo_no_valido(cliente):
    entrar(cliente, "admin", "admin123")
    assert "Vehículo no registrado" in html(cliente.get("/pagos/nuevo?placa=ZZZ999"))
    cliente.post("/usuarios/2/estado", data={"activo": "0"})
    assert "El usuario propietario está inactivo" in html(cliente.get("/pagos/nuevo?placa=XYZ789"))
    assert "El usuario propietario está inactivo" in html(pagar(cliente, "XYZ789", "2", recibido="180000"))


def test_cp22_consultar_e_imprimir_recibo(cliente):
    entrar(cliente)
    r = cliente.get("/pagos/1")
    for texto in ("RC-000001", "Laura Gómez", "ABC123", "Efectivo", "$200.000", "$20.000", "Imprimir recibo"):
        assert texto in html(r)
    assert "Anular pago" not in html(r)  # el operador no ve la opción de anular


def test_cp23_consultar_pagos_y_recaudo(cliente):
    entrar(cliente)
    pagar(cliente, "XYZ789", "2", recibido="180000")
    pagar(cliente, "ABC123", "siguiente", medio="TARJETA", referencia="APR1234")
    r = cliente.get("/pagos")  # por defecto, los pagos de hoy
    assert "RC-000004" in html(r) and "RC-000005" in html(r) and "RC-000001" not in html(r)
    assert "$360.000" in html(r) and "2 pago(s)" in html(r)
    r = cliente.get("/pagos?desde=&hasta=&medio=TARJETA")
    assert "RC-000005" in html(r) and "RC-000003" in html(r) and "RC-000004" not in html(r)
    r = cliente.get("/pagos?desde=&hasta=&texto=MOT45A")
    assert "RC-000002" in html(r) and "$90.000" in html(r) and "RC-000001" not in html(r)


def test_cp24_pendientes_y_estado_de_cuenta(cliente):
    entrar(cliente)
    r = cliente.get("/pagos/pendientes")
    assert "XYZ789" in html(r) and "Total pendiente: $180.000" in html(r)
    assert "Pendiente de pago" in html(cliente.get("/usuarios/2"))
    pagar(cliente, "XYZ789", "2", recibido="180000")
    r = cliente.get("/pagos/pendientes")
    assert "No hay mensualidades pendientes" in html(r) and "Total pendiente: $0" in html(r)
    assert "RC-000004" in html(cliente.get("/usuarios/2"))


def test_cp25_anular_pago_deja_la_mensualidad_pendiente(cliente):
    entrar(cliente, "admin", "admin123")
    assert "Escribe el motivo" in html(cliente.post("/pagos/1/anular", data={"motivo": " "}, follow_redirects=True))
    r = cliente.post("/pagos/1/anular", data={"motivo": "Se registró en el vehículo equivocado"},
                     follow_redirects=True)
    assert "Pago RC-000001 anulado" in html(r) and "RECIBO ANULADO" in html(r)
    assert "ya está anulado" in html(cliente.post("/pagos/1/anular", data={"motivo": "Otra vez"},
                                                  follow_redirects=True))
    assert "pendiente de pago" in html(cliente.post("/entrada", data={"placa": "ABC123", "accion": "confirmar"}))
    # se puede volver a pagar y el pago anulado se conserva en la lista
    assert "Recibo RC-000004" in html(pagar(cliente, "ABC123", "1", recibido="180000"))
    r = cliente.get("/pagos?desde=&hasta=&texto=ABC123")
    assert "RC-000001" in html(r) and "Anulado" in html(r)


def test_cp26_operador_no_puede_anular_pagos(cliente):
    entrar(cliente)
    r = cliente.post("/pagos/1/anular", data={"motivo": "Prueba de permisos"}, follow_redirects=True)
    assert "Solo el administrador" in html(r)
    assert "RECIBO ANULADO" not in html(cliente.get("/pagos/1"))


def test_sumar_un_mes():
    assert sumar_un_mes(date(2026, 11, 23)) == date(2026, 12, 22)
    assert sumar_un_mes(date(2026, 12, 1)) == date(2026, 12, 31)
    assert sumar_un_mes(date(2027, 1, 31)) == date(2027, 2, 27)
