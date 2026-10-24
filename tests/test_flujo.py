from tests.conftest import entrar


def html(respuesta):
    return respuesta.get_data(as_text=True)


def test_login_incorrecto(cliente):
    assert "Usuario o contraseña incorrectos" in html(entrar(cliente, clave="mala"))


def test_pantallas_requieren_sesion(cliente):
    assert cliente.get("/entrada").headers["Location"].endswith("/login")


def test_entrada_y_salida(cliente):
    entrar(cliente)
    r = cliente.post("/entrada", data={"placa": "abc123", "accion": "validar"})
    assert "Laura Gómez" in html(r) and "Vigente hasta" in html(r)

    r = cliente.post("/entrada", data={"placa": "ABC123", "accion": "confirmar"})
    assert "Entrada registrada" in html(r) and "C-01" in html(r)
    assert "9</span> libres" in html(cliente.get("/panel"))

    r = cliente.post("/entrada", data={"placa": "ABC123", "accion": "confirmar"})
    assert "ya se encuentra en el parqueadero" in html(r)

    cliente.post("/novedad", data={"placa": "ABC123", "descripcion": "Rayón puerta derecha"})
    r = cliente.post("/salida", data={"placa": "ABC123", "accion": "validar"})
    assert "Rayón puerta derecha" in html(r)

    r = cliente.post("/salida", data={"placa": "ABC123", "accion": "confirmar"})
    assert "Salida registrada" in html(r) and "Permanencia" in html(r)
    assert "10</span> libres" in html(cliente.get("/panel"))


def test_rechazos_de_entrada(cliente):
    entrar(cliente)
    casos = {
        "ZZZ999": "Vehículo no registrado",
        "DEF456": "Mensualidad vencida",
        "12ABC": "Formato de placa inválido",
    }
    for placa, mensaje in casos.items():
        assert mensaje in html(cliente.post("/entrada", data={"placa": placa, "accion": "confirmar"}))


def test_moto_usa_celda_de_moto(cliente):
    entrar(cliente)
    r = cliente.post("/entrada", data={"placa": "MOT45A", "accion": "confirmar"})
    assert "M-01" in html(r)


def test_salida_sin_entrada(cliente):
    entrar(cliente)
    r = cliente.post("/salida", data={"placa": "XYZ789", "accion": "validar"})
    assert "no se encuentra en el parqueadero" in html(r)


def test_novedad_sin_descripcion(cliente):
    entrar(cliente)
    cliente.post("/entrada", data={"placa": "XYZ789", "accion": "confirmar"})
    r = cliente.post("/novedad", data={"placa": "XYZ789", "descripcion": "  "})
    assert "La descripción es obligatoria" in html(r)


def test_historial_solo_administrador(cliente):
    entrar(cliente)
    r = cliente.get("/historial", follow_redirects=True)
    assert "Solo el administrador" in html(r)

    cliente.get("/logout")
    entrar(cliente, "admin", "admin123")
    cliente.post("/entrada", data={"placa": "ABC123", "accion": "confirmar"})
    r = cliente.get("/historial?placa=ABC")
    assert "ABC123" in html(r) and "En el parqueadero" in html(r)
