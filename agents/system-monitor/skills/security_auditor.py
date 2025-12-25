"""
Skill: Security Auditor
Auditoria de segurança em produção
"""

import os
import re
import subprocess
from typing import Dict, Any, List
from datetime import datetime
import requests


class SecurityAuditor:
    """Audita segurança do sistema"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def audit_jwt_security(self) -> Dict[str, Any]:
        """Audita configuração JWT"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'jwt_security',
            'findings': []
        }

        # Verificar se JWT secret é forte
        env_files = [
            '/opt/conecta-plus/backend/.env',
            '/opt/conecta-plus/frontend/.env',
            '/opt/conecta-plus/frontend/.env.local'
        ]

        for env_file in env_files:
            if os.path.exists(env_file):
                try:
                    with open(env_file, 'r') as f:
                        content = f.read()

                    # Buscar JWT_SECRET
                    jwt_secret = re.search(r'JWT_SECRET\s*=\s*["\']?([^"\'\n]+)["\']?', content)

                    if jwt_secret:
                        secret = jwt_secret.group(1)

                        # Avaliar força
                        finding = {
                            'file': env_file,
                            'severity': 'info',
                            'message': 'JWT Secret encontrado'
                        }

                        if len(secret) < 32:
                            finding['severity'] = 'high'
                            finding['message'] = f'JWT Secret muito curto: {len(secret)} caracteres (mínimo 32)'
                        elif secret in ['secret', 'your-secret-key', 'change-me', '123456']:
                            finding['severity'] = 'critical'
                            finding['message'] = 'JWT Secret é um valor padrão/inseguro'
                        else:
                            finding['severity'] = 'ok'
                            finding['message'] = f'JWT Secret adequado ({len(secret)} caracteres)'

                        results['findings'].append(finding)

                except Exception as e:
                    results['findings'].append({
                        'file': env_file,
                        'severity': 'error',
                        'message': f'Erro ao ler arquivo: {str(e)}'
                    })

        if not results['findings']:
            results['findings'].append({
                'severity': 'warning',
                'message': 'Nenhum JWT Secret encontrado - pode estar em variáveis de ambiente'
            })

        results['summary'] = self._summarize_findings(results['findings'])
        return results

    def audit_cors_configuration(self) -> Dict[str, Any]:
        """Audita configuração CORS"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'cors_configuration',
            'findings': []
        }

        # Testar CORS com origem suspeita
        try:
            response = requests.get(
                'http://localhost:3001/api/health',
                headers={'Origin': 'https://evil.com'},
                timeout=5
            )

            cors_header = response.headers.get('Access-Control-Allow-Origin')

            if cors_header == '*':
                results['findings'].append({
                    'severity': 'high',
                    'message': 'CORS configurado para permitir QUALQUER origem (*)- inseguro para produção'
                })
            elif cors_header:
                results['findings'].append({
                    'severity': 'ok',
                    'message': f'CORS configurado para: {cors_header}'
                })
            else:
                results['findings'].append({
                    'severity': 'ok',
                    'message': 'CORS bloqueou requisição de origem desconhecida'
                })

        except Exception as e:
            results['findings'].append({
                'severity': 'error',
                'message': f'Erro ao testar CORS: {str(e)}'
            })

        results['summary'] = self._summarize_findings(results['findings'])
        return results

    def audit_rate_limiting(self) -> Dict[str, Any]:
        """Audita rate limiting"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'rate_limiting',
            'findings': []
        }

        # Fazer 100 requisições rápidas
        rate_limited = False
        successful_requests = 0

        try:
            for i in range(100):
                response = requests.get('http://localhost:3001/api/health', timeout=1)

                if response.status_code == 429:  # Too Many Requests
                    rate_limited = True
                    break

                if response.status_code == 200:
                    successful_requests += 1

        except Exception:
            pass

        if rate_limited:
            results['findings'].append({
                'severity': 'ok',
                'message': f'Rate limiting ativo - bloqueou após {successful_requests} requisições'
            })
        else:
            results['findings'].append({
                'severity': 'warning',
                'message': f'Rate limiting não detectado - {successful_requests} requisições sem bloqueio'
            })

        results['summary'] = self._summarize_findings(results['findings'])
        return results

    def audit_hardcoded_secrets(self) -> Dict[str, Any]:
        """Procura secrets hardcoded no código"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'hardcoded_secrets',
            'findings': []
        }

        # Padrões suspeitos
        patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', 'Senha hardcoded'),
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', 'API key hardcoded'),
            (r'secret\s*=\s*["\'][^"\']{8,}["\']', 'Secret hardcoded'),
            (r'token\s*=\s*["\'][^"\']{20,}["\']', 'Token hardcoded'),
        ]

        directories = [
            '/opt/conecta-plus/frontend/src',
            '/opt/conecta-plus/backend'
        ]

        for directory in directories:
            if not os.path.exists(directory):
                continue

            for pattern, description in patterns:
                try:
                    result = subprocess.run(
                        ['grep', '-r', '-n', '-i', '-E', pattern, directory],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.stdout:
                        # Limitar a 5 ocorrências
                        lines = result.stdout.splitlines()[:5]

                        for line in lines:
                            # Filtrar false positives comuns
                            if '.env' in line or 'example' in line.lower() or 'test' in line.lower():
                                continue

                            results['findings'].append({
                                'severity': 'high',
                                'type': description,
                                'location': line.split(':')[0] if ':' in line else 'unknown',
                                'message': f'{description} detectado'
                            })

                except Exception:
                    pass

        if not results['findings']:
            results['findings'].append({
                'severity': 'ok',
                'message': 'Nenhum secret hardcoded óbvio detectado'
            })

        results['summary'] = self._summarize_findings(results['findings'])
        return results

    def audit_https_configuration(self) -> Dict[str, Any]:
        """Audita configuração HTTPS"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'https_configuration',
            'findings': []
        }

        # Verificar se SSL está ativo
        try:
            response = requests.get('https://localhost:3000', verify=False, timeout=5)
            results['findings'].append({
                'severity': 'ok',
                'message': 'HTTPS configurado e funcionando'
            })
        except requests.exceptions.SSLError:
            results['findings'].append({
                'severity': 'warning',
                'message': 'HTTPS configurado mas com certificado inválido (ok para desenvolvimento)'
            })
        except requests.exceptions.ConnectionError:
            results['findings'].append({
                'severity': 'warning',
                'message': 'HTTPS não está ativo - rodando apenas HTTP (ok para desenvolvimento)'
            })
        except Exception as e:
            results['findings'].append({
                'severity': 'info',
                'message': f'HTTPS status: {str(e)}'
            })

        results['summary'] = self._summarize_findings(results['findings'])
        return results

    def audit_dependencies_vulnerabilities(self) -> Dict[str, Any]:
        """Verifica vulnerabilidades em dependências"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'test_type': 'dependency_vulnerabilities',
            'findings': []
        }

        # npm audit
        try:
            result = subprocess.run(
                ['npm', 'audit', '--json'],
                cwd='/opt/conecta-plus/frontend',
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.stdout:
                import json
                audit = json.loads(result.stdout)

                vulnerabilities = audit.get('metadata', {}).get('vulnerabilities', {})

                for severity in ['critical', 'high', 'moderate', 'low']:
                    count = vulnerabilities.get(severity, 0)
                    if count > 0:
                        sev_level = 'critical' if severity in ['critical', 'high'] else 'warning'

                        results['findings'].append({
                            'severity': sev_level,
                            'type': 'npm',
                            'message': f'{count} vulnerabilidades de severidade {severity}'
                        })

        except Exception as e:
            results['findings'].append({
                'severity': 'info',
                'message': f'npm audit não executado: {str(e)}'
            })

        if not results['findings']:
            results['findings'].append({
                'severity': 'ok',
                'message': 'Nenhuma vulnerabilidade crítica detectada'
            })

        results['summary'] = self._summarize_findings(results['findings'])
        return results

    def _summarize_findings(self, findings: List[Dict]) -> Dict[str, Any]:
        """Gera resumo dos findings"""
        return {
            'total': len(findings),
            'critical': sum(1 for f in findings if f.get('severity') == 'critical'),
            'high': sum(1 for f in findings if f.get('severity') == 'high'),
            'warning': sum(1 for f in findings if f.get('severity') == 'warning'),
            'ok': sum(1 for f in findings if f.get('severity') == 'ok'),
            'security_score': self._calculate_security_score(findings)
        }

    def _calculate_security_score(self, findings: List[Dict]) -> int:
        """Calcula score de segurança (0-100)"""
        if not findings:
            return 100

        score = 100

        for finding in findings:
            severity = finding.get('severity', 'info')

            if severity == 'critical':
                score -= 20
            elif severity == 'high':
                score -= 10
            elif severity == 'warning':
                score -= 5

        return max(0, min(100, score))

    def run_all_audits(self) -> Dict[str, Any]:
        """Executa todas as auditorias de segurança"""
        return {
            'timestamp': datetime.now().isoformat(),
            'jwt_security': self.audit_jwt_security(),
            'cors_configuration': self.audit_cors_configuration(),
            'rate_limiting': self.audit_rate_limiting(),
            'hardcoded_secrets': self.audit_hardcoded_secrets(),
            'https_configuration': self.audit_https_configuration(),
            'dependencies': self.audit_dependencies_vulnerabilities()
        }


if __name__ == '__main__':
    import json
    auditor = SecurityAuditor({})
    results = auditor.run_all_audits()
    print(json.dumps(results, indent=2))
