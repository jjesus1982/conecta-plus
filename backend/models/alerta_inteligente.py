"""
Conecta Plus - Modelo de Alerta Inteligível
RF-01: Todo alerta deve responder 3 perguntas: O que? Por que importa? O que fazer?

Princípio: "Nenhum problema sem próximo passo"
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from ..database import Base


class NivelImpacto(str, PyEnum):
    """Níveis de impacto do alerta."""
    INFORMATIVO = "informativo"      # Sem impacto direto
    BAIXO = "baixo"                  # Impacto menor
    MEDIO = "medio"                  # Atenção necessária
    ALTO = "alto"                    # Ação imediata requerida
    CRITICO = "critico"              # Emergência


class CategoriaAlerta(str, PyEnum):
    """Categorias de alerta."""
    SEGURANCA = "seguranca"
    MANUTENCAO = "manutencao"
    FINANCEIRO = "financeiro"
    OPERACIONAL = "operacional"
    COMUNICACAO = "comunicacao"
    EQUIPAMENTO = "equipamento"


class StatusAlerta(str, PyEnum):
    """Status do alerta."""
    ATIVO = "ativo"
    EM_ATENDIMENTO = "em_atendimento"
    AGUARDANDO = "aguardando"
    RESOLVIDO = "resolvido"
    DESCARTADO = "descartado"


class AlertaInteligente(Base):
    """
    Modelo de Alerta Inteligível conforme RF-01.

    Estrutura obrigatória:
    - titulo: Texto humano, não técnico
    - contexto: Por que isso importa?
    - impacto: O que acontece se ignorar?
    - responsavel: Quem cuida disso?
    - acao_sugerida: O que fazer agora?
    - status: Em andamento / Resolvido / Aguardando

    Exemplo ANTES: "Câmera offline"
    Exemplo DEPOIS:
      titulo: "Câmera da garagem offline há 4h"
      contexto: "Esta câmera cobre a entrada principal de veículos"
      impacto: "Segurança comprometida em área crítica"
      responsavel: "Técnico Conecta Mais acionado"
      acao_sugerida: "Aguarde atualização ou acione suporte"
      status: "Em atendimento - previsão 2h"
    """
    __tablename__ = "alertas_inteligentes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Código legível: ALT-YYYYMMDD-XXXX
    codigo = Column(String(20), unique=True, nullable=False, index=True)

    # === ESTRUTURA OBRIGATÓRIA (RF-01) ===

    # O QUE? - Texto humano, não técnico
    titulo = Column(String(255), nullable=False)

    # POR QUE IMPORTA? - Contexto do impacto
    contexto = Column(Text, nullable=False)

    # O QUE ACONTECE SE IGNORAR? - Impacto real
    impacto = Column(Text, nullable=False)

    # QUEM CUIDA DISSO? - Responsável definido
    responsavel_nome = Column(String(100))
    responsavel_id = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    responsavel = relationship("Usuario", foreign_keys=[responsavel_id])

    # O QUE FAZER AGORA? - Próximo passo claro
    acao_sugerida = Column(Text, nullable=False)

    # QUAL O STATUS? - Status de resolução
    status = Column(String(30), default="ativo", index=True)

    # === CAMPOS ADICIONAIS ===

    # Classificação
    categoria = Column(String(30), default="operacional")
    nivel_impacto = Column(String(20), default="medio")

    # Previsão de resolução
    previsao_resolucao = Column(String(100))  # "hoje até 18h", "2 horas", etc.
    prazo_sla = Column(DateTime)

    # Origem do alerta (sistema que detectou)
    origem = Column(String(50))  # cftv, financeiro, portaria, seguranca, etc.
    origem_id = Column(String(100))  # ID do item original

    # Localização
    localizacao = Column(String(255))

    # Perfis que devem ver este alerta
    perfis_destinatarios = Column(JSONB, default=["sindico", "administrador"])

    # Confirmação de leitura
    lido = Column(Boolean, default=False)
    lido_por = Column(UUID(as_uuid=True), ForeignKey("usuarios.id"))
    lido_em = Column(DateTime)

    # Histórico de ações (timeline)
    timeline = Column(JSONB, default=[])

    # Metadados extras
    dados_extras = Column(JSONB, default={})

    # Condomínio
    condominio_id = Column(UUID(as_uuid=True), ForeignKey("condominios.id"), nullable=False)
    condominio = relationship("Condominio", backref="alertas_inteligentes")

    # Timestamps
    detectado_em = Column(DateTime, default=datetime.utcnow)
    atendido_em = Column(DateTime)
    resolvido_em = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AlertaInteligente {self.codigo} - {self.titulo}>"

    def adicionar_timeline(self, evento: str, descricao: str, usuario_id: str = "sistema"):
        """Adiciona evento ao timeline do alerta."""
        if self.timeline is None:
            self.timeline = []
        self.timeline.append({
            "timestamp": datetime.utcnow().isoformat(),
            "evento": evento,
            "descricao": descricao,
            "usuario": usuario_id
        })

    def marcar_lido(self, usuario_id: str):
        """Marca o alerta como lido."""
        self.lido = True
        self.lido_por = usuario_id
        self.lido_em = datetime.utcnow()
        self.adicionar_timeline("lido", "Alerta visualizado", usuario_id)

    def iniciar_atendimento(self, responsavel_id: str, responsavel_nome: str, previsao: str):
        """Inicia o atendimento do alerta."""
        self.status = "em_atendimento"
        self.responsavel_id = responsavel_id
        self.responsavel_nome = responsavel_nome
        self.previsao_resolucao = previsao
        self.atendido_em = datetime.utcnow()
        self.adicionar_timeline(
            "atendimento_iniciado",
            f"Atendimento iniciado por {responsavel_nome}. Previsão: {previsao}",
            responsavel_id
        )

    def resolver(self, usuario_id: str, resolucao: str):
        """Resolve o alerta."""
        self.status = "resolvido"
        self.resolvido_em = datetime.utcnow()
        self.adicionar_timeline("resolvido", resolucao, usuario_id)


class TemplateAlerta(Base):
    """
    Templates para geração automática de alertas inteligíveis.
    Permite configurar textos padrão por tipo de evento.
    """
    __tablename__ = "templates_alerta"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Identificação
    codigo = Column(String(50), unique=True, nullable=False)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)

    # Tipo de evento que aciona
    tipo_evento = Column(String(50), nullable=False)  # camera_offline, inadimplencia_alta, etc.

    # Templates (suportam variáveis como {camera_nome}, {dias_offline}, etc.)
    template_titulo = Column(String(255), nullable=False)
    template_contexto = Column(Text, nullable=False)
    template_impacto = Column(Text, nullable=False)
    template_acao = Column(Text, nullable=False)

    # Configurações padrão
    categoria_padrao = Column(String(30), default="operacional")
    nivel_impacto_padrao = Column(String(20), default="medio")
    perfis_padrao = Column(JSONB, default=["sindico"])

    # SLA padrão em minutos
    sla_padrao_minutos = Column(Integer, default=120)

    # Ativo
    ativo = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<TemplateAlerta {self.codigo}>"


# ==================== TEMPLATES PADRÃO ====================
TEMPLATES_PADRAO = [
    {
        "codigo": "CAMERA_OFFLINE",
        "nome": "Câmera Offline",
        "tipo_evento": "camera_offline",
        "template_titulo": "Câmera {camera_nome} offline há {tempo_offline}",
        "template_contexto": "Esta câmera cobre a área de {area}. Sem monitoramento, eventos nesta região não serão detectados.",
        "template_impacto": "Segurança comprometida na área de {area}. Possíveis incidentes podem passar despercebidos.",
        "template_acao": "Técnico será notificado automaticamente. Aguarde atualização ou acione suporte pelo chat.",
        "categoria_padrao": "equipamento",
        "nivel_impacto_padrao": "alto",
        "perfis_padrao": ["sindico", "administrador", "porteiro"],
        "sla_padrao_minutos": 120
    },
    {
        "codigo": "INADIMPLENCIA_ALTA",
        "nome": "Inadimplência Elevada",
        "tipo_evento": "inadimplencia_alta",
        "template_titulo": "Inadimplência atingiu {percentual}% das unidades",
        "template_contexto": "O percentual de inadimplência está acima do ideal (15%). Isso pode impactar o caixa do condomínio.",
        "template_impacto": "Risco de não conseguir arcar com despesas fixas. Pode ser necessário usar fundo de reserva.",
        "template_acao": "Recomendamos revisar a lista de inadimplentes e acionar cobrança. Ações disponíveis no módulo financeiro.",
        "categoria_padrao": "financeiro",
        "nivel_impacto_padrao": "alto",
        "perfis_padrao": ["sindico", "administrador"],
        "sla_padrao_minutos": 1440  # 24h
    },
    {
        "codigo": "VISITANTE_AGUARDANDO",
        "nome": "Visitante Aguardando",
        "tipo_evento": "visitante_aguardando",
        "template_titulo": "Visitante aguardando autorização há {tempo_espera}",
        "template_contexto": "Visitante {visitante_nome} aguarda na portaria para acessar a unidade {unidade}.",
        "template_impacto": "Tempo de espera prolongado causa má impressão e insatisfação do morador.",
        "template_acao": "Autorize ou recuse o acesso. Se não reconhecer, acione o morador da unidade.",
        "categoria_padrao": "operacional",
        "nivel_impacto_padrao": "medio",
        "perfis_padrao": ["porteiro"],
        "sla_padrao_minutos": 5
    },
    {
        "codigo": "MANUTENCAO_ATRASADA",
        "nome": "Manutenção Atrasada",
        "tipo_evento": "manutencao_atrasada",
        "template_titulo": "Manutenção de {equipamento} atrasada em {dias} dias",
        "template_contexto": "A manutenção preventiva de {equipamento} estava programada para {data_programada}.",
        "template_impacto": "Equipamento pode apresentar falhas. Custo de reparo pode ser maior que manutenção preventiva.",
        "template_acao": "Agende a manutenção ou registre justificativa para o atraso.",
        "categoria_padrao": "manutencao",
        "nivel_impacto_padrao": "medio",
        "perfis_padrao": ["sindico", "zelador"],
        "sla_padrao_minutos": 480  # 8h
    },
    {
        "codigo": "OCORRENCIA_SEM_RESPOSTA",
        "nome": "Ocorrência Sem Resposta",
        "tipo_evento": "ocorrencia_sem_resposta",
        "template_titulo": "Ocorrência #{numero} sem resposta há {tempo}",
        "template_contexto": "Morador da unidade {unidade} registrou: \"{titulo_ocorrencia}\"",
        "template_impacto": "Morador sem retorno fica insatisfeito e pode escalar reclamação.",
        "template_acao": "Atribua um responsável e forneça prazo estimado ao morador.",
        "categoria_padrao": "operacional",
        "nivel_impacto_padrao": "medio",
        "perfis_padrao": ["sindico", "zelador"],
        "sla_padrao_minutos": 240  # 4h
    },
    {
        "codigo": "ACESSO_SUSPEITO",
        "nome": "Acesso Suspeito Detectado",
        "tipo_evento": "acesso_suspeito",
        "template_titulo": "Acesso suspeito detectado em {local}",
        "template_contexto": "O sistema de seguranca IA detectou comportamento atípico: {descricao_ia}",
        "template_impacto": "Possível tentativa de invasão ou acesso não autorizado. Segurança do condomínio em risco.",
        "template_acao": "Verifique as imagens da câmera. Se confirmar suspeita, acione segurança ou polícia.",
        "categoria_padrao": "seguranca",
        "nivel_impacto_padrao": "critico",
        "perfis_padrao": ["porteiro", "sindico"],
        "sla_padrao_minutos": 5
    },
    {
        "codigo": "RESERVA_CONFLITO",
        "nome": "Conflito de Reserva",
        "tipo_evento": "reserva_conflito",
        "template_titulo": "Conflito de reserva para {espaco} em {data}",
        "template_contexto": "Duas reservas foram solicitadas para o mesmo horário no espaço {espaco}.",
        "template_impacto": "Moradores podem comparecer ao mesmo tempo, gerando atrito e insatisfação.",
        "template_acao": "Defina qual reserva tem prioridade e comunique os moradores afetados.",
        "categoria_padrao": "operacional",
        "nivel_impacto_padrao": "baixo",
        "perfis_padrao": ["sindico", "zelador"],
        "sla_padrao_minutos": 60
    }
]
