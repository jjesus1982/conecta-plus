#!/bin/bash
#
# Conecta Plus - Health Check Rápido
# Uso: bash scripts/health-check.sh
#

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}        CONECTA PLUS - HEALTH CHECK${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Backend
echo -n "  Backend API (3001).......... "
if curl -s --connect-timeout 3 http://localhost:3001/health > /dev/null 2>&1 || curl -s --connect-timeout 3 http://localhost:3001/ > /dev/null 2>&1; then
    echo -e "${GREEN}[OK]${NC}"
else
    echo -e "${RED}[FALHA]${NC}"
fi

# Frontend
echo -n "  Frontend Next.js (3000)..... "
if curl -s --connect-timeout 3 http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}[OK]${NC}"
else
    echo -e "${RED}[FALHA]${NC}"
fi

# Docker Container
echo -n "  Container Docker............ "
if docker ps --filter "name=conecta" --format "{{.Names}}" 2>/dev/null | grep -q "conecta"; then
    container=$(docker ps --filter "name=conecta" --format "{{.Names}}" | head -1)
    echo -e "${GREEN}[OK]${NC} ($container)"
else
    echo -e "${RED}[FALHA]${NC}"
fi

# Monitor Service
echo -n "  Monitor 24/7................ "
if systemctl is-active conecta-monitor.service > /dev/null 2>&1; then
    echo -e "${GREEN}[OK]${NC}"
else
    echo -e "${YELLOW}[INATIVO]${NC}"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# System Resources
echo -e "  ${BLUE}RECURSOS DO SISTEMA${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# CPU
cpu=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}')
echo "  CPU:      ${cpu}%"

# Memory
mem=$(free -m | grep Mem | awk '{printf "%.1f%% (%dMB / %dMB)", $3/$2*100, $3, $2}')
echo "  Memória:  $mem"

# Disk
disk=$(df -h / | tail -1 | awk '{print $5 " (" $3 " / " $2 ")"}')
echo "  Disco:    $disk"

# Uptime
echo "  Uptime:   $(uptime -p)"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Recent Alerts
if [ -f /var/log/conecta-plus/alerts.log ]; then
    alert_count=$(wc -l < /var/log/conecta-plus/alerts.log 2>/dev/null || echo "0")
    recent_critical=$(tail -50 /var/log/conecta-plus/alerts.log 2>/dev/null | grep -c "CRITICAL" || echo "0")
    recent_warning=$(tail -50 /var/log/conecta-plus/alerts.log 2>/dev/null | grep -c "WARNING" || echo "0")

    echo -e "  ${BLUE}ALERTAS (últimas 50 entradas)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ "$recent_critical" -gt 0 ]; then
        echo -e "  Críticos: ${RED}$recent_critical${NC}"
    else
        echo -e "  Críticos: ${GREEN}0${NC}"
    fi

    if [ "$recent_warning" -gt 0 ]; then
        echo -e "  Avisos:   ${YELLOW}$recent_warning${NC}"
    else
        echo -e "  Avisos:   ${GREEN}0${NC}"
    fi

    echo "  Total:    $alert_count"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  Verificação: $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# === SEÇÃO DE APRENDIZADO ===
echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  ${BLUE}INTELIGÊNCIA DO SISTEMA${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -f /opt/conecta-plus/scripts/knowledge-base.json ]; then
    problems=$(python3 -c "import json; kb=json.load(open('/opt/conecta-plus/scripts/knowledge-base.json')); print(len(kb['problems']))" 2>/dev/null || echo "0")
    patterns=$(python3 -c "import json; kb=json.load(open('/opt/conecta-plus/scripts/knowledge-base.json')); print(len(kb['patterns']))" 2>/dev/null || echo "0")
    solutions=$(python3 -c "import json; kb=json.load(open('/opt/conecta-plus/scripts/knowledge-base.json')); print(len(kb['solutions']))" 2>/dev/null || echo "0")

    echo "  Problemas conhecidos:  $problems"
    echo "  Padrões detectados:    $patterns"
    echo "  Soluções registradas:  $solutions"

    # Mostrar predições se houver
    predictions=$(python3 /opt/conecta-plus/scripts/smart-monitor.py predict 2>/dev/null | grep -c "⚠️" || echo "0")
    if [ "$predictions" -gt 0 ]; then
        echo -e "  ${YELLOW}Alertas preditivos:    $predictions${NC}"
    else
        echo -e "  Alertas preditivos:    ${GREEN}0${NC}"
    fi
else
    echo "  Base de conhecimento não inicializada"
fi
