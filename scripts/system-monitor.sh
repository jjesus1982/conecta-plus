#!/bin/bash
#
# Conecta Plus - Sistema de Monitoramento 24/7
# Monitora: Backend, Frontend, Docker, Sistema, Banco de Dados
# Auto-recuperação de falhas quando possível
#

# === CONFIGURAÇÕES ===
LOG_DIR="/var/log/conecta-plus"
LOG_FILE="$LOG_DIR/monitor.log"
ALERT_FILE="$LOG_DIR/alerts.log"
METRICS_FILE="$LOG_DIR/metrics.log"
STATUS_FILE="/tmp/conecta-plus-status.json"

# URLs e serviços
BACKEND_URL="http://localhost:3001"
FRONTEND_URL="http://localhost:3000"
BACKEND_CONTAINER="conecta-api-gateway-dev"

# Limites de alerta
CPU_THRESHOLD=80
MEMORY_THRESHOLD=85
DISK_THRESHOLD=90
RESPONSE_TIME_THRESHOLD=5000  # ms

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# === FUNÇÕES AUXILIARES ===

setup_logs() {
    mkdir -p "$LOG_DIR"
    touch "$LOG_FILE" "$ALERT_FILE" "$METRICS_FILE"
}

timestamp() {
    date '+%Y-%m-%d %H:%M:%S'
}

log() {
    echo "[$(timestamp)] $1" >> "$LOG_FILE"
    echo -e "$1"
}

log_alert() {
    local level="$1"
    local message="$2"
    echo "[$(timestamp)] [$level] $message" >> "$ALERT_FILE"

    case $level in
        "CRITICAL") echo -e "${RED}[CRITICAL]${NC} $message" ;;
        "WARNING")  echo -e "${YELLOW}[WARNING]${NC} $message" ;;
        "INFO")     echo -e "${BLUE}[INFO]${NC} $message" ;;
        "SUCCESS")  echo -e "${GREEN}[SUCCESS]${NC} $message" ;;
    esac
}

log_metric() {
    echo "[$(timestamp)] $1" >> "$METRICS_FILE"
}

# === VERIFICAÇÕES DE SAÚDE ===

check_backend() {
    local start_time=$(date +%s%3N)
    local response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$BACKEND_URL/health" 2>/dev/null)
    local end_time=$(date +%s%3N)
    local response_time=$((end_time - start_time))

    log_metric "backend_response_time=$response_time"

    if [ "$response" == "200" ] || [ "$response" == "404" ]; then
        if [ $response_time -gt $RESPONSE_TIME_THRESHOLD ]; then
            log_alert "WARNING" "Backend lento: ${response_time}ms"
            return 1
        fi
        return 0
    else
        log_alert "CRITICAL" "Backend não responde (HTTP $response)"
        return 2
    fi
}

check_frontend() {
    local start_time=$(date +%s%3N)
    local response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$FRONTEND_URL" 2>/dev/null)
    local end_time=$(date +%s%3N)
    local response_time=$((end_time - start_time))

    log_metric "frontend_response_time=$response_time"

    if [ "$response" == "200" ]; then
        if [ $response_time -gt $RESPONSE_TIME_THRESHOLD ]; then
            log_alert "WARNING" "Frontend lento: ${response_time}ms"
            return 1
        fi
        return 0
    else
        log_alert "CRITICAL" "Frontend não responde (HTTP $response)"
        return 2
    fi
}

check_docker_container() {
    local container="$1"
    local status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null)

    if [ "$status" == "running" ]; then
        # Verificar uso de recursos do container
        local stats=$(docker stats --no-stream --format "{{.CPUPerc}},{{.MemPerc}}" "$container" 2>/dev/null)
        local cpu=$(echo "$stats" | cut -d',' -f1 | tr -d '%')
        local mem=$(echo "$stats" | cut -d',' -f2 | tr -d '%')

        log_metric "container_${container}_cpu=$cpu container_${container}_mem=$mem"

        # Verificar limites
        if [ ! -z "$cpu" ] && [ "${cpu%.*}" -gt $CPU_THRESHOLD ]; then
            log_alert "WARNING" "Container $container: CPU alta (${cpu}%)"
        fi
        if [ ! -z "$mem" ] && [ "${mem%.*}" -gt $MEMORY_THRESHOLD ]; then
            log_alert "WARNING" "Container $container: Memória alta (${mem}%)"
        fi
        return 0
    else
        log_alert "CRITICAL" "Container $container não está rodando (status: $status)"
        return 2
    fi
}

