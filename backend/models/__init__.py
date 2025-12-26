"""
Conecta Plus - Modelos do Banco de Dados
"""

from .usuario import Usuario, Role
from .condominio import Condominio
from .unidade import Unidade
from .morador import Morador, TipoMorador
from .veiculo import Veiculo
from .acesso import RegistroAcesso, TipoAcesso, PontoAcesso
from .ocorrencia import Ocorrencia, StatusOcorrencia, TipoOcorrencia, OrigemPrazo
from .manutencao import OrdemServico, StatusOS, TipoOS, Fornecedor
from .financeiro import Lancamento, TipoLancamento, Boleto, StatusBoleto
from .alarme import ZonaAlarme, EventoAlarme, StatusZona
from .reserva import AreaComum, Reserva, StatusReserva
from .comunicado import Comunicado, TipoComunicado
from .assembleia import Assembleia, Votacao, Ata, StatusAssembleia

# Q1 - Fundamentos de Tranquilidade
from .sla_config import SLAConfig, TipoEntidade, PrioridadeSLA
from .decision_log import DecisionLog, ModuloSistema, TipoDecisao, NivelCriticidade
from .tranquilidade import (
    TranquilidadeSnapshot, RecomendacaoTemplate,
    EstadoTranquilidade, PerfilUsuario
)

# Q2 - Inteligencia Proativa (temporariamente desabilitado - requer schema conecta)
# from .previsao import (
#     Previsao, TipoPrevisao, SubtipoPrevisao, StatusPrevisao, TipoEntidadePrevisao
# )
# from .sugestao import (
#     Sugestao, TipoSugestao, CodigoSugestao, StatusSugestao, PerfilDestino
# )
# from .comunicacao import (
#     PreferenciaComunicacao, HistoricoComunicacao, FilaComunicacao,
#     CanalComunicacao, TipoComunicacao, UrgenciaComunicacao
# )
# from .feedback import (
#     FeedbackModelo, MetricaModelo, HistoricoTreinamento,
#     TipoOrigem, TipoFeedback, ValorFeedback
# )
# Placeholders para manter compatibilidade
TipoPrevisao = StatusPrevisao = SubtipoPrevisao = TipoEntidadePrevisao = None
TipoSugestao = StatusSugestao = PerfilDestino = CodigoSugestao = None
TipoComunicacao = UrgenciaComunicacao = CanalComunicacao = None
TipoOrigem = ValorFeedback = TipoFeedback = None

__all__ = [
    "Usuario", "Role",
    "Condominio",
    "Unidade",
    "Morador", "TipoMorador",
    "Veiculo",
    "RegistroAcesso", "TipoAcesso", "PontoAcesso",
    "Ocorrencia", "StatusOcorrencia", "TipoOcorrencia", "OrigemPrazo",
    "OrdemServico", "StatusOS", "TipoOS", "Fornecedor",
    "Lancamento", "TipoLancamento", "Boleto", "StatusBoleto",
    "ZonaAlarme", "EventoAlarme", "StatusZona",
    "AreaComum", "Reserva", "StatusReserva",
    "Comunicado", "TipoComunicado",
    "Assembleia", "Votacao", "Ata", "StatusAssembleia",
    # Q1 - Fundamentos de Tranquilidade
    "SLAConfig", "TipoEntidade", "PrioridadeSLA",
    "DecisionLog", "ModuloSistema", "TipoDecisao", "NivelCriticidade",
    "TranquilidadeSnapshot", "RecomendacaoTemplate", "EstadoTranquilidade", "PerfilUsuario",
    # Q2 - Inteligencia Proativa (temporariamente desabilitado)
    "TipoPrevisao", "StatusPrevisao", "SubtipoPrevisao", "TipoEntidadePrevisao",
    "TipoSugestao", "StatusSugestao", "PerfilDestino", "CodigoSugestao",
    "TipoComunicacao", "UrgenciaComunicacao", "CanalComunicacao",
    "TipoOrigem", "ValorFeedback", "TipoFeedback",
]
