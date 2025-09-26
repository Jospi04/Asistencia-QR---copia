USE sistema_asistencia_qr;

-- Tabla EMPRESAS
CREATE TABLE empresas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    codigo_empresa VARCHAR(50) UNIQUE NOT NULL,
    correo_admin VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Tabla EMPLEADOS
CREATE TABLE empleados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    dni VARCHAR(20),
    telefono VARCHAR(20),
    correo VARCHAR(100),
    codigo_qr_unico VARCHAR(100) UNIQUE NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- Tabla ASISTENCIA
CREATE TABLE asistencia (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empleado_id INT NOT NULL,
    fecha DATE NOT NULL,
    entrada_manana_real TIME,
    salida_manana_real TIME,
    entrada_tarde_real TIME,
    salida_tarde_real TIME,
    total_horas_trabajadas DECIMAL(5,2) DEFAULT 0,
    horas_normales DECIMAL(5,2) DEFAULT 8.00,
    horas_extras DECIMAL(5,2) DEFAULT 0,
    estado_dia ENUM('COMPLETO', 'INCOMPLETO', 'FALTA') DEFAULT 'FALTA',
    asistio_manana BOOLEAN DEFAULT FALSE,
    asistio_tarde BOOLEAN DEFAULT FALSE,
    tardanza_manana BOOLEAN DEFAULT FALSE,
    tardanza_tarde BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (empleado_id) REFERENCES empleados(id),
    UNIQUE(empleado_id, fecha)
);

-- Tabla ALERTAS_ENVIADAS
CREATE TABLE alertas_enviadas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empleado_id INT NOT NULL,
    numero INT NOT NULL,
    tipo ENUM('falta', 'tardanza') NOT NULL,
    fecha_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empleado_id) REFERENCES empleados(id)
);

-- Tabla ESCANEOS_TRACKING
CREATE TABLE escaneos_tracking (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo_qr VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45),
    timestamp_escaneo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_codigo_fecha (codigo_qr, timestamp_escaneo)
);

-- Tabla ADMINISTRADORES
CREATE TABLE administradores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id INT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    usuario VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    telefono VARCHAR(20),
    correo VARCHAR(100),
    rol ENUM('superadmin', 'admin_empresa') DEFAULT 'admin_empresa',
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);

-- Tabla CONFIG_ALERTAS
CREATE TABLE config_alertas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empresa_id INT NOT NULL,
    numero_faltas_para_alerta INT DEFAULT 3,
    numero_tardanzas_para_alerta INT DEFAULT 3,
    mensaje_correo_falta TEXT,
    mensaje_correo_tardanza TEXT,
    mensaje_correo_admin TEXT,
    activo BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id)
);