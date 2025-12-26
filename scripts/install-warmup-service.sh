#!/bin/bash
#
# Conecta Plus - Instalar Warmup Service
# ========================================
# Instala e configura o servico de warmup no systemd.
#
# Uso:
#   sudo ./install-warmup-service.sh [--enable-timer]
#
# Opcoes:
#   --enable-timer    Habilita execucao periodica (a cada 4h)
#

set -e

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Diretorios
BASE_DIR="/opt/conecta-plus"
CONFIG_DIR="${BASE_DIR}/config/systemd"
SYSTEMD_DIR="/etc/systemd/system"

# Verificar root
if [ "$EUID" -ne 0 ]; then
    log_error "Execute como root: sudo $0"
    exit 1
fi

# Verificar arquivos de configuracao
if [ ! -f "${CONFIG_DIR}/conecta-warmup.service" ]; then
    log_error "Arquivo conecta-warmup.service nao encontrado em ${CONFIG_DIR}"
    exit 1
fi

if [ ! -f "${CONFIG_DIR}/conecta-warmup.timer" ]; then
    log_error "Arquivo conecta-warmup.timer nao encontrado em ${CONFIG_DIR}"
    exit 1
fi

# Parse argumentos
ENABLE_TIMER=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --enable-timer)
            ENABLE_TIMER=true
            shift
            ;;
        --help)
            echo "Uso: $0 [--enable-timer]"
            echo ""
            echo "Opcoes:"
            echo "  --enable-timer    Habilita execucao periodica (a cada 4h)"
            exit 0
            ;;
        *)
            log_warn "Argumento desconhecido: $1"
            shift
            ;;
    esac
done

log_info "=========================================="
log_info "Instalando Conecta Plus Warmup Service"
log_info "=========================================="

# Criar diretorio de logs
mkdir -p "${BASE_DIR}/logs"
chmod 755 "${BASE_DIR}/logs"

# Parar servicos existentes (se houver)
if systemctl is-active --quiet conecta-warmup.service 2>/dev/null; then
    log_info "Parando servico existente..."
    systemctl stop conecta-warmup.service
fi

if systemctl is-active --quiet conecta-warmup.timer 2>/dev/null; then
    log_info "Parando timer existente..."
    systemctl stop conecta-warmup.timer
fi

# Copiar arquivos
log_info "Copiando arquivos de servico..."
cp "${CONFIG_DIR}/conecta-warmup.service" "${SYSTEMD_DIR}/"
cp "${CONFIG_DIR}/conecta-warmup.timer" "${SYSTEMD_DIR}/"
chmod 644 "${SYSTEMD_DIR}/conecta-warmup.service"
chmod 644 "${SYSTEMD_DIR}/conecta-warmup.timer"

# Recarregar systemd
log_info "Recarregando systemd..."
systemctl daemon-reload

# Habilitar service
log_info "Habilitando servico..."
systemctl enable conecta-warmup.service

# Timer (opcional)
if [ "$ENABLE_TIMER" = true ]; then
    log_info "Habilitando timer para execucao periodica..."
    systemctl enable conecta-warmup.timer
    systemctl start conecta-warmup.timer
    log_info "Timer habilitado - warmup sera executado a cada 4 horas"
else
    log_info "Timer nao habilitado - warmup sera executado apenas no boot"
    log_info "Para habilitar execucao periodica: systemctl enable --now conecta-warmup.timer"
fi

# Verificar status
log_info "=========================================="
log_info "Instalacao concluida!"
log_info "=========================================="
echo ""
echo "Comandos uteis:"
echo "  - Executar warmup agora:     systemctl start conecta-warmup.service"
echo "  - Ver status do servico:     systemctl status conecta-warmup.service"
echo "  - Ver logs:                  journalctl -u conecta-warmup.service"
echo "  - Habilitar timer:           systemctl enable --now conecta-warmup.timer"
echo "  - Ver status do timer:       systemctl list-timers conecta-warmup.timer"
echo ""

exit 0
