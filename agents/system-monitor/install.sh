#!/bin/bash
# Script de instalação do System Monitor Agent

set -e

echo "🛡️  Installing Conecta Plus System Monitor Agent..."
echo ""

# 1. Instalar dependências Python
echo "1. Installing Python dependencies..."
pip3 install -r /opt/conecta-plus/agents/system-monitor/requirements.txt

# 2. Criar diretórios necessários
echo "2. Creating directories..."
mkdir -p /opt/conecta-plus/agents/system-monitor/{logs,reports,corrections}

# 3. Tornar agente executável
echo "3. Making agent executable..."
chmod +x /opt/conecta-plus/agents/system-monitor/agent.py
chmod +x /opt/conecta-plus/agents/system-monitor/dashboard/app.py

# 4. Instalar serviços systemd
echo "4. Installing systemd services..."
cp /opt/conecta-plus/agents/system-monitor/system-monitor.service /etc/systemd/system/
cp /opt/conecta-plus/agents/system-monitor/system-monitor-dashboard.service /etc/systemd/system/

# 5. Recarregar systemd
echo "5. Reloading systemd..."
systemctl daemon-reload

# 6. Habilitar serviços
echo "6. Enabling services..."
systemctl enable system-monitor.service
systemctl enable system-monitor-dashboard.service

echo ""
echo "✅ Installation complete!"
echo ""
echo "📋 Available commands:"
echo "  • Start agent:      systemctl start system-monitor"
echo "  • Stop agent:       systemctl stop system-monitor"
echo "  • Agent status:     systemctl status system-monitor"
echo "  • View logs:        journalctl -u system-monitor -f"
echo ""
echo "  • Start dashboard:  systemctl start system-monitor-dashboard"
echo "  • Stop dashboard:   systemctl stop system-monitor-dashboard"
echo "  • Dashboard status: systemctl status system-monitor-dashboard"
echo ""
echo "  • Run once:         python3 /opt/conecta-plus/agents/system-monitor/agent.py --once"
echo ""
echo "🌐 Dashboard will be available at: http://localhost:8888"
echo ""
