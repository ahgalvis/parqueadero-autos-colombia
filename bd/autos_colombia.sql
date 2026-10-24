-- =============================================================
-- Parqueadero "Autos Colombia" - Modelo físico (MySQL 8)
-- Iteración 1: Gestión de entrada y salida de vehículos
-- =============================================================
DROP DATABASE IF EXISTS autos_colombia;
CREATE DATABASE autos_colombia CHARACTER SET utf8mb4 COLLATE utf8mb4_spanish_ci;
USE autos_colombia;

-- Personal del parqueadero que usa el sistema (RF-01)
CREATE TABLE operador (
  id_operador      INT AUTO_INCREMENT PRIMARY KEY,
  nombre           VARCHAR(100) NOT NULL,
  usuario          VARCHAR(30)  NOT NULL UNIQUE,
  contrasena_hash  VARCHAR(255) NOT NULL,
  rol              ENUM('OPERADOR','ADMINISTRADOR') NOT NULL DEFAULT 'OPERADOR',
  activo           BOOLEAN NOT NULL DEFAULT TRUE
);

-- Cliente con mensualidad (CRUD completo en iteración 2)
CREATE TABLE usuario (
  id_usuario  INT AUTO_INCREMENT PRIMARY KEY,
  documento   VARCHAR(20)  NOT NULL UNIQUE,
  nombre      VARCHAR(100) NOT NULL,
  telefono    VARCHAR(20),
  correo      VARCHAR(100)
);

CREATE TABLE vehiculo (
  id_vehiculo  INT AUTO_INCREMENT PRIMARY KEY,
  placa        VARCHAR(6)  NOT NULL UNIQUE,
  tipo         ENUM('CARRO','MOTO') NOT NULL,
  marca        VARCHAR(40),
  color        VARCHAR(30),
  id_usuario   INT NOT NULL,
  CONSTRAINT fk_vehiculo_usuario FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario),
  -- RNF-04: carro AAA123, moto AAA12A
  CONSTRAINT chk_placa CHECK (
    (tipo = 'CARRO' AND placa REGEXP '^[A-Z]{3}[0-9]{3}$') OR
    (tipo = 'MOTO'  AND placa REGEXP '^[A-Z]{3}[0-9]{2}[A-Z]$')
  )
);

-- Mensualidad del vehículo (RF-03). Los pagos se detallan en iteración 3.
CREATE TABLE mensualidad (
  id_mensualidad  INT AUTO_INCREMENT PRIMARY KEY,
  id_vehiculo     INT NOT NULL,
  fecha_inicio    DATE NOT NULL,
  fecha_fin       DATE NOT NULL,
  valor           DECIMAL(10,2) NOT NULL,
  CONSTRAINT fk_mensualidad_vehiculo FOREIGN KEY (id_vehiculo) REFERENCES vehiculo(id_vehiculo),
  CONSTRAINT chk_fechas CHECK (fecha_fin >= fecha_inicio)
);

CREATE TABLE celda (
  id_celda  INT AUTO_INCREMENT PRIMARY KEY,
  codigo    VARCHAR(10) NOT NULL UNIQUE,
  tipo      ENUM('CARRO','MOTO') NOT NULL,
  estado    ENUM('LIBRE','OCUPADA') NOT NULL DEFAULT 'LIBRE'
);

