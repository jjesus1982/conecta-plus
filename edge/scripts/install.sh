#!/bin/bash
# Conecta Plus Edge Node - Script de Instalação
# Suporta: Ubuntu 20.04+, Debian 11+, Raspberry Pi OS
# Hardware: x86_64, ARM64 (Raspberry Pi 4/5)

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Conecta Plus Edge Node - Instalação                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Este script deve ser executado como root${NC}"
   exit 1
fi

# Variáveis
INSTALL_DIR="/opt/conecta-plus-edge"
DATA_DIR="/var/lib/conecta-plus"
CONFIG_DIR="/etc/conecta-plus"
LOG_DIR="/var/log/conecta-plus"

# Detectar arquitetura
ARCH=$(uname -m)
echo -e "${GREEN}Arquitetura detectada: ${ARCH}${NC}"

# Detectar SO
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VERSION=$VERSION_ID
    echo -e "${GREEN}Sistema Operacional: ${OS} ${VERSION}${NC}"
fi

# Verificar requisitos mínimos
echo -e "\n${YELLOW}Verificando requisitos...${NC}"

# RAM mínima: 4GB
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -lt 3 ]; then
    echo -e "${YELLOW}Aviso: Recomendado pelo menos 4GB de RAM (detectado: ${TOTAL_RAM}GB)${NC}"
fi

# Disco mínimo: 64GB
TOTAL_DISK=$(df -BG / | awk 'NR==2 {print $2}' | tr -d 'G')
if [ "$TOTAL_DISK" -lt 50 ]; then
    echo -e "${YELLOW}Aviso: Recomendado pelo menos 64GB de disco (detectado: ${TOTAL_DISK}GB)${NC}"
fi

echo -e "${GREEN}Requisitos verificados!${NC}"

# Atualizar sistema
echo -e "\n${YELLOW}Atualizando sistema...${NC}"
apt-get update
apt-get upgrade -y

# Instalar dependências
echo -e "\n${YELLOW}Instalando dependências...${NC}"
apt-get install -y \
    curl \
    wget \
    git \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release \
    python3 \
    python3-pip \
    python3-venv \
    jq \
    htop \
    net-tools \
    nmap \
    avahi-daemon \
    avahi-utils

# Instalar Docker
echo -e "\n${YELLOW}Instalando Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh

    # Adicionar usuário atual ao grupo docker
    usermod -aG docker $SUDO_USER 2>/dev/null || true

    systemctl enable docker
    systemctl start docker
fi

# Instalar Docker Compose
echo -e "\n${YELLOW}Instalando Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | jq -r .tag_name)
    curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Criar diretórios
echo -e "\n${YELLOW}Criando diretórios...${NC}"
mkdir -p $INSTALL_DIR
mkdir -p $DATA_DIR/{recordings,snapshots,models}
mkdir -p $CONFIG_DIR/{frigate,mosquitto,prometheus,grafana}
mkdir -p $LOG_DIR

# Copiar arquivos de configuração
echo -e "\n${YELLOW}Configurando serviços...${NC}"

# Configuração do Mosquitto
cat > $CONFIG_DIR/mosquitto/mosquitto.conf << 'EOF'
listener 1883
listener 9001
protocol websockets
allow_anonymous true
persistence true
persistence_location /mosquitto/data/
log_dest stdout
EOF

# Configuração do Frigate
cat > $CONFIG_DIR/frigate/config.yml << 'EOF'
mqtt:
  enabled: true
  host: mqtt
  port: 1883
  topic_prefix: frigate

detectors:
  cpu1:
    type: cpu
    num_threads: 4

database:
  path: /config/frigate.db

record:
  enabled: true
  retain:
    days: 7
    mode: all
  events:
    retain:
      default: 30
      mode: motion

snapshots:
  enabled: true
  retain:
    default: 30

objects:
  track:
    - person
    - car
    - motorcycle
    - bicycle
    - dog
    - cat

cameras: {}
EOF

