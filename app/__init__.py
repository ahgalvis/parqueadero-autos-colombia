from flask import Flask

from app.config import Config
from app.datos import conexion
from app.datos.repositorios import OperadorRepositorio


def create_app(config=Config):
    app = Flask(__name__, template_folder="presentacion/templates")
    app.config.from_object(config)
    conexion.iniciar(app)

    from app.presentacion.rutas_auth import bp as auth_bp
    from app.presentacion.rutas_movimientos import bp as movimientos_bp
    from app.presentacion.rutas_consultas import bp as consultas_bp
    from app.presentacion.rutas_usuarios import bp as usuarios_bp
    from app.presentacion.rutas_celdas import bp as celdas_bp
    from app.presentacion.rutas_personal import bp as personal_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(movimientos_bp)
    app.register_blueprint(consultas_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(celdas_bp)
    app.register_blueprint(personal_bp)

    from app.presentacion.seguridad import operador_actual
    app.context_processor(lambda: {"operador": operador_actual()})

    with app.app_context():
        # Los datos de prueba traen la clave 'PENDIENTE'; aquí se reemplaza por un hash real.
        OperadorRepositorio().inicializar_claves_pendientes()
    return app
