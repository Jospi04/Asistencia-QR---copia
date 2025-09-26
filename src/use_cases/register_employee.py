from src.domain.entities import Empleado
from src.domain.repositories import EmpleadoRepository
import time
import random
import string

class RegisterEmployeeUseCase:
    def __init__(self, empleado_repository: EmpleadoRepository):
        self.empleado_repository = empleado_repository
    
    def execute(self, nombre: str, empresa_id: int, dni: str, 
                telefono: str = "", correo: str = "") -> Empleado:
        """
        Registra un nuevo empleado y genera su código QR único
        """
        # Generar código QR único
        codigo_qr = self._generate_unique_qr_code(empresa_id)
        
        # Crear empleado
        empleado = Empleado(
            empresa_id=empresa_id,
            nombre=nombre,
            dni=dni,
            codigo_qr_unico=codigo_qr,
            telefono=telefono,
            correo=correo
        )
        
        # Guardar en repositorio
        empleado_guardado = self.empleado_repository.create(empleado)
        
        return empleado_guardado
    
    def _generate_unique_qr_code(self, empresa_id: int) -> str:
        """
        Genera un código QR único para el empleado
        Formato: EMP_[EMPRESA_ID]_[TIMESTAMP]_[RANDOM]
        """
        timestamp = int(time.time())
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"EMP_{empresa_id}_{timestamp}_{random_chars}"

class RegisterEmployeeRequest:
    def __init__(self, nombre: str, empresa_id: int, dni: str, 
                 telefono: str = "", correo: str = ""):
        self.nombre = nombre
        self.empresa_id = empresa_id
        self.dni = dni
        self.telefono = telefono
        self.correo = correo

