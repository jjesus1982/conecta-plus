#!/bin/bash
# ============================================
# Conecta Plus - Load Test Runner
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/results"
BASE_URL="${BASE_URL:-http://localhost:8000}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "     Conecta Plus - Load Test Suite"
echo "============================================"
echo "Base URL: ${BASE_URL}"
echo "Results: ${RESULTS_DIR}"
echo ""

# Verificar se k6 esta instalado
if ! command -v k6 &> /dev/null; then
    echo -e "${YELLOW}k6 nao encontrado. Instalando...${NC}"

    # Detectar sistema
    if [ -f /etc/debian_version ]; then
        sudo gpg -k
        sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69 || true
        echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
        sudo apt-get update
        sudo apt-get install k6 -y
    else
        echo -e "${RED}Sistema nao suportado para instalacao automatica${NC}"
        echo "Instale k6 manualmente: https://k6.io/docs/getting-started/installation/"
        exit 1
    fi
fi

# Criar diretorio de resultados
mkdir -p "${RESULTS_DIR}"

# Funcao para rodar teste
run_test() {
    local test_name=$1
    local test_file="${SCRIPT_DIR}/${test_name}.js"
    local result_file="${RESULTS_DIR}/${test_name}_${TIMESTAMP}.json"

    echo ""
    echo -e "${YELLOW}>>> Executando: ${test_name}${NC}"
    echo "----------------------------------------"

    if k6 run \
        --env BASE_URL="${BASE_URL}" \
        --out json="${result_file}" \
        "${test_file}"; then
        echo -e "${GREEN}[OK] ${test_name} concluido${NC}"
        return 0
    else
        echo -e "${RED}[FAIL] ${test_name} falhou${NC}"
        return 1
    fi
}

# Menu de opcoes
case "${1:-menu}" in
    smoke)
        run_test "smoke"
        ;;
    load)
        run_test "load"
        ;;
    stress)
        run_test "stress"
        ;;
    spike)
        run_test "spike"
        ;;
    all)
        echo "Executando todos os testes..."
        run_test "smoke" || true
        run_test "load" || true
        run_test "stress" || true
        run_test "spike" || true
        ;;
    quick)
        echo "Executando teste rapido (smoke)..."
        run_test "smoke"
        ;;
    *)
        echo "Uso: $0 {smoke|load|stress|spike|all|quick}"
        echo ""
        echo "Testes disponiveis:"
        echo "  smoke  - Teste rapido de sanidade (~1 min)"
        echo "  load   - Teste de carga normal (~10 min)"
        echo "  stress - Teste de stress (~15 min)"
        echo "  spike  - Teste de pico (~5 min)"
        echo "  all    - Todos os testes (~31 min)"
        echo "  quick  - Apenas smoke test"
        exit 0
        ;;
esac

echo ""
echo "============================================"
echo "Resultados salvos em: ${RESULTS_DIR}"
echo "============================================"
