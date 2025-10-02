from datetime import datetime, time, timedelta
import pytz # ✅ Manejo de zonas horarias
import math  # ✅ Magia para redondear hacia arriba
from src.infrastructure.email_service import EmailService
from src.domain.entities import Empleado, Asistencia
from src.domain.repositories import (
    EmpleadoRepository, 
    AsistenciaRepository, 
    HorarioEstandarRepository,
    EscaneoTrackingRepository
)
from src.infrastructure.mysql_connection import get_connection
from typing import Optional, Tuple


class MarkAttendanceUseCase:
    def __init__(self, 
                 empleado_repository: EmpleadoRepository,
                 asistencia_repository: AsistenciaRepository,
                 horario_repository: HorarioEstandarRepository,
                 escaneo_repository: EscaneoTrackingRepository):
        self.empleado_repository = empleado_repository
        self.asistencia_repository = asistencia_repository
        self.horario_repository = horario_repository
        self.escaneo_repository = escaneo_repository
        self.email_service = EmailService()
    
    def execute(self, codigo_qr: str, ip_address: str = "") -> dict:
        # Verificar si hay escaneo reciente
        if self.escaneo_repository.existe_registro_reciente(codigo_qr, 10):
            return {
                "status": "duplicado",
                "message": "Código QR escaneado recientemente",
                "data": None
            }
        
        self.escaneo_repository.create(codigo_qr, ip_address)
        empleado = None
        empleado = self.empleado_repository.get_by_codigo_qr(codigo_qr)
        if not empleado and codigo_qr.startswith("EMP_"):
            try:
                parts = codigo_qr.split("_")
                if len(parts) >= 3:
                    empleado_id = int(parts[2])
                    empleado = self.empleado_repository.get_by_id(empleado_id)
            except (ValueError, IndexError):
                pass
        if not empleado:
            return {
                "status": "error",
                "message": "Empleado no encontrado",
                "data": None
            }
        tz = pytz.timezone("America/Lima")
        fecha_actual = datetime.now(tz).date().strftime('%Y-%m-%d')
        hora_actual = datetime.now(tz).time()

        asistencia = self.asistencia_repository.get_by_empleado_and_fecha(
            empleado.id, fecha_actual
        )
        
        if not asistencia:
            asistencia = Asistencia(
                empleado_id=empleado.id,
                fecha=fecha_actual
            )
        
        resultado = self._procesar_registro_horario(asistencia, hora_actual)

        if resultado["actualizado"]:
            #  Primero calculo las horas trabajadas y estado por turnos
            self._calcular_horas_trabajadas(asistencia)

            #  Luego guardo en BD ya con horas y estados calculados
            if asistencia.id:
                self.asistencia_repository.update(asistencia)
            else:
                self.asistencia_repository.create(asistencia)
        
        # ❌ Comentado: No enviar alertas automáticas inmediatas
        # self.verificar_y_enviar_alertas(empleado.id)
        
        return {
            "status": "success",
            "message": resultado["mensaje"],
            "data": {
                "empleado": {
                    "id": empleado.id,
                    "nombre": empleado.nombre
                },
                "asistencia": {
                    "fecha": asistencia.fecha,
                    "entrada_manana_real": str(asistencia.entrada_manana_real) if asistencia.entrada_manana_real else None,
                    "salida_manana_real": str(asistencia.salida_manana_real) if asistencia.salida_manana_real else None,
                    "entrada_tarde_real": str(asistencia.entrada_tarde_real) if asistencia.entrada_tarde_real else None,
                    "salida_tarde_real": str(asistencia.salida_tarde_real) if asistencia.salida_tarde_real else None,
                    "total_horas_trabajadas": asistencia.total_horas_trabajadas,
                    "horas_normales": asistencia.horas_normales,
                    "horas_extras": asistencia.horas_extras,
                    "estado_dia": asistencia.estado_dia,
                    "asistio_manana": asistencia.asistio_manana,
                    "asistio_tarde": asistencia.asistio_tarde,
                    "tardanza_manana": asistencia.tardanza_manana,
                    "tardanza_tarde": asistencia.tardanza_tarde
                }
            }
        }
    
    def _procesar_registro_horario(self, asistencia: Asistencia, hora_actual: time) -> dict:
        """
        Procesa el registro horario con lógica de turnos basada en la hora actual.
        - Solo permite registros de mañana antes de las 12:00 PM.
        - A partir de las 12:00 PM, solo permite registros de tarde.
        """
        #  Definir límites de turnos
        hora_limite_mañana = time(13, 30)  # Hasta las 14:00 PM es "mañana"

        #  Verificar si ya pasó el turno de mañana
        ya_es_tarde = hora_actual >= hora_limite_mañana

        # 🔁 Lógica mejorada por orden y hora
        if not asistencia.entrada_manana_real and not ya_es_tarde:
            # Solo permite entrada mañana si aún no ha pasado el límite
            asistencia.entrada_manana_real = hora_actual
            return {"actualizado": True, "mensaje": f"✅ Entrada mañana registrada: {hora_actual.strftime('%H:%M')}"}

        elif not asistencia.salida_manana_real and asistencia.entrada_manana_real and not ya_es_tarde:
            # Permite salida mañana solo si hay entrada y aún no es tarde
            asistencia.salida_manana_real = hora_actual
            return {"actualizado": True, "mensaje": f"✅ Salida mañana registrada: {hora_actual.strftime('%H:%M')}"}

        elif not asistencia.entrada_tarde_real:
            # A partir de las 12:00, fuerza el registro en la tarde
            asistencia.entrada_tarde_real = hora_actual
            return {"actualizado": True, "mensaje": f"✅ Entrada tarde registrada: {hora_actual.strftime('%H:%M')}"}

        elif not asistencia.salida_tarde_real:
            asistencia.salida_tarde_real = hora_actual
            return {"actualizado": True, "mensaje": f"✅ Salida tarde registrada: {hora_actual.strftime('%H:%M')}"}

        else:
            return {
                "actualizado": False, 
                "mensaje": "❌ Todos los registros del día ya están completos"
            }
    
    def _calcular_horas_trabajadas(self, asistencia: Asistencia):
        # ✅ Determinar si asistió a cada turno (marcó entrada Y salida)
        asistencia.asistio_manana = (
            bool(asistencia.entrada_manana_real) and 
            bool(asistencia.salida_manana_real)
        )
        asistencia.asistio_tarde = (
            bool(asistencia.entrada_tarde_real) and 
            bool(asistencia.salida_tarde_real)
        )

        # ✅ Calcular horas solo si ambos registros están
        total_minutos = 0
        if asistencia.entrada_manana_real and asistencia.salida_manana_real:
            minutos_manana = self._calcular_minutos_entre_horas(
                asistencia.entrada_manana_real, asistencia.salida_manana_real
            )
            total_minutos += minutos_manana
        if asistencia.entrada_tarde_real and asistencia.salida_tarde_real:
            minutos_tarde = self._calcular_minutos_entre_horas(
                asistencia.entrada_tarde_real, asistencia.salida_tarde_real
            )
            total_minutos += minutos_tarde

        # ✅ Convertir a horas (solo para mostrar)
        total_horas = total_minutos / 60.0
        asistencia.total_horas_trabajadas = round(total_horas, 2)

        # ✅ Horas normales y extras — CALCULA CON MINUTOS, NO CON HORAS REDONDEADAS
        minutos_normales = 8 * 60  # 480 minutos
        if total_minutos > minutos_normales:
            minutos_extras = total_minutos - minutos_normales
            asistencia.horas_extras = round(minutos_extras / 60.0, 2)
            asistencia.horas_normales = 8.0
        else:
            asistencia.horas_normales = round(total_horas, 2)
            asistencia.horas_extras = 0.0

        # ✅ Estado del día
        if asistencia.asistio_manana and asistencia.asistio_tarde:
            asistencia.estado_dia = "COMPLETO"
        elif asistencia.asistio_manana or asistencia.asistio_tarde:
            asistencia.estado_dia = "INCOMPLETO"
        else:
            asistencia.estado_dia = "FALTA"

        # ✅ Evaluar tardanzas (SIN TOLERANCIA)
        self._evaluar_tardanzas(asistencia)
    
    def _evaluar_tardanzas(self, asistencia: Asistencia):
        # ⚙️ HORARIOS ESPERADOS SIN TOLERANCIA
        hora_entrada_manana_esperada = time(6, 50)  # 6:50 AM
        hora_entrada_tarde_esperada = time(13, 0)   # 1:00 PM

        # ✅ Comparar directamente sin tolerancia
        if asistencia.entrada_manana_real:
            asistencia.tardanza_manana = asistencia.entrada_manana_real > hora_entrada_manana_esperada
        else:
            asistencia.tardanza_manana = False

        if asistencia.entrada_tarde_real:
            asistencia.tardanza_tarde = asistencia.entrada_tarde_real > hora_entrada_tarde_esperada
        else:
            asistencia.tardanza_tarde = False

    def _calcular_minutos_entre_horas(self, hora_inicio, hora_fin) -> int:
        try:
            hoy = datetime.today().date()

            # Blindaje: convertir si llega como datetime
            if isinstance(hora_inicio, datetime):
                hora_inicio = hora_inicio.time()
            if isinstance(hora_fin, datetime):
                hora_fin = hora_fin.time()

            # Blindaje: si llega timedelta, ignoro
            if isinstance(hora_inicio, timedelta) or isinstance(hora_fin, timedelta):
                print("⚠️ Aviso: hora_inicio o hora_fin llegaron como timedelta, se ignora este cálculo.")
                return 0

            # ✅ Convertir a datetime con fecha actual
            inicio_dt = datetime.combine(hoy, hora_inicio)
            fin_dt = datetime.combine(hoy, hora_fin)

            diferencia = fin_dt - inicio_dt
            total_segundos = diferencia.total_seconds()

            # ✅ Redondear hacia arriba: 1 segundo = 1 minuto
            minutos_redondeados = int(total_segundos // 60)

            return max(0, int(minutos_redondeados))
        except Exception as e:
            print(f"❌ Error calculando minutos entre horas: {e}")
            return 0
    
    # ---------------- ALERTAS REALES -----------------
    
    def verificar_y_enviar_alertas(self, empleado_id: int):
        try:
            empleado = self.empleado_repository.get_by_id(empleado_id)
            if not empleado or not empleado.correo:
                return False
            
            # Obtener configuración de alertas
            config_alerta = self._obtener_configuracion_alerta(empleado.empresa_id)
            if not config_alerta or not config_alerta.activo:
                return False
            
            # Contar faltas y tardanzas recientes
            faltas = self._contar_faltas_recientes(empleado_id, dias=30)
            tardanzas = self._contar_tardanzas_recientes(empleado_id, dias=30)
            
            # Verificar alertas por faltas
            if faltas >= config_alerta.numero_faltas_para_alerta:
                if not self._alerta_ya_enviada(empleado_id, faltas, tipo="falta"):
                    self._enviar_alerta_faltas(empleado, config_alerta, faltas)
                    self._registrar_alerta_enviada(empleado_id, faltas, tipo="falta")
            
            # Verificar alertas por tardanzas
            if tardanzas >= config_alerta.numero_tardanzas_para_alerta:
                if not self._alerta_ya_enviada(empleado_id, tardanzas, tipo="tardanza"):
                    self._enviar_alerta_tardanzas(empleado, config_alerta, tardanzas)
                    self._registrar_alerta_enviada(empleado_id, tardanzas, tipo="tardanza")
            
            return True
        except Exception as e:
            print(f"Error verificando alertas: {e}")
            return False

    def _obtener_configuracion_alerta(self, empresa_id: int):
        """Obtiene la configuración de alertas para una empresa"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            query = """
                SELECT ca.*, e.nombre as empresa_nombre
                FROM CONFIG_ALERTAS ca
                JOIN EMPRESAS e ON ca.empresa_id = e.id
                WHERE ca.empresa_id = %s AND ca.activo = TRUE
                LIMIT 1
            """
            cursor.execute(query, (empresa_id,))
            resultado = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if resultado:
                return {
                    "id": resultado[0],
                    "empresa_id": resultado[1],
                    "numero_faltas_para_alerta": resultado[2],
                    "numero_tardanzas_para_alerta": resultado[7] if len(resultado) > 7 else 3,
                    "mensaje_correo_falta": resultado[3],
                    "mensaje_correo_tardanza": resultado[8] if len(resultado) > 8 else "Tienes demasiadas tardanzas.",
                    "mensaje_correo_admin": resultado[4],
                    "activo": resultado[5],
                    "empresa_nombre": resultado[6]
                }
            return None
        except Exception as e:
            print(f"Error obteniendo configuración de alertas: {e}")
            return None

    def _obtener_email_admin(self, empresa_id: int):
        """Obtiene el correo del administrador de la empresa"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            query = """
                SELECT correo
                FROM ADMINISTRADORES
                WHERE id = %s
                LIMIT 1
            """
            cursor.execute(query, (empresa_id,))
            resultado = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if resultado:
                return resultado[0]
            return None
        except Exception as e:
            print(f"Error obteniendo correo admin: {e}")
            return None

    def _contar_faltas_recientes(self, empleado_id: int, dias: int = 30) -> int:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            query = """
                SELECT COUNT(*) 
                FROM ASISTENCIA
                WHERE empleado_id = %s 
                  AND fecha >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                  AND estado_dia = 'FALTA'
            """
            cursor.execute(query, (empleado_id, dias))
            resultado = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return resultado
        except Exception as e:
            print(f"Error contando faltas: {e}")
            return 0

    def _contar_tardanzas_recientes(self, empleado_id: int, dias: int = 30) -> int:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            query = """
                SELECT COUNT(*) 
                FROM ASISTENCIA
                WHERE empleado_id = %s 
                  AND fecha >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
                  AND (tardanza_manana = TRUE OR tardanza_tarde = TRUE)
            """
            cursor.execute(query, (empleado_id, dias))
            resultado = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return resultado
        except Exception as e:
            print(f"Error contando tardanzas: {e}")
            return 0

    def _alerta_ya_enviada(self, empleado_id: int, numero: int, tipo: str) -> bool:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            query = """
                SELECT 1
                FROM ALERTAS_ENVIADAS
                WHERE empleado_id = %s AND numero = %s AND tipo = %s
                LIMIT 1
            """
            cursor.execute(query, (empleado_id, numero, tipo))
            existe = cursor.fetchone() is not None
            cursor.close()
            conn.close()
            return existe
        except Exception as e:
            print(f"Error verificando alerta: {e}")
            return False

    def _registrar_alerta_enviada(self, empleado_id: int, numero: int, tipo: str):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            query = """
                INSERT INTO ALERTAS_ENVIADAS (empleado_id, numero, tipo)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, (empleado_id, numero, tipo))
            conn.commit()
            cursor.close()
            conn.close()
            print(f"✅ Alerta registrada para empleado {empleado_id} con {numero} {tipo}s")
        except Exception as e:
            print(f"Error registrando alerta: {e}")

    def _enviar_alerta_faltas(self, empleado, config_alerta, numero_faltas):
        try:
            # Enviar correo al empleado
            self.email_service.enviar_alerta_faltas(
                nombre_empleado=empleado.nombre,
                email_empleado=empleado.correo,
                numero_faltas=numero_faltas,
                empresa_nombre=config_alerta.empresa_nombre,
                mensaje=config_alerta.mensaje_correo_falta
            )
            
            # Enviar correo a la jefa
            self.email_service.enviar_alerta_admin(
                nombre_empleado=empleado.nombre,
                email_admin=self._obtener_email_admin(empleado.empresa_id),
                numero_faltas=numero_faltas,
                empresa_nombre=config_alerta.empresa_nombre,
                mensaje=config_alerta.mensaje_correo_admin
            )
        except Exception as e:
            print(f"Error enviando alerta de faltas: {e}")

    def _enviar_alerta_tardanzas(self, empleado, config_alerta, numero_tardanzas):
        try:
            # Enviar correo al empleado
            self.email_service.enviar_alerta_tardanzas(
                nombre_empleado=empleado.nombre,
                email_empleado=empleado.correo,
                numero_tardanzas=numero_tardanzas,
                empresa_nombre=config_alerta.empresa_nombre,
                mensaje=config_alerta.mensaje_correo_tardanza
            )
            
            # Enviar correo a la jefa
            self.email_service.enviar_alerta_admin(
                nombre_empleado=empleado.nombre,
                email_admin=self._obtener_email_admin(empleado.empresa_id),
                numero_tardanzas=numero_tardanzas,
                empresa_nombre=config_alerta.empresa_nombre,
                mensaje=config_alerta.mensaje_correo_admin
            )
        except Exception as e:
            print(f"Error enviando alerta de tardanzas: {e}")

    # ---------------- ALERTAS REALES -----------------
    
    def verificar_y_enviar_alertas_faltas(self, empleado_id: int):
        """Mantengo por compatibilidad, pero uso verificar_y_enviar_alertas"""
        return self.verificar_y_enviar_alertas(empleado_id)

    # ---------------- REPORTE SEMANAL -----------------

    def generar_reporte_semanal(self):
        """Genera y envía reporte semanal de asistencia por empresa"""
        try:
            # Obtener todas las empresas
            empresas = self.empleado_repository.empresa_repo.get_all()
            
            for empresa in empresas:
                # Obtener empleados de la empresa
                empleados = self.empleado_repository.get_by_empresa_id(empresa.id)
                
                # Resumen de la semana
                resumen_tardanzas = []
                resumen_faltas = []
                empleados_sin_incidencias = []
                
                for empleado in empleados:
                    # Contar tardanzas y faltas de la semana pasada
                    tardanzas = self._contar_tardanzas_semana(empleado.id)
                    faltas = self._contar_faltas_semana(empleado.id)
                    
                    if tardanzas > 0:
                        resumen_tardanzas.append({
                            "nombre": empleado.nombre,
                            "tardanzas": tardanzas
                        })
                    if faltas > 0:
                        resumen_faltas.append({
                            "nombre": empleado.nombre,
                            "faltas": faltas
                        })
                    if tardanzas == 0 and faltas == 0:
                        empleados_sin_incidencias.append(empleado.nombre)
                
                # Si hay incidencias, enviar correo
                if len(resumen_tardanzas) > 0 or len(resumen_faltas) > 0:
                    self._enviar_reporte_semanal_empresa(
                        empresa=empresa,
                        resumen_tardanzas=resumen_tardanzas,
                        resumen_faltas=resumen_faltas,
                        empleados_sin_incidencias=empleados_sin_incidencias
                    )
            
            print("✅ Reportes semanales enviados a la jefa")
            return True
        except Exception as e:
            print(f"Error generando reportes semanales: {e}")
            return False

    def enviar_reporte_individual_empleados(self):
        """Envía reporte individual a cada empleado con sus faltas y tardanzas de la semana"""
        try:
            # Obtener todos los empleados activos
            empleados = self.empleado_repository.get_all()
            
            for empleado in empleados:
                if not empleado.activo or not empleado.correo:
                    continue
                
                # Contar faltas y tardanzas de la semana
                faltas = self._contar_faltas_semana(empleado.id)
                tardanzas = self._contar_tardanzas_semana(empleado.id)
                
                # Solo enviar si tiene incidencias
                if faltas > 0 or tardanzas > 0:
                    self._enviar_reporte_individual_empleado(empleado, faltas, tardanzas)
            
            print("✅ Reportes individuales enviados a empleados")
            return True
        except Exception as e:
            print(f"Error enviando reportes individuales: {e}")
            return False

    def _enviar_reporte_individual_empleado(self, empleado, faltas, tardanzas):
        """Envía reporte individual al empleado"""
        try:
            asunto = f"📊 Tu Reporte Semanal de Asistencia - {datetime.now().strftime('%d/%m/%Y')}"
            
            contenido = f"""
            <h2>📊 Tu Reporte Semanal de Asistencia</h2>
            <p><strong>Hola {empleado.nombre}</strong>,</p>
            <p>Este es tu resumen de asistencia de la semana pasada:</p>
            <hr>
            """
            
            if faltas > 0:
                contenido += f"""
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <p style="margin: 0; font-size: 16px;">
                        <strong>🚨 Faltas:</strong> {faltas} día(s) sin registrar asistencia.
                    </p>
                </div>
                """
            
            if tardanzas > 0:
                contenido += f"""
                <div style="background-color: #e3f2fd; border: 1px solid #2196f3; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <p style="margin: 0; font-size: 16px;">
                        <strong>⏰ Tardanzas:</strong> Llegaste tarde {tardanzas} vez/veces.
                    </p>
                </div>
                """
            
            contenido += """
            <div style="background-color: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 8px; margin: 15px 0;">
                <p style="margin: 0; font-size: 16px;">
                    <strong>📋 Recomendación:</strong> Por favor, regulariza tu asistencia para evitar sanciones.
                </p>
            </div>
            <hr>
            <p>Este reporte se genera automáticamente cada semana.</p>
            <p>¡Gracias por tu compromiso!</p>
            """
            
            # Enviar correo
            exito = self.email_service.enviar_correo(
                destinatario=empleado.correo,
                asunto=asunto,
                mensaje_html=contenido
            )
            
            if exito:
                print(f"✅ Reporte individual enviado a {empleado.nombre} ({empleado.correo})")
            else:
                print(f"❌ Error enviando reporte individual a {empleado.nombre}")
                
        except Exception as e:
            print(f"Error enviando reporte individual a {empleado.nombre}: {e}")

    def _contar_tardanzas_semana(self, empleado_id: int) -> int:
        """Cuenta tardanzas de la semana pasada (lunes a domingo)"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            # Obtener lunes y domingo de la semana pasada
            query = """
                SELECT COUNT(*)
                FROM ASISTENCIA
                WHERE empleado_id = %s
                  AND fecha >= DATE_SUB(CURDATE(), INTERVAL 1 WEEK)
                  AND fecha <= CURDATE()
                  AND (tardanza_manana = TRUE OR tardanza_tarde = TRUE)
            """
            cursor.execute(query, (empleado_id,))
            resultado = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return resultado
        except Exception as e:
            print(f"Error contando tardanzas semanales: {e}")
            return 0

    def _contar_faltas_semana(self, empleado_id: int) -> int:
        """Cuenta faltas de la semana pasada (lunes a domingo)"""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            query = """
                SELECT COUNT(*)
                FROM ASISTENCIA
                WHERE empleado_id = %s
                  AND fecha >= DATE_SUB(CURDATE(), INTERVAL 1 WEEK)
                  AND fecha <= CURDATE()
                  AND estado_dia = 'FALTA'
            """
            cursor.execute(query, (empleado_id,))
            resultado = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return resultado
        except Exception as e:
            print(f"Error contando faltas semanales: {e}")
            return 0

    def _enviar_reporte_semanal_empresa(self, empresa, resumen_tardanzas, resumen_faltas, empleados_sin_incidencias):
        """Envía reporte semanal a la jefa de la empresa"""
        try:
            # Obtener correo de la jefa
            correo_jefa = self._obtener_email_admin(empresa.id)
            if not correo_jefa:
                print(f"❌ No se encontró correo de la jefa para empresa {empresa.nombre}")
                return False
            
            # Generar contenido del correo
            contenido = self._generar_contenido_reporte_semanal(
                empresa=empresa,
                resumen_tardanzas=resumen_tardanzas,
                resumen_faltas=resumen_faltas,
                empleados_sin_incidencias=empleados_sin_incidencias
            )
            
            # Enviar correo
            exito = self.email_service.enviar_reporte_semanal(
                email_destino=correo_jefa,
                asunto=f"📊 Reporte Semanal de Asistencia - {empresa.nombre}",
                contenido=contenido
            )
            
            if exito:
                print(f"✅ Reporte semanal enviado a {correo_jefa} para empresa {empresa.nombre}")
                return True
            else:
                print(f"❌ Error enviando reporte semanal a {correo_jefa}")
                return False
        except Exception as e:
            print(f"Error enviando reporte semanal: {e}")
            return False

    def _generar_contenido_reporte_semanal(self, empresa, resumen_tardanzas, resumen_faltas, empleados_sin_incidencias):
        """Genera el contenido del reporte semanal"""
        contenido = f"""
        <h2>📊 Reporte Semanal de Asistencia - {empresa.nombre}</h2>
        <p><strong>Período:</strong> {datetime.now().strftime('%d/%m/%Y')} (últimos 7 días)</p>
        <hr>
        """
        
        # Empleados con tardanzas
        if len(resumen_tardanzas) > 0:
            contenido += "<h3>✅ EMPLEADOS CON TARDANZAS:</h3><ul>"
            for item in resumen_tardanzas:
                nivel = "¡Atención!" if item["tardanzas"] >= 3 else "En observación" if item["tardanzas"] >= 2 else "Leve"
                contenido += f"<li><strong>{item['nombre']}</strong>: {item['tardanzas']} tardanza(s) → {nivel}</li>"
            contenido += "</ul>"
        
        # Empleados con faltas
        if len(resumen_faltas) > 0:
            contenido += "<h3>✅ EMPLEADOS CON FALTAS:</h3><ul>"
            for item in resumen_faltas:
                nivel = "¡Urgente!" if item["faltas"] >= 3 else "Justificar" if item["faltas"] >= 2 else "Leve"
                contenido += f"<li><strong>{item['nombre']}</strong>: {item['faltas']} falta(s) → {nivel}</li>"
            contenido += "</ul>"
        
        # Empleados sin incidencias
        if len(empleados_sin_incidencias) > 0:
            contenido += f"<h3>✅ EMPLEADOS SIN INCIDENCIAS:</h3><p>{', '.join(empleados_sin_incidencias)}</p>"
        
        contenido += """
        <hr>
        <p>Por favor, revisa con el equipo para mejorar la puntualidad.</p>
        <p>¡Gracias por tu liderazgo Jacque!</p>
        <p><em>Este reporte se genera automáticamente cada semana.</em></p>
        """
        
        return contenido