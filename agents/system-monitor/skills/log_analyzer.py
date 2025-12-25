"""
Skill: Log Analyzer
Analisa logs do sistema em busca de erros, padrões e anomalias
"""

import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter
import hashlib


class LogAnalyzer:
    """Analisa logs do sistema identificando erros e padrões"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.error_patterns = self._compile_patterns()
        self.error_history = defaultdict(list)
        self.analysis_cache = {}

    def _compile_patterns(self) -> List[re.Pattern]:
        """Compila padrões regex para identificar erros"""
        patterns = []
        for log_config in self.config.get('monitoring', {}).get('logs', []):
            for pattern in log_config.get('patterns', []):
                patterns.append(re.compile(pattern, re.IGNORECASE))
        return patterns

    def analyze_log_file(
        self,
        log_path: str,
        lines: int = 1000,
        since: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Analisa arquivo de log

        Args:
            log_path: Caminho do arquivo de log
            lines: Número de linhas para analisar (do final)
            since: Analisar apenas logs após este timestamp

        Returns:
            Dicionário com análise completa
        """
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Ler últimas N linhas
                log_lines = self._tail(f, lines)

            analysis = {
                'log_path': log_path,
                'timestamp': datetime.now().isoformat(),
                'total_lines': len(log_lines),
                'errors': [],
                'warnings': [],
                'patterns': defaultdict(int),
                'severity': 'ok',
                'summary': {},
                'recommendations': []
            }

            # Analisar cada linha
            for line_num, line in enumerate(log_lines, 1):
                self._analyze_line(line, line_num, analysis)

            # Calcular severidade geral
            analysis['severity'] = self._calculate_severity(analysis)

            # Gerar recomendações
            analysis['recommendations'] = self._generate_recommendations(analysis)

            # Estatísticas
            analysis['summary'] = self._generate_summary(analysis)

            return analysis

        except FileNotFoundError:
            return {
                'log_path': log_path,
                'error': 'Log file not found',
                'severity': 'error'
            }
        except Exception as e:
            return {
                'log_path': log_path,
                'error': f'Analysis failed: {str(e)}',
                'severity': 'error'
            }

    def _tail(self, file, lines: int = 1000) -> List[str]:
        """Lê últimas N linhas de um arquivo"""
        BUFFER_SIZE = 8192
        file.seek(0, 2)
        file_size = file.tell()

        blocks = []
        remaining_size = file_size

        while remaining_size > 0 and len(blocks) < lines:
            if remaining_size - BUFFER_SIZE > 0:
                file.seek(remaining_size - BUFFER_SIZE)
                blocks.append(file.read(BUFFER_SIZE))
                remaining_size -= BUFFER_SIZE
            else:
                file.seek(0)
                blocks.append(file.read(remaining_size))
                remaining_size = 0

        content = ''.join(reversed(blocks))
        return content.splitlines()[-lines:]

    def _analyze_line(self, line: str, line_num: int, analysis: Dict[str, Any]):
        """Analisa uma linha de log"""
        line_lower = line.lower()

        # Detectar erros
        if any(keyword in line_lower for keyword in ['error', 'erro', 'failed', 'failure']):
            error = self._extract_error(line, line_num)
            if error:
                analysis['errors'].append(error)

        # Detectar warnings
        if any(keyword in line_lower for keyword in ['warn', 'warning', 'aviso']):
            warning = self._extract_warning(line, line_num)
            if warning:
                analysis['warnings'].append(warning)

        # Contar padrões
        for pattern in self.error_patterns:
            if pattern.search(line):
                analysis['patterns'][pattern.pattern] += 1

    def _extract_error(self, line: str, line_num: int) -> Optional[Dict[str, Any]]:
        """Extrai informações detalhadas de um erro"""
        # Tentar extrair stack trace
        stack_trace = None
        if 'at ' in line or 'File ' in line:
            stack_trace = line

        # Tentar extrair código de erro
        error_code = None
        code_match = re.search(r'(E[A-Z]+|Error \d+)', line)
        if code_match:
            error_code = code_match.group(1)

        # Gerar hash único do erro
        error_hash = hashlib.md5(line.encode()).hexdigest()[:8]

        return {
            'line': line_num,
            'message': line.strip(),
            'error_code': error_code,
            'stack_trace': stack_trace,
            'timestamp': datetime.now().isoformat(),
            'hash': error_hash,
            'type': self._classify_error(line)
        }

    def _extract_warning(self, line: str, line_num: int) -> Optional[Dict[str, Any]]:
        """Extrai informações de um warning"""
        return {
            'line': line_num,
            'message': line.strip(),
            'timestamp': datetime.now().isoformat(),
            'type': self._classify_warning(line)
        }

    def _classify_error(self, line: str) -> str:
        """Classifica tipo de erro"""
        line_lower = line.lower()

        if 'econnreset' in line_lower or 'socket hang up' in line_lower:
            return 'network'
        elif 'timeout' in line_lower:
            return 'timeout'
        elif 'module not found' in line_lower or 'cannot find' in line_lower:
            return 'dependency'
        elif 'enospc' in line_lower or 'disk' in line_lower:
            return 'disk'
        elif 'memory' in line_lower or 'oom' in line_lower:
            return 'memory'
        elif 'permission' in line_lower or 'eacces' in line_lower:
            return 'permission'
        elif 'lock' in line_lower:
            return 'lock'
        else:
            return 'unknown'

    def _classify_warning(self, line: str) -> str:
        """Classifica tipo de warning"""
        line_lower = line.lower()

        if 'deprecated' in line_lower:
            return 'deprecated'
        elif 'port' in line_lower and 'in use' in line_lower:
            return 'port_conflict'
        else:
            return 'general'

    def _calculate_severity(self, analysis: Dict[str, Any]) -> str:
        """Calcula severidade geral baseado nos erros encontrados"""
        error_count = len(analysis['errors'])
        warning_count = len(analysis['warnings'])

        # Verificar erros críticos
        critical_patterns = ['enospc', 'oom', 'critical', 'fatal']
        has_critical = any(
            any(pattern in error['message'].lower() for pattern in critical_patterns)
            for error in analysis['errors']
        )

        if has_critical:
            return 'critical'
        elif error_count > 10:
            return 'high'
        elif error_count > 5:
            return 'medium'
        elif error_count > 0 or warning_count > 10:
            return 'low'
        else:
            return 'ok'

    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Gera recomendações baseadas nos erros encontrados"""
        recommendations = []

        # Contar tipos de erros
        error_types = Counter(error['type'] for error in analysis['errors'])

        for error_type, count in error_types.items():
            if error_type == 'network' and count > 3:
                recommendations.append(
                    "Muitos erros de rede (ECONNRESET). Implementar retry logic e timeout."
                )
            elif error_type == 'timeout' and count > 3:
                recommendations.append(
                    "Múltiplos timeouts detectados. Verificar performance da API backend."
                )
            elif error_type == 'dependency':
                recommendations.append(
                    "Dependências faltando. Executar npm install / pip install."
                )
            elif error_type == 'disk':
                recommendations.append(
                    "Problemas de espaço em disco. Limpar arquivos temporários e logs antigos."
                )
            elif error_type == 'memory':
                recommendations.append(
                    "Alto uso de memória. Verificar vazamentos de memória e otimizar código."
                )
            elif error_type == 'lock':
                recommendations.append(
                    "Arquivos lock detectados. Remover locks e reiniciar processos."
                )

        return recommendations

    def _generate_summary(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Gera resumo estatístico"""
        error_types = Counter(error['type'] for error in analysis['errors'])

        return {
            'total_errors': len(analysis['errors']),
            'total_warnings': len(analysis['warnings']),
            'error_types': dict(error_types),
            'most_common_error': error_types.most_common(1)[0] if error_types else None,
            'unique_errors': len(set(error['hash'] for error in analysis['errors'])),
        }

    def analyze_all_logs(self) -> Dict[str, Any]:
        """Analisa todos os logs configurados"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'logs': {},
            'overall_severity': 'ok',
            'total_errors': 0,
            'total_warnings': 0,
            'critical_issues': []
        }

        for log_config in self.config.get('monitoring', {}).get('logs', []):
            log_path = log_config['path']
            log_type = log_config['type']

            analysis = self.analyze_log_file(log_path)
            results['logs'][log_type] = analysis

            # Acumular contadores
            results['total_errors'] += len(analysis.get('errors', []))
            results['total_warnings'] += len(analysis.get('warnings', []))

            # Detectar issues críticos
            if analysis.get('severity') in ['critical', 'high']:
                results['critical_issues'].append({
                    'log': log_type,
                    'severity': analysis['severity'],
                    'error_count': len(analysis.get('errors', []))
                })

        # Calcular severidade geral
        severities = [log['severity'] for log in results['logs'].values()]
        if 'critical' in severities:
            results['overall_severity'] = 'critical'
        elif 'high' in severities:
            results['overall_severity'] = 'high'
        elif 'medium' in severities:
            results['overall_severity'] = 'medium'
        elif 'low' in severities:
            results['overall_severity'] = 'low'

        return results


if __name__ == '__main__':
    # Teste
    import yaml

    with open('/opt/conecta-plus/agents/system-monitor/config.yaml') as f:
        config = yaml.safe_load(f)

    analyzer = LogAnalyzer(config)
    results = analyzer.analyze_all_logs()

    print(json.dumps(results, indent=2))
