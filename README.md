# Parqueadero Autos Colombia

Sistema de información para el parqueadero de mensualidades "Autos Colombia".

**Iteración 1: gestión de entrada y salida de vehículos.** Incluye inicio de sesión, registro de entrada (con validación de placa, mensualidad vigente y asignación automática de celda), registro de salida (con liberación de celda y tiempo de permanencia), novedades, vehículos dentro del parqueadero, estado de celdas e historial de movimientos.

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

Placas de prueba: `ABC123`, `XYZ789` (carros vigentes), `MOT45A` (moto vigente), `DEF456` (mensualidad vencida).

## Pruebas

Las pruebas recrean la base de datos `autos_colombia` desde el script, así que borran los datos que tengas:

```bash
python -m pytest
```

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
