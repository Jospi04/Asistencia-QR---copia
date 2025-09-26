from src.domain.entities import Empresa
from src.domain.repositories import EmpresaRepository
from typing import List

class ListCompaniesUseCase:
    def __init__(self, empresa_repository: EmpresaRepository):
        self.empresa_repository = empresa_repository
    
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
        # Aquí se podría extender para incluir conteo de empleados
        # si se tiene acceso al repositorio de empleados
        return [
            {
                "id": empresa.id,
                "nombre": empresa.nombre,
                "codigo_empresa": empresa.codigo_empresa,
                "empleado_count": 0  # Placeholder, se calcularía realmente
            }
            for empresa in empresas
        ]

class ListCompaniesRequest:
    def __init__(self):
        pass

# class ListCompanies:
#     def __init__(self, empresa_repo):
#         self.empresa_repo = empresa_repo

#     def execute(self):
#         return self.empresa_repo.list_all()
