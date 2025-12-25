"""
Skill: Production Validator
Valida configurações para produção
"""

import os
import json
from typing import Dict, Any, List
from datetime import datetime


class ProductionValidator:
    """Valida configurações de produção"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def validate_environment_variables(self) -> Dict[str, Any]:
        """Valida variáveis de ambiente necessárias"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'environment_variables',
            'findings': []
        }

        # Variáveis críticas que devem existir
        required_vars = [
            ('DATABASE_URL', 'Conexão com banco de dados'),
            ('JWT_SECRET', 'Secret para tokens JWT'),
            ('NODE_ENV', 'Ambiente de execução'),
        ]

        recommended_vars = [
            ('SMTP_HOST', 'Servidor de email'),
            ('SMTP_PORT', 'Porta SMTP'),
            ('REDIS_URL', 'Conexão Redis'),
            ('API_URL', 'URL da API'),
        ]

        # Verificar .env files
        env_files = [
            '/opt/conecta-plus/backend/.env',
            '/opt/conecta-plus/frontend/.env.local'
        ]

        all_vars = {}

        for env_file in env_files:
            if os.path.exists(env_file):
                try:
                    with open(env_file) as f:
                        for line in f:
                            if '=' in line and not line.strip().startswith('#'):
                                key, value = line.strip().split('=', 1)
                                all_vars[key] = value
                except Exception:
                    pass

        # Verificar required
        for var, description in required_vars:
            if var not in all_vars and var not in os.environ:
                results['findings'].append({
                    'severity': 'high',
                    'variable': var,
                    'message': f'Variável crítica ausente: {description}'
                })
            elif var in all_vars or var in os.environ:
                results['findings'].append({
                    'severity': 'ok',
                    'variable': var,
                    'message': f'{description} configurado'
                })

        # Verificar recommended
        for var, description in recommended_vars:
            if var not in all_vars and var not in os.environ:
                results['findings'].append({
                    'severity': 'warning',
                    'variable': var,
                    'message': f'Variável recomendada ausente: {description}'
                })

        # Verificar NODE_ENV
        node_env = all_vars.get('NODE_ENV') or os.environ.get('NODE_ENV')
        if node_env == 'development':
            results['findings'].append({
                'severity': 'warning',
                'variable': 'NODE_ENV',
                'message': 'Sistema em modo desenvolvimento - alterar para production'
            })
        elif node_env == 'production':
            results['findings'].append({
                'severity': 'ok',
                'variable': 'NODE_ENV',
                'message': 'Sistema configurado para production'
            })

        results['summary'] = self._summarize(results['findings'])
        return results

    def validate_database_configuration(self) -> Dict[str, Any]:
        """Valida configuração de banco de dados"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'database_configuration',
            'findings': []
        }

        # Verificar se está usando SQLite (não recomendado para produção)
        db_url = os.environ.get('DATABASE_URL', '')

        if 'sqlite' in db_url.lower():
            results['findings'].append({
                'severity': 'high',
                'message': 'SQLite detectado - não recomendado para produção. Use PostgreSQL/MySQL'
            })
        elif 'postgresql' in db_url.lower() or 'postgres' in db_url.lower():
            results['findings'].append({
                'severity': 'ok',
                'message': 'PostgreSQL configurado (recomendado)'
            })
        elif 'mysql' in db_url.lower():
            results['findings'].append({
                'severity': 'ok',
                'message': 'MySQL configurado'
            })
        else:
            results['findings'].append({
                'severity': 'warning',
                'message': 'Database URL não configurado ou tipo desconhecido'
            })

        # Verificar pool de conexões
        if 'max_connections' not in db_url.lower() and 'pool_size' not in db_url.lower():
            results['findings'].append({
                'severity': 'warning',
                'message': 'Pool de conexões não configurado explicitamente'
            })

        results['summary'] = self._summarize(results['findings'])
        return results

    def validate_logging_configuration(self) -> Dict[str, Any]:
        """Valida configuração de logs"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'logging_configuration',
            'findings': []
        }

        # Verificar se diretórios de log existem
        log_dirs = [
            '/opt/conecta-plus/backend/logs',
            '/opt/conecta-plus/frontend/logs',
            '/opt/conecta-plus/agents/system-monitor/logs'
        ]

        for log_dir in log_dirs:
            if os.path.exists(log_dir):
                # Verificar permissões de escrita
                if os.access(log_dir, os.W_OK):
                    results['findings'].append({
                        'severity': 'ok',
                        'directory': log_dir,
                        'message': 'Diretório de logs acessível'
                    })
                else:
                    results['findings'].append({
                        'severity': 'high',
                        'directory': log_dir,
                        'message': 'Diretório de logs sem permissão de escrita'
                    })
            else:
                results['findings'].append({
                    'severity': 'warning',
                    'directory': log_dir,
                    'message': 'Diretório de logs não existe'
                })

        # Verificar rotação de logs
        if not os.path.exists('/etc/logrotate.d/conecta-plus'):
            results['findings'].append({
                'severity': 'warning',
                'message': 'Rotação de logs não configurada - logs podem crescer indefinidamente'
            })

        results['summary'] = self._summarize(results['findings'])
        return results

    def validate_smtp_configuration(self) -> Dict[str, Any]:
        """Valida configuração SMTP"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'smtp_configuration',
            'findings': []
        }

        smtp_vars = ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASSWORD']
        configured = sum(1 for var in smtp_vars if var in os.environ)

        if configured == 0:
            results['findings'].append({
                'severity': 'warning',
                'message': 'SMTP não configurado - emails não serão enviados'
            })
        elif configured < 4:
            results['findings'].append({
                'severity': 'warning',
                'message': f'SMTP parcialmente configurado ({configured}/4 variáveis)'
            })
        else:
            results['findings'].append({
                'severity': 'ok',
                'message': 'SMTP totalmente configurado'
            })

        results['summary'] = self._summarize(results['findings'])
        return results

    def validate_monitoring_configuration(self) -> Dict[str, Any]:
        """Valida configuração de monitoramento"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'monitoring_configuration',
            'findings': []
        }

        # Verificar se System Monitor está rodando
        import subprocess

        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'system-monitor'],
                capture_output=True,
                text=True
            )

            if result.stdout.strip() == 'active':
                results['findings'].append({
                    'severity': 'ok',
                    'message': 'System Monitor Agent ativo'
                })
            else:
                results['findings'].append({
                    'severity': 'high',
                    'message': 'System Monitor Agent não está rodando'
                })
        except Exception:
            results['findings'].append({
                'severity': 'warning',
                'message': 'Não foi possível verificar status do System Monitor'
            })

        # Verificar Dashboard
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', 'system-monitor-dashboard'],
                capture_output=True,
                text=True
            )

            if result.stdout.strip() == 'active':
                results['findings'].append({
                    'severity': 'ok',
                    'message': 'Monitor Dashboard ativo'
                })
            else:
                results['findings'].append({
                    'severity': 'warning',
                    'message': 'Monitor Dashboard não está rodando'
                })
        except Exception:
            pass

        results['summary'] = self._summarize(results['findings'])
        return results

    def validate_build_configuration(self) -> Dict[str, Any]:
        """Valida configuração de build"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'build_configuration',
            'findings': []
        }

        # Verificar se Next.js está em modo production
        next_config = '/opt/conecta-plus/frontend/next.config.ts'

        if os.path.exists(next_config):
            with open(next_config) as f:
                content = f.read()

                if 'output: \'standalone\'' in content:
                    results['findings'].append({
                        'severity': 'ok',
                        'message': 'Next.js configurado para standalone build'
                    })

        # Verificar se .next/BUILD_ID existe
        build_id = '/opt/conecta-plus/frontend/.next/BUILD_ID'

        if os.path.exists(build_id):
            results['findings'].append({
                'severity': 'ok',
                'message': 'Build Next.js disponível'
            })
        else:
            results['findings'].append({
                'severity': 'warning',
                'message': 'Build Next.js não encontrado - executar npm run build'
            })

        results['summary'] = self._summarize(results['findings'])
        return results

    def _summarize(self, findings: List[Dict]) -> Dict[str, Any]:
        """Gera resumo"""
        return {
            'total': len(findings),
            'critical': sum(1 for f in findings if f.get('severity') == 'critical'),
            'high': sum(1 for f in findings if f.get('severity') == 'high'),
            'warning': sum(1 for f in findings if f.get('severity') == 'warning'),
            'ok': sum(1 for f in findings if f.get('severity') == 'ok'),
            'readiness_score': self._calculate_readiness(findings)
        }

    def _calculate_readiness(self, findings: List[Dict]) -> int:
        """Calcula production readiness score (0-100)"""
        if not findings:
            return 50

        score = 100

        for finding in findings:
            severity = finding.get('severity', 'info')

            if severity == 'critical':
                score -= 25
            elif severity == 'high':
                score -= 15
            elif severity == 'warning':
                score -= 5

        return max(0, min(100, score))

    def run_all_validations(self) -> Dict[str, Any]:
        """Executa todas as validações"""
        return {
            'timestamp': datetime.now().isoformat(),
            'environment': self.validate_environment_variables(),
            'database': self.validate_database_configuration(),
            'logging': self.validate_logging_configuration(),
            'smtp': self.validate_smtp_configuration(),
            'monitoring': self.validate_monitoring_configuration(),
            'build': self.validate_build_configuration()
        }


if __name__ == '__main__':
    validator = ProductionValidator({})
    results = validator.run_all_validations()
    print(json.dumps(results, indent=2))