check_system_resources() {
    # CPU
    local cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
    log_metric "system_cpu=$cpu_usage"

    if [ "${cpu_usage%.*}" -gt $CPU_THRESHOLD ]; then
        log_alert "WARNING" "CPU do sistema alta: ${cpu_usage}%"
    fi

    # Memória
    local mem_info=$(free | grep Mem)
    local mem_total=$(echo $mem_info | awk '{print $2}')
    local mem_used=$(echo $mem_info | awk '{print $3}')
    local mem_percent=$((mem_used * 100 / mem_total))
    log_metric "system_mem=$mem_percent"

    if [ $mem_percent -gt $MEMORY_THRESHOLD ]; then
        log_alert "WARNING" "Memória do sistema alta: ${mem_percent}%"
    fi

    # Disco
    local disk_usage=$(df -h / | tail -1 | awk '{print $5}' | tr -d '%')
    log_metric "system_disk=$disk_usage"

    if [ $disk_usage -gt $DISK_THRESHOLD ]; then
        log_alert "CRITICAL" "Disco quase cheio: ${disk_usage}%"
    fi
}

check_nextjs_errors() {
    local log_file="/tmp/nextjs-dev.log"
    if [ -f "$log_file" ]; then
        # Verificar erros recentes (últimos 30 segundos)
        local recent_errors=$(tail -50 "$log_file" 2>/dev/null | grep -i "error\|failed\|exception" | tail -5)
        if [ ! -z "$recent_errors" ]; then
            log_alert "WARNING" "Erros no Next.js detectados"
            echo "$recent_errors" >> "$ALERT_FILE"
        fi

        # Verificar Fast Refresh reloads
        local reload_count=$(tail -100 "$log_file" 2>/dev/null | grep -c "Fast Refresh had to perform a full reload")
        if [ $reload_count -gt 3 ]; then
            log_alert "WARNING" "Muitos reloads do Fast Refresh: $reload_count"
        fi
    fi
}

check_ports() {
    # Backend (usando ss que é mais confiável)
    if ! ss -tlnp 2>/dev/null | grep -q ":3001"; then
        log_alert "CRITICAL" "Porta 3001 (Backend) não está em uso"
        return 1
    fi

    # Frontend
    if ! ss -tlnp 2>/dev/null | grep -q ":3000"; then
        log_alert "CRITICAL" "Porta 3000 (Frontend) não está em uso"
        return 1
    fi

    return 0
}

# === AUTO-RECUPERAÇÃO ===

restart_backend() {
    log_alert "INFO" "Tentando reiniciar backend..."

    # Parar container existente
    docker stop "$BACKEND_CONTAINER" 2>/dev/null
    docker rm "$BACKEND_CONTAINER" 2>/dev/null

    # Iniciar novo container (porta 3001:3001 pois o app escuta na 3001)
    cd /opt/conecta-plus/services/api-gateway
    docker run -d --name "$BACKEND_CONTAINER" -p 3001:3001 api-gateway

    sleep 8  # Aguardar mais tempo para o uvicorn iniciar

    if check_backend; then
        log_alert "SUCCESS" "Backend reiniciado com sucesso"
        return 0
    else
        log_alert "CRITICAL" "Falha ao reiniciar backend"
        return 1
    fi
}

restart_frontend() {
    log_alert "INFO" "Tentando reiniciar frontend..."

    # Matar processos existentes
    pkill -9 -f "next dev" 2>/dev/null
    pkill -9 -f "next-server" 2>/dev/null
    sleep 3

    # Limpar lock files
    rm -rf /opt/conecta-plus/frontend/.next/dev/lock 2>/dev/null

    # Reiniciar usando nohup para processo independente
    cd /opt/conecta-plus/frontend
    nohup npm run dev > /tmp/nextjs-dev.log 2>&1 &
    disown

    sleep 12  # Aguardar Next.js compilar

    if check_frontend; then
        log_alert "SUCCESS" "Frontend reiniciado com sucesso"
        return 0
    else
        log_alert "CRITICAL" "Falha ao reiniciar frontend"
        return 1
    fi
}

# === STATUS JSON ===

update_status() {
    local backend_status="$1"
    local frontend_status="$2"
    local container_status="$3"

    cat > "$STATUS_FILE" << EOF
{
    "timestamp": "$(timestamp)",
    "services": {
        "backend": {
            "status": "$backend_status",
            "url": "$BACKEND_URL"
        },
        "frontend": {
            "status": "$frontend_status",
            "url": "$FRONTEND_URL"
        },
        "docker": {
            "status": "$container_status",
            "container": "$BACKEND_CONTAINER"
        }
    },
    "system": {
        "cpu": "$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')",
        "memory": "$(free -m | grep Mem | awk '{printf "%.1f%%", $3/$2*100}')",
        "disk": "$(df -h / | tail -1 | awk '{print $5}')"
    },
    "uptime": "$(uptime -p)"
}
EOF
}

# === LOOP PRINCIPAL ===

