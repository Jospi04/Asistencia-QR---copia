from src.domain.entities import Empresa
from src.domain.repositories import EmpresaRepository, EmpleadoRepository
from typing import List

class ListCompaniesUseCase:
    def __init__(self, empresa_repository: EmpresaRepository, empleado_repository: EmpleadoRepository = None):
        self.empresa_repository = empresa_repository
        self.empleado_repository = empleado_repository
    
    def execute(self) -> List[Empresa]:
        """
        Obtiene la lista de todas las empresas
        """
        return self.empresa_repository.get_all()
    
    def execute_with_employee_count(self) -> List[dict]:
        """
        Obtiene la lista de empresas con el conteo de empleados
        """
        empresas = self.empresa_repository.get_all()
        
        resultado = []
        for empresa in empresas:
            # Contar empleados reales si hay repositorio disponible
            empleado_count = 0
            if self.empleado_repository:
                empleados = self.empleado_repository.get_by_empresa_id(empresa.id)
                empleado_count = len(empleados) if empleados else 0
            
            resultado.append({
                "id": empresa.id,
                "nombre": empresa.nombre,
                "codigo_empresa": empresa.codigo_empresa,
                "empleado_count": empleado_count
            })
        
        return resultado


class ListCompaniesRequest:
    def __init__(self):
        pass