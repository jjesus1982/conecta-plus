#!/usr/bin/env python3
"""
Dashboard Web para System Monitor Agent
"""

from flask import Flask, render_template_string, jsonify, send_from_directory
import json
import os
from datetime import datetime
from pathlib import Path

app = Flask(__name__)

STATE_FILE = '/opt/conecta-plus/agents/system-monitor/state.json'
REPORTS_DIR = '/opt/conecta-plus/agents/system-monitor/reports'


def load_state():
    """Carrega estado atual do agente"""
    default_state = {
        'last_update': 'Nunca',
        'iteration': 0,
        'total_errors_fixed': 0,
        'total_gaps_detected': 0,
        'total_tests_run': 0,
        'total_tests_passed': 0,
        'last_cycle': {
            'log_analysis': {'overall_severity': 'ok'},
            'metrics': {},
            'actions_taken': [],
            'fixes_applied': [],
            'test_results': None,
            'timestamp': None
        }
    }

    try:
        with open(STATE_FILE) as f:
            state = json.load(f)

        # Garantir que last_cycle tenha estrutura mínima
        if 'last_cycle' not in state:
            state['last_cycle'] = default_state['last_cycle']
        else:
            # Preencher campos faltantes no last_cycle
            for key, value in default_state['last_cycle'].items():
                if key not in state['last_cycle']:
                    state['last_cycle'][key] = value

            # Garantir log_analysis existe
            if 'log_analysis' not in state['last_cycle'] or not isinstance(state['last_cycle']['log_analysis'], dict):
                state['last_cycle']['log_analysis'] = {'overall_severity': 'ok'}
            elif 'overall_severity' not in state['last_cycle']['log_analysis']:
                state['last_cycle']['log_analysis']['overall_severity'] = 'ok'

        return state
    except:
        return default_state


def get_recent_reports():
    """Retorna relatórios recentes"""
    reports = []

    try:
        for file in sorted(Path(REPORTS_DIR).glob('*.html'), reverse=True)[:10]:
            reports.append({
                'name': file.name,
                'path': str(file),
                'timestamp': datetime.fromtimestamp(file.stat().st_mtime).isoformat()
            })
    except:
        pass

    return reports