monitor_loop() {
    local check_interval=${1:-30}  # Intervalo padrão: 30 segundos
    local auto_recover=${2:-true}

    log "=== Iniciando Monitor Conecta Plus ==="
    log "Intervalo: ${check_interval}s | Auto-recuperação: $auto_recover"

    local backend_failures=0
    local frontend_failures=0
    local max_failures=3

    while true; do
        echo -e "\n${BLUE}[$(timestamp)]${NC} Verificando serviços..."

        # Status padrão
        local backend_status="healthy"
        local frontend_status="healthy"
        local container_status="healthy"

        # Verificar Backend
        if ! check_backend; then
            backend_status="unhealthy"
            ((backend_failures++))

            if [ "$auto_recover" == "true" ] && [ $backend_failures -ge $max_failures ]; then
                restart_backend
                backend_failures=0
            fi
        else
            backend_failures=0
            echo -e "${GREEN}✓${NC} Backend OK"
        fi

        # Verificar Frontend
        if ! check_frontend; then
            frontend_status="unhealthy"
            ((frontend_failures++))

            if [ "$auto_recover" == "true" ] && [ $frontend_failures -ge $max_failures ]; then
                restart_frontend
                frontend_failures=0
            fi
        else
            frontend_failures=0
            echo -e "${GREEN}✓${NC} Frontend OK"
        fi

        # Verificar Container Docker
        if ! check_docker_container "$BACKEND_CONTAINER"; then
            container_status="unhealthy"
            if [ "$auto_recover" == "true" ]; then
                restart_backend
            fi
        else
            echo -e "${GREEN}✓${NC} Container Docker OK"
        fi

        # Verificar Recursos do Sistema
        check_system_resources
        echo -e "${GREEN}✓${NC} Recursos do sistema verificados"

        # Verificar Erros do Next.js
        check_nextjs_errors

        # Verificar Portas
        check_ports

        # Atualizar status JSON
        update_status "$backend_status" "$frontend_status" "$container_status"

        # Executar aprendizado a cada 2 ciclos (1 minuto)
        if [ $((SECONDS % 60)) -lt $check_interval ]; then
            python3 /opt/conecta-plus/scripts/smart-monitor.py learn > /dev/null 2>&1 &
        fi

        # Aguardar próximo ciclo
        sleep $check_interval
    done
}

# === COMANDOS ===

show_status() {
    if [ -f "$STATUS_FILE" ]; then
        cat "$STATUS_FILE" | python3 -m json.tool 2>/dev/null || cat "$STATUS_FILE"
    else
        echo "Status não disponível. Execute o monitor primeiro."
    fi
}

show_alerts() {
    local lines=${1:-20}
    if [ -f "$ALERT_FILE" ]; then
        echo "=== Últimos $lines alertas ==="
        tail -n $lines "$ALERT_FILE"
    else
        echo "Nenhum alerta registrado."
    fi
}

show_metrics() {
    local lines=${1:-20}
    if [ -f "$METRICS_FILE" ]; then
        echo "=== Últimas $lines métricas ==="
        tail -n $lines "$METRICS_FILE"
    else
        echo "Nenhuma métrica registrada."
    fi
}

show_help() {
    echo "Conecta Plus - Sistema de Monitoramento 24/7"
    echo ""
    echo "Uso: $0 [comando] [opções]"
    echo ""
    echo "Comandos:"
    echo "  start [intervalo] [auto_recover]  Inicia o monitoramento (padrão: 30s, true)"
    echo "  status                            Mostra status atual dos serviços"
    echo "  alerts [n]                        Mostra últimos n alertas (padrão: 20)"
    echo "  metrics [n]                       Mostra últimas n métricas (padrão: 20)"
    echo "  check                             Executa verificação única"
    echo "  restart-backend                   Reinicia o backend"
    echo "  restart-frontend                  Reinicia o frontend"
    echo "  help                              Mostra esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  $0 start 60 true    # Monitor a cada 60s com auto-recuperação"
    echo "  $0 start 30 false   # Monitor a cada 30s sem auto-recuperação"
    echo "  $0 alerts 50        # Mostra últimos 50 alertas"
}

single_check() {
    setup_logs
    echo "=== Verificação única do sistema ==="
    echo ""

    echo -n "Backend: "
    if check_backend; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FALHA${NC}"
    fi

    echo -n "Frontend: "
    if check_frontend; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FALHA${NC}"
    fi

    echo -n "Container Docker: "
    if check_docker_container "$BACKEND_CONTAINER"; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FALHA${NC}"
    fi

    echo -n "Portas: "
    if check_ports; then
        echo -e "${GREEN}OK${NC}"
    else
        echo -e "${RED}FALHA${NC}"
    fi

    echo ""
    check_system_resources

    echo ""
    update_status "checked" "checked" "checked"
    echo "Status salvo em: $STATUS_FILE"
}

# === MAIN ===

setup_logs

case "${1:-help}" in
    start)
        monitor_loop "${2:-30}" "${3:-true}"
        ;;
    status)
        show_status
        ;;
    alerts)
        show_alerts "${2:-20}"
        ;;
    metrics)
        show_metrics "${2:-20}"
        ;;
    check)
        single_check
        ;;
    restart-backend)
        restart_backend
        ;;
    restart-frontend)
        restart_frontend
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        ;;
esac
