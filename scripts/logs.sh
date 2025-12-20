#!/bin/bash
# ============================================
# Conecta Plus - Script de Visualização de Logs
# Visualiza logs dos serviços de forma unificada
# ============================================

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # Sem cor

# Configurações
LOG_DIR="/opt/conecta-plus/logs"
LINES=${2:-100}

# Função de ajuda
show_help() {
    echo -e "${BLUE}"
    echo "============================================"
    echo "   Conecta Plus - Visualizador de Logs"
    echo "============================================"
    echo -e "${NC}"
    echo ""
    echo "Uso: $0 [serviço] [linhas]"
    echo ""
    echo -e "${YELLOW}Serviços disponíveis:${NC}"
    echo "  all        - Todos os logs (docker-compose)"
    echo "  postgres   - Logs do PostgreSQL"
    echo "  redis      - Logs do Redis"
    echo "  nginx      - Logs do Nginx"
    echo "  backend    - Logs do Backend API"
    echo "  frontend   - Logs do Frontend"
    echo "  guardian   - Logs do Guardian (câmeras)"
    echo "  setup      - Logs do setup inicial"
    echo "  backup     - Logs de backup"
    echo "  deploy     - Logs de deploy"
    echo ""
    echo -e "${YELLOW}Exemplos:${NC}"
    echo "  $0 backend      # Últimas 100 linhas do backend"
    echo "  $0 postgres 50  # Últimas 50 linhas do postgres"
    echo "  $0 all          # Todos os logs em tempo real"
    echo ""
    echo -e "${YELLOW}Opções especiais:${NC}"
    echo "  -f, --follow    Seguir logs em tempo real"
    echo "  -h, --help      Mostrar esta ajuda"
    echo ""
}

# Função para mostrar logs do Docker
docker_logs() {
    local service=$1
    local container="conecta-$service"

    if docker ps -a | grep -q "$container"; then
        echo -e "${CYAN}=== Logs: $container ===${NC}"
        if [ "$FOLLOW" = true ]; then
            docker logs -f "$container"
        else
            docker logs --tail "$LINES" "$container"
        fi
    else
        echo -e "${RED}Container $container não encontrado${NC}"
        echo -e "Containers disponíveis:"
        docker ps -a --format "  - {{.Names}}" | grep conecta || echo "  Nenhum container Conecta Plus encontrado"
    fi
}

# Função para mostrar logs de arquivo
file_logs() {
    local file=$1
    local name=$2

    if [ -f "$file" ]; then
        echo -e "${CYAN}=== Logs: $name ===${NC}"
        if [ "$FOLLOW" = true ]; then
            tail -f "$file"
        else
            tail -n "$LINES" "$file"
        fi
    else
        echo -e "${YELLOW}Arquivo de log não encontrado: $file${NC}"
    fi
}

# Processar argumentos
FOLLOW=false
SERVICE=""

for arg in "$@"; do
    case $arg in
        -f|--follow)
            FOLLOW=true
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            if [ -z "$SERVICE" ]; then
                SERVICE=$arg
            else
                LINES=$arg
            fi
            ;;
    esac
done

# Se nenhum serviço especificado, mostrar ajuda
if [ -z "$SERVICE" ]; then
    show_help
    exit 0
fi

# Banner
echo -e "${BLUE}"
echo "============================================"
echo "   Conecta Plus - Visualizador de Logs"
echo "============================================"
echo -e "${NC}"
echo -e "Serviço: ${GREEN}$SERVICE${NC}"
echo -e "Linhas: $LINES"
[ "$FOLLOW" = true ] && echo -e "Modo: ${YELLOW}Seguindo em tempo real (Ctrl+C para sair)${NC}"
echo ""

# Selecionar serviço
case $SERVICE in
    all)
        echo -e "${CYAN}=== Todos os Logs (Docker Compose) ===${NC}"
        cd /opt/conecta-plus
        if [ "$FOLLOW" = true ]; then
            docker-compose logs -f
        else
            docker-compose logs --tail "$LINES"
        fi
        ;;
    postgres|postgresql|pg|db)
        docker_logs "postgres"
        ;;
    redis|cache)
        docker_logs "redis"
        ;;
    nginx|proxy|web)
        docker_logs "nginx"
        # Também mostrar logs de arquivo se existirem
        echo ""
        [ -f "$LOG_DIR/nginx/access.log" ] && file_logs "$LOG_DIR/nginx/access.log" "Nginx Access"
        [ -f "$LOG_DIR/nginx/error.log" ] && file_logs "$LOG_DIR/nginx/error.log" "Nginx Error"
        ;;
    backend|api)
        docker_logs "backend"
        ;;
    frontend|front|ui)
        docker_logs "frontend"
        ;;
    guardian|cameras|ia)
        docker_logs "guardian"
        ;;
    setup|install)
        file_logs "/var/log/conecta-setup.log" "Setup Inicial"
        ;;
    backup)
        file_logs "/var/log/conecta-backup.log" "Backup"
        ;;
    deploy)
        file_logs "/var/log/conecta-deploy.log" "Deploy"
        ;;
    *)
        echo -e "${RED}Serviço desconhecido: $SERVICE${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Fim dos logs.${NC}"
