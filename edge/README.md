# Conecta Plus Edge Computing

Sistema de computação de borda para condomínios com suporte a modo offline e sincronização cloud.

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLOUD (Azure/AWS/GCP)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   API        │  │   Database   │  │   Storage    │              │
│  │   Gateway    │  │   (PgSQL)    │  │   (S3/Blob)  │              │
│  └──────┬───────┘  └──────────────┘  └──────────────┘              │
│         │                                                           │
└─────────┼───────────────────────────────────────────────────────────┘
          │ HTTPS/WSS (Sync)
          │
┌─────────▼───────────────────────────────────────────────────────────┐
│                      EDGE NODE (Condomínio)                         │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │    Edge      │  │    Sync      │  │    Device    │              │
│  │   Gateway    │──│   Agent      │  │   Manager    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│         │                                   │                       │
│  ┌──────▼──────┐  ┌──────────────┐  ┌──────▼──────┐                │
│  │   Redis     │  │   Frigate    │  │    MQTT     │                │
│  │   Cache     │  │    NVR       │  │   Broker    │                │
│  └─────────────┘  └──────────────┘  └─────────────┘                │
│                          │                  │                       │
│  ┌───────────────────────▼──────────────────▼──────────────────┐   │
│  │                    Edge AI Worker                            │   │
│  │  ┌─────────┐  ┌─────────────┐  ┌─────────────────┐          │   │
│  │  │  YOLO   │  │    Face     │  │      LPR        │          │   │
│  │  │  v8     │  │  Recognition │  │ (Plate Reader)  │          │   │
│  │  └─────────┘  └─────────────┘  └─────────────────┘          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DISPOSITIVOS LOCAIS                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│  │ Câmeras │  │ Controle│  │ Alarme  │  │ Portões │  │Interfone│  │
│  │  ONVIF  │  │ Acesso  │  │         │  │         │  │         │  │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Hardware Suportado

### Recomendado
- **Intel NUC** (i5/i7) - Melhor desempenho
- **Raspberry Pi 5** (8GB) - Melhor custo-benefício
- **Mini PC** (AMD Ryzen) - Bom equilíbrio

### Requisitos Mínimos
- CPU: 4 cores ARM64 ou x86_64
- RAM: 4GB (8GB recomendado)
- Disco: 64GB SSD (256GB+ para gravações)
- Rede: Gigabit Ethernet

### Aceleradores IA (Opcional)
- **Google Coral TPU** (USB ou M.2) - Recomendado para detecção
- **Intel NCS2** - Alternativa ao Coral
- **GPU NVIDIA** (Jetson Nano/Xavier) - Máximo desempenho

## Instalação

### Script Automático (Recomendado)

```bash
curl -fsSL https://raw.githubusercontent.com/conectaplus/edge/main/scripts/install.sh | sudo bash
```

### Manual com Docker Compose

```bash
# Clonar repositório
git clone https://github.com/conectaplus/edge.git
cd edge/docker

# Configurar
cp .env.example .env
nano .env

# Iniciar
docker-compose up -d
```

### Kubernetes (k3s)

```bash
# Instalar k3s
curl -sfL https://get.k3s.io | sh -

# Aplicar manifests
kubectl apply -f kubernetes/edge-deployment.yaml
```

## Componentes

### Edge Gateway
API local que funciona mesmo sem internet:
- Registro de acessos e eventos
- Cache de dados com Redis
- Proxy para dispositivos locais
- Endpoint para apps mobile

### Sync Agent
Sincronização bidirecional com cloud:
- Queue de eventos offline
- Compressão e criptografia
- Retry automático
- Resolução de conflitos

### Edge AI Worker
Inferência local de IA:
- Detecção de objetos (YOLO v8)
- Reconhecimento facial
- Leitura de placas (LPR)
- Classificação de comportamentos

### Frigate NVR
Sistema de gravação profissional:
- Gravação contínua e por eventos
- Detecção de objetos em tempo real
- Replay instantâneo
- Integração com IA

### Device Manager
Gerenciamento de dispositivos:
- Discovery automático (ONVIF, mDNS)
- Configuração remota
- Health monitoring
- Firmware updates

## Configuração

### Variáveis de Ambiente

```env
# Identificação
NODE_ID=edge-001
NODE_NAME=Condomínio Principal

# Cloud
CLOUD_API_URL=https://api.conectaplus.com.br
CLOUD_API_KEY=seu-api-key

# Recursos
USE_GPU=false
AI_INFERENCE_ENABLED=true

# Sync
SYNC_INTERVAL=30
OFFLINE_MODE_ENABLED=true
```

### Câmeras (Frigate)

```yaml
cameras:
  entrada_principal:
    ffmpeg:
      inputs:
        - path: rtsp://user:pass@192.168.1.100:554/stream1
          roles:
            - detect
            - record
    detect:
      width: 1920
      height: 1080
      fps: 5
    record:
      enabled: true
    zones:
      entrada:
        coordinates: 0,0,0.5,0,0.5,1,0,1
```

## Modo Offline

O sistema opera normalmente sem conexão internet:

1. **Acessos** - Validação local via cache
2. **Gravações** - Armazenamento local
3. **Detecções** - Inferência local
4. **Alertas** - Notificação via MQTT local

Quando a conexão é restabelecida:
- Eventos são sincronizados automaticamente
- Gravações críticas são enviadas ao cloud
- Configurações são atualizadas

## Monitoramento

### Dashboards Grafana
- Status do node
- Uso de recursos
- Eventos de detecção
- Latência cloud

### Métricas Prometheus
- `edge_sync_pending` - Eventos pendentes
- `edge_cloud_latency_ms` - Latência cloud
- `edge_ai_inference_time` - Tempo de inferência
- `edge_cameras_online` - Câmeras online

## Segurança

- TLS/mTLS para comunicação cloud
- Criptografia AES-256 para dados locais
- Autenticação JWT
- Certificados automáticos (Let's Encrypt)
- Firewall configurado automaticamente

## Troubleshooting

### Verificar status
```bash
docker-compose ps
docker-compose logs -f edge-gateway
```

### Testar conectividade cloud
```bash
curl -v https://api.conectaplus.com.br/health
```

### Verificar sincronização
```bash
curl http://localhost:8080/sync/queue
```

### Reiniciar serviços
```bash
docker-compose restart
```

## Licença

Proprietário - Conecta Plus
