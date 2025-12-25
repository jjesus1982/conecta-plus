"""
Skill: Reporter
Gera relatórios detalhados sobre o sistema
"""

import json
from datetime import datetime
from typing import Dict, Any, List
import os


class Reporter:
    """Gera relatórios em diversos formatos"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.output_dir = config.get('reporting', {}).get('output_dir', '/opt/conecta-plus/agents/system-monitor/reports')

        # Criar diretório se não existir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_report(
        self,
        log_analysis: Dict[str, Any],
        gaps: Dict[str, Any],
        fixes: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Gera relatório completo em múltiplos formatos

        Args:
            log_analysis: Resultado da análise de logs
            gaps: Gaps detectados
            fixes: Correções aplicadas

        Returns:
            Dicionário com paths dos relatórios gerados
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'log_analysis': log_analysis,
            'gaps': gaps,
            'fixes': fixes,
            'summary': self._generate_summary(log_analysis, gaps, fixes)
        }

        paths = {}

        # JSON
        if 'json' in self.config.get('reporting', {}).get('formats', []):
            json_path = self._generate_json(report_data, timestamp)
            paths['json'] = json_path

        # HTML
        if 'html' in self.config.get('reporting', {}).get('formats', []):
            html_path = self._generate_html(report_data, timestamp)
            paths['html'] = html_path

        # Markdown
        if 'markdown' in self.config.get('reporting', {}).get('formats', []):
            md_path = self._generate_markdown(report_data, timestamp)
            paths['markdown'] = md_path

        return paths

    def _generate_summary(
        self,
        log_analysis: Dict[str, Any],
        gaps: Dict[str, Any],
        fixes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Gera resumo executivo"""
        return {
            'system_health': log_analysis.get('overall_severity', 'unknown'),
            'total_errors': log_analysis.get('total_errors', 0),
            'total_warnings': log_analysis.get('total_warnings', 0),
            'critical_issues': len(log_analysis.get('critical_issues', [])),
            'total_gaps': gaps.get('total_gaps', 0),
            'critical_gaps': gaps.get('critical_gaps', 0),
            'total_fixes_applied': fixes.get('total_fixes', 0),
            'successful_fixes': fixes.get('successful_fixes', 0),
            'fix_success_rate': fixes.get('success_rate', 0),
            'recommendations': self._generate_recommendations(log_analysis, gaps, fixes)
        }

    def _generate_recommendations(
        self,
        log_analysis: Dict[str, Any],
        gaps: Dict[str, Any],
        fixes: Dict[str, Any]
    ) -> List[str]:
        """Gera recomendações prioritárias"""
        recommendations = []

        # Da análise de logs
        for log_type, log_data in log_analysis.get('logs', {}).items():
            recommendations.extend(log_data.get('recommendations', []))

        # Dos gaps
        for gap in gaps.get('gaps', []):
            if gap.get('severity') in ['critical', 'high']:
                recommendations.append(gap.get('solution', gap.get('description')))

        # Limitar a top 10
        return recommendations[:10]

    def _generate_json(self, report_data: Dict[str, Any], timestamp: str) -> str:
        """Gera relatório JSON"""
        filename = f'report_{timestamp}.json'
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        return filepath

    def _generate_html(self, report_data: Dict[str, Any], timestamp: str) -> str:
        """Gera relatório HTML"""
        filename = f'report_{timestamp}.html'
        filepath = os.path.join(self.output_dir, filename)

        summary = report_data['summary']
        log_analysis = report_data['log_analysis']
        gaps = report_data['gaps']
        fixes = report_data['fixes']

        # Determinar cor do status
        health_colors = {
            'ok': '#22c55e',
            'low': '#eab308',
            'medium': '#f97316',
            'high': '#ef4444',
            'critical': '#dc2626'
        }

        health = summary['system_health']
        health_color = health_colors.get(health, '#6b7280')

        html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Conecta Plus - System Monitor Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f9fafb;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px 8px 0 0;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .header .timestamp {{ opacity: 0.9; font-size: 14px; }}
        .content {{ padding: 30px; }}
        .section {{ margin-bottom: 40px; }}
        .section h2 {{
            font-size: 20px;
            color: #1f2937;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #f9fafb;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #667eea;
        }}
        .stat-card .label {{
            font-size: 12px;
            color: #6b7280;
            text-transform: uppercase;
            margin-bottom: 5px;
        }}
        .stat-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #1f2937;
        }}
        .health-badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 14px;
            color: white;
            background: {health_color};
        }}
        .table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .table th {{
            background: #f3f4f6;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #374151;
            border-bottom: 2px solid #e5e7eb;
        }}
        .table td {{
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }}
        .severity-critical {{ color: #dc2626; font-weight: 600; }}
        .severity-high {{ color: #ef4444; font-weight: 600; }}
        .severity-medium {{ color: #f97316; font-weight: 600; }}
        .severity-low {{ color: #eab308; font-weight: 600; }}
        .recommendations {{
            background: #f0f9ff;
            border-left: 4px solid #3b82f6;
            padding: 20px;
            border-radius: 4px;
        }}
        .recommendations ul {{
            list-style-position: inside;
            color: #1e40af;
        }}
        .recommendations li {{
            margin: 8px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ Conecta Plus System Monitor</h1>
            <div class="timestamp">Report generated at {report_data['timestamp']}</div>
        </div>

        <div class="content">
            <!-- Summary -->
            <div class="section">
                <h2>📊 Executive Summary</h2>
                <div class="stats">
                    <div class="stat-card">
                        <div class="label">System Health</div>
                        <div class="value">
                            <span class="health-badge">{health.upper()}</span>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Total Errors</div>
                        <div class="value">{summary['total_errors']}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Critical Issues</div>
                        <div class="value">{summary['critical_issues']}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Gaps Detected</div>
                        <div class="value">{summary['total_gaps']}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Fixes Applied</div>
                        <div class="value">{summary['total_fixes_applied']}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Fix Success Rate</div>
                        <div class="value">{summary['fix_success_rate']:.1f}%</div>
                    </div>
                </div>
            </div>

            <!-- Errors -->
            <div class="section">
                <h2>🚨 Recent Errors</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Type</th>
                            <th>Message</th>
                            <th>Severity</th>
                            <th>Timestamp</th>
                        </tr>
                    </thead>
                    <tbody>
'''

        # Adicionar erros de todos os logs
        for log_type, log_data in log_analysis.get('logs', {}).items():
            for error in log_data.get('errors', [])[:10]:  # Top 10
                severity = error.get('type', 'unknown')
                html += f'''
                        <tr>
                            <td>{error.get('type', 'unknown')}</td>
                            <td style="max-width: 400px; overflow: hidden; text-overflow: ellipsis;">
                                {error.get('message', '')[:100]}
                            </td>
                            <td><span class="severity-{severity}">{severity.upper()}</span></td>
                            <td>{error.get('timestamp', '')}</td>
                        </tr>
'''

        html += '''
                    </tbody>
                </table>
            </div>

            <!-- Gaps -->
            <div class="section">
                <h2>🔍 Detected Gaps</h2>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Category</th>
                            <th>Description</th>
                            <th>Severity</th>
                            <th>Solution</th>
                        </tr>
                    </thead>
                    <tbody>
'''

        for gap in gaps.get('gaps', [])[:20]:  # Top 20
            severity = gap.get('severity', 'low')
            html += f'''
                        <tr>
                            <td>{gap.get('category', 'unknown')}</td>
                            <td>{gap.get('description', '')}</td>
                            <td><span class="severity-{severity}">{severity.upper()}</span></td>
                            <td>{gap.get('solution', 'N/A')}</td>
                        </tr>
'''

        html += '''
                    </tbody>
                </table>
            </div>

            <!-- Recommendations -->
            <div class="section">
                <h2>💡 Recommendations</h2>
                <div class="recommendations">
                    <ul>
'''

        for rec in summary.get('recommendations', []):
            html += f'                        <li>{rec}</li>\n'

        html += '''
                    </ul>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return filepath

    def _generate_markdown(self, report_data: Dict[str, Any], timestamp: str) -> str:
        """Gera relatório Markdown"""
        filename = f'report_{timestamp}.md'
        filepath = os.path.join(self.output_dir, filename)

        summary = report_data['summary']
        log_analysis = report_data['log_analysis']
        gaps = report_data['gaps']
        fixes = report_data['fixes']

        md = f'''# 🛡️ Conecta Plus System Monitor Report

**Generated:** {report_data['timestamp']}

---

## 📊 Executive Summary

| Metric | Value |
|--------|-------|
| System Health | **{summary['system_health'].upper()}** |
| Total Errors | {summary['total_errors']} |
| Critical Issues | {summary['critical_issues']} |
| Gaps Detected | {summary['total_gaps']} |
| Critical Gaps | {summary['critical_gaps']} |
| Fixes Applied | {summary['total_fixes_applied']} |
| Successful Fixes | {summary['successful_fixes']} |
| Fix Success Rate | {summary['fix_success_rate']:.1f}% |

---

## 🚨 Recent Errors

'''

        # Adicionar erros
        for log_type, log_data in log_analysis.get('logs', {}).items():
            md += f'\n### {log_type.upper()}\n\n'
            errors = log_data.get('errors', [])[:10]

            if errors:
                md += '| Type | Message | Timestamp |\n'
                md += '|------|---------|----------|\n'

                for error in errors:
                    message = error.get('message', '')[:80].replace('|', '\\|')
                    md += f"| {error.get('type', 'unknown')} | {message} | {error.get('timestamp', '')} |\n"
            else:
                md += '_No errors detected_\n'

        # Gaps
        md += '\n---\n\n## 🔍 Detected Gaps\n\n'

        if gaps.get('gaps'):
            md += '| Category | Description | Severity | Solution |\n'
            md += '|----------|-------------|----------|----------|\n'

            for gap in gaps['gaps'][:20]:
                desc = gap.get('description', '').replace('|', '\\|')
                solution = gap.get('solution', 'N/A').replace('|', '\\|')
                md += f"| {gap.get('category', 'unknown')} | {desc} | **{gap.get('severity', 'low').upper()}** | {solution} |\n"
        else:
            md += '_No gaps detected_\n'

        # Recommendations
        md += '\n---\n\n## 💡 Recommendations\n\n'

        if summary.get('recommendations'):
            for i, rec in enumerate(summary['recommendations'], 1):
                md += f'{i}. {rec}\n'
        else:
            md += '_No recommendations at this time_\n'

        # Footer
        md += f'''
---

**System Monitor Agent v{self.config.get('agent', {}).get('version', '1.0.0')}**
'''

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)

        return filepath


if __name__ == '__main__':
    # Teste
    import yaml

    with open('/opt/conecta-plus/agents/system-monitor/config.yaml') as f:
        config = yaml.safe_load(f)

    reporter = Reporter(config)

    # Dados de teste
    test_data = {
        'log_analysis': {'overall_severity': 'medium', 'total_errors': 5, 'total_warnings': 10, 'critical_issues': [], 'logs': {}},
        'gaps': {'total_gaps': 3, 'critical_gaps': 0, 'gaps': []},
        'fixes': {'total_fixes': 2, 'successful_fixes': 2, 'success_rate': 100}
    }

    paths = reporter.generate_report(**test_data)
    print(json.dumps(paths, indent=2))