-- Cada estancia: una entrada y (cuando ocurra) su salida (RF-02, RF-06)
CREATE TABLE registro (
  id_registro          INT AUTO_INCREMENT PRIMARY KEY,
  id_vehiculo          INT NOT NULL,
  id_celda             INT NOT NULL,
  fecha_hora_entrada   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_hora_salida    DATETIME NULL,
  id_operador_entrada  INT NOT NULL,
  id_operador_salida   INT NULL,
  -- Columnas auxiliares: solo tienen valor mientras la estancia está abierta
  vehiculo_abierto INT GENERATED ALWAYS AS (IF(fecha_hora_salida IS NULL, id_vehiculo, NULL)) STORED,
  celda_abierta    INT GENERATED ALWAYS AS (IF(fecha_hora_salida IS NULL, id_celda, NULL)) STORED,
  CONSTRAINT fk_registro_vehiculo FOREIGN KEY (id_vehiculo) REFERENCES vehiculo(id_vehiculo),
  CONSTRAINT fk_registro_celda    FOREIGN KEY (id_celda)    REFERENCES celda(id_celda),
  CONSTRAINT fk_registro_op_ent   FOREIGN KEY (id_operador_entrada) REFERENCES operador(id_operador),
  CONSTRAINT fk_registro_op_sal   FOREIGN KEY (id_operador_salida)  REFERENCES operador(id_operador),
  CONSTRAINT uq_vehiculo_abierto UNIQUE (vehiculo_abierto), -- RF-04: sin doble entrada
  CONSTRAINT uq_celda_abierta    UNIQUE (celda_abierta),    -- RNF-04: una celda, un vehículo
  CONSTRAINT chk_salida CHECK (fecha_hora_salida IS NULL OR fecha_hora_salida >= fecha_hora_entrada)
);

-- Novedades ocurridas durante una estancia (RF-10)
CREATE TABLE novedad (
  id_novedad   INT AUTO_INCREMENT PRIMARY KEY,
  id_registro  INT NOT NULL,
  descripcion  VARCHAR(500) NOT NULL,
  fecha_hora   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  id_operador  INT NOT NULL,
  CONSTRAINT fk_novedad_registro FOREIGN KEY (id_registro) REFERENCES registro(id_registro),
  CONSTRAINT fk_novedad_operador FOREIGN KEY (id_operador) REFERENCES operador(id_operador)
);

CREATE INDEX idx_registro_entrada ON registro (fecha_hora_entrada);

-- =============================================================
-- Datos de prueba
-- Contraseñas: se generan desde la aplicación (hash). Aquí van
-- valores de ejemplo que la app reemplaza al iniciar.
-- =============================================================
INSERT INTO operador (nombre, usuario, contrasena_hash, rol) VALUES
 ('Administrador General', 'admin', 'PENDIENTE', 'ADMINISTRADOR'),
 ('Carlos Pérez',          'operador', 'PENDIENTE', 'OPERADOR');

INSERT INTO usuario (documento, nombre, telefono, correo) VALUES
 ('1010101010', 'Laura Gómez',   '3001234567', 'laura@correo.com'),
 ('2020202020', 'Andrés Rojas',  '3109876543', 'andres@correo.com'),
 ('3030303030', 'María Torres',  '3205551234', 'maria@correo.com');

INSERT INTO vehiculo (placa, tipo, marca, color, id_usuario) VALUES
 ('ABC123', 'CARRO', 'Mazda',     'Rojo',   1),
 ('XYZ789', 'CARRO', 'Chevrolet', 'Gris',   2),
 ('MOT45A', 'MOTO',  'Yamaha',    'Negro',  3),
 ('DEF456', 'CARRO', 'Renault',   'Blanco', 3);

-- DEF456 tiene la mensualidad vencida para probar HU-02 criterio 3
INSERT INTO mensualidad (id_vehiculo, fecha_inicio, fecha_fin, valor) VALUES
 (1, CURDATE() - INTERVAL 10 DAY, CURDATE() + INTERVAL 20 DAY, 180000),
 (2, CURDATE() - INTERVAL 5 DAY,  CURDATE() + INTERVAL 25 DAY, 180000),
 (3, CURDATE() - INTERVAL 3 DAY,  CURDATE() + INTERVAL 27 DAY,  90000),
 (4, CURDATE() - INTERVAL 40 DAY, CURDATE() - INTERVAL 10 DAY, 180000);

INSERT INTO celda (codigo, tipo) VALUES
 ('C-01','CARRO'),('C-02','CARRO'),('C-03','CARRO'),('C-04','CARRO'),('C-05','CARRO'),
 ('C-06','CARRO'),('C-07','CARRO'),('C-08','CARRO'),('C-09','CARRO'),('C-10','CARRO'),
 ('M-01','MOTO'),('M-02','MOTO'),('M-03','MOTO'),('M-04','MOTO'),('M-05','MOTO');