# Template HTML do dashboard
DASHBOARD_HTML = '''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conecta Plus - System Monitor Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        .header h1 {
            font-size: 32px;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        .status-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            background: #22c55e;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #1e293b;
            padding: 25px;
            border-radius: 12px;
            border: 1px solid #334155;
            transition: all 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            border-color: #667eea;
        }
        .stat-card .label {
            font-size: 12px;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }
        .stat-card .value {
            font-size: 36px;
            font-weight: bold;
            color: #fff;
            margin-bottom: 5px;
        }
        .stat-card .trend {
            font-size: 14px;
            color: #22c55e;
        }
        .section {
            background: #1e293b;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            border: 1px solid #334155;
        }
        .section h2 {
            font-size: 20px;
            margin-bottom: 20px;
            color: #f1f5f9;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .table {
            width: 100%;
            border-collapse: collapse;
        }
        .table th {
            text-align: left;
            padding: 12px;
            background: #0f172a;
            color: #94a3b8;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
        }
        .table td {
            padding: 12px;
            border-bottom: 1px solid #334155;
        }
        .table tr:hover {
            background: #0f172a;
        }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
        }
        .badge-critical { background: #dc2626; color: white; }
        .badge-high { background: #ea580c; color: white; }
        .badge-medium { background: #f59e0b; color: white; }
        .badge-low { background: #84cc16; color: white; }
        .badge-ok { background: #22c55e; color: white; }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .metric-card {
            background: #0f172a;
            padding: 20px;
            border-radius: 8px;
        }
        .metric-card h3 {
            font-size: 14px;
            color: #94a3b8;
            margin-bottom: 15px;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #334155;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s;
        }
        .progress-fill.warning {
            background: linear-gradient(90deg, #f59e0b, #ea580c);
        }
        .progress-fill.danger {
            background: linear-gradient(90deg, #ef4444, #dc2626);
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #fff;
        }
        .refresh-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: transform 0.2s;
        }
        .refresh-btn:hover {
            transform: scale(1.05);
        }
        .timeline {
            position: relative;
            padding-left: 30px;
        }
        .timeline-item {
            position: relative;
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-left: 2px solid #334155;
            padding-left: 25px;
        }
        .timeline-item:before {
            content: '';
            position: absolute;
            left: -6px;
            top: 0;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #667eea;
        }
        .timeline-time {
            font-size: 12px;
            color: #94a3b8;
            margin-bottom: 5px;
        }
        .timeline-content {
            color: #e2e8f0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>
                🛡️ Painel de Monitoramento do Sistema
                <span class="status-badge">● ATIVO</span>
            </h1>
            <div style="opacity: 0.9; margin-top: 10px;">
                Última Atualização: <span id="lastUpdate">{{ state.last_update }}</span>
                <button class="refresh-btn" onclick="location.reload()" style="float: right; margin-top: -10px;">
                    🔄 Atualizar
                </button>
            </div>
        </div>

        <!-- Health Score Principal -->
        {% set health = state.last_cycle.health_score if state.last_cycle.health_score else {} %}
        {% set score = health.overall_score if health.overall_score else 0 %}
        {% set level = health.health_level if health.health_level else 'Unknown' %}
        {% set score_color = '#22c55e' if score >= 75 else '#f59e0b' if score >= 60 else '#ef4444' %}
        <div class="stats-grid" style="margin-bottom: 30px;">
            <div class="stat-card" style="grid-column: span 2; background: linear-gradient(135deg, #1e293b 0%, #334155 100%); border: 2px solid {{ score_color }};">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div>
                        <div class="label" style="font-size: 18px;">🏥 Health Score</div>
                        <div class="value" style="font-size: 64px; color: {{ score_color }};">{{ score }}<span style="font-size: 24px;">/100</span></div>
                        <div class="trend" style="font-size: 16px;">{{ level }} - Sistema monitorado 24/7</div>
                    </div>
                    <div style="text-align: right;">
                        {% set bp = health.breakdown if health.breakdown else {} %}
                        <div style="margin: 5px 0; font-size: 14px;">📊 Gaps: {{ bp.gaps.score if bp.gaps else 0 }}/40</div>
                        <div style="margin: 5px 0; font-size: 14px;">💻 Métricas: {{ bp.metrics.score if bp.metrics else 0 }}/30</div>
                        <div style="margin: 5px 0; font-size: 14px;">🧪 Testes: {{ bp.tests.score if bp.tests else 0 }}/20</div>
                        <div style="margin: 5px 0; font-size: 14px;">🔧 Healing: {{ bp.healing.score if bp.healing else 0 }}/10</div>
                    </div>
                </div>
            </div>
            <!-- Prioridades P1-P4 -->
            {% set priorities = state.last_cycle.gaps.by_priority if state.last_cycle.gaps and state.last_cycle.gaps.by_priority else {} %}
            <div class="stat-card" style="background: linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%);">
                <div class="label">🔴 P1 - Crítico</div>
                <div class="value" style="font-size: 48px;">{{ priorities.P1 if priorities.P1 else 0 }}</div>
                <div class="trend">Ação imediata</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #78350f 0%, #92400e 100%);">
                <div class="label">🟠 P2 - Alto</div>
                <div class="value" style="font-size: 48px;">{{ priorities.P2 if priorities.P2 else 0 }}</div>
                <div class="trend">Resolver em 24h</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #713f12 0%, #854d0e 100%);">
                <div class="label">🟡 P3 - Médio</div>
                <div class="value" style="font-size: 48px;">{{ priorities.P3 if priorities.P3 else 0 }}</div>
                <div class="trend">Planejar correção</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #14532d 0%, #166534 100%);">
                <div class="label">🟢 P4 - Baixo</div>
                <div class="value" style="font-size: 48px;">{{ priorities.P4 if priorities.P4 else 0 }}</div>
                <div class="trend">Dívida técnica</div>
            </div>
        </div>

        <!-- Estatísticas Gerais -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="label">Total de Iterações</div>
                <div class="value">{{ state.iteration }}</div>
                <div class="trend">Ciclos de monitoramento concluídos</div>
            </div>
            <div class="stat-card">
                <div class="label">Erros Corrigidos</div>
                <div class="value" style="color: #22c55e;">{{ state.total_errors_fixed }}</div>
                <div class="trend">Resolvidos automaticamente</div>
            </div>
            <div class="stat-card">
                <div class="label">Problemas Detectados</div>
                <div class="value">{{ state.total_gaps_detected }}</div>
                <div class="trend">Questões identificadas</div>
            </div>
            <div class="stat-card">
                <div class="label">Taxa de Correção</div>
                <div class="value">
                    {% if state.total_gaps_detected > 0 %}
                    {{ "%.1f"|format(state.total_errors_fixed / state.total_gaps_detected * 100) }}%
                    {% else %}
                    0%
                    {% endif %}
                </div>
                <div class="trend">Eficiência do auto-healing</div>
            </div>
        </div>

        <!-- Safe Healing Score -->
        {% set sh = state.last_cycle.safe_healing if state.last_cycle.safe_healing else {} %}
        {% set hs = sh.healing_score if sh.healing_score else {} %}
        {% set hs_score = hs.current if hs.current else 0 %}
        {% set hs_color = '#22c55e' if hs_score >= 8 else '#f59e0b' if hs_score >= 5 else '#ef4444' %}
        <div class="section" style="margin-top: 30px;">
            <h2>🔧 Safe Auto-Healing (Progressivo)</h2>
            <div class="stats-grid">
                <div class="stat-card" style="grid-column: span 2; border: 2px solid {{ hs_color }};">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div class="label" style="font-size: 16px;">Healing Score</div>
                            <div class="value" style="font-size: 48px; color: {{ hs_color }};">{{ "%.1f"|format(hs_score) }}<span style="font-size: 20px;">/10</span></div>
                            <div class="trend">
                                {% if hs_score >= 8 %}
                                🟢 Pronto para P3
                                {% elif hs_score >= 5 %}
                                🟡 Evoluindo
                                {% else %}
                                🔴 Construindo confiança
                                {% endif %}
                            </div>
                        </div>
                        <div style="text-align: right; font-size: 14px;">
                            <div style="margin: 5px 0;">✅ Sucessos P4: {{ hs.p4_successes if hs.p4_successes else 0 }}/20</div>
                            <div style="margin: 5px 0;">🎯 P3 Habilitado: {{ 'Sim' if hs.p3_ready else 'Não' }}</div>
                            <div style="margin: 5px 0;">📊 Total tentativas: {{ hs.total_attempts if hs.total_attempts else 0 }}</div>
                        </div>
                    </div>
                </div>
                <div class="stat-card" style="background: #14532d;">
                    <div class="label">✅ Validados</div>
                    <div class="value" style="font-size: 36px;">{{ sh.successful if sh.successful else 0 }}</div>
                    <div class="trend">Com rollback disponível</div>
                </div>
                <div class="stat-card" style="background: #78350f;">
                    <div class="label">⏹️ Abortados</div>
                    <div class="value" style="font-size: 36px;">{{ sh.aborted if sh.aborted else 0 }}</div>
                    <div class="trend">Sem rollback ou P1-P3</div>
                </div>
            </div>

            <!-- Últimas ações de healing -->
            {% if sh.actions %}
            <div style="margin-top: 20px; background: #1e293b; padding: 15px; border-radius: 8px;">
                <h3 style="margin-bottom: 15px;">📋 Últimas Ações de Healing</h3>
                {% for action in sh.actions[-5:]|reverse %}
                <div style="padding: 10px; margin: 5px 0; background: #0f172a; border-radius: 4px; display: flex; justify-content: space-between;">
                    <span>
                        {% if action.final_result == 'success' %}✅
                        {% elif action.final_result == 'partial' %}⚠️
                        {% elif action.final_result == 'aborted' %}⏹️
                        {% else %}❌{% endif %}
                        {{ action.issue[:50] }}
                    </span>
                    <span style="color: #94a3b8;">{{ action.priority }}</span>
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>

        <!-- Resumo dos Resultados dos Testes -->
        {% if state.total_tests_run %}
        <div class="stats-grid">
            <div class="stat-card" style="border: 2px solid #667eea;">
                <div class="label">Total de Testes Executados</div>
                <div class="value">{{ state.total_tests_run }}</div>
                <div class="trend">Testes executados no ciclo de 24h</div>
            </div>
            <div class="stat-card" style="border: 2px solid #22c55e;">
                <div class="label">Testes Aprovados</div>
                <div class="value">{{ state.total_tests_passed }}</div>
                <div class="trend">{{ "%.1f"|format((state.total_tests_passed / state.total_tests_run * 100) if state.total_tests_run > 0 else 0) }}% taxa de aprovação</div>
            </div>
            <div class="stat-card" style="border: 2px solid #f59e0b;">
                <div class="label">Pontuação Geral</div>
                <div class="value">{{ state.last_cycle.test_results.summary.overall_score if state.last_cycle.test_results else 'N/A' }}</div>
                <div class="trend">Score de qualidade do sistema</div>
            </div>
            <div class="stat-card" style="border: 2px solid #ef4444;">
                <div class="label">Problemas Críticos</div>
                <div class="value">{{ state.last_cycle.test_results.summary.critical_issues|length if state.last_cycle.test_results else 0 }}</div>
                <div class="trend">Requerem atenção imediata</div>
            </div>
        </div>
        {% endif %}

        <!-- Resultados Completos dos Testes -->
        {% if state.last_cycle.test_results %}
        <div class="section">
            <h2>🧪 Resultados Completos dos Testes</h2>

            <!-- Resumo dos Testes -->
            <div class="metrics" style="margin-bottom: 30px;">
                <div class="metric-card">
                    <h3>Pontuação de Segurança</h3>
                    <div class="progress-bar">
                        <div class="progress-fill {% if state.last_cycle.test_results.summary.security_score < 50 %}danger{% elif state.last_cycle.test_results.summary.security_score < 75 %}warning{% endif %}"
                             style="width: {{ state.last_cycle.test_results.summary.security_score }}%"></div>
                    </div>
                    <div class="metric-value">{{ state.last_cycle.test_results.summary.security_score }}/100</div>
                </div>

                <div class="metric-card">
                    <h3>Prontidão para Produção</h3>
                    <div class="progress-bar">
                        <div class="progress-fill {% if state.last_cycle.test_results.summary.production_readiness < 50 %}danger{% elif state.last_cycle.test_results.summary.production_readiness < 75 %}warning{% endif %}"
                             style="width: {{ state.last_cycle.test_results.summary.production_readiness }}%"></div>
                    </div>
                    <div class="metric-value">{{ state.last_cycle.test_results.summary.production_readiness }}/100</div>
                </div>

                <div class="metric-card">
                    <h3>Taxa de Aprovação</h3>
                    <div class="progress-bar">
                        <div class="progress-fill {% if state.last_cycle.test_results.summary.pass_rate < 50 %}danger{% elif state.last_cycle.test_results.summary.pass_rate < 75 %}warning{% endif %}"
                             style="width: {{ state.last_cycle.test_results.summary.pass_rate }}%"></div>
                    </div>
                    <div class="metric-value">{{ "%.1f"|format(state.last_cycle.test_results.summary.pass_rate) }}%</div>
                </div>
            </div>

            <!-- Testes de Carga -->
            {% if state.last_cycle.test_results.load_tests %}
            <h3 style="color: #94a3b8; font-size: 16px; margin: 25px 0 15px 0;">🔥 Resultados de Teste de Carga</h3>
            <table class="table">
                <thead>
                    <tr>
                        <th>Endpoint</th>
                        <th>Taxa de Sucesso</th>
                        <th>Tempo Médio de Resposta</th>
                        <th>Req/Seg</th>
                        <th>Nota</th>
                    </tr>
                </thead>
                <tbody>
                    {% for test in state.last_cycle.test_results.load_tests.results %}
                    <tr>
                        <td>{{ test.endpoint }}</td>
                        <td>{{ "%.1f"|format(test.success_rate) }}%</td>
                        <td>{{ "%.2f"|format(test.avg_response_time) }}s</td>
                        <td>{{ "%.1f"|format(test.requests_per_second) }}</td>
                        <td>
                            <span class="badge {% if test.performance_grade == 'A' %}badge-ok{% elif test.performance_grade in ['B', 'C'] %}badge-medium{% else %}badge-critical{% endif %}">
                                {{ test.performance_grade }}
                            </span>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% endif %}

            <!-- Auditoria de Segurança -->
            {% if state.last_cycle.test_results.security_audit %}
            <h3 style="color: #94a3b8; font-size: 16px; margin: 25px 0 15px 0;">🔒 Resultados da Auditoria de Segurança</h3>
            <table class="table">
                <thead>
                    <tr>
                        <th>Tipo de Auditoria</th>
                        <th>Crítico</th>
                        <th>Alto</th>
                        <th>Aviso</th>
                        <th>Pontuação</th>
                    </tr>
                </thead>
                <tbody>
                    {% for audit_name, audit_data in state.last_cycle.test_results.security_audit.items() if audit_name != 'timestamp' %}
                    {% if audit_data.summary %}
                    <tr>
                        <td>{{ audit_name.replace('_', ' ').title() }}</td>
                        <td><span class="badge badge-critical">{{ audit_data.summary.critical }}</span></td>
                        <td><span class="badge badge-high">{{ audit_data.summary.high }}</span></td>
                        <td><span class="badge badge-medium">{{ audit_data.summary.warning }}</span></td>
                        <td><span class="badge badge-ok">{{ audit_data.summary.security_score }}/100</span></td>
                    </tr>
                    {% endif %}
                    {% endfor %}
                </tbody>
            </table>
            {% endif %}

            <!-- Problemas Críticos -->
            {% if state.last_cycle.test_results.summary.critical_issues %}
            <h3 style="color: #ef4444; font-size: 16px; margin: 25px 0 15px 0;">⚠️ Problemas Críticos Detectados</h3>
            <div style="background: #7f1d1d; border-left: 4px solid #ef4444; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <ul style="list-style: none; padding: 0;">
                    {% for issue in state.last_cycle.test_results.summary.critical_issues %}
                    <li style="padding: 8px 0; border-bottom: 1px solid #991b1b;">
                        <span class="badge badge-critical">{{ issue.type }}</span>
                        <span style="margin-left: 10px;">{{ issue.message }}</span>
                    </li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}

            <!-- Validação de Produção -->
            {% if state.last_cycle.test_results.production_validation %}
            <h3 style="color: #94a3b8; font-size: 16px; margin: 25px 0 15px 0;">⚙️ Configuração de Produção</h3>
            <div class="metrics">
                {% for validation_name, validation_data in state.last_cycle.test_results.production_validation.items() if validation_name != 'timestamp' %}
                {% if validation_data.summary %}
                <div class="metric-card">
                    <h3>{{ validation_name.replace('_', ' ').title() }}</h3>
                    <div style="display: flex; gap: 10px; margin-top: 10px;">
                        <span class="badge badge-critical">{{ validation_data.summary.high }} Alto</span>
                        <span class="badge badge-medium">{{ validation_data.summary.warning }} Aviso</span>
                        <span class="badge badge-ok">{{ validation_data.summary.ok }} OK</span>
                    </div>
                    <div style="margin-top: 10px; font-size: 14px; color: #94a3b8;">
                        Prontidão: <strong style="color: #fff;">{{ validation_data.summary.readiness_score }}/100</strong>
                    </div>
                </div>
                {% endif %}
                {% endfor %}
            </div>
            {% endif %}
        </div>
        {% endif %}

        <!-- Métricas do Sistema -->
        <div class="section">
            <h2>📊 Métricas do Sistema</h2>
            <div class="metrics" id="metricsContainer">
                {% if state.last_cycle.metrics %}
                <div class="metric-card">
                    <h3>Uso de CPU</h3>
                    <div class="progress-bar">
                        <div class="progress-fill {% if state.last_cycle.metrics.cpu.percent > 80 %}danger{% elif state.last_cycle.metrics.cpu.percent > 60 %}warning{% endif %}"
                             style="width: {{ state.last_cycle.metrics.cpu.percent }}%"></div>
                    </div>
                    <div class="metric-value">{{ "%.1f"|format(state.last_cycle.metrics.cpu.percent) }}%</div>
                </div>

                <div class="metric-card">
                    <h3>Uso de Memória</h3>
                    <div class="progress-bar">
                        <div class="progress-fill {% if state.last_cycle.metrics.memory.percent > 80 %}danger{% elif state.last_cycle.metrics.memory.percent > 60 %}warning{% endif %}"
                             style="width: {{ state.last_cycle.metrics.memory.percent }}%"></div>
                    </div>
                    <div class="metric-value">{{ "%.1f"|format(state.last_cycle.metrics.memory.percent) }}%</div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 5px;">
                        {{ state.last_cycle.metrics.memory.used_mb }} MB / {{ state.last_cycle.metrics.memory.total_mb }} MB
                    </div>
                </div>

                <div class="metric-card">
                    <h3>Uso de Disco</h3>
                    <div class="progress-bar">
                        <div class="progress-fill {% if state.last_cycle.metrics.disk.percent > 80 %}danger{% elif state.last_cycle.metrics.disk.percent > 60 %}warning{% endif %}"
                             style="width: {{ state.last_cycle.metrics.disk.percent }}%"></div>
                    </div>
                    <div class="metric-value">{{ "%.1f"|format(state.last_cycle.metrics.disk.percent) }}%</div>
                    <div style="font-size: 12px; color: #94a3b8; margin-top: 5px;">
                        {{ state.last_cycle.metrics.disk.used_gb }} GB / {{ state.last_cycle.metrics.disk.total_gb }} GB
                    </div>
                </div>
                {% else %}
                <div class="metric-card">
                    <p style="color: #94a3b8;">Nenhuma métrica disponível ainda</p>
                </div>
                {% endif %}
            </div>
        </div>

        <!-- Ações Recentes -->
        <div class="section">
            <h2>⚡ Ações Recentes</h2>
            <div class="timeline">
                {% if state.last_cycle.actions_taken %}
                    {% for action in state.last_cycle.actions_taken %}
                    <div class="timeline-item">
                        <div class="timeline-time">{{ state.last_cycle.timestamp }}</div>
                        <div class="timeline-content">{{ action }}</div>
                    </div>
                    {% endfor %}
                {% else %}
                    <p style="color: #94a3b8;">Nenhuma ação recente</p>
                {% endif %}
            </div>
        </div>

        <!-- Correções Recentes -->
        {% if state.last_cycle.fixes_applied %}
        <div class="section">
            <h2>🔧 Correções Recentes Aplicadas</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Tipo de Erro</th>
                        <th>Ação</th>
                        <th>Status</th>
                        <th>Detalhes</th>
                    </tr>
                </thead>
                <tbody>
                    {% for fix in state.last_cycle.fixes_applied[:10] %}
                    <tr>
                        <td><span class="badge badge-medium">{{ fix.error.type }}</span></td>
                        <td>{{ fix.result.action or 'N/A' }}</td>
                        <td>
                            {% if fix.result.success %}
                                <span class="badge badge-ok">✓ SUCESSO</span>
                            {% else %}
                                <span class="badge badge-critical">✗ FALHOU</span>
                            {% endif %}
                        </td>
                        <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis;">
                            {{ fix.result.reason or fix.result.details or 'N/A' }}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        <!-- Relatórios Recentes -->
        <div class="section">
            <h2>📄 Relatórios Gerados</h2>
            <table class="table">
                <thead>
                    <tr>
                        <th>Relatório</th>
                        <th>Gerado em</th>
                        <th>Ação</th>
                    </tr>
                </thead>
                <tbody>
                    {% for report in reports %}
                    <tr>
                        <td>{{ report.name }}</td>
                        <td>{{ report.timestamp }}</td>
                        <td>
                            <a href="/reports/{{ report.name }}" target="_blank" style="color: #667eea; text-decoration: none;">
                                Ver Relatório →
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        // Atualização automática a cada 30 segundos
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>
'''


@app.route('/')
def dashboard():
    """Dashboard principal"""
    state = load_state()
    reports = get_recent_reports()

    return render_template_string(DASHBOARD_HTML, state=state, reports=reports)


@app.route('/api/state')
def api_state():
    """API: Estado atual"""
    return jsonify(load_state())


@app.route('/api/reports')
def api_reports():
    """API: Lista de relatórios"""
    return jsonify(get_recent_reports())


@app.route('/reports/<path:filename>')
def serve_report(filename):
    """Serve relatórios HTML"""
    return send_from_directory(REPORTS_DIR, filename)


def main():
    """Inicia servidor web"""
    port = 8888
    print(f"🚀 Dashboard running at http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    main()
