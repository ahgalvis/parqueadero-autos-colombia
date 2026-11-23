# Parqueadero Autos Colombia

Sistema de información para el parqueadero de mensualidades "Autos Colombia".

**Iteración 1: gestión de entrada y salida de vehículos.** Incluye inicio de sesión, registro de entrada (con validación de placa, mensualidad vigente y asignación automática de celda), registro de salida (con liberación de celda y tiempo de permanencia), novedades, vehículos dentro del parqueadero, estado de celdas e historial de movimientos.

**Iteración 2: gestión de usuarios y gestión de celdas.** Incluye registro, búsqueda, edición e inactivación de usuarios (clientes con mensualidad); registro, edición y retiro de sus vehículos con su mensualidad; cuentas del personal (operadores y administradores); y mapa de celdas con creación, modificación, inhabilitación y habilitación de celdas. Una celda inhabilitada no se asigna, y un usuario inactivo o un vehículo retirado no puede entrar.

**Iteración 3: gestión de pagos.** Incluye registrar el pago de una mensualidad (efectivo con cálculo del cambio, tarjeta o transferencia con número de aprobación), cobrar la siguiente mensualidad, recibo con número consecutivo (RC-000001) para imprimir, consulta de pagos con el total recaudado por medio de pago, mensualidades pendientes de pago, estado de cuenta del usuario y anulación de pagos por el administrador (con motivo; el pago no se borra). Desde esta iteración un vehículo solo puede entrar si su mensualidad vigente está **pagada**.

> **Si ya tenías una iteración anterior instalada:** la base de datos cambió (la iteración 3 agrega la tabla `pago`). Vuelve a cargar `bd/autos_colombia.sql` (paso 3) para crear las columnas nuevas. Esto borra los datos de prueba anteriores y los vuelve a crear.

## Tecnologías

- Python 3.10 o superior
- Flask 3 (aplicación web) con plantillas Jinja2 y Bootstrap 5
- MySQL 8 (también funciona con MariaDB)

## Arquitectura

Arquitectura en capas. Cada paquete solo depende de los de abajo:

```
app/
├── presentacion/   Rutas de Flask y plantillas HTML (capa de presentación)
├── negocio/        Servicios con las reglas del parqueadero (capa de negocio)
├── datos/          Repositorios y conexión a MySQL (capa de datos)
├── modelo/         Clases de dominio: Operador, Vehiculo, Celda, Registro...
└── config.py       Parámetros de conexión
bd/autos_colombia.sql   Script del modelo físico con datos de prueba
tests/                  Pruebas automáticas del flujo completo
```

## Instalación (Windows, PowerShell)

Ejecuta los comandos **uno por uno** en PowerShell.

