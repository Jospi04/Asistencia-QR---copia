import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('EMAIL_PORT', '587'))
        self.email_user = os.getenv('EMAIL_USER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.sender_name = os.getenv('EMAIL_SENDER_NAME', 'Sistema Asistencia QR')

    def enviar_correo(self, destinatario: str, asunto: str, mensaje_html: str) -> bool:
        """Envía correo electrónico"""
        try:
            if not destinatario or not self.email_user or not self.email_password:
                print("Datos de correo incompletos")
                return False

            msg = MIMEMultipart('alternative')
            msg['Subject'] = asunto
            msg['From'] = f"{self.sender_name} <{self.email_user}>"
            msg['To'] = destinatario

            html_part = MIMEText(mensaje_html, 'html')
            msg.attach(html_part)

            print(f"Enviando correo a {destinatario}...")
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.send_message(msg)
            server.quit()

            print(f"Correo enviado exitosamente a {destinatario}")
            return True
        except Exception as e:
            print(f"Error enviando correo a {destinatario}: {e}")
            return False

    def enviar_alerta_faltas(self, nombre_empleado: str, email_empleado: str, 
                           numero_faltas: int, empresa_nombre: str) -> bool:
        """Envía alerta de faltas por correo"""
        if not email_empleado or not nombre_empleado:
            print("Datos de empleado incompletos para enviar alerta")
            return False

        asunto_empleado = f"Alerta de Asistencia - {empresa_nombre}"
        html_empleado = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <div style="background-color: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h2 style="color: #d32f2f; margin: 0;">Alerta de Asistencia</h2>
                        <div style="width: 50px; height: 3px; background-color: #d32f2f; margin: 15px auto;"></div>
                    </div>
                    <p style="font-size: 18px; margin-bottom: 20px;">
                        <strong>Hola {nombre_empleado}</strong>,
                    </p>
                    <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; 
                                padding: 20px; border-radius: 8px; margin: 25px 0;">
                        <p style="margin: 0 0 10px 0; font-size: 16px;">
                            <strong>Importante:</strong>
                        </p>
                        <p style="margin: 0; font-size: 16px;">
                            Has acumulado <strong style="color: #d32f2f; font-size: 18px;">{numero_faltas} faltas</strong> 
                            en el sistema de asistencia de <strong>{empresa_nombre}</strong>.
                        </p>
                    </div>
                    <div style="background-color: #e3f2fd; border: 1px solid #2196f3; 
                                padding: 20px; border-radius: 8px; margin: 25px 0;">
                        <p style="margin: 0 0 10px 0; font-size: 16px;">
                            <strong>Acción requerida:</strong>
                        </p>
                        <p style="margin: 0; font-size: 16px;">
                            Por favor, regulariza tu asistencia para evitar sanciones.
                        </p>
                    </div>
                    <div style="margin: 30px 0; padding: 15px; background-color: #f0f0f0; border-radius: 5px;">
                        <p style="margin: 0; font-size: 14px; color: #666;">
                            <strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br>
                            <strong>Sistema:</strong> Asistencia QR - {empresa_nombre}
                        </p>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 20px; font-size: 12px; color: #888;">
                    <p>Este es un mensaje automático del Sistema de Asistencia QR</p>
                </div>
            </div>
        </body>
        </html>
        """

        email_empresa = os.getenv('EMAIL_EMPRESA', self.email_user)
        asunto_empresa = f"Alerta: Empleado con {numero_faltas} faltas"
        html_empresa = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                <div style="background-color: #fff; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <div style="text-align: center; margin-bottom: 30px;">
                        <h2 style="color: #d32f2f; margin: 0;">Alerta de Empleado</h2>
                        <div style="width: 50px; height: 3px; background-color: #d32f2f; margin: 15px auto;"></div>
                    </div>
                    <div style="background-color: #fff; border: 2px solid #d32f2f; 
                                padding: 25px; border-radius: 8px; margin: 25px 0;">
                        <h3 style="color: #d32f2f; margin-top: 0;">Alerta Crítica</h3>
                        <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                            <tr>
                                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Empresa:</strong></td>
                                <td style="padding: 10px; border: 1px solid #ddd;">{empresa_nombre}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Empleado:</strong></td>
                                <td style="padding: 10px; border: 1px solid #ddd;">{nombre_empleado}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Email:</strong></td>
                                <td style="padding: 10px; border: 1px solid #ddd;">{email_empleado}</td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border: 1px solid #ddd;"><strong>Faltas acumuladas:</strong></td>
                                <td style="padding: 10px; border: 1px solid #ddd;">
                                    <span style="color: #d32f2f; font-weight: bold; font-size: 18px;">{numero_faltas}</span>
                                </td>
                            </tr>
                        </table>
                    </div>
                    <div style="background-color: #fff3cd; border: 1px solid #ffd700; 
                                padding: 20px; border-radius: 8px; margin: 25px 0;">
                        <p style="margin: 0 0 10px 0; font-size: 16px;">
                            <strong>Recomendación:</strong>
                        </p>
                        <p style="margin: 0; font-size: 16px;">
                            Tomar las medidas necesarias con el empleado.
                        </p>
                    </div>
                    <div style="margin: 30px 0; padding: 15px; background-color: #f0f0f0; border-radius: 5px;">
                        <p style="margin: 0; font-size: 14px; color: #666;">
                            <strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}<br>
                            <strong>Sistema:</strong> Asistencia QR - {empresa_nombre}
                        </p>
                    </div>
                </div>
                <div style="text-align: center; margin-top: 20px; font-size: 12px; color: #888;">
                    <p>Sistema de Asistencia QR - {empresa_nombre}</p>
                </div>
            </div>
        </body>
        </html>
        """

        print("Enviando alerta al empleado...")
        exito_empleado = self.enviar_correo(email_empleado, asunto_empleado, html_empleado)
        print("Enviando alerta a la empresa...")
        exito_empresa = self.enviar_correo(email_empresa, asunto_empresa, html_empresa)

        if exito_empleado and exito_empresa:
            print("Ambas alertas enviadas correctamente")
        elif exito_empleado:
            print("Alerta enviada solo al empleado")
        elif exito_empresa:
            print("Alerta enviada solo a la empresa")
        else:
            print("No se pudieron enviar las alertas")

        return exito_empleado or exito_empresa

    def enviar_reporte_semanal(self, email_destino: str, asunto: str, contenido: str) -> bool:
        """Envía reporte semanal a la jefa"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = asunto
            msg['From'] = f"{self.sender_name} <{self.email_user}>"
            msg['To'] = email_destino

            html_part = MIMEText(contenido, 'html')
            msg.attach(html_part)

            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.email_user, self.email_password)
            server.send_message(msg)
            server.quit()

            return True
        except Exception as e:
            print(f"Error enviando reporte semanal: {e}")
            return False