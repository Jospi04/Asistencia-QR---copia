from datetime import datetime
from src.domain.entities import Empleado, Asistencia
from src.domain.repositories import (
    EmpleadoRepository, 
    AsistenciaRepository,
    EmpresaRepository
)
from typing import List, Dict, Optional
import calendar


def minutos_a_hhmm(total_minutos: int) -> str:
    """
    Convierte minutos totales a formato HH:MM
    Ej: 90 → "1:30", 16 → "0:16", 480 → "8:00"
    """
    if total_minutos < 0:
        total_minutos = 0
    horas = total_minutos // 60
    minutos = total_minutos % 60
    return f"{horas}:{minutos:02d}"


class GetReportUseCase:
    def __init__(self, 
                 empleado_repository: EmpleadoRepository,
                 asistencia_repository: AsistenciaRepository,
                 empresa_repository: EmpresaRepository):
        self.empleado_repository = empleado_repository
        self.asistencia_repository = asistencia_repository
        self.empresa_repository = empresa_repository
    
    def execute_monthly_report(self, empresa_id: int, mes: int, anio: int) -> dict:
        """
        Genera reporte mensual de asistencia para una empresa
        """
        # Obtener empleados de la empresa
        empleados = self.empleado_repository.get_by_empresa_id(empresa_id)
        
        # Primer y último día del mes
        primer_dia = f"{anio}-{mes:02d}-01"
        ultimo_dia = f"{anio}-{mes:02d}-{calendar.monthrange(anio, mes)[1]}"
        
        # Recopilar datos para cada empleado
        reporte_empleados = []
        totales = {
            "total_empleados": len(empleados),
            "dias_laborables": 0,
            "total_horas_normales": 0,
            "total_horas_extras": 0,
            "total_faltas": 0,
            "total_turnos_manana": 0,
            "total_turnos_tarde": 0,
            "total_faltas_manana": 0,
            "total_faltas_tarde": 0,
            "total_retardos_manana": 0,
            "total_retardos_tarde": 0
        }
        
        for empleado in empleados:
            # Obtener asistencias del período
            asistencias = self.asistencia_repository.get_by_empleado_and_periodo(
                empleado.id, primer_dia, ultimo_dia
            )
            
            # Calcular estadísticas del empleado
            stats = self._calcular_estadisticas_empleado(asistencias)
            
            reporte_empleados.append({
                "id": empleado.id,
                "nombre": empleado.nombre,
                "dni": empleado.dni,
                "asistencias": stats["asistencias_completas"] + stats["asistencias_incompletas"],
                "faltas": stats["faltas"],
                "horas_normales": minutos_a_hhmm(int(stats["horas_normales"] * 60)),
                "horas_extras": minutos_a_hhmm(int(stats["horas_extras"] * 60)),
                "retardos": stats["retardos_manana"] + stats["retardos_tarde"],
                "turnos_manana": stats["turnos_manana"],
                "turnos_tarde": stats["turnos_tarde"],
                "faltas_manana": stats["faltas_manana"],
                "faltas_tarde": stats["faltas_tarde"],
                "retardos_manana": stats["retardos_manana"],
                "retardos_tarde": stats["retardos_tarde"],
                "porcentaje_asistencia": stats["porcentaje_asistencia"]
            })
            
            # Actualizar totales
            totales["total_horas_normales"] += stats["horas_normales"]
            totales["total_horas_extras"] += stats["horas_extras"]
            totales["total_faltas"] += stats["faltas"]
            totales["total_turnos_manana"] += stats["turnos_manana"]
            totales["total_turnos_tarde"] += stats["turnos_tarde"]
            totales["total_faltas_manana"] += stats["faltas_manana"]
            totales["total_faltas_tarde"] += stats["faltas_tarde"]
            totales["total_retardos_manana"] += stats["retardos_manana"]
            totales["total_retardos_tarde"] += stats["retardos_tarde"]
        
        # Calcular días laborables del mes
        totales["dias_laborables"] = self._contar_dias_laborables(mes, anio)

        # ✅ Redondear totales a 2 decimales para evitar errores de representación
        totales["total_horas_normales"] = round(totales["total_horas_normales"], 2)
        totales["total_horas_extras"] = round(totales["total_horas_extras"], 2)
        
        return {
            "empresa": self._get_empresa_info(empresa_id),
            "periodo": {
                "mes": mes,
                "anio": anio,
                "primer_dia": primer_dia,
                "ultimo_dia": ultimo_dia
            },
            "totales": totales,
            "empleados": reporte_empleados,
            "generado_el": datetime.now().isoformat()
        }
    
    def execute_employee_detail_report(self, empleado_id: int, mes: int, anio: int) -> dict:
        """
        Genera reporte detallado de un empleado específico
        """
        # Obtener empleado
        empleado = self.empleado_repository.get_by_id(empleado_id)
        if not empleado:
            return {"error": "Empleado no encontrado"}
        
        # Primer y último día del mes
        primer_dia = f"{anio}-{mes:02d}-01"
        ultimo_dia = f"{anio}-{mes:02d}-{calendar.monthrange(anio, mes)[1]}"
        
        # Obtener asistencias
        asistencias = self.asistencia_repository.get_by_empleado_and_periodo(
            empleado.id, primer_dia, ultimo_dia
        )
        
        # Detalle diario
        detalle_diario = []
        for asistencia in asistencias:
            # Convertir total_horas_trabajadas a minutos → HH:MM
            total_minutos = int(asistencia.total_horas_trabajadas * 60)
            total_horas_format = minutos_a_hhmm(total_minutos)

            detalle_diario.append({
                "fecha": asistencia.fecha,
                "entrada_manana": str(asistencia.entrada_manana_real) if asistencia.entrada_manana_real else None,
                "salida_manana": str(asistencia.salida_manana_real) if asistencia.salida_manana_real else None,
                "entrada_tarde": str(asistencia.entrada_tarde_real) if asistencia.entrada_tarde_real else None,
                "salida_tarde": str(asistencia.salida_tarde_real) if asistencia.salida_tarde_real else None,
                "total_horas": total_horas_format,
                "horas_extras": minutos_a_hhmm(int(asistencia.horas_extras * 60)),
                "estado": asistencia.estado_dia
            })
        
        # Estadísticas generales
        stats = self._calcular_estadisticas_empleado(asistencias)
        
        return {
            "empleado": {
                "id": empleado.id,
                "nombre": empleado.nombre,
                "dni": empleado.dni,
                "empresa": self._get_empresa_info(empleado.empresa_id)
            },
            "periodo": {
                "mes": mes,
                "anio": anio
            },
            "estadisticas": stats,
            "detalle_diario": detalle_diario,
            "total_dias": len(asistencias),
            "generado_el": datetime.now().isoformat()
        }
    
    def _calcular_estadisticas_empleado(self, asistencias: List[Asistencia]) -> dict:
        """
        Calcula estadísticas para un empleado basado en sus asistencias
        """
        total_horas_normales = 0
        total_horas_extras = 0
        faltas = 0
        asistencias_completas = 0
        asistencias_incompletas = 0
        turnos_manana = 0
        turnos_tarde = 0
        faltas_manana = 0
        faltas_tarde = 0
        retardos_manana = 0
        retardos_tarde = 0

        for asistencia in asistencias:
            if asistencia.estado_dia == "FALTA":
                faltas += 1
                faltas_manana += 1
                faltas_tarde += 1
            elif asistencia.estado_dia == "COMPLETO":
                asistencias_completas += 1
                total_horas_normales += asistencia.horas_normales
                total_horas_extras += asistencia.horas_extras
                turnos_manana += 1
                turnos_tarde += 1
                if asistencia.tardanza_manana:
                    retardos_manana += 1
                if asistencia.tardanza_tarde:
                    retardos_tarde += 1
            elif asistencia.estado_dia == "INCOMPLETO":
                asistencias_incompletas += 1
                total_horas_normales += asistencia.horas_normales
                total_horas_extras += asistencia.horas_extras
                if asistencia.asistio_manana:
                    turnos_manana += 1
                    if asistencia.tardanza_manana:
                        retardos_manana += 1
                else:
                    faltas_manana += 1
                if asistencia.asistio_tarde:
                    turnos_tarde += 1
                    if asistencia.tardanza_tarde:
                        retardos_tarde += 1
                else:
                    faltas_tarde += 1

        total_dias = len(asistencias)
        porcentaje_asistencia = 0
        if total_dias > 0:
            dias_con_asistencia = asistencias_completas + asistencias_incompletas
            porcentaje_asistencia = round((dias_con_asistencia / total_dias) * 100, 2)

        return {
            "horas_normales": round(total_horas_normales, 2),
            "horas_extras": round(total_horas_extras, 2),
            "faltas": faltas,
            "retardos_manana": retardos_manana,
            "retardos_tarde": retardos_tarde,
            "asistencias_completas": asistencias_completas,
            "asistencias_incompletas": asistencias_incompletas,
            "porcentaje_asistencia": porcentaje_asistencia,
            "turnos_manana": turnos_manana,
            "turnos_tarde": turnos_tarde,
            "faltas_manana": faltas_manana,
            "faltas_tarde": faltas_tarde
        }
    
    def _get_empresa_info(self, empresa_id: int) -> dict:
        """
        Obtiene información básica de la empresa
        """
        empresa = self.empresa_repository.get_by_id(empresa_id)
        if empresa:
            return {
                "id": empresa.id,
                "nombre": empresa.nombre,
                "codigo_empresa": empresa.codigo_empresa
            }
        return {}
    
    def _contar_dias_laborables(self, mes: int, anio: int) -> int:
        """
        Cuenta los días laborables en un mes (lunes a viernes)
        """
        import calendar
        from datetime import date
        
        dias_laborables = 0
        ultimo_dia = calendar.monthrange(anio, mes)[1]
        
        for dia in range(1, ultimo_dia + 1):
            fecha = date(anio, mes, dia)
            # 0-4 son lunes a viernes (laborables)
            if fecha.weekday() < 5:
                dias_laborables += 1
        
        return dias_laborables

class GetReportRequest:
    def __init__(self, empresa_id: int = None, empleado_id: int = None, 
                 mes: int = None, anio: int = None):
        self.empresa_id = empresa_id or datetime.now().month
        self.anio = anio or datetime.now().year
        self.empleado_id = empleado_id
        self.mes = mes