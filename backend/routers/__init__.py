"""
Conecta Plus - Routers da API
"""

from .auth import router as auth_router
from .usuarios import router as usuarios_router
from .condominios import router as condominios_router
from .unidades import router as unidades_router
from .moradores import router as moradores_router
from .acesso import router as acesso_router
from .ocorrencias import router as ocorrencias_router
from .manutencao import router as manutencao_router
from .financeiro import router as financeiro_router
from .alarmes import router as alarmes_router
from .reservas import router as reservas_router
from .comunicados import router as comunicados_router
from .assembleias import router as assembleias_router
from .dashboard import router as dashboard_router
from .guardian import router as guardian_router

__all__ = [
    "auth_router",
    "usuarios_router",
    "condominios_router",
    "unidades_router",
    "moradores_router",
    "acesso_router",
    "ocorrencias_router",
    "manutencao_router",
    "financeiro_router",
    "alarmes_router",
    "reservas_router",
    "comunicados_router",
    "assembleias_router",
    "dashboard_router",
    "guardian_router",
]
