"""
Conecta Plus - Modelos do Banco de Dados
"""

from .usuario import Usuario, Role
from .condominio import Condominio
from .unidade import Unidade
from .morador import Morador, TipoMorador
from .veiculo import Veiculo
from .acesso import RegistroAcesso, TipoAcesso, PontoAcesso
from .ocorrencia import Ocorrencia, StatusOcorrencia, TipoOcorrencia
from .manutencao import OrdemServico, StatusOS, TipoOS, Fornecedor
from .financeiro import Lancamento, TipoLancamento, Boleto, StatusBoleto
from .alarme import ZonaAlarme, EventoAlarme, StatusZona
from .reserva import AreaComum, Reserva, StatusReserva
from .comunicado import Comunicado, TipoComunicado
from .assembleia import Assembleia, Votacao, Ata, StatusAssembleia

__all__ = [
    "Usuario", "Role",
    "Condominio",
    "Unidade",
    "Morador", "TipoMorador",
    "Veiculo",
    "RegistroAcesso", "TipoAcesso", "PontoAcesso",
    "Ocorrencia", "StatusOcorrencia", "TipoOcorrencia",
    "OrdemServico", "StatusOS", "TipoOS", "Fornecedor",
    "Lancamento", "TipoLancamento", "Boleto", "StatusBoleto",
    "ZonaAlarme", "EventoAlarme", "StatusZona",
    "AreaComum", "Reserva", "StatusReserva",
    "Comunicado", "TipoComunicado",
    "Assembleia", "Votacao", "Ata", "StatusAssembleia",
]
