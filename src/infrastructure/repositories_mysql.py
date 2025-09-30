from typing import List, Optional
from datetime import datetime, timedelta, time
from .mysql_connection import MySQLConnection
from src.domain.repositories import *
from src.domain.entities import *
import hashlib  # ✅ Para verificar contraseñas

# ✅ Función de ayuda para convertir cualquier tipo de hora de MySQL a time
def convertir_a_time(valor) -> Optional[time]:
    """
    Convierte un valor de MySQL (puede ser time, timedelta, str o None) a datetime.time
    """
    if valor is None:
        return None
    if isinstance(valor, time):
        return valor
    if isinstance(valor, timedelta):
        total_seconds = int(valor.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        # Asegurar que las horas estén en rango 0-23 (por si acaso)
        hours = hours % 24
        return time(hours, minutes, seconds)
    if isinstance(valor, str):
        try:
            # Intentar parsear 'HH:MM:SS'
            parts = valor.split(':')
            if len(parts) >= 2:
                h = int(parts[0])
                m = int(parts[1])
                s = int(parts[2]) if len(parts) > 2 else 0
                return time(h % 24, m, s)
        except:
            return None
    return None

class EmpresaRepositoryMySQL(EmpresaRepository):
    def __init__(self, db_connection: MySQLConnection):
        self.db = db_connection
    
    def get_all(self) -> List[Empresa]:
        query = "SELECT * FROM EMPRESAS ORDER BY nombre"
        results = self.db.execute_query(query)
        if not results:
            return []
        
        empresas = []
        for row in results:
            empresa = Empresa(
                id=row['id'],
                nombre=row['nombre'],
                codigo_empresa=row['codigo_empresa']
            )
            empresa.created_at = row.get('created_at')
            empresa.updated_at = row.get('updated_at')
            empresas.append(empresa)
        return empresas
    
    def get_by_id(self, id: int) -> Optional[Empresa]:
        query = "SELECT * FROM EMPRESAS WHERE id = %s"
        results = self.db.execute_query(query, (id,))
        if not results:
            return None
        
        row = results[0]
        empresa = Empresa(
            id=row['id'],
            nombre=row['nombre'],
            codigo_empresa=row['codigo_empresa']
        )
        empresa.created_at = row.get('created_at')
        empresa.updated_at = row.get('updated_at')
        return empresa
    
    def create(self, empresa: Empresa) -> Empresa:
        query = """
            INSERT INTO EMPRESAS (nombre, codigo_empresa) 
            VALUES (%s, %s)
        """
        empresa_id = self.db.execute_insert(query, (empresa.nombre, empresa.codigo_empresa))
        if empresa_id:
            empresa.id = empresa_id
        return empresa
    
    def update(self, empresa: Empresa) -> Empresa:
        query = """
            UPDATE EMPRESAS 
            SET nombre = %s, codigo_empresa = %s 
            WHERE id = %s
        """
        self.db.execute_update(query, (empresa.nombre, empresa.codigo_empresa, empresa.id))
        return empresa
    
    def delete(self, id: int) -> bool:
        query = "DELETE FROM EMPRESAS WHERE id = %s"
        return self.db.execute_update(query, (id,))

class EmpleadoRepositoryMySQL(EmpleadoRepository):
    def __init__(self, db_connection: MySQLConnection):
        self.db = db_connection
    
    def get_all(self) -> List[Empleado]:
        query = "SELECT * FROM EMPLEADOS WHERE activo = TRUE ORDER BY nombre"
        results = self.db.execute_query(query)
        if not results:
            return []
        
        empleados = []
        for row in results:
            empleado = Empleado(
                id=row['id'],
                empresa_id=row['empresa_id'],
                nombre=row['nombre'],
                dni=row['dni'],
                codigo_qr_unico=row['codigo_qr_unico'],
                telefono=row['telefono'],
                correo=row['correo'],
                activo=row['activo']
            )
            empleado.fecha_registro = row.get('fecha_registro')
            empleados.append(empleado)
        return empleados
    
    def get_by_id(self, id: int) -> Optional[Empleado]:
        query = "SELECT * FROM EMPLEADOS WHERE id = %s AND activo = TRUE"
        results = self.db.execute_query(query, (id,))
        if not results:
            return None
        
        row = results[0]
        empleado = Empleado(
            id=row['id'],
            empresa_id=row['empresa_id'],
            nombre=row['nombre'],
            dni=row['dni'],
            codigo_qr_unico=row['codigo_qr_unico'],
            telefono=row['telefono'],
            correo=row['correo'],
            activo=row['activo']
        )
        empleado.fecha_registro = row.get('fecha_registro')
        return empleado
    
    def get_by_empresa_id(self, empresa_id: int) -> List[Empleado]:
        query = "SELECT * FROM EMPLEADOS WHERE empresa_id = %s AND activo = TRUE ORDER BY nombre"
        results = self.db.execute_query(query, (empresa_id,))
        if not results:
            return []
        
        empleados = []
        for row in results:
            empleado = Empleado(
                id=row['id'],
                empresa_id=row['empresa_id'],
                nombre=row['nombre'],
                dni=row['dni'],
                codigo_qr_unico=row['codigo_qr_unico'],
                telefono=row['telefono'],
                correo=row['correo'],
                activo=row['activo']
            )
            empleado.fecha_registro = row.get('fecha_registro')
            empleados.append(empleado)
        return empleados
    
    def get_by_codigo_qr(self, codigo_qr: str) -> Optional[Empleado]:
        query = "SELECT * FROM EMPLEADOS WHERE codigo_qr_unico = %s AND activo = TRUE"
        results = self.db.execute_query(query, (codigo_qr,))
        if not results:
            return None
        
        row = results[0]
        empleado = Empleado(
            id=row['id'],
            empresa_id=row['empresa_id'],
            nombre=row['nombre'],
            dni=row['dni'],
            codigo_qr_unico=row['codigo_qr_unico'],
            telefono=row['telefono'],
            correo=row['correo'],
            activo=row['activo']
        )
        empleado.fecha_registro = row.get('fecha_registro')
        return empleado
    
    def create(self, empleado: Empleado) -> Empleado:
        query = """
            INSERT INTO EMPLEADOS (empresa_id, nombre, dni, codigo_qr_unico, telefono, correo) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        empleado_id = self.db.execute_insert(query, (
            empleado.empresa_id, empleado.nombre, empleado.dni,
            empleado.codigo_qr_unico, empleado.telefono, empleado.correo
        ))
        if empleado_id:
            empleado.id = empleado_id
        return empleado
    
    def update(self, empleado: Empleado) -> Empleado:
        query = """
            UPDATE EMPLEADOS 
            SET empresa_id = %s, nombre = %s, dni = %s, 
                telefono = %s, correo = %s, activo = %s 
            WHERE id = %s
        """
        self.db.execute_update(query, (
            empleado.empresa_id, empleado.nombre, empleado.dni,
            empleado.telefono, empleado.correo, empleado.activo, empleado.id
        ))
        return empleado
    
    def delete(self, id: int) -> bool:
        """ELIMINACIÓN COMPLETA de la base de datos"""
        try:
            # Eliminar registros relacionados primero (en orden de dependencia)
            queries = [
                "DELETE FROM ALERTAS_ENVIADAS WHERE empleado_id = %s",
                "DELETE FROM ASISTENCIA WHERE empleado_id = %s",
                "DELETE FROM ESCANEOS_TRACKING WHERE codigo_qr IN (SELECT codigo_qr_unico FROM EMPLEADOS WHERE id = %s)",
                "DELETE FROM EMPLEADOS WHERE id = %s"
            ]
            
            for query in queries:
                self.db.execute_update(query, (id,))
            
            return True
        except Exception as e:
            print(f"Error eliminando empleado {id}: {e}")
            return False

class AsistenciaRepositoryMySQL(AsistenciaRepository):
    def __init__(self, db_connection: MySQLConnection):
        self.db = db_connection
    
    def get_by_empleado_and_fecha(self, empleado_id: int, fecha: str) -> Optional[Asistencia]:
        query = """
            SELECT * FROM ASISTENCIA 
            WHERE empleado_id = %s AND fecha = %s
        """
        results = self.db.execute_query(query, (empleado_id, fecha))
        if not results:
            return None
        
        row = results[0]
        asistencia = Asistencia(
            id=row['id'],
            empleado_id=row['empleado_id'],
            fecha=str(row['fecha']),
            entrada_manana_real=convertir_a_time(row['entrada_manana_real']),
            salida_manana_real=convertir_a_time(row['salida_manana_real']),
            entrada_tarde_real=convertir_a_time(row['entrada_tarde_real']),
            salida_tarde_real=convertir_a_time(row['salida_tarde_real']),
            total_horas_trabajadas=float(row['total_horas_trabajadas'] or 0),
            horas_normales=float(row['horas_normales'] or 8),
            horas_extras=float(row['horas_extras'] or 0),
            estado_dia=row['estado_dia']
        )
        asistencia.created_at = row.get('created_at')
        asistencia.updated_at = row.get('updated_at')
        return asistencia
    
    def get_by_fecha(self, fecha: str) -> List[Asistencia]:
        query = """
            SELECT * FROM ASISTENCIA 
            WHERE fecha = %s
            ORDER BY empleado_id
        """
        results = self.db.execute_query(query, (fecha,))
        if not results:
            return []
        
        asistencias = []
        for row in results:
            asistencia = Asistencia(
                id=row['id'],
                empleado_id=row['empleado_id'],
                fecha=str(row['fecha']),
                entrada_manana_real=convertir_a_time(row['entrada_manana_real']),
                salida_manana_real=convertir_a_time(row['salida_manana_real']),
                entrada_tarde_real=convertir_a_time(row['entrada_tarde_real']),
                salida_tarde_real=convertir_a_time(row['salida_tarde_real']),
                total_horas_trabajadas=float(row['total_horas_trabajadas'] or 0),
                horas_normales=float(row['horas_normales'] or 8),
                horas_extras=float(row['horas_extras'] or 0),
                estado_dia=row['estado_dia']
            )
            asistencia.created_at = row.get('created_at')
            asistencia.updated_at = row.get('updated_at')
            asistencias.append(asistencia)
        return asistencias
    
    def get_by_empleado_and_periodo(self, empleado_id: int, fecha_inicio: str, fecha_fin: str) -> List[Asistencia]:
        query = """
            SELECT * FROM ASISTENCIA 
            WHERE empleado_id = %s AND fecha BETWEEN %s AND %s
            ORDER BY fecha
        """
        results = self.db.execute_query(query, (empleado_id, fecha_inicio, fecha_fin))
        if not results:
            return []
        
        asistencias = []
        for row in results:
            asistencia = Asistencia(
                id=row['id'],
                empleado_id=row['empleado_id'],
                fecha=str(row['fecha']),
                entrada_manana_real=convertir_a_time(row['entrada_manana_real']),
                salida_manana_real=convertir_a_time(row['salida_manana_real']),
                entrada_tarde_real=convertir_a_time(row['entrada_tarde_real']),
                salida_tarde_real=convertir_a_time(row['salida_tarde_real']),
                total_horas_trabajadas=float(row['total_horas_trabajadas'] or 0),
                horas_normales=float(row['horas_normales'] or 8),
                horas_extras=float(row['horas_extras'] or 0),
                estado_dia=row['estado_dia']
            )
            asistencia.created_at = row.get('created_at')
            asistencia.updated_at = row.get('updated_at')
            asistencias.append(asistencia)
        return asistencias
    
    def create(self, asistencia: Asistencia) -> Asistencia:
        query = """
            INSERT INTO ASISTENCIA 
            (empleado_id, fecha, entrada_manana_real, salida_manana_real, 
             entrada_tarde_real, salida_tarde_real, total_horas_trabajadas, 
             horas_normales, horas_extras, estado_dia)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        asistencia_id = self.db.execute_insert(query, (
            asistencia.empleado_id, asistencia.fecha,
            asistencia.entrada_manana_real, asistencia.salida_manana_real,
            asistencia.entrada_tarde_real, asistencia.salida_tarde_real,
            asistencia.total_horas_trabajadas, asistencia.horas_normales,
            asistencia.horas_extras, asistencia.estado_dia
        ))
        if asistencia_id:
            asistencia.id = asistencia_id
        return asistencia
    
    def update(self, asistencia: Asistencia) -> Asistencia:
        query = """
            UPDATE ASISTENCIA 
            SET entrada_manana_real = %s, salida_manana_real = %s,
                entrada_tarde_real = %s, salida_tarde_real = %s,
                total_horas_trabajadas = %s, horas_normales = %s,
                horas_extras = %s, estado_dia = %s
            WHERE id = %s
        """
        self.db.execute_update(query, (
            asistencia.entrada_manana_real, asistencia.salida_manana_real,
            asistencia.entrada_tarde_real, asistencia.salida_tarde_real,
            asistencia.total_horas_trabajadas, asistencia.horas_normales,
            asistencia.horas_extras, asistencia.estado_dia, asistencia.id
        ))
        return asistencia
    
    # MÉTODOS CORREGIDOS PARA ALERTAS
    
    def contar_faltas_empleado(self, empleado_id: int, dias: int = 30) -> int:
        """Cuenta las faltas de un empleado en los últimos X días"""
        try:
            query = """
                SELECT COUNT(*) as count FROM ASISTENCIA 
                WHERE empleado_id = %s 
                AND fecha >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                AND estado_dia = 'FALTA'
            """
            results = self.db.execute_query(query, (empleado_id, dias))
            if results and len(results) > 0:
                return results[0]['count']
            return 0
        except Exception as e:
            print(f"Error contando faltas: {e}")
            return 0
    
    def alerta_ya_enviada(self, empleado_id: int, numero_faltas: int) -> bool:
        """Verifica si ya se envió alerta por este número de faltas"""
        try:
            query = """
                SELECT COUNT(*) as count FROM ALERTAS_ENVIADAS 
                WHERE empleado_id = %s AND numero_faltas = %s
            """
            results = self.db.execute_query(query, (empleado_id, numero_faltas))
            if results and len(results) > 0:
                return results[0]['count'] > 0
            return False
        except Exception as e:
            print(f"Error verificando alerta enviada: {e}")
            return False
    
    def registrar_alerta_enviada(self, empleado_id: int, numero_faltas: int) -> bool:
        """Registra que se envió una alerta"""
        try:
            query = """
                INSERT INTO ALERTAS_ENVIADAS (empleado_id, numero_faltas, fecha_envio)
                VALUES (%s, %s, NOW())
            """
            result = self.db.execute_insert(query, (empleado_id, numero_faltas))
            return result is not None
        except Exception as e:
            print(f"Error registrando alerta: {e}")
            return False

class HorarioEstandarRepositoryMySQL(HorarioEstandarRepository):
    def __init__(self, db_connection: MySQLConnection):
        self.db = db_connection
    
    def get_by_empresa_id(self, empresa_id: int) -> Optional[HorarioEstandar]:
        query = "SELECT * FROM HORARIOS_ESTANDAR WHERE empresa_id = %s"
        results = self.db.execute_query(query, (empresa_id,))
        if not results:
            return None
        
        row = results[0]
        horario = HorarioEstandar(
            id=row['id'],
            empresa_id=row['empresa_id'],
            entrada_manana=row['entrada_manana'],
            salida_manana=row['salida_manana'],
            entrada_tarde=row['entrada_tarde'],
            salida_tarde=row['salida_tarde']
        )
        return horario
    
    def create(self, horario: HorarioEstandar) -> HorarioEstandar:
        query = """
            INSERT INTO HORARIOS_ESTANDAR 
            (empresa_id, entrada_manana, salida_manana, entrada_tarde, salida_tarde)
            VALUES (%s, %s, %s, %s, %s)
        """
        horario_id = self.db.execute_insert(query, (
            horario.empresa_id, horario.entrada_manana, horario.salida_manana,
            horario.entrada_tarde, horario.salida_tarde
        ))
        if horario_id:
            horario.id = horario_id
        return horario
    
    def update(self, horario: HorarioEstandar) -> HorarioEstandar:
        query = """
            UPDATE HORARIOS_ESTANDAR 
            SET entrada_manana = %s, salida_manana = %s,
                entrada_tarde = %s, salida_tarde = %s
            WHERE id = %s
        """
        self.db.execute_update(query, (
            horario.entrada_manana, horario.salida_manana,
            horario.entrada_tarde, horario.salida_tarde, horario.id
        ))
        return horario

class EscaneoTrackingRepositoryMySQL(EscaneoTrackingRepository):
    def __init__(self, db_connection: MySQLConnection):
        self.db = db_connection
    
    def create(self, codigo_qr: str, ip_address: str = "") -> bool:
        query = """
            INSERT INTO ESCANEOS_TRACKING (codigo_qr, ip_address)
            VALUES (%s, %s)
        """
        return self.db.execute_insert(query, (codigo_qr, ip_address)) is not None
    
    def existe_registro_reciente(self, codigo_qr: str, segundos: int = 10) -> bool:
        query = """
            SELECT COUNT(*) as count FROM ESCANEOS_TRACKING 
            WHERE codigo_qr = %s 
            AND timestamp_escaneo >= DATE_SUB(NOW(), INTERVAL %s SECOND)
        """
        results = self.db.execute_query(query, (codigo_qr, segundos))
        if results and len(results) > 0:
            return results[0]['count'] > 0
        return False
    
    def registrar_escaneo(self, codigo_qr: str, ip_address: str = "") -> bool:
        """Registra un escaneo (método adicional útil)"""
        return self.create(codigo_qr, ip_address)

# ✅ Nueva clase: AdministradorRepository
class AdministradorRepository:
    def __init__(self, db_connection: MySQLConnection):
        self.db = db_connection
    
    def get_by_username(self, username: str) -> Optional[dict]:
        """Obtiene un administrador por su nombre de usuario"""
        query = """
            SELECT id, empresa_id, nombre, usuario, password_hash, telefono, correo, rol, activo, created_at
            FROM ADMINISTRADORES
            WHERE usuario = %s AND activo = TRUE
        """
        results = self.db.execute_query(query, (username,))
        if not results:
            return None
        return results[0]
    
    def verify_password(self, stored_password_hash: str, provided_password: str) -> bool:
        """Verifica si la contraseña proporcionada coincide con el hash almacenado"""
        # Si usas hash simple (como en tu ejemplo), usa esto:
        provided_hash = hashlib.sha256(provided_password.encode('utf-8')).hexdigest()
        return provided_hash == stored_password_hash