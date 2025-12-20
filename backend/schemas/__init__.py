"""
Conecta Plus - Schemas Pydantic
"""

from .auth import Token, TokenData, LoginRequest
from .usuario import UsuarioBase, UsuarioCreate, UsuarioUpdate, UsuarioResponse
from .condominio import CondominioBase, CondominioCreate, CondominioResponse
from .unidade import UnidadeBase, UnidadeCreate, UnidadeResponse
from .morador import MoradorBase, MoradorCreate, MoradorResponse
from .acesso import RegistroAcessoCreate, RegistroAcessoResponse, PontoAcessoResponse
from .ocorrencia import OcorrenciaBase, OcorrenciaCreate, OcorrenciaUpdate, OcorrenciaResponse
from .manutencao import OrdemServicoCreate, OrdemServicoUpdate, OrdemServicoResponse, FornecedorResponse
from .financeiro import LancamentoCreate, LancamentoResponse, BoletoResponse
from .alarme import ZonaAlarmeResponse, EventoAlarmeResponse, ComandoAlarme
from .reserva import AreaComumResponse, ReservaCreate, ReservaResponse
from .comunicado import ComunicadoCreate, ComunicadoResponse
from .assembleia import AssembleiaCreate, AssembleiaResponse, VotacaoResponse

__all__ = [
    "Token", "TokenData", "LoginRequest",
    "UsuarioBase", "UsuarioCreate", "UsuarioUpdate", "UsuarioResponse",
    "CondominioBase", "CondominioCreate", "CondominioResponse",
    "UnidadeBase", "UnidadeCreate", "UnidadeResponse",
    "MoradorBase", "MoradorCreate", "MoradorResponse",
    "RegistroAcessoCreate", "RegistroAcessoResponse", "PontoAcessoResponse",
    "OcorrenciaBase", "OcorrenciaCreate", "OcorrenciaUpdate", "OcorrenciaResponse",
    "OrdemServicoCreate", "OrdemServicoUpdate", "OrdemServicoResponse", "FornecedorResponse",
    "LancamentoCreate", "LancamentoResponse", "BoletoResponse",
    "ZonaAlarmeResponse", "EventoAlarmeResponse", "ComandoAlarme",
    "AreaComumResponse", "ReservaCreate", "ReservaResponse",
    "ComunicadoCreate", "ComunicadoResponse",
    "AssembleiaCreate", "AssembleiaResponse", "VotacaoResponse",
]
