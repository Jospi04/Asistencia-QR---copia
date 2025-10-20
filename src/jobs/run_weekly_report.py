# src/jobs/run_weekly_report.py

import os
from datetime import datetime
from dotenv import load_dotenv

# --- FIX de Ruta Relativa ---
# Esto es necesario para que el script pueda encontrar los módulos en la carpeta 'src'
import sys
import os.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
# -----------------------------

# Cargar variables de entorno (necesario para las credenciales de DB y email)
load_dotenv() 

# Importar infraestructura y use case
from src.infrastructure.mysql_connection import MySQLConnection
from src.infrastructure.repositories_mysql import (
    EmpresaRepositoryMySQL,
    EmpleadoRepositoryMySQL,
    AsistenciaRepositoryMySQL,
    HorarioEstandarRepositoryMySQL,
    EscaneoTrackingRepositoryMySQL,
    AdministradorRepository # <-- Necesario si se usa en el setup
)
from src.use_cases.mark_attendance import MarkAttendanceUseCase


def run_weekly_job():
    """Inicializa las dependencias y ejecuta las tareas de reporte semanal."""
    try:
        print("=" * 70)
        print("🚀 JOB SEMANAL INICIADO (CRON EXTERNO)")
        print(f"⏰ Hora servidor: {datetime.now()}")
        print("=" * 70)
        
        # 1. Configuración de dependencias (REPLICANDO EL ENTORNO DE app.py)
        db_connection = MySQLConnection()
        
        empresa_repo = EmpresaRepositoryMySQL(db_connection)
        empleado_repo = EmpleadoRepositoryMySQL(db_connection)
        asistencia_repo = AsistenciaRepositoryMySQL(db_connection)
        horario_repo = HorarioEstandarRepositoryMySQL(db_connection)
        escaneo_repo = EscaneoTrackingRepositoryMySQL(db_connection)
        
        EMAIL_EMPRESA_ADMIN = os.getenv('EMAIL_EMPRESA', '')
        
        # 2. Inicializar el Use Case (INYECCIÓN COMPLETA DE DEPENDENCIAS)
        # La firma de MarkAttendanceUseCase es: 
        # (empleado_repo, asistencia_repo, horario_repo, escaneo_repo, empresa_repo, email_admin)
        mark_attendance_use_case = MarkAttendanceUseCase(
            empleado_repo,           
            asistencia_repo,         
            horario_repo,            
            escaneo_repo,            
            empresa_repo,            # <-- ESTA ES LA POSICIÓN CORRECTA
            EMAIL_EMPRESA_ADMIN
        )
        
        # 3. Ejecutar las tareas
        print("\n📧 PASO 1: Enviando reportes CONSOLIDADOS a la jefa...")
        # Si esto falla, la única causa es que mark_attendance.py no está actualizado.
        mark_attendance_use_case.generar_reporte_semanal() 
        print("✅ Reportes consolidados a la jefa enviados correctamente\n")
        
        print("📧 PASO 2: Enviando reportes INDIVIDUALES a empleados...")
        mark_attendance_use_case.enviar_reporte_individual_empleados()
        print("✅ Reportes individuales a empleados enviados correctamente\n")
        
        print("🎉 JOB SEMANAL COMPLETADO EXITOSAMENTE")
        print("=" * 70)
        
    except Exception as e:
        print("=" * 70)
        print(f"❌ ERROR CRÍTICO durante la ejecución del Job: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 70)

if __name__ == '__main__':
    run_weekly_job()