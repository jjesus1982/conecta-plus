#!/bin/bash
#
# Conecta Plus - Medicao de Cold Start
# =====================================
# Mede o tempo de resposta das primeiras requisicoes apos startup.
#
# Uso:
#   ./measure-coldstart.sh [--wait SECONDS] [--requests COUNT]
#
# Opcoes:
#   --wait SECONDS    Tempo para aguardar apos restart (default: 5)
#   --requests COUNT  Numero de requisicoes de teste (default: 10)
#

set -e

# Cores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuracoes
BACKEND_URL=${BACKEND_URL:-"http://localhost:8000"}
WAIT_SECONDS=5
REQUEST_COUNT=10
RESULTS_FILE="/opt/conecta-plus/logs/coldstart_results.log"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_data() { echo -e "${BLUE}[DATA]${NC} $1"; }

# Parse argumentos
while [[ $# -gt 0 ]]; do
    case $1 in
        --wait)
            WAIT_SECONDS="$2"
            shift 2
            ;;
        --requests)
            REQUEST_COUNT="$2"
            shift 2
            ;;
        --url)
            BACKEND_URL="$2"
            shift 2
            ;;
        --help)
            echo "Uso: $0 [--wait SECONDS] [--requests COUNT] [--url URL]"
            exit 0
            ;;
        *)
            log_warn "Argumento desconhecido: $1"
            shift
            ;;
    esac
done

# Verificar curl
if ! command -v curl &> /dev/null; then
    log_warn "curl nao encontrado. Instalando..."
    apt-get update && apt-get install -y curl
fi

# Funcao para medir tempo de resposta
measure_request() {
    local endpoint=$1
    local result

    result=$(curl -sf -o /dev/null -w "%{time_total}" "${BACKEND_URL}${endpoint}" 2>/dev/null || echo "ERROR")

    if [ "$result" = "ERROR" ]; then
        echo "-1"
    else
        # Converter para milissegundos
        echo "scale=2; $result * 1000" | bc
    fi
}

# Funcao para calcular media
calculate_average() {
    local sum=0
    local count=0

    for val in "$@"; do
        if [ "$val" != "-1" ]; then
            sum=$(echo "scale=2; $sum + $val" | bc)
            count=$((count + 1))
        fi
    done

    if [ $count -gt 0 ]; then
        echo "scale=2; $sum / $count" | bc
    else
        echo "0"
    fi
}

log_info "=========================================="
log_info "Conecta Plus - Medicao de Cold Start"
log_info "=========================================="
log_info "Backend URL: $BACKEND_URL"
log_info "Requisicoes de teste: $REQUEST_COUNT"
log_info "=========================================="

# Verificar se backend esta rodando
log_info "Verificando se backend esta disponivel..."
if ! curl -sf "${BACKEND_URL}/health" > /dev/null 2>&1; then
    log_warn "Backend nao disponivel. Aguardando ${WAIT_SECONDS}s..."
    sleep $WAIT_SECONDS

    if ! curl -sf "${BACKEND_URL}/health" > /dev/null 2>&1; then
        log_warn "Backend ainda nao disponivel. Tentando mais ${WAIT_SECONDS}s..."
        sleep $WAIT_SECONDS
    fi
fi

# Obter status do warmup (se disponivel)
log_info "Verificando status do warmup..."
warmup_status=$(curl -sf "${BACKEND_URL}/health/warmup" 2>/dev/null || echo '{"status":"unavailable"}')
echo "Warmup status: $warmup_status" | head -c 200
echo ""

# Medir requisicoes
log_info ""
log_info "Iniciando medicoes..."
log_info ""

declare -a health_times
declare -a api_times
declare -a db_times

# Endpoints para testar
endpoints=(
    "/health"
    "/api/v1/"
    "/health/ready"
)

# Testar cada endpoint
for endpoint in "${endpoints[@]}"; do
    log_data "Testando $endpoint..."
    times=()

    for i in $(seq 1 $REQUEST_COUNT); do
        time_ms=$(measure_request "$endpoint")
        times+=("$time_ms")

        if [ "$time_ms" = "-1" ]; then
            printf "  [%2d] ERRO\n" $i
        else
            printf "  [%2d] %.2f ms\n" $i $time_ms
        fi
    done

    # Calcular estatisticas
    avg=$(calculate_average "${times[@]}")

    # Min e Max
    min=999999
    max=0
    for t in "${times[@]}"; do
        if [ "$t" != "-1" ]; then
            if (( $(echo "$t < $min" | bc -l) )); then
                min=$t
            fi
            if (( $(echo "$t > $max" | bc -l) )); then
                max=$t
            fi
        fi
    done

    log_data "  Estatisticas $endpoint:"
    log_data "    - Media: ${avg}ms"
    log_data "    - Min:   ${min}ms"
    log_data "    - Max:   ${max}ms"
    log_data "    - Primeira: ${times[0]}ms"
    echo ""

    # Salvar para primeira req (cold start)
    if [ "$endpoint" = "/health" ]; then
        health_times=("${times[@]}")
    fi
done

# Resumo final
log_info "=========================================="
log_info "RESUMO"
log_info "=========================================="

first_health=${health_times[0]}
avg_health=$(calculate_average "${health_times[@]}")

if (( $(echo "$first_health < 100" | bc -l) )); then
    log_info "Cold start: ${GREEN}OTIMO${NC} (${first_health}ms)"
elif (( $(echo "$first_health < 500" | bc -l) )); then
    log_info "Cold start: ${YELLOW}BOM${NC} (${first_health}ms)"
elif (( $(echo "$first_health < 1000" | bc -l) )); then
    log_warn "Cold start: ${YELLOW}ACEITAVEL${NC} (${first_health}ms)"
else
    log_warn "Cold start: ${RED}LENTO${NC} (${first_health}ms) - Warmup pode nao estar funcionando"
fi

log_info "Media apos warmup: ${avg_health}ms"
log_info ""

# Salvar resultados
timestamp=$(date '+%Y-%m-%d %H:%M:%S')
{
    echo "=========================================="
    echo "Medicao: $timestamp"
    echo "=========================================="
    echo "First request (cold): ${first_health}ms"
    echo "Average (warm): ${avg_health}ms"
    echo "Warmup status: $warmup_status"
    echo ""
} >> "$RESULTS_FILE"

log_info "Resultados salvos em: $RESULTS_FILE"
