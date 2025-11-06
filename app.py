from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
import os
from datetime import datetime
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import calendar
from datetime import timedelta
from collections import Counter

# Importar infraestructura
from src.infrastructure.mysql_connection import MySQLConnection
from src.infrastructure.repositories_mysql import (
    EmpresaRepositoryMySQL,
    EmpleadoRepositoryMySQL,
    AsistenciaRepositoryMySQL,
    HorarioEstandarRepositoryMySQL,
    EscaneoTrackingRepositoryMySQL,
    AdministradorRepository
)

# Importar use cases
from src.use_cases.register_employee import RegisterEmployeeUseCase
from src.use_cases.mark_attendance import MarkAttendanceUseCase
from src.use_cases.list_companies import ListCompaniesUseCase
from src.use_cases.get_report import GetReportUseCase, minutos_a_hhmm

# Importar QR generator
from src.infrastructure.qr_generator import QRGenerator

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or 'clave-secreta-temporal-desarrollo-cambiar-en-produccion'

# Configuración de base de datos
db_connection = MySQLConnection()
# Inicializar repositorios
empresa_repo = EmpresaRepositoryMySQL(db_connection)
empleado_repo = EmpleadoRepositoryMySQL(db_connection)
asistencia_repo = AsistenciaRepositoryMySQL(db_connection)
horario_repo = HorarioEstandarRepositoryMySQL(db_connection)
escaneo_repo = EscaneoTrackingRepositoryMySQL(db_connection)

# Inicializar use cases
register_employee_use_case = RegisterEmployeeUseCase(empleado_repo)
mark_attendance_use_case = MarkAttendanceUseCase(empleado_repo, asistencia_repo, horario_repo, escaneo_repo)
list_companies_use_case = ListCompaniesUseCase(empresa_repo,)
get_report_use_case = GetReportUseCase(empleado_repo, asistencia_repo, empresa_repo)

# Inicializar QR generator
qr_generator = QRGenerator()

def obtener_nombre_mes(numero_mes):
    """Obtiene el nombre del mes por su número"""
    meses = [
        '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
        'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
    ]
    return meses[numero_mes] if 1 <= numero_mes <= 12 else ''

# Rutas principales
@app.route('/')
def index():
    return render_template('scan.html')

# Rutas de administración
@app.route('/admin')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    empresas = list_companies_use_case.execute()
    return render_template('admin_dashboard.html', empresas=empresas)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin_repo = AdministradorRepository(db_connection)
        administrador = admin_repo.get_by_username(username)
        
        if administrador and admin_repo.verify_password(administrador['password_hash'], password):
            session['admin_logged_in'] = True
            session['admin_id'] = administrador['id']
            session['admin_nombre'] = administrador['nombre']
            session['admin_rol'] = administrador['rol']
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Credenciales inválidas', 'error')
    
    return render_template('login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin/add_employee', methods=['GET', 'POST'])
def admin_add_employee():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        try:
            nombre = request.form['nombre']
            empresa_id = int(request.form['empresa_id'])
            dni = request.form['dni']
            telefono = request.form.get('telefono', '')
            correo = request.form.get('correo', '')
            
            empleado = register_employee_use_case.execute(
                nombre=nombre,
                empresa_id=empresa_id,
                dni=dni,
                telefono=telefono,
                correo=correo
            )
            
            empresa = empresa_repo.get_by_id(empresa_id)
            if empresa:
                qr_path = qr_generator.generate_employee_qr(empleado.id, empresa.codigo_empresa)
                if qr_path:
                    flash('Empleado registrado con éxito. Código QR generado.', 'success')
                else:
                    flash('Empleado registrado, pero hubo un error generando el QR.', 'warning')
            else:
                flash('Empleado registrado con éxito.', 'success')
            
            return redirect(url_for('admin_add_employee'))
            
        except Exception as e:
            flash(f'Error registrando empleado: {str(e)}', 'error')
    
    empresas = list_companies_use_case.execute()
    return render_template('admin_add_employee.html', empresas=empresas)

@app.route('/admin/employees')
def admin_list_employees():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    empresa_id = request.args.get('empresa_id', type=int)
    
    if empresa_id:
        empleados = empleado_repo.get_by_empresa_id(empresa_id)
        empresa = empresa_repo.get_by_id(empresa_id)
    else:
        empleados = empleado_repo.get_all()
        empresa = None
    
    empresas = list_companies_use_case.execute()
    return render_template('admin_list_employees.html', 
                         empleados=empleados, 
                         empresas=empresas, 
                         empresa_seleccionada=empresa)

