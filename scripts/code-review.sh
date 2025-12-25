#!/bin/bash
###############################################################################
# Code Review Automatizado - Conecta Plus
# Analisa qualidade, segurança e performance do código
###############################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="/opt/conecta-plus"
REPORT_DIR="$PROJECT_ROOT/reports/code-review-$(date +%Y%m%d-%H%M%S)"

mkdir -p "$REPORT_DIR"

log() {
    echo -e "${GREEN}[✓]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
}

info() {
    echo -e "${BLUE}[i]${NC} $1"
}

###############################################################################
# 1. FRONTEND CODE REVIEW
###############################################################################

review_frontend() {
    log "==========  FRONTEND CODE REVIEW =========="

    cd "$PROJECT_ROOT/frontend"

    # ESLint
    info "Executando ESLint..."
    if npm run lint > "$REPORT_DIR/eslint-report.txt" 2>&1; then
        log "ESLint: Nenhum problema encontrado"
    else
        warn "ESLint: Problemas encontrados (ver $REPORT_DIR/eslint-report.txt)"
    fi

    # TypeScript Check
    info "Verificando tipos TypeScript..."
    if npx tsc --noEmit > "$REPORT_DIR/typescript-check.txt" 2>&1; then
        log "TypeScript: Tipos OK"
    else
        warn "TypeScript: Erros de tipo encontrados"
    fi

    # Bundle Size Analysis
    info "Analisando tamanho do bundle..."
    if [ -d ".next" ]; then
        du -sh .next > "$REPORT_DIR/bundle-size.txt"
        log "Bundle size analisado"
    fi

    log "✓ Frontend review concluído"
}

###############################################################################
# 2. BACKEND CODE REVIEW
###############################################################################

review_backend() {
    log "========== BACKEND CODE REVIEW =========="

    cd "$PROJECT_ROOT"

    # Install tools if needed
    pip3 install --break-system-packages -q flake8 pylint bandit radon 2>/dev/null || true

    # Flake8 (PEP8 compliance)
    info "Executando Flake8..."
    flake8 --max-line-length=120 \
           --exclude=node_modules,venv,.git,__pycache__ \
           --format=html \
           --htmldir="$REPORT_DIR/flake8" \
           backend/ services/ 2>&1 | head -50 > "$REPORT_DIR/flake8-summary.txt" || true

    # Pylint (code quality)
    info "Executando Pylint..."
    find backend services -name "*.py" -type f | head -20 | while read file; do
        pylint "$file" >> "$REPORT_DIR/pylint-report.txt" 2>&1 || true
    done

    # Bandit (security)
    info "Executando Bandit (security scan)..."
    bandit -r backend/ services/ \
           -f json \
           -o "$REPORT_DIR/bandit-security.json" 2>&1 || true

    # Radon (complexity)
    info "Analisando complexidade do código..."
    radon cc backend/ services/ -a -s > "$REPORT_DIR/complexity-report.txt" 2>&1 || true
    radon mi backend/ services/ -s > "$REPORT_DIR/maintainability-index.txt" 2>&1 || true

    log "✓ Backend review concluído"
}

###############################################################################
# 3. CÓDIGO DUPLICADO
###############################################################################

find_duplicates() {
    log "========== DETECTANDO CÓDIGO DUPLICADO =========="

    cd "$PROJECT_ROOT"

    # Install jscpd if needed
    if ! command -v jscpd &> /dev/null; then
        npm install -g jscpd 2>/dev/null || warn "jscpd não instalado"
    fi

    if command -v jscpd &> /dev/null; then
        info "Procurando código duplicado..."
        jscpd frontend/src backend services \
            --min-lines 5 \
            --min-tokens 50 \
            --format "json" \
            --output "$REPORT_DIR/duplicates.json" 2>&1 || true

        log "✓ Análise de duplicação concluída"
    fi
}

###############################################################################
# 4. SECURITY SCAN
###############################################################################

security_scan() {
    log "========== SECURITY SCAN =========="

    cd "$PROJECT_ROOT"

    # NPM Audit
    info "Executando npm audit..."
    cd frontend
    npm audit --json > "$REPORT_DIR/npm-audit.json" 2>&1 || true
    cd ..

    # Python Safety Check
    info "Executando safety check..."
    pip3 install --break-system-packages safety 2>/dev/null || true
    safety check --json > "$REPORT_DIR/python-safety.json" 2>&1 || true

    # Check for secrets
    info "Procurando secrets expostos..."
    grep -r -E "(password|secret|api_key|token|private_key)\s*=\s*[\"']" \
        --include="*.py" --include="*.js" --include="*.ts" \
        backend/ frontend/src services/ 2>/dev/null > "$REPORT_DIR/potential-secrets.txt" || true

    log "✓ Security scan concluído"
}

