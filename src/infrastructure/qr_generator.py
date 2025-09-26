import qrcode
import os
from io import BytesIO
import base64
from typing import Optional

class QRGenerator:
    def __init__(self, save_directory: str = "static/qr/"):
        self.save_directory = save_directory
        # Crear directorio si no existe
        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)
    
    def generate_qr_code(self, data: str, filename: str = None) -> Optional[str]:
        """
        Genera un código QR y lo guarda como archivo
        Retorna la ruta del archivo generado
        """
        try:
            # Crear código QR
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            # Crear imagen
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Generar nombre de archivo si no se proporciona
            if not filename:
                filename = f"qr_{hash(data)}.png"
            
            # Ruta completa del archivo
            file_path = os.path.join(self.save_directory, filename)
            
            # Guardar imagen
            img.save(file_path)
            
            return file_path
        except Exception as e:
            print(f"Error generando código QR: {e}")
            return None
    
    def generate_qr_base64(self, data: str) -> Optional[str]:
        """
        Genera un código QR y lo retorna como string base64
        Útil para mostrar en HTML sin guardar archivo
        """
        try:
            # Crear código QR
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)
            
            # Crear imagen
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convertir a base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return img_str
        except Exception as e:
            print(f"Error generando código QR base64: {e}")
            return None
    
    def generate_employee_qr(self, empleado_id: int, empresa_codigo: str) -> Optional[str]:
        """
        Genera un código QR específico para un empleado
        Formato: EMP_[EMPRESA_CODIGO]_[EMPLEADO_ID]_[TIMESTAMP]
        """
        import time
        timestamp = int(time.time())
        qr_data = f"EMP_{empresa_codigo}_{empleado_id}_{timestamp}"
        filename = f"emp_{empresa_codigo}_{empleado_id}.png"
        
        return self.generate_qr_code(qr_data, filename)
    
    def validate_qr_format(self, qr_data: str) -> bool:
        """
        Valida si el formato del código QR es válido para el sistema
        """
        # Formato esperado: EMP_[CODIGO]_[ID]_[TIMESTAMP]
        if qr_data.startswith("EMP_") and len(qr_data.split("_")) >= 4:
            return True
        return False

# Función de utilidad para uso global
def generate_qr_for_employee(empleado_id: int, empresa_codigo: str) -> Optional[str]:
    """
    Función de conveniencia para generar QR de empleado
    """
    qr_generator = QRGenerator()
    return qr_generator.generate_employee_qr(empleado_id, empresa_codigo)