@app.route('/admin/edit_employee/<int:empleado_id>', methods=['GET', 'POST'])
def edit_employee(empleado_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    empleado = empleado_repo.get_by_id(empleado_id)
    if not empleado:
        flash('Empleado no encontrado', 'error')
        return redirect(url_for('admin_list_employees'))
    
    if request.method == 'POST':
        try:
            empleado.nombre = request.form['nombre']
            empleado.empresa_id = int(request.form['empresa_id'])
            empleado.dni = request.form['dni']
            empleado.telefono = request.form.get('telefono', '')
            empleado.correo = request.form.get('correo', '')
            
            empleado_repo.update(empleado)
            flash('Empleado actualizado con éxito', 'success')
            return redirect(url_for('admin_list_employees'))
            
        except Exception as e:
            flash(f'Error actualizando empleado: {str(e)}', 'error')
    
    empresas = list_companies_use_case.execute()
    return render_template('admin_edit_employee.html', empleado=empleado, empresas=empresas)

@app.route('/admin/toggle_employee/<int:empleado_id>', methods=['POST'])
def toggle_employee(empleado_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    try:
        empleado = empleado_repo.get_by_id(empleado_id)
        if not empleado:
            return jsonify({'success': False, 'message': 'Empleado no encontrado'}), 404
        
        empleado.activo = not empleado.activo
        empleado_repo.update(empleado)
        
        estado = "activado" if empleado.activo else "desactivado"
        return jsonify({
            'success': True, 
            'message': f'Empleado {estado} con éxito',
            'activo': empleado.activo
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/admin/delete_employee/<int:empleado_id>', methods=['POST'])
def delete_employee(empleado_id):
    if not session.get('admin_logged_in'):
        return jsonify({'success': False, 'message': 'No autorizado'}), 401
    
    try:
        empleado = empleado_repo.get_by_id(empleado_id)
        if not empleado:
            return jsonify({'success': False, 'message': 'Empleado no encontrado'}), 404
        
        nombre_empleado = empleado.nombre
        
        empleado_repo.delete(empleado_id)
        
        return jsonify({
            'success': True, 
            'message': f'Empleado {nombre_empleado} eliminado permanentemente de la base de datos'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/admin/download_qr/<int:empleado_id>')
def download_qr(empleado_id):
    try:
        empleado = empleado_repo.get_by_id(empleado_id)
        if not empleado:
            flash('Empleado no encontrado', 'error')
            return redirect(url_for('admin_list_employees'))
        
        empresa = empresa_repo.get_by_id(empleado.empresa_id)
        if not empresa:
            flash('Empresa no encontrada', 'error')
            return redirect(url_for('admin_list_employees'))
        
        qr_path = qr_generator.generate_employee_qr(empleado.id, empresa.codigo_empresa)
        
        if qr_path and os.path.exists(qr_path):
            return send_file(
                qr_path,
                mimetype='image/png',
                as_attachment=True,
                download_name=f'qr_empleado_{empleado_id}_{empresa.codigo_empresa}.png'
            )
        else:
            flash('Error generando código QR para descarga', 'error')
            return redirect(url_for('admin_list_employees'))
            
    except Exception as e:
        flash(f'Error descargando QR: {str(e)}', 'error')
        return redirect(url_for('admin_list_employees'))

@app.route('/scan')
def scan_qr():
    return render_template('scan.html')

@app.route('/api/scan', methods=['POST'])
def api_scan_qr():
    try:
        data = request.get_json()
        codigo_qr = data.get('codigo_qr', '')
        ip_address = request.remote_addr
        
        resultado = mark_attendance_use_case.execute(codigo_qr, ip_address)
        
        return jsonify(resultado)
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Error procesando escaneo: {str(e)}",
            "data": None
        })

@app.route('/reports')
def reports():
     if not session.get('admin_logged_in'):
        flash('Debes iniciar sesión para acceder a los reportes', 'error')
        return redirect(url_for('admin_login'))
     
     empresas = list_companies_use_case.execute()
     return render_template('report.html', empresas=empresas)

@app.route('/api/reports/monthly')
def api_monthly_report():
    try:
        empresa_id = request.args.get('empresa_id', type=int)
        mes = request.args.get('mes', type=int, default=datetime.now().month)
        anio = request.args.get('anio', type=int, default=datetime.now().year)
        
        if not empresa_id:
            return jsonify({"error": "Empresa ID requerido"}), 400
        
        reporte = get_report_use_case.execute_monthly_report(empresa_id, mes, anio)
        return jsonify(reporte)
        
    except Exception as e:
        return jsonify({"error": f"Error generando reporte: {str(e)}"}), 500

@app.route('/api/reports/employee/<int:empleado_id>')
def api_employee_report(empleado_id):
    try:    
        mes = request.args.get('mes', type=int, default=datetime.now().month)
        anio = request.args.get('anio', type=int, default=datetime.now().year)
        
        reporte = get_report_use_case.execute_employee_detail_report(empleado_id, mes, anio)
        return jsonify(reporte)
        
    except Exception as e:
        return jsonify({"error": f"Error generando reporte: {str(e)}"}), 500
    
@app.route('/api/empleados')
def api_get_empleados():
    """Obtiene empleados de una empresa"""
    try:
        empresa_id = request.args.get('empresa_id', type=int)
        
        if not empresa_id:
            return jsonify({"error": "empresa_id requerido"}), 400
        
        empleados = empleado_repo.get_by_empresa_id(empresa_id)
        
        # Convertir a diccionario
        empleados_data = []
        for emp in empleados:
            empleados_data.append({
                "id": emp.id,
                "nombre": emp.nombre,
                "dni": emp.dni,
                "empresa_id": emp.empresa_id,
                "activo": emp.activo
            })
        
        return jsonify(empleados_data)
        
    except Exception as e:
        print(f"Error en api_get_empleados: {e}")
        return jsonify({"error": str(e)}), 500
    

@app.route('/api/asistencias/<int:empleado_id>')
def api_get_asistencia_empleado(empleado_id):
    """Obtiene asistencia de un empleado en una fecha específica"""
    try:
        fecha = request.args.get('fecha')
        
        if not fecha:
            return jsonify({"error": "Fecha requerida"}), 400
        
        asistencia = asistencia_repo.get_by_empleado_and_fecha(empleado_id, fecha)
        
        if asistencia:
            return jsonify({
                "fecha": str(asistencia.fecha),
                "entrada_manana_real": str(asistencia.entrada_manana_real) if asistencia.entrada_manana_real else None,
                "salida_manana_real": str(asistencia.salida_manana_real) if asistencia.salida_manana_real else None,
                "entrada_tarde_real": str(asistencia.entrada_tarde_real) if asistencia.entrada_tarde_real else None,
                "salida_tarde_real": str(asistencia.salida_tarde_real) if asistencia.salida_tarde_real else None
            })
        else:
            return jsonify({}), 200
            
    except Exception as e:
        print(f"Error en api_get_asistencia_empleado: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/export/excel')
def export_report_excel():
    try:
        empresa_id = request.args.get('empresa_id', type=int)
        mes = request.args.get('mes', type=int, default=datetime.now().month)
        anio = request.args.get('anio', type=int, default=datetime.now().year)
        
        if not empresa_id:
            flash('Empresa ID requerido', 'error')
            return redirect(url_for('reports'))
        
        empleados = empleado_repo.get_by_empresa_id(empresa_id)
        primer_dia = f"{anio}-{mes:02d}-01"
        ultimo_dia = f"{anio}-{mes:02d}-{calendar.monthrange(anio, mes)[1]}"
        
        output = BytesIO()
        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte Diario"
        
        header_font = Font(bold=True)
        header_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
        alignment_center = Alignment(horizontal="center", vertical="center")
        
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        fila_actual = 1
        
        for empleado in empleados:
            ws.merge_cells(start_row=fila_actual, start_column=1, end_row=fila_actual, end_column=10)
            titulo_cell = ws.cell(row=fila_actual, column=1, value=f"EMPLEADO: {empleado.nombre.upper()}")
            titulo_cell.font = Font(bold=True, size=14)
            titulo_cell.fill = PatternFill(start_color="CCCCCC", end_color="CCCCCC", fill_type="solid")
            titulo_cell.alignment = Alignment(horizontal="center", vertical="center")
            fila_actual += 1
            
            headers = ['DIA', 'ENTRADA_MANANA', 'SALIDA_MANANA', 'TOTAL_MANANA', 
                      'ENTRADA_TARDE', 'SALIDA_TARDE', 'TOTAL_TARDE', 'TOTAL_DIA', 'HORAS_NORMALES', 'HORAS_EXTRAS']
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=fila_actual, column=col, value=header)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = alignment_center
                cell.border = thin_border
            fila_actual += 1
            
            total_manana_minutos = 0
            total_tarde_minutos = 0
            total_horas_extras_mes = 0
            
            dias_del_mes = calendar.monthrange(anio, mes)[1]
            
            for dia in range(1, dias_del_mes + 1):
                fecha = f"{anio}-{mes:02d}-{dia:02d}"
                
                asistencia = asistencia_repo.get_by_empleado_and_fecha(empleado.id, fecha)
                
                if asistencia:
                    total_manana = ""
                    if asistencia.entrada_manana_real and asistencia.salida_manana_real:
                        minutos_manana = int((asistencia.salida_manana_real.hour * 60 + asistencia.salida_manana_real.minute) - 
                                           (asistencia.entrada_manana_real.hour * 60 + asistencia.entrada_manana_real.minute))
                        total_manana = minutos_a_hhmm(max(0, minutos_manana))
                        h, m = map(int, total_manana.split(":"))
                        total_manana_minutos += h * 60 + m
                    
                    total_tarde = ""
                    if asistencia.entrada_tarde_real and asistencia.salida_tarde_real:
                        minutos_tarde = int((asistencia.salida_tarde_real.hour * 60 + asistencia.salida_tarde_real.minute) - 
                                          (asistencia.entrada_tarde_real.hour * 60 + asistencia.entrada_tarde_real.minute))
                        total_tarde = minutos_a_hhmm(max(0, minutos_tarde))
                        h, m = map(int, total_tarde.split(":"))
                        total_tarde_minutos += h * 60 + m
                    
                    total_dia_minutos = 0
                    if total_manana:
                        h, m = map(int, total_manana.split(":"))
                        total_dia_minutos += h * 60 + m
                    if total_tarde:
                        h, m = map(int, total_tarde.split(":"))
                        total_dia_minutos += h * 60 + m
                    total_dia = minutos_a_hhmm(total_dia_minutos)
                    
                    minutos_normales_dia = min(total_dia_minutos, 8 * 60)
                    minutos_extras_dia = max(0, total_dia_minutos - (8 * 60))
                    
                    total_horas_extras_mes += minutos_extras_dia
                    
                    horas_normales_dia = minutos_a_hhmm(minutos_normales_dia)
                    horas_extras_dia = minutos_a_hhmm(minutos_extras_dia)
                    
                    valores = [
                        dia,
                        str(asistencia.entrada_manana_real) if asistencia.entrada_manana_real else "",
                        str(asistencia.salida_manana_real) if asistencia.salida_manana_real else "",
                        total_manana,
                        str(asistencia.entrada_tarde_real) if asistencia.entrada_tarde_real else "",
                        str(asistencia.salida_tarde_real) if asistencia.salida_tarde_real else "",
                        total_tarde,
                        total_dia,
                        horas_normales_dia,
                        horas_extras_dia
                    ]
                else:
                    valores = [dia, "", "", "", "", "", "", "", "", ""]
                
                for col, valor in enumerate(valores, 1):
                    cell = ws.cell(row=fila_actual, column=col, value=valor)
                    cell.border = thin_border
                    if col == 1:
                        cell.alignment = Alignment(horizontal="center")
                
                fila_actual += 1
            
            total_manana_mes = minutos_a_hhmm(total_manana_minutos)
            total_tarde_mes = minutos_a_hhmm(total_tarde_minutos)
            total_dia_mes = minutos_a_hhmm(total_manana_minutos + total_tarde_minutos)

            total_minutos_mes = total_manana_minutos + total_tarde_minutos
            minutos_normales_mes = total_minutos_mes - total_horas_extras_mes
            minutos_extras_mes = total_horas_extras_mes

            horas_normales_mes = minutos_a_hhmm(minutos_normales_mes)
            horas_extras_mes = minutos_a_hhmm(minutos_extras_mes)
            
            valores_totales = [
                "TOTAL MES",
                "", "", total_manana_mes,
                "", "", total_tarde_mes,
                total_dia_mes,
                horas_normales_mes,
                horas_extras_mes
            ]
            for col, valor in enumerate(valores_totales, 1):
                cell = ws.cell(row=fila_actual, column=col, value=valor)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="DDDDDD", end_color="DDDDDD", fill_type="solid")
                cell.border = thin_border
                if col == 1:
                    cell.alignment = Alignment(horizontal="center")
            fila_actual += 1
            
            fila_actual += 1
        
        column_widths = [8, 15, 15, 15, 15, 15, 15, 15, 15, 15]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width
        
        wb.save(output)
        output.seek(0)
        
        nombre_empresa = empresa_repo.get_by_id(empresa_id).nombre.replace(' ', '_') if empresa_repo.get_by_id(empresa_id) else 'empresa'
        nombre_archivo = f"reporte_diario_{nombre_empresa}_{mes}_{anio}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=nombre_archivo
        )
        
    except Exception as e:
        flash(f'Error generando reporte Excel: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/admin/generate_qr/<int:empleado_id>')
def generate_employee_qr(empleado_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        empleado = empleado_repo.get_by_id(empleado_id)
        if not empleado:
            flash('Empleado no encontrado', 'error')
            return redirect(url_for('admin_list_employees'))
        
        empresa = empresa_repo.get_by_id(empleado.empresa_id)
        if not empresa:
            flash('Empresa no encontrada', 'error')
            return redirect(url_for('admin_list_employees'))
        
        qr_path = qr_generator.generate_employee_qr(empleado.id, empresa.codigo_empresa)
        if qr_path:
            flash('Código QR generado con éxito.', 'success')
        else:
            flash('Error generando código QR', 'error')
            
    except Exception as e:
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('admin_list_employees'))

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', error_message="Página no encontrada"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error_message="Error interno del servidor"), 500

# ===============================================
# 📊 REPORTE SEMANAL DE ACTIVIDAD Y RENDIMIENTO
# ===============================================

from datetime import timedelta
from collections import Counter

@app.route('/admin/weekly-report')
def admin_weekly_report():
    """Página principal del reporte semanal"""
    if not session.get('admin_logged_in'):
        flash('Debes iniciar sesión para acceder al reporte semanal', 'error')
        return redirect(url_for('admin_login'))
    
    empresas = list_companies_use_case.execute()
    return render_template('weekly_report.html', empresas=empresas)


@app.route('/api/weekly-report/summary')
def api_weekly_report_summary():
    """Resumen general de la semana"""
    if not session.get('admin_logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    try:
        from src.infrastructure.mysql_connection import get_connection
        
        empresa_id = request.args.get('empresa_id', type=int)
        semana_offset = request.args.get('semana', type=int, default=0)
        
        hoy = datetime.now().date()
        inicio_semana = hoy - timedelta(days=hoy.weekday()) + timedelta(weeks=semana_offset)
        fin_semana = inicio_semana + timedelta(days=6)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        empresa_filter = "AND e.empresa_id = %s" if empresa_id else ""
        params = [inicio_semana.strftime('%Y-%m-%d'), fin_semana.strftime('%Y-%m-%d')]
        if empresa_id:
            params.append(empresa_id)
        
        # Total empleados activos
        if empresa_id:
            cursor.execute("SELECT COUNT(*) FROM EMPLEADOS WHERE empresa_id = %s AND activo = TRUE", (empresa_id,))
        else:
            cursor.execute("SELECT COUNT(*) FROM EMPLEADOS WHERE activo = TRUE")
        total_empleados = cursor.fetchone()[0]
        
        # Promedio de asistencia de la semana
        cursor.execute(f"""
            SELECT 
                COUNT(DISTINCT CONCAT(a.empleado_id, '-', a.fecha)) as registros_totales,
                COUNT(DISTINCT CASE WHEN (a.tardanza_manana = FALSE AND a.tardanza_tarde = FALSE 
                                          AND a.entrada_manana_real IS NOT NULL) 
                                    THEN CONCAT(a.empleado_id, '-', a.fecha) END) as registros_puntuales
            FROM ASISTENCIA a
            JOIN EMPLEADOS e ON a.empleado_id = e.id
            WHERE a.fecha BETWEEN %s AND %s
              AND e.activo = TRUE
              {empresa_filter}
        """, params)
        
        result = cursor.fetchone()
        registros_totales = result[0] or 0
        registros_puntuales = result[1] or 0
        
        promedio_puntualidad = int((registros_puntuales / registros_totales * 100)) if registros_totales > 0 else 0
        
        # Porcentaje de asistencia promedio
        dias_semana = 7 if fin_semana <= datetime.now().date() else (datetime.now().date() - inicio_semana).days + 1
        asistencias_esperadas = total_empleados * dias_semana
        porcentaje_asistencia = int((registros_totales / asistencias_esperadas * 100)) if asistencias_esperadas > 0 else 0
        
        # Total de tardanzas
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM ASISTENCIA a
            JOIN EMPLEADOS e ON a.empleado_id = e.id
            WHERE a.fecha BETWEEN %s AND %s
              AND (a.tardanza_manana = TRUE OR a.tardanza_tarde = TRUE)
              {empresa_filter}
        """, params)
        total_tardanzas = cursor.fetchone()[0]
        
        # Total de faltas
        total_faltas = asistencias_esperadas - registros_totales
        
        # Horas extras acumuladas
        cursor.execute(f"""
            SELECT SUM(a.horas_extras)
            FROM ASISTENCIA a
            JOIN EMPLEADOS e ON a.empleado_id = e.id
            WHERE a.fecha BETWEEN %s AND %s
              {empresa_filter}
        """, params)
        horas_extras = cursor.fetchone()[0] or 0
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "periodo": {
                "inicio": inicio_semana.strftime('%Y-%m-%d'),
                "fin": fin_semana.strftime('%Y-%m-%d'),
                "inicio_formato": inicio_semana.strftime('%d/%m/%Y'),
                "fin_formato": fin_semana.strftime('%d/%m/%Y')
            },
            "total_empleados": total_empleados,
            "promedio_puntualidad": promedio_puntualidad,
            "porcentaje_asistencia": porcentaje_asistencia,
            "total_tardanzas": total_tardanzas,
            "total_faltas": total_faltas,
            "horas_extras": round(horas_extras, 2)
        })
        
    except Exception as e:
        import traceback
        print(f"Error en weekly summary: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/api/weekly-report/daily-attendance')
def api_weekly_report_daily_attendance():
    """Asistencia diaria de la semana"""
    if not session.get('admin_logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    try:
        from src.infrastructure.mysql_connection import get_connection
        
        empresa_id = request.args.get('empresa_id', type=int)
        semana_offset = request.args.get('semana', type=int, default=0)
        
        hoy = datetime.now().date()
        inicio_semana = hoy - timedelta(days=hoy.weekday()) + timedelta(weeks=semana_offset)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        dias_labels = []
        asistencias_data = []
        tardanzas_data = []
        faltas_data = []
        
        # Total de empleados
        if empresa_id:
            cursor.execute("SELECT COUNT(*) FROM EMPLEADOS WHERE empresa_id = %s AND activo = TRUE", (empresa_id,))
        else:
            cursor.execute("SELECT COUNT(*) FROM EMPLEADOS WHERE activo = TRUE")
        total_empleados = cursor.fetchone()[0]
        
        for i in range(7):
            dia = inicio_semana + timedelta(days=i)
            
            if dia > datetime.now().date():
                break
            
            dia_str = dia.strftime('%Y-%m-%d')
            
            # Traducir días a español
            dias_semana_es = {
                'Monday': 'Lun', 'Tuesday': 'Mar', 'Wednesday': 'Mié',
                'Thursday': 'Jue', 'Friday': 'Vie', 'Saturday': 'Sáb', 'Sunday': 'Dom'
            }
            dia_nombre_en = dia.strftime('%A')
            dia_nombre_es = dias_semana_es.get(dia_nombre_en, dia_nombre_en[:3])
            dias_labels.append(f"{dia_nombre_es} {dia.day}")
            
            empresa_filter = "AND e.empresa_id = %s" if empresa_id else ""
            params = [dia_str]
            if empresa_id:
                params.append(empresa_id)
            
            # Asistencias
            cursor.execute(f"""
                SELECT COUNT(DISTINCT a.empleado_id)
                FROM ASISTENCIA a
                JOIN EMPLEADOS e ON a.empleado_id = e.id
                WHERE a.fecha = %s
                  AND (a.entrada_manana_real IS NOT NULL OR a.entrada_tarde_real IS NOT NULL)
                  {empresa_filter}
            """, params)
            asistencias = cursor.fetchone()[0]
            asistencias_data.append(asistencias)
            
            # Tardanzas
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM ASISTENCIA a
                JOIN EMPLEADOS e ON a.empleado_id = e.id
                WHERE a.fecha = %s
                  AND (a.tardanza_manana = TRUE OR a.tardanza_tarde = TRUE)
                  {empresa_filter}
            """, params)
            tardanzas = cursor.fetchone()[0]
            tardanzas_data.append(tardanzas)
            
            faltas = total_empleados - asistencias
            faltas_data.append(faltas)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "dias": dias_labels,
            "asistencias": asistencias_data,
            "tardanzas": tardanzas_data,
            "faltas": faltas_data
        })
        
    except Exception as e:
        import traceback
        print(f"Error en daily attendance: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/api/weekly-report/frequent-hours')
def api_weekly_report_frequent_hours():
    """Horas más frecuentes de ingreso"""
    if not session.get('admin_logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    try:
        from src.infrastructure.mysql_connection import get_connection
        
        empresa_id = request.args.get('empresa_id', type=int)
        semana_offset = request.args.get('semana', type=int, default=0)
        
        hoy = datetime.now().date()
        inicio_semana = hoy - timedelta(days=hoy.weekday()) + timedelta(weeks=semana_offset)
        fin_semana = inicio_semana + timedelta(days=6)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        empresa_filter = "AND e.empresa_id = %s" if empresa_id else ""
        params = [inicio_semana.strftime('%Y-%m-%d'), fin_semana.strftime('%Y-%m-%d')]
        if empresa_id:
            params.append(empresa_id)
        
        # Horas de entrada mañana
        cursor.execute(f"""
            SELECT TIME_FORMAT(a.entrada_manana_real, '%H:00') as hora
            FROM ASISTENCIA a
            JOIN EMPLEADOS e ON a.empleado_id = e.id
            WHERE a.fecha BETWEEN %s AND %s
              AND a.entrada_manana_real IS NOT NULL
              {empresa_filter}
        """, params)
        
        horas_manana = [row[0] for row in cursor.fetchall()]
        frecuencia_manana = Counter(horas_manana)
        hora_frecuente_manana = frecuencia_manana.most_common(1)[0] if frecuencia_manana else (None, 0)
        
        # Horas de entrada tarde
        cursor.execute(f"""
            SELECT TIME_FORMAT(a.entrada_tarde_real, '%H:00') as hora
            FROM ASISTENCIA a
            JOIN EMPLEADOS e ON a.empleado_id = e.id
            WHERE a.fecha BETWEEN %s AND %s
              AND a.entrada_tarde_real IS NOT NULL
              {empresa_filter}
        """, params)
        
        horas_tarde = [row[0] for row in cursor.fetchall()]
        frecuencia_tarde = Counter(horas_tarde)
        hora_frecuente_tarde = frecuencia_tarde.most_common(1)[0] if frecuencia_tarde else (None, 0)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "hora_frecuente_manana": hora_frecuente_manana[0] if hora_frecuente_manana[0] else "N/A",
            "frecuencia_manana": hora_frecuente_manana[1],
            "hora_frecuente_tarde": hora_frecuente_tarde[0] if hora_frecuente_tarde[0] else "N/A",
            "frecuencia_tarde": hora_frecuente_tarde[1]
        })
        
    except Exception as e:
        import traceback
        print(f"Error en frequent hours: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/api/weekly-report/worst-days')
def api_weekly_report_worst_days():
    """Días con menor asistencia"""
    if not session.get('admin_logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    try:
        from src.infrastructure.mysql_connection import get_connection
        
        empresa_id = request.args.get('empresa_id', type=int)
        semana_offset = request.args.get('semana', type=int, default=0)
        
        hoy = datetime.now().date()
        inicio_semana = hoy - timedelta(days=hoy.weekday()) + timedelta(weeks=semana_offset)
        fin_semana = inicio_semana + timedelta(days=6)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        empresa_filter = "AND e.empresa_id = %s" if empresa_id else ""
        params = [inicio_semana.strftime('%Y-%m-%d'), fin_semana.strftime('%Y-%m-%d')]
        if empresa_id:
            params.append(empresa_id)
        
        cursor.execute(f"""
            SELECT 
                a.fecha,
                COUNT(DISTINCT a.empleado_id) as total_asistencias,
                DAYNAME(a.fecha) as dia_semana
            FROM ASISTENCIA a
            JOIN EMPLEADOS e ON a.empleado_id = e.id
            WHERE a.fecha BETWEEN %s AND %s
              AND (a.entrada_manana_real IS NOT NULL OR a.entrada_tarde_real IS NOT NULL)
              {empresa_filter}
            GROUP BY a.fecha
            ORDER BY total_asistencias ASC
            LIMIT 3
        """, params)
        
        peores_dias = []
        for row in cursor.fetchall():
            fecha = row[0]
            asistencias = row[1]
            dia_semana = row[2]
            
            dias_traduccion = {
                'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
                'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
            }
            dia_es = dias_traduccion.get(dia_semana, dia_semana)
            
            peores_dias.append({
                "fecha": fecha.strftime('%d/%m/%Y'),
                "dia": dia_es,
                "asistencias": asistencias
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(peores_dias)
        
    except Exception as e:
        import traceback
        print(f"Error en worst days: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/api/weekly-report/companies-comparison')
def api_weekly_report_companies_comparison():
    """Comparación entre empresas"""
    if not session.get('admin_logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    try:
        from src.infrastructure.mysql_connection import get_connection
        
        empresa_id = request.args.get('empresa_id', type=int)
        semana_offset = request.args.get('semana', type=int, default=0)
        
        hoy = datetime.now().date()
        inicio_semana = hoy - timedelta(days=hoy.weekday()) + timedelta(weeks=semana_offset)
        fin_semana = inicio_semana + timedelta(days=6)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Si hay empresa seleccionada, solo mostrar esa
        if empresa_id:
            cursor.execute("""
                SELECT 
                    emp.id,
                    emp.nombre,
                    COUNT(DISTINCT e.id) as total_empleados,
                    COUNT(DISTINCT CASE WHEN a.fecha BETWEEN %s AND %s 
                                        AND (a.entrada_manana_real IS NOT NULL OR a.entrada_tarde_real IS NOT NULL)
                                        THEN CONCAT(a.empleado_id, '-', a.fecha) END) as asistencias_semana
                FROM EMPRESAS emp
                LEFT JOIN EMPLEADOS e ON emp.id = e.empresa_id AND e.activo = TRUE
                LEFT JOIN ASISTENCIA a ON e.id = a.empleado_id
                WHERE emp.id = %s
                GROUP BY emp.id, emp.nombre
            """, (inicio_semana.strftime('%Y-%m-%d'), fin_semana.strftime('%Y-%m-%d'), empresa_id))
        else:
            cursor.execute("""
                SELECT 
                    emp.id,
                    emp.nombre,
                    COUNT(DISTINCT e.id) as total_empleados,
                    COUNT(DISTINCT CASE WHEN a.fecha BETWEEN %s AND %s 
                                        AND (a.entrada_manana_real IS NOT NULL OR a.entrada_tarde_real IS NOT NULL)
                                        THEN CONCAT(a.empleado_id, '-', a.fecha) END) as asistencias_semana
                FROM EMPRESAS emp
                LEFT JOIN EMPLEADOS e ON emp.id = e.empresa_id AND e.activo = TRUE
                LEFT JOIN ASISTENCIA a ON e.id = a.empleado_id
                GROUP BY emp.id, emp.nombre
                ORDER BY emp.nombre
            """, (inicio_semana.strftime('%Y-%m-%d'), fin_semana.strftime('%Y-%m-%d')))
        
        empresas_data = []
        dias_transcurridos = min(7, (datetime.now().date() - inicio_semana).days + 1)
        if dias_transcurridos < 1:
            dias_transcurridos = 1
        
        for row in cursor.fetchall():
            nombre = row[1]
            total_empleados = row[2] or 0
            asistencias = row[3] or 0
            
            asistencias_esperadas = total_empleados * dias_transcurridos
            porcentaje = int((asistencias / asistencias_esperadas * 100)) if asistencias_esperadas > 0 else 0
            
            if total_empleados > 0:
                empresas_data.append({
                    "nombre": nombre,
                    "total_empleados": total_empleados,
                    "porcentaje_asistencia": porcentaje
                })
        
        cursor.close()
        conn.close()
        
        return jsonify(empresas_data)
        
    except Exception as e:
        import traceback
        print(f"Error en companies comparison: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/api/weekly-report/top-punctual')
def api_weekly_report_top_punctual():
    """Top 5 empleados más puntuales de la semana"""
    if not session.get('admin_logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    
    try:
        from src.infrastructure.mysql_connection import get_connection
        
        empresa_id = request.args.get('empresa_id', type=int)
        semana_offset = request.args.get('semana', type=int, default=0)
        
        hoy = datetime.now().date()
        inicio_semana = hoy - timedelta(days=hoy.weekday()) + timedelta(weeks=semana_offset)
        fin_semana = inicio_semana + timedelta(days=6)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        empresa_filter = "AND e.empresa_id = %s" if empresa_id else ""
        params = [inicio_semana.strftime('%Y-%m-%d'), fin_semana.strftime('%Y-%m-%d')]
        if empresa_id:
            params.append(empresa_id)
        
        cursor.execute(f"""
    SELECT 
        e.nombre,
        COUNT(CASE 
            WHEN (
                -- Si tiene entrada en la mañana, debe ser <= 06:50
                (a.entrada_manana_real IS NOT NULL AND TIME(a.entrada_manana_real) <= '06:50:00')
                OR a.entrada_manana_real IS NULL  -- permite que no tenga turno mañana
            )
            AND (
                -- Si tiene entrada en la tarde, debe ser <= 14:50
                (a.entrada_tarde_real IS NOT NULL AND TIME(a.entrada_tarde_real) <= '14:50:00')
                OR a.entrada_tarde_real IS NULL   -- permite que no tenga turno tarde
            )
            AND (
                a.entrada_manana_real IS NOT NULL OR a.entrada_tarde_real IS NOT NULL  -- al menos vino en algún turno
            )
            THEN 1 
        END) as dias_puntuales,
        COUNT(DISTINCT a.fecha) as total_dias_asistidos
    FROM EMPLEADOS e
    LEFT JOIN ASISTENCIA a ON e.id = a.empleado_id 
        AND a.fecha BETWEEN %s AND %s
    WHERE e.activo = TRUE {empresa_filter}
    GROUP BY e.id, e.nombre
    HAVING dias_puntuales > 0
    ORDER BY dias_puntuales DESC, total_dias_asistidos DESC
    LIMIT 5
""", params)
        
        top_puntuales = []
        for row in cursor.fetchall():
            top_puntuales.append({
                "nombre": row[0],
                "dias_puntuales": row[1],
                "total_dias": row[2]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(top_puntuales)
        
    except Exception as e:
        import traceback
        print(f"Error en top punctual: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/api/weekly-report/top-late')
def api_weekly_report_top_late():
    """Top 5 empleados con más tardanzas reales (basado en horas reales)"""
    if not session.get('admin_logged_in'):
        return jsonify({"error": "No autorizado"}), 401
    try:
        from src.infrastructure.mysql_connection import get_connection
        empresa_id = request.args.get('empresa_id', type=int)
        semana_offset = request.args.get('semana', type=int, default=0)
        hoy = datetime.now().date()
        inicio_semana = hoy - timedelta(days=hoy.weekday()) + timedelta(weeks=semana_offset)
        fin_semana = inicio_semana + timedelta(days=6)
        conn = get_connection()
        cursor = conn.cursor()
        empresa_filter = "AND e.empresa_id = %s" if empresa_id else ""
        params = [inicio_semana.strftime('%Y-%m-%d'), fin_semana.strftime('%Y-%m-%d')]
        if empresa_id:
            params.append(empresa_id)

        # 🔥 NUEVA LÓGICA: basada en horas reales, no en booleanos
        cursor.execute(f"""
            SELECT 
                e.nombre,
                COUNT(CASE 
                    WHEN (
                        (a.entrada_manana_real IS NOT NULL AND TIME(a.entrada_manana_real) > '06:50:00')
                        OR
                        (a.entrada_tarde_real IS NOT NULL AND TIME(a.entrada_tarde_real) > '14:50:00')
                    )
                    THEN 1 
                END) as total_tardanzas,
                COUNT(DISTINCT a.fecha) as total_dias
            FROM EMPLEADOS e
            INNER JOIN ASISTENCIA a ON e.id = a.empleado_id 
                AND a.fecha BETWEEN %s AND %s
            WHERE e.activo = TRUE {empresa_filter}
            GROUP BY e.id, e.nombre
            HAVING total_tardanzas > 0
            ORDER BY total_tardanzas DESC
            LIMIT 5
        """, params)

        top_tardes = []
        for row in cursor.fetchall():
            top_tardes.append({
                "nombre": row[0],
                "tardanzas": row[1],
                "total_dias": row[2]
            })
        cursor.close()
        conn.close()
        return jsonify(top_tardes)
    except Exception as e:
        import traceback
        print(f"Error en top late: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8080)