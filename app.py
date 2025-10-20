from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
import os
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
load_dotenv()
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import calendar
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

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

EMAIL_EMPRESA_ADMIN = os.getenv('EMAIL_EMPRESA') 
if not EMAIL_EMPRESA_ADMIN:
    print("⚠️ ADVERTENCIA: Variable EMAIL_EMPRESA no encontrada en .env.")

# Inicializar repositorios
empresa_repo = EmpresaRepositoryMySQL(db_connection)
empleado_repo = EmpleadoRepositoryMySQL(db_connection)
asistencia_repo = AsistenciaRepositoryMySQL(db_connection)
horario_repo = HorarioEstandarRepositoryMySQL(db_connection)
escaneo_repo = EscaneoTrackingRepositoryMySQL(db_connection)

# Inicializar use cases
register_employee_use_case = RegisterEmployeeUseCase(empleado_repo)
mark_attendance_use_case = MarkAttendanceUseCase(empleado_repo, asistencia_repo, horario_repo, escaneo_repo, empresa_repo, EMAIL_EMPRESA_ADMIN)
list_companies_use_case = ListCompaniesUseCase(empresa_repo,)
get_report_use_case = GetReportUseCase(empleado_repo, asistencia_repo, empresa_repo)

# Inicializar QR generator
qr_generator = QRGenerator()

# --------------------------------------------------------------------------------------
# FUNCIÓN DEL JOB SEMANAL
# --------------------------------------------------------------------------------------
def job_reporte_semanal():
    """Job semanal que envía reportes a la dueña y a los empleados"""
    try:
        print("=" * 70)
        print("🚀 JOB SEMANAL INICIADO")
        print(f"⏰ Hora servidor: {datetime.now()}")
        print("=" * 70)
        
        print("\n📧 PASO 1: Enviando reportes CONSOLIDADOS a la jefa...")
        mark_attendance_use_case.generar_reporte_semanal()
        print("✅ Reportes consolidados enviados\n")
        
        print("📧 PASO 2: Enviando reportes INDIVIDUALES a empleados...")
        mark_attendance_use_case.enviar_reporte_individual_empleados()
        print("✅ Reportes individuales enviados\n")
        
        print("🎉 JOB SEMANAL COMPLETADO EXITOSAMENTE")
        print("=" * 70)
    except Exception as e:
        print("=" * 70)
        print(f"❌ ERROR en Job Semanal: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 70)

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


# --------------------------------------------------------------------------------------
# INICIO DEL SCHEDULER (Solo en producción/Fly.io)
# --------------------------------------------------------------------------------------
if __name__ == '__main__':
    
    print("=" * 70)
    print("🚀 INICIANDO APLICACIÓN")
    print("=" * 70)
    
    # Crear scheduler
    scheduler = BackgroundScheduler()
    
    # Programar job semanal - LUNES 7:00 AM (Perú)
    scheduler.add_job(
        job_reporte_semanal, 
        trigger='cron', 
        day_of_week='mon',   # Lunes
        hour=7,              # 7:00 AM
        minute=0, 
        timezone='America/Lima'
    )
    
    print("✅ Job programado: Lunes a las 7:00 AM (Perú)")
    
    # Iniciar scheduler
    scheduler.start()
    print("✅ Scheduler iniciado correctamente")
    
    # Registrar shutdown
    atexit.register(lambda: scheduler.shutdown(wait=False))
    
    if EMAIL_EMPRESA_ADMIN:
        print(f"📧 Email admin: {EMAIL_EMPRESA_ADMIN}")
    else:
        print("⚠️  EMAIL_EMPRESA no configurado")
    
    print("=" * 70)
    print("🌐 Iniciando servidor Flask...\n")
    
    # Iniciar Flask (debug=False para producción)
    app.run(debug=False, host='0.0.0.0', port=8080)