1. Instala [Git](https://git-scm.com/download/win), [Python](https://www.python.org/downloads/) (marca "Add python.exe to PATH") y [MySQL](https://dev.mysql.com/downloads/installer/). Cierra y vuelve a abrir PowerShell después de instalarlos.
2. Clona el repositorio y crea el entorno virtual:

   ```powershell
   cd Documents
   git clone https://github.com/ahgalvis/parqueadero-autos-colombia.git
   cd parqueadero-autos-colombia
   python -m venv venv
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned   # solo la primera vez
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

   Al activar debe aparecer `(venv)` al inicio de la línea.

3. Crea la base de datos. Entra a MySQL (te pide la contraseña de root):

   ```powershell
   mysql -u root -p
   ```

   Si `mysql` no se reconoce, abre "MySQL 8.0 Command Line Client" desde el menú Inicio. Ya dentro (verás `mysql>`), carga el script usando barras `/` y sal:

   ```sql
   SOURCE C:/Users/TU_USUARIO/Documents/parqueadero-autos-colombia/bd/autos_colombia.sql;
   SHOW TABLES FROM autos_colombia;
   exit
   ```

   También puedes abrir `bd/autos_colombia.sql` en MySQL Workbench y ejecutarlo con el rayo.

4. Indica tu contraseña de MySQL (se debe repetir cada vez que abras PowerShell) y ejecuta la aplicación:

   ```powershell
   $env:DB_PASSWORD="tu_clave_de_mysql"
   python run.py
   ```

   Abre http://127.0.0.1:5000

   Variables disponibles: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `SECRET_KEY`.

### macOS / Linux

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
mysql -u root -p < bd/autos_colombia.sql
export DB_PASSWORD=tu_clave_de_mysql
python run.py
```

## Usuarios de prueba

| Usuario | Contraseña | Rol |
|---|---|---|
| admin | admin123 | Administrador |
| operador | operador123 | Operador |

Placas de prueba: `ABC123` (carro, mensualidad vigente y pagada), `XYZ789` (carro, mensualidad vigente **sin pagar**: no puede entrar hasta registrar el pago), `MOT45A` (moto, vigente y pagada), `DEF456` (mensualidad vencida).

## Pruebas

Las pruebas recrean la base de datos `autos_colombia` desde el script, así que borran los datos que tengas:

```bash
python -m pytest
```

`tests/test_flujo.py` cubre la iteración 1, `tests/test_usuarios_celdas.py` la iteración 2 (casos CP-01 a CP-14) y `tests/test_pagos.py` la iteración 3 (casos CP-15 a CP-26). En total son 35 pruebas.

## Trazabilidad

| Historia de usuario | Ruta | Servicio |
|---|---|---|
| HU-01 Iniciar sesión | `/login` | `AutenticacionServicio` |
| HU-02 Registrar entrada | `/entrada` | `RegistroServicio.registrar_entrada` |
| HU-03 Registrar salida | `/salida` | `RegistroServicio.registrar_salida` |
| HU-04 Vehículos en parqueadero | `/vehiculos` | `ConsultaServicio.vehiculos_dentro` |
| HU-05 Estado de celdas | `/panel` | `ConsultaServicio.resumen_celdas` |
| HU-06 Registrar novedad | `/novedad` | `NovedadServicio` |
| HU-07 Historial | `/historial` | `ConsultaServicio.historial` |
| HU-08 Registrar usuario | `/usuarios/nuevo` | `UsuarioServicio.registrar` |
| HU-09 Consultar y actualizar usuario | `/usuarios`, `/usuarios/<id>/editar` | `UsuarioServicio.listar`, `actualizar` |
| HU-10 Inactivar o activar usuario | `/usuarios/<id>/estado` | `UsuarioServicio.cambiar_estado` |
| HU-11 Registrar vehículo y mensualidad | `/usuarios/<id>/vehiculos/nuevo` | `UsuarioServicio.registrar_vehiculo` |
| HU-12 Actualizar o retirar vehículo | `/vehiculos/<id>/editar`, `/vehiculos/<id>/estado`, `/vehiculos/<id>/mensualidad` | `UsuarioServicio.actualizar_vehiculo`, `cambiar_estado_vehiculo`, `renovar_mensualidad` |
| HU-13 Gestionar cuentas del personal | `/personal` | `PersonalServicio` |
| HU-14 Registrar y modificar celdas | `/celdas/nueva`, `/celdas/<id>/editar` | `CeldaServicio.registrar`, `modificar` |
| HU-15 Consultar mapa de celdas | `/celdas` | `CeldaServicio.mapa` |
| HU-16 Inhabilitar y habilitar celda | `/celdas/<id>/inhabilitar`, `/celdas/<id>/habilitar` | `CeldaServicio.inhabilitar`, `habilitar` |
| HU-17 Registrar pago de mensualidad | `/pagos/nuevo` | `PagoServicio.cuenta_de_placa`, `registrar_pago` |
| HU-18 Cobrar la siguiente mensualidad | `/pagos/nuevo` (opción “siguiente”) | `PagoServicio.siguiente_mensualidad` |
| HU-19 Consultar e imprimir recibo | `/pagos/<id>` | `PagoServicio.recibo` |
| HU-20 Consultar pagos y recaudo | `/pagos` | `PagoServicio.listar` |
| HU-21 Pendientes de pago y estado de cuenta | `/pagos/pendientes`, `/usuarios/<id>` | `PagoServicio.pendientes`, `estado_cuenta` |
| HU-22 Anular pago | `/pagos/<id>/anular` | `PagoServicio.anular` |
| HU-23 Validar pago en la entrada | `/entrada` | `RegistroServicio.validar_entrada` |