# Configuração do Prometheus
cat > $CONFIG_DIR/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'edge-gateway'
    static_configs:
      - targets: ['edge-gateway:8080']

  - job_name: 'frigate'
    static_configs:
      - targets: ['frigate:5000']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
EOF

# Criar arquivo de ambiente
echo -e "\n${YELLOW}Configurando variáveis de ambiente...${NC}"

# Gerar IDs únicos
NODE_ID="edge-$(hostname | tr '[:upper:]' '[:lower:]' | tr -d ' ')-$(date +%s | tail -c 5)"
ENCRYPTION_KEY=$(openssl rand -hex 32)

cat > $CONFIG_DIR/.env << EOF
# Conecta Plus Edge Node Configuration
# Gerado em: $(date)

# Identificação do Node
NODE_ID=$NODE_ID
NODE_NAME="$(hostname)"

# Cloud API
CLOUD_API_URL=https://api.conectaplus.com.br
CLOUD_API_KEY=

# Segurança
ENCRYPTION_KEY=$ENCRYPTION_KEY
FRIGATE_RTSP_PASSWORD=$(openssl rand -hex 8)
GRAFANA_PASSWORD=$(openssl rand -hex 8)

# GPU (descomente se disponível)
# USE_GPU=true
EOF

chmod 600 $CONFIG_DIR/.env

# Baixar docker-compose
echo -e "\n${YELLOW}Baixando configuração Docker Compose...${NC}"
# Em produção, baixar do repositório
# curl -o $INSTALL_DIR/docker-compose.yaml https://raw.githubusercontent.com/conectaplus/edge/main/docker/docker-compose.yaml

# Criar link simbólico para config
ln -sf $CONFIG_DIR/.env $INSTALL_DIR/.env
ln -sf $CONFIG_DIR $INSTALL_DIR/config

# Criar serviço systemd
echo -e "\n${YELLOW}Criando serviço systemd...${NC}"
cat > /etc/systemd/system/conecta-edge.service << EOF
[Unit]
Description=Conecta Plus Edge Node
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable conecta-edge

# Configurar firewall
echo -e "\n${YELLOW}Configurando firewall...${NC}"
if command -v ufw &> /dev/null; then
    ufw allow 80/tcp    # HTTP
    ufw allow 443/tcp   # HTTPS
    ufw allow 1883/tcp  # MQTT
    ufw allow 5000/tcp  # Frigate
    ufw allow 8554/tcp  # RTSP
    ufw allow 3000/tcp  # Grafana
fi

# Otimizações do sistema
echo -e "\n${YELLOW}Aplicando otimizações do sistema...${NC}"

# Aumentar limites de arquivos abertos
cat >> /etc/security/limits.conf << EOF
* soft nofile 65536
* hard nofile 65536
EOF

# Otimizar network
cat >> /etc/sysctl.conf << EOF
# Conecta Plus Edge Optimizations
net.core.somaxconn = 65535
net.ipv4.tcp_max_syn_backlog = 65535
net.core.netdev_max_backlog = 65535
vm.swappiness = 10
EOF

sysctl -p

# Finalização
echo -e "\n${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                   Instalação Concluída!                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${YELLOW}Próximos passos:${NC}"
echo "1. Configure o arquivo: $CONFIG_DIR/.env"
echo "   - Adicione CLOUD_API_KEY"
echo "   - Configure câmeras no $CONFIG_DIR/frigate/config.yml"
echo ""
echo "2. Inicie os serviços:"
echo "   sudo systemctl start conecta-edge"
echo ""
echo "3. Acesse:"
echo "   - Edge Gateway: http://$(hostname -I | awk '{print $1}'):80"
echo "   - Frigate NVR:  http://$(hostname -I | awk '{print $1}'):5000"
echo "   - Grafana:      http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo -e "${GREEN}Node ID: $NODE_ID${NC}"
echo ""
echo -e "${BLUE}Documentação: https://docs.conectaplus.com.br/edge${NC}"
