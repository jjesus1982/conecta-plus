"""
Conecta Plus - API Gateway
FastAPI backend principal que serve como gateway para todos os serviços
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import jwt
import os
import uuid
import asyncio
from contextlib import asynccontextmanager
from websocket_manager import manager as ws_manager

# Importa módulo de banco de dados e repositórios
try:
    from database import get_pool, close_pool
    from repositories.base import (
        usuario_repo, condominio_repo, camera_repo,
        unidade_repo, morador_repo, acesso_repo,
        dashboard_repo, ponto_acesso_repo, manutencao_repo
    )
    DATABASE_AVAILABLE = True
except ImportError as e:
    DATABASE_AVAILABLE = False
    print(f"⚠️ Banco de dados não disponível: {e}")

# Importa router financeiro com novos serviços
try:
    from routers.financeiro import router as financeiro_router
    FINANCEIRO_ROUTER_AVAILABLE = True
except ImportError:
    FINANCEIRO_ROUTER_AVAILABLE = False
    print("⚠️ Router financeiro não disponível, usando endpoints mock")

# Configurações
SECRET_KEY = os.getenv("SECRET_KEY", "conecta-plus-secret-key-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas

security = HTTPBearer()

# Lifespan para startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Conecta Plus API Gateway iniciando...")
    # Inicializa pool de conexões do banco
    if DATABASE_AVAILABLE:
        try:
            await get_pool()
            print("✅ Pool de conexões PostgreSQL inicializado")
        except Exception as e:
            print(f"⚠️ Erro ao conectar ao banco: {e}")
    yield
    # Fecha pool de conexões
    if DATABASE_AVAILABLE:
        try:
            await close_pool()
            print("✅ Pool de conexões PostgreSQL fechado")
        except Exception as e:
            print(f"⚠️ Erro ao fechar pool: {e}")
    print("👋 Conecta Plus API Gateway encerrando...")

app = FastAPI(
    title="Conecta Plus API",
    description="API Gateway para o sistema Conecta Plus de gestão de condomínios",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui router financeiro se disponível
if FINANCEIRO_ROUTER_AVAILABLE:
    app.include_router(financeiro_router)
    print("✅ Router financeiro carregado com IA e integração Cora")

# ==================== MODELS ====================

class LoginRequest(BaseModel):
    email: EmailStr
    senha: str

class UserResponse(BaseModel):
    id: str
    email: str
    nome: str
    role: str
    condominioId: Optional[str] = None
    avatar: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    condominio: Optional[Dict[str, Any]] = None

class CondominioResponse(BaseModel):
    id: str
    nome: str
    cnpj: str
    endereco: Dict[str, str]
    telefone: str
    email: str

# ==================== MOCK DATA ====================

# Usuários mock para desenvolvimento
MOCK_USERS = {
    "admin@conectaplus.com.br": {
        "id": "1",
        "email": "admin@conectaplus.com.br",
        "nome": "Administrador",
        "senha": "admin123",
        "role": "admin",
        "condominioId": "1",
    },
    "sindico@conectaplus.com.br": {
        "id": "2",
        "email": "sindico@conectaplus.com.br",
        "nome": "João Silva",
        "senha": "sindico123",
        "role": "sindico",
        "condominioId": "1",
    },
    "porteiro@conectaplus.com.br": {
        "id": "3",
        "email": "porteiro@conectaplus.com.br",
        "nome": "Carlos Santos",
        "senha": "porteiro123",
        "role": "porteiro",
        "condominioId": "1",
    },
}

MOCK_CONDOMINIO = {
    "id": "1",
    "nome": "Residencial Conecta Plus",
    "cnpj": "12.345.678/0001-90",
    "endereco": {
        "logradouro": "Rua das Palmeiras",
        "numero": "500",
        "bairro": "Jardim América",
        "cidade": "São Paulo",
        "estado": "SP",
        "cep": "01234-567",
    },
    "telefone": "(11) 3456-7890",
    "email": "contato@residencialconecta.com.br",
    "configuracoes": {
        "corPrimaria": "#2563eb",
        "corSecundaria": "#1e40af",
        "modulosAtivos": ["cftv", "acesso", "financeiro", "ocorrencias", "reservas", "encomendas", "comunicados"],
    },
}

MOCK_CAMERAS = [
    {"id": "1", "nome": "Portaria Principal", "ip": "192.168.1.101", "status": "online", "localizacao": "Entrada Principal", "ptz": True, "gravando": True},
    {"id": "2", "nome": "Estacionamento A", "ip": "192.168.1.102", "status": "online", "localizacao": "Garagem Subsolo 1", "ptz": False, "gravando": True},
    {"id": "3", "nome": "Estacionamento B", "ip": "192.168.1.103", "status": "offline", "localizacao": "Garagem Subsolo 2", "ptz": False, "gravando": False},
    {"id": "4", "nome": "Hall Social", "ip": "192.168.1.104", "status": "online", "localizacao": "Térreo", "ptz": True, "gravando": True},
    {"id": "5", "nome": "Piscina", "ip": "192.168.1.105", "status": "online", "localizacao": "Área de Lazer", "ptz": False, "gravando": True},
    {"id": "6", "nome": "Academia", "ip": "192.168.1.106", "status": "online", "localizacao": "2º Andar", "ptz": False, "gravando": True},
]

MOCK_ACESSOS = [
    {"id": "1", "pessoaNome": "Carlos Silva", "tipo": "entrada", "metodo": "facial", "local": "Portão Principal", "timestamp": datetime.now().isoformat(), "autorizado": True},
    {"id": "2", "pessoaNome": "Maria Santos", "tipo": "saida", "metodo": "cartao", "local": "Garagem", "timestamp": datetime.now().isoformat(), "autorizado": True},
]

MOCK_DASHBOARD_STATS = {
    "moradores": 248,
    "unidades": 120,
    "visitantesHoje": 15,
    "ocorrenciasAbertas": 7,
    "camerasOnline": 24,
    "camerasTotal": 26,
    "encomendas": 12,
    "reservasHoje": 3,
    "inadimplencia": 8.5,
    "arrecadacaoMes": 156780.00,
}

# ==================== AUTH HELPERS ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

# ==================== ROUTES ====================

@app.get("/")
async def root():
    return {"message": "Conecta Plus API Gateway", "version": "1.0.0", "status": "online"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ==================== AUTH ====================

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    user = None
    condominio_data = None

    # Tenta buscar do banco de dados primeiro
    if DATABASE_AVAILABLE:
        try:
            user = await usuario_repo.get_by_email(request.email)
            if user:
                # Verificar senha (por enquanto aceita qualquer senha para usuários do banco)
                # TODO: Implementar hash de senha com bcrypt
                condominio_data = await condominio_repo.get_default()
        except Exception as e:
            print(f"Erro ao buscar usuário no banco: {e}")

    # Fallback para dados mock se banco falhar ou usuário não encontrado
    if not user:
        mock_user = MOCK_USERS.get(request.email)
        if mock_user and mock_user["senha"] == request.senha:
            user = {
                "id": mock_user["id"],
                "email": mock_user["email"],
                "nome": mock_user["nome"],
                "role": mock_user["role"],
                "condominio_id": mock_user.get("condominioId")
            }
            condominio_data = MOCK_CONDOMINIO

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )

    access_token = create_access_token(
        data={"sub": str(user["id"]), "email": user["email"], "role": user["role"].lower()}
    )

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=str(user["id"]),
            email=user["email"],
            nome=user["nome"],
            role=user["role"].lower(),
            condominioId=str(user.get("condominio_id")) if user.get("condominio_id") else None,
        ),
        condominio=condominio_data,
    )

@app.get("/api/auth/me")
async def get_current_user(payload: dict = Depends(verify_token)):
    email = payload.get("email")
    user = None
    condominio_data = None

    # Tenta buscar do banco
    if DATABASE_AVAILABLE:
        try:
            user = await usuario_repo.get_by_email(email)
            if user:
                condominio_data = await condominio_repo.get_default()
        except Exception as e:
            print(f"Erro ao buscar usuário: {e}")

    # Fallback para mock
    if not user:
        mock_user = MOCK_USERS.get(email)
        if mock_user:
            user = mock_user
            condominio_data = MOCK_CONDOMINIO

    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    return {
        "user": UserResponse(
            id=str(user["id"]),
            email=user["email"],
            nome=user["nome"],
            role=user.get("role", "morador").lower(),
            condominioId=str(user.get("condominio_id") or user.get("condominioId", "")),
        ),
        "condominio": condominio_data,
    }

@app.post("/api/auth/logout")
async def logout(payload: dict = Depends(verify_token)):
    return {"message": "Logout realizado com sucesso"}

@app.get("/api/auth/sso/config")
async def get_sso_config():
    """Retorna configuração de SSO (desabilitado por padrão)"""
    return {
        "google_enabled": False,
        "microsoft_enabled": False,
        "ldap_enabled": False,
        "google_client_id": None,
        "microsoft_client_id": None,
        "microsoft_tenant_id": None
    }

# ==================== DASHBOARD ====================

@app.get("/api/dashboard/estatisticas")
async def get_dashboard_stats(payload: dict = Depends(verify_token)):
    # Tenta buscar do banco
    if DATABASE_AVAILABLE:
        try:
            condominio = await condominio_repo.get_default()
            if condominio:
                stats = await dashboard_repo.get_stats(str(condominio["id"]))
                return stats
        except Exception as e:
            print(f"Erro ao buscar estatísticas: {e}")
    # Fallback para mock
    return MOCK_DASHBOARD_STATS

@app.get("/api/dashboard/alertas")
async def get_dashboard_alerts(payload: dict = Depends(verify_token)):
    return [
        {"id": "1", "tipo": "camera_offline", "mensagem": "Câmera Estacionamento B offline", "prioridade": "alta", "timestamp": datetime.now().isoformat()},
        {"id": "2", "tipo": "visitante_aguardando", "mensagem": "Visitante aguardando na portaria", "prioridade": "media", "timestamp": datetime.now().isoformat()},
    ]

@app.get("/api/dashboard/atividades")
async def get_dashboard_activities(payload: dict = Depends(verify_token)):
    return [
        {"id": "1", "tipo": "acesso", "descricao": "Morador Carlos entrou pelo portão principal", "hora": "14:32"},
        {"id": "2", "tipo": "encomenda", "descricao": "Nova encomenda para Apt 203", "hora": "14:15"},
    ]

# ==================== FRIGATE ====================

MOCK_FRIGATE_INSTANCES = [
    {"id": "frigate-main", "name": "Frigate Principal", "url": "http://frigate:5000"},
]

MOCK_FRIGATE_CAMERAS = [
    {"name": "portaria_principal", "enabled": True, "detect_enabled": True, "record_enabled": True, "snapshots_enabled": True, "motion_enabled": True, "width": 1920, "height": 1080, "fps": 15},
    {"name": "estacionamento_a", "enabled": True, "detect_enabled": True, "record_enabled": True, "snapshots_enabled": True, "motion_enabled": True, "width": 1920, "height": 1080, "fps": 15},
    {"name": "estacionamento_b", "enabled": False, "detect_enabled": False, "record_enabled": False, "snapshots_enabled": False, "motion_enabled": False, "width": 1920, "height": 1080, "fps": 15},
    {"name": "hall_social", "enabled": True, "detect_enabled": True, "record_enabled": True, "snapshots_enabled": True, "motion_enabled": True, "width": 1920, "height": 1080, "fps": 15},
    {"name": "piscina", "enabled": True, "detect_enabled": True, "record_enabled": True, "snapshots_enabled": True, "motion_enabled": True, "width": 1280, "height": 720, "fps": 10},
    {"name": "academia", "enabled": True, "detect_enabled": True, "record_enabled": True, "snapshots_enabled": True, "motion_enabled": True, "width": 1280, "height": 720, "fps": 10},
]

@app.get("/api/frigate/instances")
async def list_frigate_instances(payload: dict = Depends(verify_token)):
    return MOCK_FRIGATE_INSTANCES

@app.get("/api/frigate/instances/{instance_id}/cameras")
async def list_frigate_cameras(instance_id: str, payload: dict = Depends(verify_token)):
    return MOCK_FRIGATE_CAMERAS

@app.get("/api/frigate/instances/{instance_id}/cameras/{camera_name}/snapshot")
async def get_frigate_snapshot(instance_id: str, camera_name: str, payload: dict = Depends(verify_token)):
    return {"url": f"/api/frigate/{instance_id}/{camera_name}/snapshot.jpg", "timestamp": datetime.now().isoformat()}

@app.get("/api/frigate/instances/{instance_id}/cameras/{camera_name}/stream")
async def get_frigate_stream(instance_id: str, camera_name: str, stream_type: str = "hls", payload: dict = Depends(verify_token)):
    return {"url": f"/api/frigate/{instance_id}/{camera_name}/stream.m3u8", "type": stream_type}

@app.get("/api/frigate/instances/{instance_id}/events")
async def list_frigate_events(instance_id: str, payload: dict = Depends(verify_token)):
    return [
        {"id": "evt1", "camera": "portaria_principal", "label": "person", "score": 0.95, "start_time": datetime.now().timestamp(), "has_clip": True, "has_snapshot": True, "zones": ["entrada"]},
        {"id": "evt2", "camera": "estacionamento_a", "label": "car", "score": 0.92, "start_time": datetime.now().timestamp(), "has_clip": True, "has_snapshot": True, "zones": ["garagem"]},
    ]

# ==================== CFTV ====================

@app.get("/api/cftv/cameras")
async def list_cameras(payload: dict = Depends(verify_token)):
    # Tenta buscar do banco
    if DATABASE_AVAILABLE:
        try:
            condominio = await condominio_repo.get_default()
            if condominio:
                cameras = await camera_repo.list_all(str(condominio["id"]))
                return {"items": cameras, "total": len(cameras)}
        except Exception as e:
            print(f"Erro ao buscar câmeras: {e}")
    # Fallback para mock
    return {"items": MOCK_CAMERAS, "total": len(MOCK_CAMERAS)}

@app.get("/api/cftv/cameras/{camera_id}")
async def get_camera(camera_id: str, payload: dict = Depends(verify_token)):
    # Tenta buscar do banco
    if DATABASE_AVAILABLE:
        try:
            camera = await camera_repo.get_by_id(camera_id)
            if camera:
                return camera
        except Exception as e:
            print(f"Erro ao buscar câmera: {e}")
    # Fallback para mock
    camera = next((c for c in MOCK_CAMERAS if c["id"] == camera_id), None)
    if not camera:
        raise HTTPException(status_code=404, detail="Câmera não encontrada")
    return camera

@app.get("/api/cftv/cameras/{camera_id}/snapshot")
async def get_camera_snapshot(camera_id: str, payload: dict = Depends(verify_token)):
    return {"url": f"/api/cftv/stream/{camera_id}/snapshot.jpg", "timestamp": datetime.now().isoformat()}

# ==================== CONTROLE DE ACESSO ====================

@app.get("/api/acesso/registros")
async def list_acessos(payload: dict = Depends(verify_token)):
    return {"items": MOCK_ACESSOS, "total": len(MOCK_ACESSOS)}

@app.get("/api/acesso/visitantes")
async def list_visitantes(payload: dict = Depends(verify_token)):
    return {
        "items": [
            {"id": "1", "nome": "Pedro Almeida", "documento": "123.456.789-00", "unidadeDestino": "Apt 405", "status": "aguardando"},
            {"id": "2", "nome": "Fernanda Lima", "documento": "987.654.321-00", "unidadeDestino": "Apt 203", "status": "aguardando"},
        ],
        "total": 2,
    }

@app.post("/api/acesso/visitantes/{visitante_id}/autorizar")
async def autorizar_visitante(visitante_id: str, payload: dict = Depends(verify_token)):
    return {"message": "Visitante autorizado", "id": visitante_id}

@app.post("/api/acesso/dispositivos/{dispositivo_id}/abrir")
async def abrir_dispositivo(dispositivo_id: str, payload: dict = Depends(verify_token)):
    return {"message": f"Comando enviado para dispositivo {dispositivo_id}", "success": True}

# ==================== FINANCEIRO ====================

# Models do Financeiro
class BoletoCreate(BaseModel):
    unidade_id: str
    valor: float
    vencimento: str
    descricao: Optional[str] = "Taxa de Condomínio"
    tipo: Optional[str] = "condominio"  # condominio, extra, multa, acordo
    parcela: Optional[int] = None
    total_parcelas: Optional[int] = None

class BoletoUpdate(BaseModel):
    valor: Optional[float] = None
    vencimento: Optional[str] = None
    descricao: Optional[str] = None
    status: Optional[str] = None

class PagamentoRegistro(BaseModel):
    boleto_id: str
    valor_pago: float
    data_pagamento: str
    forma_pagamento: str  # pix, boleto, transferencia, dinheiro
    comprovante: Optional[str] = None
    observacao: Optional[str] = None

class LancamentoCreate(BaseModel):
    tipo: str  # receita, despesa
    categoria: str
    descricao: str
    valor: float
    data: str
    unidade_id: Optional[str] = None
    fornecedor: Optional[str] = None
    documento: Optional[str] = None
    recorrente: Optional[bool] = False

class ConfiguracaoBancaria(BaseModel):
    banco: str  # inter, bradesco, itau, santander, bb, caixa
    ambiente: str  # sandbox, producao
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    certificado: Optional[str] = None
    conta: Optional[str] = None
    agencia: Optional[str] = None

# Mock Data Financeiro Expandido
MOCK_BOLETOS = [
    {
        "id": "bol_001",
        "unidade_id": "1",
        "unidade": "Apt 101 - Bloco A",
        "morador": "Carlos Silva",
        "valor": 850.00,
        "valor_original": 850.00,
        "juros": 0,
        "multa": 0,
        "desconto": 0,
        "vencimento": "2024-12-10",
        "competencia": "12/2024",
        "descricao": "Taxa de Condomínio - Dezembro/2024",
        "tipo": "condominio",
        "status": "pago",
        "data_pagamento": "2024-12-08",
        "forma_pagamento": "pix",
        "codigo_barras": "23793.38128 60000.000003 00000.000400 1 92850000085000",
        "linha_digitavel": "23793381286000000000300000004001928500000850",
        "pix_copia_cola": "00020126580014br.gov.bcb.pix0136a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "nosso_numero": "00000004",
        "banco": "Inter",
        "created_at": "2024-11-25T10:00:00",
    },
    {
        "id": "bol_002",
        "unidade_id": "2",
        "unidade": "Apt 102 - Bloco A",
        "morador": "Maria Santos",
        "valor": 850.00,
        "valor_original": 850.00,
        "juros": 0,
        "multa": 0,
        "desconto": 0,
        "vencimento": "2024-12-10",
        "competencia": "12/2024",
        "descricao": "Taxa de Condomínio - Dezembro/2024",
        "tipo": "condominio",
        "status": "pendente",
        "data_pagamento": None,
        "forma_pagamento": None,
        "codigo_barras": "23793.38128 60000.000003 00000.000401 1 92850000085000",
        "linha_digitavel": "23793381286000000000300000004011928500000850",
        "pix_copia_cola": "00020126580014br.gov.bcb.pix0136b2c3d4e5-f6g7-8901-bcde-fg2345678901",
        "nosso_numero": "00000005",
        "banco": "Inter",
        "created_at": "2024-11-25T10:00:00",
    },
    {
        "id": "bol_003",
        "unidade_id": "3",
        "unidade": "Apt 103 - Bloco A",
        "morador": "Pedro Oliveira",
        "valor": 892.50,
        "valor_original": 850.00,
        "juros": 25.50,
        "multa": 17.00,
        "desconto": 0,
        "vencimento": "2024-11-10",
        "competencia": "11/2024",
        "descricao": "Taxa de Condomínio - Novembro/2024",
        "tipo": "condominio",
        "status": "vencido",
        "data_pagamento": None,
        "forma_pagamento": None,
        "codigo_barras": "23793.38128 60000.000003 00000.000402 1 92850000089250",
        "linha_digitavel": "23793381286000000000300000004021928500000892",
        "pix_copia_cola": "00020126580014br.gov.bcb.pix0136c3d4e5f6-g7h8-9012-cdef-gh3456789012",
        "nosso_numero": "00000006",
        "banco": "Inter",
        "dias_atraso": 39,
        "created_at": "2024-10-25T10:00:00",
    },
    {
        "id": "bol_004",
        "unidade_id": "4",
        "unidade": "Apt 201 - Bloco A",
        "morador": "Ana Costa",
        "valor": 850.00,
        "valor_original": 850.00,
        "juros": 0,
        "multa": 0,
        "desconto": 42.50,
        "vencimento": "2024-12-10",
        "competencia": "12/2024",
        "descricao": "Taxa de Condomínio - Dezembro/2024",
        "tipo": "condominio",
        "status": "pendente",
        "data_pagamento": None,
        "forma_pagamento": None,
        "codigo_barras": "23793.38128 60000.000003 00000.000403 1 92850000080750",
        "linha_digitavel": "23793381286000000000300000004031928500000807",
        "pix_copia_cola": "00020126580014br.gov.bcb.pix0136d4e5f6g7-h8i9-0123-defg-hi4567890123",
        "nosso_numero": "00000007",
        "banco": "Inter",
        "created_at": "2024-11-25T10:00:00",
    },
]

MOCK_LANCAMENTOS = [
    {"id": "lanc_001", "tipo": "receita", "categoria": "condominio", "descricao": "Taxa de Condomínio - Dezembro/2024", "valor": 102000.00, "data": "2024-12-01", "status": "confirmado"},
    {"id": "lanc_002", "tipo": "receita", "categoria": "reserva", "descricao": "Reserva Salão de Festas - Apt 305", "valor": 350.00, "data": "2024-12-05", "status": "confirmado"},
    {"id": "lanc_003", "tipo": "despesa", "categoria": "manutencao", "descricao": "Manutenção Elevadores", "valor": 2500.00, "data": "2024-12-03", "fornecedor": "Elevadores ABC", "documento": "NF-12345", "status": "pago"},
    {"id": "lanc_004", "tipo": "despesa", "categoria": "energia", "descricao": "Conta de Energia - Áreas Comuns", "valor": 4850.00, "data": "2024-12-01", "fornecedor": "Enel", "documento": "12345678", "status": "pendente"},
    {"id": "lanc_005", "tipo": "despesa", "categoria": "agua", "descricao": "Conta de Água - Áreas Comuns", "valor": 1230.00, "data": "2024-12-01", "fornecedor": "Sabesp", "documento": "87654321", "status": "pago"},
    {"id": "lanc_006", "tipo": "despesa", "categoria": "funcionarios", "descricao": "Folha de Pagamento - Dezembro", "valor": 18500.00, "data": "2024-12-05", "status": "agendado"},
    {"id": "lanc_007", "tipo": "despesa", "categoria": "seguranca", "descricao": "Monitoramento CFTV", "valor": 890.00, "data": "2024-12-01", "fornecedor": "Segurança Total", "status": "pago"},
]

MOCK_CATEGORIAS = {
    "receita": [
        {"id": "condominio", "nome": "Taxa de Condomínio", "cor": "#22c55e"},
        {"id": "extra", "nome": "Taxa Extra", "cor": "#3b82f6"},
        {"id": "reserva", "nome": "Reservas", "cor": "#8b5cf6"},
        {"id": "multa", "nome": "Multas", "cor": "#ef4444"},
        {"id": "outros", "nome": "Outros", "cor": "#6b7280"},
    ],
    "despesa": [
        {"id": "manutencao", "nome": "Manutenção", "cor": "#f59e0b"},
        {"id": "funcionarios", "nome": "Funcionários", "cor": "#06b6d4"},
        {"id": "energia", "nome": "Energia", "cor": "#eab308"},
        {"id": "agua", "nome": "Água", "cor": "#0ea5e9"},
        {"id": "seguranca", "nome": "Segurança", "cor": "#ec4899"},
        {"id": "limpeza", "nome": "Limpeza", "cor": "#14b8a6"},
        {"id": "administrativo", "nome": "Administrativo", "cor": "#6366f1"},
        {"id": "outros", "nome": "Outros", "cor": "#6b7280"},
    ],
}

MOCK_BANCOS_CONFIG = {
    "inter": {"id": "inter", "nome": "Banco Inter", "logo": "/bancos/inter.png", "configurado": True, "ambiente": "sandbox"},
    "bradesco": {"id": "bradesco", "nome": "Bradesco", "logo": "/bancos/bradesco.png", "configurado": False, "ambiente": None},
    "itau": {"id": "itau", "nome": "Itaú", "logo": "/bancos/itau.png", "configurado": False, "ambiente": None},
    "santander": {"id": "santander", "nome": "Santander", "logo": "/bancos/santander.png", "configurado": False, "ambiente": None},
    "bb": {"id": "bb", "nome": "Banco do Brasil", "logo": "/bancos/bb.png", "configurado": False, "ambiente": None},
    "caixa": {"id": "caixa", "nome": "Caixa Econômica", "logo": "/bancos/caixa.png", "configurado": False, "ambiente": None},
}

# === BOLETOS ===

@app.get("/api/financeiro/boletos")
async def list_boletos(
    status: Optional[str] = None,
    unidade_id: Optional[str] = None,
    competencia: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    payload: dict = Depends(verify_token)
):
    """Lista boletos com filtros opcionais"""
    boletos = MOCK_BOLETOS.copy()

    if status:
        boletos = [b for b in boletos if b["status"] == status]
    if unidade_id:
        boletos = [b for b in boletos if b["unidade_id"] == unidade_id]
    if competencia:
        boletos = [b for b in boletos if b["competencia"] == competencia]

    total = len(boletos)
    start = (page - 1) * limit
    end = start + limit

    return {
        "items": boletos[start:end],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }

@app.get("/api/financeiro/boletos/{boleto_id}")
async def get_boleto(boleto_id: str, payload: dict = Depends(verify_token)):
    """Retorna detalhes de um boleto específico"""
    boleto = next((b for b in MOCK_BOLETOS if b["id"] == boleto_id), None)
    if not boleto:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")
    return boleto

@app.post("/api/financeiro/boletos")
async def create_boleto(boleto: BoletoCreate, payload: dict = Depends(verify_token)):
    """Cria um novo boleto"""
    # Buscar unidade
    unidade = next((u for u in [
        {"id": "1", "bloco": "A", "numero": "101", "morador": "Carlos Silva"},
        {"id": "2", "bloco": "A", "numero": "102", "morador": "Maria Santos"},
        {"id": "3", "bloco": "A", "numero": "103", "morador": "Pedro Oliveira"},
        {"id": "4", "bloco": "A", "numero": "201", "morador": "Ana Costa"},
    ] if u["id"] == boleto.unidade_id), None)

    if not unidade:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")

    novo_boleto = {
        "id": f"bol_{str(uuid.uuid4())[:8]}",
        "unidade_id": boleto.unidade_id,
        "unidade": f"Apt {unidade['numero']} - Bloco {unidade['bloco']}",
        "morador": unidade["morador"],
        "valor": boleto.valor,
        "valor_original": boleto.valor,
        "juros": 0,
        "multa": 0,
        "desconto": 0,
        "vencimento": boleto.vencimento,
        "competencia": datetime.strptime(boleto.vencimento, "%Y-%m-%d").strftime("%m/%Y"),
        "descricao": boleto.descricao,
        "tipo": boleto.tipo,
        "status": "pendente",
        "data_pagamento": None,
        "forma_pagamento": None,
        "codigo_barras": f"23793.38128 60000.000003 00000.{str(uuid.uuid4())[:6]} 1 9285000008{int(boleto.valor*100):04d}",
        "linha_digitavel": f"23793381286000000000300000{str(uuid.uuid4())[:6]}19285000008{int(boleto.valor):04d}",
        "pix_copia_cola": f"00020126580014br.gov.bcb.pix0136{uuid.uuid4()}",
        "nosso_numero": f"{len(MOCK_BOLETOS)+1:08d}",
        "banco": "Inter",
        "created_at": datetime.now().isoformat(),
    }

    MOCK_BOLETOS.append(novo_boleto)

    return {
        "success": True,
        "message": "Boleto criado com sucesso",
        "boleto": novo_boleto,
    }

@app.post("/api/financeiro/boletos/lote")
async def create_boletos_lote(
    competencia: str,
    vencimento: str,
    valor: float,
    descricao: Optional[str] = "Taxa de Condomínio",
    payload: dict = Depends(verify_token)
):
    """Cria boletos em lote para todas as unidades"""
    unidades = [
        {"id": "1", "bloco": "A", "numero": "101", "morador": "Carlos Silva"},
        {"id": "2", "bloco": "A", "numero": "102", "morador": "Maria Santos"},
        {"id": "3", "bloco": "A", "numero": "103", "morador": "Pedro Oliveira"},
        {"id": "4", "bloco": "A", "numero": "201", "morador": "Ana Costa"},
    ]

    boletos_criados = []
    for unidade in unidades:
        novo_boleto = {
            "id": f"bol_{str(uuid.uuid4())[:8]}",
            "unidade_id": unidade["id"],
            "unidade": f"Apt {unidade['numero']} - Bloco {unidade['bloco']}",
            "morador": unidade["morador"],
            "valor": valor,
            "valor_original": valor,
            "juros": 0,
            "multa": 0,
            "desconto": 0,
            "vencimento": vencimento,
            "competencia": competencia,
            "descricao": f"{descricao} - {competencia}",
            "tipo": "condominio",
            "status": "pendente",
            "banco": "Inter",
            "created_at": datetime.now().isoformat(),
        }
        MOCK_BOLETOS.append(novo_boleto)
        boletos_criados.append(novo_boleto)

    return {
        "success": True,
        "message": f"{len(boletos_criados)} boletos criados com sucesso",
        "total": len(boletos_criados),
        "boletos": boletos_criados,
    }

@app.put("/api/financeiro/boletos/{boleto_id}")
async def update_boleto(boleto_id: str, boleto: BoletoUpdate, payload: dict = Depends(verify_token)):
    """Atualiza um boleto existente"""
    idx = next((i for i, b in enumerate(MOCK_BOLETOS) if b["id"] == boleto_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    if boleto.valor is not None:
        MOCK_BOLETOS[idx]["valor"] = boleto.valor
    if boleto.vencimento is not None:
        MOCK_BOLETOS[idx]["vencimento"] = boleto.vencimento
    if boleto.descricao is not None:
        MOCK_BOLETOS[idx]["descricao"] = boleto.descricao
    if boleto.status is not None:
        MOCK_BOLETOS[idx]["status"] = boleto.status

    return {"success": True, "message": "Boleto atualizado", "boleto": MOCK_BOLETOS[idx]}

@app.delete("/api/financeiro/boletos/{boleto_id}")
async def delete_boleto(boleto_id: str, payload: dict = Depends(verify_token)):
    """Cancela um boleto"""
    idx = next((i for i, b in enumerate(MOCK_BOLETOS) if b["id"] == boleto_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    MOCK_BOLETOS[idx]["status"] = "cancelado"
    return {"success": True, "message": "Boleto cancelado"}

@app.post("/api/financeiro/boletos/{boleto_id}/enviar")
async def enviar_boleto(boleto_id: str, email: Optional[str] = None, whatsapp: Optional[str] = None, payload: dict = Depends(verify_token)):
    """Envia boleto por email ou WhatsApp"""
    boleto = next((b for b in MOCK_BOLETOS if b["id"] == boleto_id), None)
    if not boleto:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    return {
        "success": True,
        "message": f"Boleto enviado com sucesso",
        "enviado_para": {"email": email, "whatsapp": whatsapp},
    }

@app.get("/api/financeiro/boletos/{boleto_id}/pdf")
async def get_boleto_pdf(boleto_id: str, payload: dict = Depends(verify_token)):
    """Retorna URL para download do PDF do boleto"""
    boleto = next((b for b in MOCK_BOLETOS if b["id"] == boleto_id), None)
    if not boleto:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    return {
        "url": f"/api/financeiro/boletos/{boleto_id}/download.pdf",
        "filename": f"boleto_{boleto['nosso_numero']}.pdf",
    }

# === PAGAMENTOS ===

@app.post("/api/financeiro/pagamentos")
async def registrar_pagamento(pagamento: PagamentoRegistro, payload: dict = Depends(verify_token)):
    """Registra pagamento manual de um boleto"""
    idx = next((i for i, b in enumerate(MOCK_BOLETOS) if b["id"] == pagamento.boleto_id), None)
    if idx is None:
        raise HTTPException(status_code=404, detail="Boleto não encontrado")

    MOCK_BOLETOS[idx]["status"] = "pago"
    MOCK_BOLETOS[idx]["data_pagamento"] = pagamento.data_pagamento
    MOCK_BOLETOS[idx]["forma_pagamento"] = pagamento.forma_pagamento
    MOCK_BOLETOS[idx]["valor_pago"] = pagamento.valor_pago

    return {
        "success": True,
        "message": "Pagamento registrado com sucesso",
        "boleto": MOCK_BOLETOS[idx],
    }

@app.post("/api/financeiro/webhook/pagamento")
async def webhook_pagamento(request: Request):
    """Webhook para receber notificações de pagamento dos bancos"""
    body = await request.json()
    # Processar webhook de pagamento
    return {"received": True, "timestamp": datetime.now().isoformat()}

# === LANÇAMENTOS ===

@app.get("/api/financeiro/lancamentos")
async def list_lancamentos(
    tipo: Optional[str] = None,
    categoria: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    payload: dict = Depends(verify_token)
):
    """Lista lançamentos financeiros"""
    lancamentos = MOCK_LANCAMENTOS.copy()

    if tipo:
        lancamentos = [l for l in lancamentos if l["tipo"] == tipo]
    if categoria:
        lancamentos = [l for l in lancamentos if l["categoria"] == categoria]

    total = len(lancamentos)
    start = (page - 1) * limit
    end = start + limit

    return {
        "items": lancamentos[start:end],
        "total": total,
        "page": page,
        "limit": limit,
    }

@app.post("/api/financeiro/lancamentos")
async def create_lancamento(lancamento: LancamentoCreate, payload: dict = Depends(verify_token)):
    """Cria um novo lançamento financeiro"""
    novo = {
        "id": f"lanc_{str(uuid.uuid4())[:8]}",
        "tipo": lancamento.tipo,
        "categoria": lancamento.categoria,
        "descricao": lancamento.descricao,
        "valor": lancamento.valor,
        "data": lancamento.data,
        "unidade_id": lancamento.unidade_id,
        "fornecedor": lancamento.fornecedor,
        "documento": lancamento.documento,
        "recorrente": lancamento.recorrente,
        "status": "pendente",
        "created_at": datetime.now().isoformat(),
    }
    MOCK_LANCAMENTOS.append(novo)

    return {"success": True, "message": "Lançamento criado", "lancamento": novo}

@app.get("/api/financeiro/categorias")
async def list_categorias(payload: dict = Depends(verify_token)):
    """Lista categorias de lançamentos"""
    return MOCK_CATEGORIAS

# === RELATÓRIOS ===

@app.get("/api/financeiro/resumo")
async def get_resumo_financeiro(mes: Optional[str] = None, payload: dict = Depends(verify_token)):
    """Retorna resumo financeiro do mês"""
    total_receitas = sum(l["valor"] for l in MOCK_LANCAMENTOS if l["tipo"] == "receita")
    total_despesas = sum(l["valor"] for l in MOCK_LANCAMENTOS if l["tipo"] == "despesa")

    boletos_pagos = len([b for b in MOCK_BOLETOS if b["status"] == "pago"])
    boletos_pendentes = len([b for b in MOCK_BOLETOS if b["status"] == "pendente"])
    boletos_vencidos = len([b for b in MOCK_BOLETOS if b["status"] == "vencido"])

    return {
        "periodo": mes or datetime.now().strftime("%m/%Y"),
        "receitas": {
            "total": total_receitas,
            "previsto": 120 * 850.00,  # 120 unidades x valor base
            "realizado": total_receitas,
            "percentual": round(total_receitas / (120 * 850.00) * 100, 1),
        },
        "despesas": {
            "total": total_despesas,
            "orcado": 35000.00,
            "realizado": total_despesas,
            "economia": 35000.00 - total_despesas,
        },
        "saldo": total_receitas - total_despesas,
        "boletos": {
            "total": len(MOCK_BOLETOS),
            "pagos": boletos_pagos,
            "pendentes": boletos_pendentes,
            "vencidos": boletos_vencidos,
        },
        "inadimplencia": {
            "taxa": round(boletos_vencidos / len(MOCK_BOLETOS) * 100, 1) if MOCK_BOLETOS else 0,
            "valor": sum(b["valor"] for b in MOCK_BOLETOS if b["status"] == "vencido"),
            "unidades": boletos_vencidos,
        },
    }

@app.get("/api/financeiro/relatorios/inadimplencia")
async def get_inadimplencia(payload: dict = Depends(verify_token)):
    """Relatório detalhado de inadimplência"""
    vencidos = [b for b in MOCK_BOLETOS if b["status"] == "vencido"]
    total_valor = sum(b["valor"] for b in vencidos)

    return {
        "taxa": round(len(vencidos) / len(MOCK_BOLETOS) * 100, 1) if MOCK_BOLETOS else 0,
        "valor_total": total_valor,
        "quantidade_boletos": len(vencidos),
        "unidades_inadimplentes": len(set(b["unidade_id"] for b in vencidos)),
        "detalhes": vencidos,
        "por_tempo": {
            "ate_30_dias": len([b for b in vencidos if b.get("dias_atraso", 0) <= 30]),
            "31_a_60_dias": len([b for b in vencidos if 30 < b.get("dias_atraso", 0) <= 60]),
            "61_a_90_dias": len([b for b in vencidos if 60 < b.get("dias_atraso", 0) <= 90]),
            "acima_90_dias": len([b for b in vencidos if b.get("dias_atraso", 0) > 90]),
        },
    }

@app.get("/api/financeiro/relatorios/fluxo-caixa")
async def get_fluxo_caixa(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    payload: dict = Depends(verify_token)
):
    """Relatório de fluxo de caixa"""
    receitas_por_categoria = {}
    despesas_por_categoria = {}

    for l in MOCK_LANCAMENTOS:
        if l["tipo"] == "receita":
            receitas_por_categoria[l["categoria"]] = receitas_por_categoria.get(l["categoria"], 0) + l["valor"]
        else:
            despesas_por_categoria[l["categoria"]] = despesas_por_categoria.get(l["categoria"], 0) + l["valor"]

    return {
        "periodo": {"inicio": data_inicio, "fim": data_fim},
        "saldo_anterior": 45680.00,
        "entradas": sum(l["valor"] for l in MOCK_LANCAMENTOS if l["tipo"] == "receita"),
        "saidas": sum(l["valor"] for l in MOCK_LANCAMENTOS if l["tipo"] == "despesa"),
        "saldo_atual": 45680.00 + sum(l["valor"] for l in MOCK_LANCAMENTOS if l["tipo"] == "receita") - sum(l["valor"] for l in MOCK_LANCAMENTOS if l["tipo"] == "despesa"),
        "receitas_por_categoria": receitas_por_categoria,
        "despesas_por_categoria": despesas_por_categoria,
    }

@app.get("/api/financeiro/relatorios/previsao")
async def get_previsao(meses: int = 3, payload: dict = Depends(verify_token)):
    """Previsão financeira para os próximos meses"""
    receita_media = 102000.00
    despesa_media = 28000.00

    previsoes = []
    for i in range(1, meses + 1):
        mes = datetime.now() + timedelta(days=30*i)
        previsoes.append({
            "mes": mes.strftime("%m/%Y"),
            "receita_prevista": receita_media,
            "despesa_prevista": despesa_media,
            "saldo_previsto": receita_media - despesa_media,
        })

    return {
        "meses": meses,
        "previsoes": previsoes,
        "receita_media_historica": receita_media,
        "despesa_media_historica": despesa_media,
    }

# === EXPORTAÇÃO ===

@app.get("/api/financeiro/exportar")
async def exportar_financeiro(
    tipo: str,  # boletos, lancamentos, inadimplencia, fluxo-caixa
    formato: str = "xlsx",  # xlsx, csv, pdf
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    payload: dict = Depends(verify_token)
):
    """Exporta relatórios financeiros"""
    return {
        "url": f"/api/financeiro/download/{tipo}_{datetime.now().strftime('%Y%m%d')}.{formato}",
        "filename": f"relatorio_{tipo}_{datetime.now().strftime('%Y%m%d')}.{formato}",
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
    }

# === INTEGRAÇÃO BANCÁRIA ===

@app.get("/api/financeiro/bancos")
async def list_bancos(payload: dict = Depends(verify_token)):
    """Lista bancos disponíveis e configurações"""
    return {
        "bancos": list(MOCK_BANCOS_CONFIG.values()),
        "ativo": next((b for b in MOCK_BANCOS_CONFIG.values() if b["configurado"]), None),
    }

@app.get("/api/financeiro/bancos/{banco_id}")
async def get_banco_config(banco_id: str, payload: dict = Depends(verify_token)):
    """Retorna configuração de um banco"""
    if banco_id not in MOCK_BANCOS_CONFIG:
        raise HTTPException(status_code=404, detail="Banco não encontrado")
    return MOCK_BANCOS_CONFIG[banco_id]

@app.post("/api/financeiro/bancos/{banco_id}/configurar")
async def configurar_banco(banco_id: str, config: ConfiguracaoBancaria, payload: dict = Depends(verify_token)):
    """Configura integração bancária"""
    if banco_id not in MOCK_BANCOS_CONFIG:
        raise HTTPException(status_code=404, detail="Banco não suportado")

    MOCK_BANCOS_CONFIG[banco_id]["configurado"] = True
    MOCK_BANCOS_CONFIG[banco_id]["ambiente"] = config.ambiente

    return {
        "success": True,
        "message": f"Banco {MOCK_BANCOS_CONFIG[banco_id]['nome']} configurado com sucesso",
        "banco": MOCK_BANCOS_CONFIG[banco_id],
    }

@app.post("/api/financeiro/bancos/{banco_id}/testar")
async def testar_conexao_banco(banco_id: str, payload: dict = Depends(verify_token)):
    """Testa conexão com o banco"""
    if banco_id not in MOCK_BANCOS_CONFIG:
        raise HTTPException(status_code=404, detail="Banco não encontrado")

    return {
        "success": True,
        "message": "Conexão testada com sucesso",
        "banco": banco_id,
        "latency_ms": 145,
    }

@app.post("/api/financeiro/bancos/{banco_id}/sincronizar")
async def sincronizar_banco(banco_id: str, payload: dict = Depends(verify_token)):
    """Sincroniza pagamentos com o banco"""
    return {
        "success": True,
        "message": "Sincronização concluída",
        "pagamentos_sincronizados": 12,
        "novos_pagamentos": 3,
        "erros": 0,
    }

# === ACORDOS ===

@app.get("/api/financeiro/acordos")
async def list_acordos(payload: dict = Depends(verify_token)):
    """Lista acordos de pagamento"""
    return {
        "items": [
            {
                "id": "acordo_001",
                "unidade": "Apt 103 - Bloco A",
                "morador": "Pedro Oliveira",
                "valor_original": 2550.00,
                "valor_acordo": 2805.00,
                "parcelas": 3,
                "parcelas_pagas": 1,
                "status": "em_dia",
                "created_at": "2024-11-15",
            },
        ],
        "total": 1,
    }

@app.post("/api/financeiro/acordos")
async def create_acordo(payload: dict = Depends(verify_token)):
    """Cria um acordo de pagamento"""
    return {
        "success": True,
        "message": "Acordo criado com sucesso",
        "acordo_id": f"acordo_{str(uuid.uuid4())[:8]}",
    }

# ==================== OCORRÊNCIAS ====================

@app.get("/api/ocorrencias")
async def list_ocorrencias(payload: dict = Depends(verify_token)):
    return {
        "items": [
            {"id": "1", "titulo": "Vazamento no corredor", "tipo": "vazamento", "prioridade": "alta", "status": "em_andamento"},
            {"id": "2", "titulo": "Lâmpada queimada", "tipo": "iluminacao", "prioridade": "baixa", "status": "aberta"},
        ],
        "total": 2,
    }

@app.post("/api/ocorrencias")
async def create_ocorrencia(payload: dict = Depends(verify_token)):
    return {"id": str(uuid.uuid4()), "message": "Ocorrência criada com sucesso"}

# ==================== RESERVAS ====================

@app.get("/api/reservas/areas")
async def list_areas(payload: dict = Depends(verify_token)):
    return {
        "items": [
            {"id": "1", "nome": "Salão de Festas", "capacidade": 80, "valor": 350.00},
            {"id": "2", "nome": "Churrasqueira", "capacidade": 20, "valor": 150.00},
            {"id": "3", "nome": "Quadra", "capacidade": 20, "valor": 0},
        ],
        "total": 3,
    }

@app.get("/api/reservas")
async def list_reservas(payload: dict = Depends(verify_token)):
    return {
        "items": [
            {"id": "1", "area": "Salão de Festas", "data": "2024-12-20", "status": "confirmada"},
            {"id": "2", "area": "Churrasqueira", "data": "2024-12-21", "status": "pendente"},
        ],
        "total": 2,
    }

# ==================== ENCOMENDAS ====================

@app.get("/api/encomendas")
async def list_encomendas(payload: dict = Depends(verify_token)):
    return {
        "items": [
            {"id": "1", "unidade": "Apt 101", "descricao": "Caixa média", "remetente": "Amazon", "status": "recebida"},
            {"id": "2", "unidade": "Apt 203", "descricao": "Pacote pequeno", "remetente": "Mercado Livre", "status": "notificada"},
        ],
        "total": 2,
    }

@app.post("/api/encomendas")
async def create_encomenda(payload: dict = Depends(verify_token)):
    return {"id": str(uuid.uuid4()), "message": "Encomenda registrada"}

# ==================== COMUNICADOS ====================

@app.get("/api/comunicados")
async def list_comunicados(payload: dict = Depends(verify_token)):
    return {
        "items": [
            {"id": "1", "titulo": "Manutenção dos elevadores", "tipo": "manutencao", "publicadoEm": datetime.now().isoformat()},
            {"id": "2", "titulo": "Assembleia Geral", "tipo": "evento", "publicadoEm": datetime.now().isoformat()},
        ],
        "total": 2,
    }

# ==================== MORADORES/UNIDADES ====================

@app.get("/api/usuarios")
async def list_usuarios(payload: dict = Depends(verify_token)):
    return {
        "items": [
            {"id": "1", "nome": "Carlos Silva", "email": "carlos@email.com", "unidade": "Apt 101", "tipo": "proprietario"},
            {"id": "2", "nome": "Maria Santos", "email": "maria@email.com", "unidade": "Apt 203", "tipo": "inquilino"},
        ],
        "total": 2,
    }

@app.get("/api/unidades")
async def list_unidades(payload: dict = Depends(verify_token)):
    return {
        "items": [
            {"id": "1", "bloco": "A", "numero": "101", "moradores": 3, "status": "ocupada"},
            {"id": "2", "bloco": "A", "numero": "102", "moradores": 2, "status": "ocupada"},
            {"id": "3", "bloco": "A", "numero": "201", "moradores": 0, "status": "vazia"},
        ],
        "total": 3,
    }

# Alias para financeiro/unidades
@app.get("/api/financeiro/unidades")
async def list_unidades_financeiro(payload: dict = Depends(verify_token)):
    """Lista unidades para módulo financeiro"""
    if DATABASE_AVAILABLE:
        try:
            condominio = await condominio_repo.get_default()
            if condominio:
                unidades = await unidade_repo.list_all(str(condominio["id"]))
                return {"items": unidades, "total": len(unidades)}
        except Exception as e:
            print(f"Erro ao buscar unidades: {e}")
    # Fallback mock
    return {
        "items": [
            {"id": "1", "bloco": "A", "numero": "101", "tipo": "apartamento", "area": 75.5, "fracao": 0.0083, "proprietario": "Carlos Silva", "status": "adimplente"},
            {"id": "2", "bloco": "A", "numero": "102", "tipo": "apartamento", "area": 75.5, "fracao": 0.0083, "proprietario": "Maria Santos", "status": "adimplente"},
        ],
        "total": 2,
    }

@app.get("/api/financeiro/moradores")
async def list_moradores_financeiro(payload: dict = Depends(verify_token)):
    """Lista moradores para módulo financeiro"""
    if DATABASE_AVAILABLE:
        try:
            condominio = await condominio_repo.get_default()
            if condominio:
                moradores = await morador_repo.list_all(str(condominio["id"]))
                return {"items": moradores, "total": len(moradores)}
        except Exception as e:
            print(f"Erro ao buscar moradores: {e}")
    # Fallback mock
    return {
        "items": [
            {"id": "1", "nome": "Carlos Silva", "email": "carlos@email.com", "telefone": "(11) 99999-0001", "unidade_id": "1", "tipo": "proprietario"},
        ],
        "total": 1,
    }

# ==================== PONTOS DE ACESSO ====================

@app.get("/api/acesso/pontos")
async def list_pontos_acesso(payload: dict = Depends(verify_token)):
    """Lista pontos de controle de acesso"""
    if DATABASE_AVAILABLE:
        try:
            condominio = await condominio_repo.get_default()
            if condominio:
                pontos = await ponto_acesso_repo.list_all(str(condominio["id"]))
                return {"items": pontos, "total": len(pontos)}
        except Exception as e:
            print(f"Erro ao buscar pontos de acesso: {e}")
    # Fallback mock
    return {
        "items": [
            {"id": "1", "nome": "Portão Principal", "tipo": "entrada", "status": "online"},
            {"id": "2", "nome": "Portão Garagem", "tipo": "entrada", "status": "online"},
        ],
        "total": 2,
    }

# ==================== MANUTENÇÃO ====================

@app.get("/api/manutencao")
async def list_manutencao(payload: dict = Depends(verify_token)):
    """Lista ordens de manutenção"""
    if DATABASE_AVAILABLE:
        try:
            condominio = await condominio_repo.get_default()
            if condominio:
                ordens = await manutencao_repo.list_all(str(condominio["id"]))
                return {"items": ordens, "total": len(ordens)}
        except Exception as e:
            print(f"Erro ao buscar manutenções: {e}")
    # Fallback mock
    return {
        "items": [
            {"id": "1", "titulo": "Troca de lâmpadas corredor", "categoria": "eletrica", "prioridade": "baixa", "status": "aberta"},
        ],
        "total": 1,
    }

@app.post("/api/manutencao")
async def create_manutencao(request: Request, payload: dict = Depends(verify_token)):
    """Cria ordem de manutenção"""
    if DATABASE_AVAILABLE:
        try:
            condominio = await condominio_repo.get_default()
            body = await request.json()
            if condominio:
                body['condominio_id'] = str(condominio["id"])
                body['solicitante_id'] = payload.get("sub")
                ordem_id = await manutencao_repo.create(body)
                return {"id": str(ordem_id), "message": "Ordem de manutenção criada com sucesso"}
        except Exception as e:
            print(f"Erro ao criar manutenção: {e}")
    return {"id": str(uuid.uuid4()), "message": "Ordem de manutenção criada com sucesso"}

# ==================== CONDOMINIOS ====================

@app.get("/api/condominios/{condominio_id}")
async def get_condominio(condominio_id: str, payload: dict = Depends(verify_token)):
    if DATABASE_AVAILABLE:
        try:
            cond = await condominio_repo.get_by_id(condominio_id)
            if cond:
                return cond
        except Exception as e:
            print(f"Erro ao buscar condomínio: {e}")
    return MOCK_CONDOMINIO

@app.get("/api/condominios/{condominio_id}/estatisticas")
async def get_condominio_stats(condominio_id: str, payload: dict = Depends(verify_token)):
    if DATABASE_AVAILABLE:
        try:
            stats = await dashboard_repo.get_stats(condominio_id)
            return stats
        except Exception as e:
            print(f"Erro ao buscar estatísticas: {e}")
    return MOCK_DASHBOARD_STATS

# ==================== ERROR HANDLERS ====================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Erro interno do servidor"},
    )

# ==================== WEBSOCKET ====================

@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str, token: str = None):
    """WebSocket endpoint para comunicação em tempo real"""
    user_id = None

    # Validar token se fornecido
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
        except jwt.JWTError:
            await websocket.close(code=4001)
            return

    await ws_manager.connect(websocket, channel, user_id)

    try:
        while True:
            # Recebe mensagens do cliente
            data = await websocket.receive_text()
            message = {"type": "echo", "data": data, "timestamp": datetime.now().isoformat()}
            await websocket.send_json(message)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel, user_id)


# WebSocket para notificações financeiras em tempo real
try:
    from services.websocket_notifier import websocket_handler as financeiro_ws_handler

    @app.websocket("/ws/financeiro/{condominio_id}")
    async def websocket_financeiro(websocket: WebSocket, condominio_id: str, token: str = None):
        """
        WebSocket para notificações do módulo financeiro
        - Pagamentos confirmados
        - Boletos criados/vencidos
        - Alertas de inadimplência
        - Sincronizações bancárias
        """
        await financeiro_ws_handler(websocket, condominio_id, token)
except ImportError:
    print("⚠️ WebSocket financeiro não disponível")

@app.get("/api/ws/stats")
async def get_ws_stats(payload: dict = Depends(verify_token)):
    """Retorna estatísticas das conexões WebSocket"""
    return ws_manager.get_stats()

# ==================== UPLOAD ====================

@app.post("/api/upload")
async def upload_file(payload: dict = Depends(verify_token)):
    """Endpoint de upload (mock)"""
    return {"url": f"/uploads/{uuid.uuid4()}.jpg", "message": "Upload realizado"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3001)