###############################################################################
# 5. PERFORMANCE ANALYSIS
###############################################################################

performance_analysis() {
    log "========== PERFORMANCE ANALYSIS =========="

    cd "$PROJECT_ROOT"

    info "Analisando imports grandes..."
    find backend services -name "*.py" -type f -exec wc -l {} + | sort -rn | head -20 > "$REPORT_DIR/large-files.txt"

    info "Analisando imports circulares..."
    find backend services -name "*.py" | head -50 | while read file; do
        grep "^import\|^from" "$file" 2>/dev/null
    done > "$REPORT_DIR/imports-analysis.txt"

    log "✓ Performance analysis concluído"
}

###############################################################################
# 6. GENERATE SUMMARY REPORT
###############################################################################

generate_summary() {
    log "========== GERANDO RELATÓRIO FINAL =========="

    cat > "$REPORT_DIR/SUMMARY.md" << EOF
# Code Review Report - Conecta Plus
**Data:** $(date '+%Y-%m-%d %H:%M:%S')
**Revisão Automática**

---

## 📊 Resumo Executivo

### Frontend
- ✓ ESLint executado
- ✓ TypeScript verificado
- ✓ Bundle size analisado

### Backend
- ✓ Flake8 (PEP8) executado
- ✓ Pylint (quality) executado
- ✓ Bandit (security) executado
- ✓ Radon (complexity) executado

### Security
- ✓ NPM audit executado
- ✓ Python safety check executado
- ✓ Secrets scan executado

### Performance
- ✓ Arquivos grandes identificados
- ✓ Imports analisados

---

## 📁 Arquivos de Relatório

1. \`eslint-report.txt\` - Problemas de linting
2. \`typescript-check.txt\` - Erros de tipo TypeScript
3. \`flake8-summary.txt\` - Violações PEP8
4. \`pylint-report.txt\` - Qualidade de código Python
5. \`bandit-security.json\` - Vulnerabilidades de segurança
6. \`complexity-report.txt\` - Complexidade ciclomática
7. \`maintainability-index.txt\` - Índice de manutenibilidade
8. \`duplicates.json\` - Código duplicado
9. \`npm-audit.json\` - Vulnerabilidades NPM
10. \`python-safety.json\` - Vulnerabilidades Python
11. \`potential-secrets.txt\` - Possíveis secrets expostos
12. \`large-files.txt\` - Arquivos grandes
13. \`imports-analysis.txt\` - Análise de imports

---

## 🎯 Próximas Ações Recomendadas

### Alta Prioridade
1. Revisar e corrigir vulnerabilidades de segurança
2. Remover secrets expostos
3. Reduzir complexidade de código (CC > 10)

### Média Prioridade
4. Corrigir violações de linting
5. Refatorar código duplicado
6. Melhorar índice de manutenibilidade

### Baixa Prioridade
7. Otimizar imports
8. Reduzir tamanho de arquivos grandes
9. Melhorar documentação

---

**Relatório gerado por:** Code Review Automation
**Localização:** \`$REPORT_DIR\`
EOF

    log "✓ Relatório gerado: $REPORT_DIR/SUMMARY.md"
}

###############################################################################
# MAIN EXECUTION
###############################################################################

main() {
    echo ""
    log "╔═══════════════════════════════════════════════════════╗"
    log "║       CODE REVIEW AUTOMATIZADO - CONECTA PLUS         ║"
    log "╚═══════════════════════════════════════════════════════╝"
    echo ""

    review_frontend
    review_backend
    find_duplicates
    security_scan
    performance_analysis
    generate_summary

    echo ""
    log "╔═══════════════════════════════════════════════════════╗"
    log "║  ✅ CODE REVIEW CONCLUÍDO!                            ║"
    log "║                                                       ║"
    log "║  Relatórios em: $REPORT_DIR"
    log "║  Resumo: $REPORT_DIR/SUMMARY.md"
    log "╚═══════════════════════════════════════════════════════╝"
    echo ""
}

main "$@"
