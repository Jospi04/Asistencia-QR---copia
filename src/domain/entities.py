from datetime import datetime, time
from typing import Optional

class Empresa:
    def __init__(self, id: int = None, nombre: str = "", codigo_empresa: str = ""):
        self.id = id
        self.nombre = nombre
        self.codigo_empresa = codigo_empresa
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None

class Empleado:
    def __init__(self, id: int = None, empresa_id: int = None, nombre: str = "", 
                 dni: str = "", codigo_qr_unico: str = "", telefono: str = "", 
                 correo: str = "", activo: bool = True):
        self.id = id
        self.empresa_id = empresa_id
        self.nombre = nombre
        self.dni = dni
        self.codigo_qr_unico = codigo_qr_unico
        self.telefono = telefono
        self.correo = correo
        self.activo = activo
        self.fecha_registro: Optional[datetime] = None

class HorarioEstandar:
    def __init__(self, id: int = None, empresa_id: int = None,
                 entrada_manana: time = time(6, 50),
                 salida_manana: time = time(12, 50),
                 entrada_tarde: time = time(14, 50),
                 salida_tarde: time = time(18, 50)):
        self.id = id
        self.empresa_id = empresa_id
        self.entrada_manana = entrada_manana
        self.salida_manana = salida_manana
        self.entrada_tarde = entrada_tarde
        self.salida_tarde = salida_tarde

from datetime import datetime, time
from typing import Optional

class Asistencia:
    def __init__(self, id: int = None, empleado_id: int = None, fecha: str = "",
                 entrada_manana_real: time = None, salida_manana_real: time = None,
                 entrada_tarde_real: time = None, salida_tarde_real: time = None,
                 total_horas_trabajadas: float = 0.0, horas_normales: float = 8.0,
                 horas_extras: float = 0.0, estado_dia: str = "INCOMPLETO"):
        self.id = id
        self.empleado_id = empleado_id
        self.fecha = fecha
        self.entrada_manana_real = entrada_manana_real
        self.salida_manana_real = salida_manana_real
        self.entrada_tarde_real = entrada_tarde_real
        self.salida_tarde_real = salida_tarde_real
        self.total_horas_trabajadas = total_horas_trabajadas
        self.horas_normales = horas_normales
        self.horas_extras = horas_extras
        self.estado_dia = estado_dia
        
        # ✅ Nuevos campos para control por turno
        self.asistio_manana: bool = False
        self.asistio_tarde: bool = False
        self.tardanza_manana: bool = False
        self.tardanza_tarde: bool = False
        
        # Campos de auditoría
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None

class Administrador:
    def __init__(self, id: int = None, empresa_id: int = None, nombre: str = "",
                 usuario: str = "", password_hash: str = "", telefono: str = "",
                 correo: str = "", rol: str = "ADMIN_EMPRESA", activo: bool = True):
        self.id = id
        self.empresa_id = empresa_id
        self.nombre = nombre
        self.usuario = usuario
        self.password_hash = password_hash
        self.telefono = telefono
        self.correo = correo
        self.rol = rol
        self.activo = activo
        self.created_at: Optional[datetime] = None

class ConfigAlertas:
    def __init__(self, id: int = None, empresa_id: int = None,
                 numero_faltas_para_alerta: int = 4,
                 mensaje_whatsapp_falta: str = "",
                 mensaje_whatsapp_admin: str = "", activo: bool = True):
        self.id = id
        self.empresa_id = empresa_id
        self.numero_faltas_para_alerta = numero_faltas_para_alerta
        self.mensaje_whatsapp_falta = mensaje_whatsapp_falta
        self.mensaje_whatsapp_admin = mensaje_whatsapp_admin
        self.activo = activo

class EscaneoTracking:
    def __init__(self, id: int = None, codigo_qr: str = "", ip_address: str = ""):
        self.id = id
        self.codigo_qr = codigo_qr
        self.ip_address = ip_address
        self.timestamp_escaneo: Optional[datetime] = None            # VACACIONES, PERMISO, DESCANSO

