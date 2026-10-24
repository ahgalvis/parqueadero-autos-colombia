from app.datos.repositorios import CeldaRepositorio, RegistroRepositorio


class ConsultaServicio:
    def __init__(self):
        self.registros = RegistroRepositorio()
        self.celdas = CeldaRepositorio()

    def vehiculos_dentro(self, placa=None):
        return self.registros.vehiculos_dentro((placa or "").strip().upper() or None)

    def resumen_celdas(self):
        return self.celdas.resumen()

    def historial(self, placa=None, desde=None, hasta=None):
        return self.registros.historial((placa or "").strip().upper() or None, desde or None, hasta or None)
