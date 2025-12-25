"""
Skill: Network Monitor
Monitora conectividade, latência, DNS, SSL, portas abertas
"""

import subprocess
import socket
import ssl
from typing import Dict, Any, List
from datetime import datetime, timedelta
import requests


class NetworkMonitor:
    """Monitora rede e conectividade"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def check_internet_connectivity(self) -> Dict[str, Any]:
        """Verifica conectividade com internet"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'connected': False,
            'latency_ms': None,
            'issues': []
        }

        # Tentar ping em servidores conhecidos
        servers = [
            ('8.8.8.8', 'Google DNS'),
            ('1.1.1.1', 'Cloudflare DNS'),
            ('208.67.222.222', 'OpenDNS')
        ]

        successful_pings = 0

        for server_ip, server_name in servers:
            try:
                ping_result = subprocess.run(
                    ['ping', '-c', '1', '-W', '2', server_ip],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if ping_result.returncode == 0:
                    successful_pings += 1

                    # Extrair latência
                    for line in ping_result.stdout.split('\n'):
                        if 'time=' in line:
                            try:
                                latency = float(line.split('time=')[1].split()[0])
                                if result['latency_ms'] is None or latency < result['latency_ms']:
                                    result['latency_ms'] = round(latency, 2)
                            except:
                                pass

            except Exception:
                pass

        if successful_pings > 0:
            result['connected'] = True
            result['servers_reachable'] = successful_pings

            if result['latency_ms'] and result['latency_ms'] > 100:
                result['issues'].append({
                    'severity': 'warning',
                    'message': f'Latência alta: {result["latency_ms"]}ms'
                })
        else:
            result['issues'].append({
                'severity': 'critical',
                'message': 'Nenhum servidor externo alcançável - possível problema de rede'
            })

        return result

    def check_dns_resolution(self) -> Dict[str, Any]:
        """Verifica resolução DNS"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'dns_working': False,
            'resolutions': [],
            'issues': []
        }

        test_domains = [
            'google.com',
            'github.com',
            'cloudflare.com'
        ]

        successful_resolutions = 0

        for domain in test_domains:
            try:
                import time
                start = time.time()
                addr_info = socket.getaddrinfo(domain, 80)
                resolution_time = (time.time() - start) * 1000  # ms

                if addr_info:
                    successful_resolutions += 1
                    result['resolutions'].append({
                        'domain': domain,
                        'resolved': True,
                        'time_ms': round(resolution_time, 2),
                        'ip': addr_info[0][4][0]
                    })

                    if resolution_time > 500:
                        result['issues'].append({
                            'severity': 'warning',
                            'message': f'DNS lento para {domain}: {resolution_time:.2f}ms'
                        })

            except socket.gaierror:
                result['resolutions'].append({
                    'domain': domain,
                    'resolved': False,
                    'error': 'DNS resolution failed'
                })

                result['issues'].append({
                    'severity': 'high',
                    'message': f'Falha ao resolver {domain}'
                })

            except Exception as e:
                result['resolutions'].append({
                    'domain': domain,
                    'resolved': False,
                    'error': str(e)
                })

        if successful_resolutions > 0:
            result['dns_working'] = True
        else:
            result['issues'].append({
                'severity': 'critical',
                'message': 'DNS não está funcionando - nenhum domínio resolvido'
            })

        return result

    def check_ssl_certificate(self, hostname: str, port: int = 443) -> Dict[str, Any]:
        """Verifica certificado SSL de um servidor"""
        result = {
            'hostname': hostname,
            'port': port,
            'timestamp': datetime.now().isoformat(),
            'valid': False,
            'details': {},
            'issues': []
        }

        try:
            context = ssl.create_default_context()

            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert()

                    # Informações do certificado
                    result['details']['subject'] = dict(x[0] for x in cert.get('subject', []))
                    result['details']['issuer'] = dict(x[0] for x in cert.get('issuer', []))
                    result['details']['version'] = cert.get('version')

                    # Verificar validade
                    not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
                    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')

                    now = datetime.now()

                    result['details']['valid_from'] = not_before.isoformat()
                    result['details']['valid_until'] = not_after.isoformat()

                    days_until_expiry = (not_after - now).days
                    result['details']['days_until_expiry'] = days_until_expiry

                    if now >= not_before and now <= not_after:
                        result['valid'] = True

                        # Alertar se expira em menos de 30 dias
                        if days_until_expiry < 30:
                            result['issues'].append({
                                'severity': 'high',
                                'message': f'Certificado expira em {days_until_expiry} dias'
                            })
                        elif days_until_expiry < 60:
                            result['issues'].append({
                                'severity': 'warning',
                                'message': f'Certificado expira em {days_until_expiry} dias'
                            })
                    else:
                        result['issues'].append({
                            'severity': 'critical',
                            'message': 'Certificado SSL expirado ou ainda não válido'
                        })

        except ssl.SSLError as e:
            result['issues'].append({
                'severity': 'critical',
                'message': f'Erro SSL: {str(e)}'
            })
        except socket.timeout:
            result['issues'].append({
                'severity': 'high',
                'message': 'Timeout ao conectar'
            })
        except Exception as e:
            result['issues'].append({
                'severity': 'high',
                'message': f'Erro ao verificar SSL: {str(e)}'
            })

        return result

    def check_open_ports(self) -> Dict[str, Any]:
        """Verifica portas abertas importantes"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'ports': [],
            'issues': []
        }

        # Portas importantes do Conecta Plus
        important_ports = [
            (80, 'HTTP', 'nginx'),
            (443, 'HTTPS', 'nginx'),
            (3000, 'Frontend', 'frontend'),
            (3001, 'API Gateway', 'api-gateway'),
            (5432, 'PostgreSQL', 'postgres'),
            (6379, 'Redis', 'redis'),
            (27017, 'MongoDB', 'mongodb'),
            (8000, 'Backend API', 'backend'),
            (8888, 'Monitor Dashboard', 'monitor')
        ]

        for port, service, component in important_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result_code = sock.connect_ex(('localhost', port))
                sock.close()

                port_open = (result_code == 0)

                result['ports'].append({
                    'port': port,
                    'service': service,
                    'component': component,
                    'open': port_open,
                    'status': 'listening' if port_open else 'closed'
                })

                # Alertar se porta crítica está fechada
                if not port_open and port in [80, 443, 3001, 5432]:
                    result['issues'].append({
                        'severity': 'critical',
                        'message': f'Porta crítica {port} ({service}) está fechada'
                    })

            except Exception as e:
                result['ports'].append({
                    'port': port,
                    'service': service,
                    'component': component,
                    'open': False,
                    'error': str(e)
                })

        return result

    def check_external_api_health(self) -> Dict[str, Any]:
        """Verifica saúde de APIs externas/endpoints"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'endpoints': [],
            'issues': []
        }

        # Endpoints para testar
        endpoints = [
            ('http://localhost/api/health', 'API Gateway Health'),
            ('http://localhost:3001/api/health', 'Backend API Health'),
            ('http://localhost:8000/health', 'Backend Python API Health'),
            ('http://localhost:8888', 'Monitor Dashboard')
        ]

        for url, name in endpoints:
            endpoint_result = {
                'url': url,
                'name': name,
                'reachable': False,
                'response_time_ms': None,
                'status_code': None
            }

            try:
                import time
                start = time.time()
                response = requests.get(url, timeout=5, verify=False)
                response_time = (time.time() - start) * 1000

                endpoint_result['reachable'] = True
                endpoint_result['response_time_ms'] = round(response_time, 2)
                endpoint_result['status_code'] = response.status_code

                if response.status_code >= 500:
                    result['issues'].append({
                        'severity': 'high',
                        'message': f'{name}: Erro 5xx - {response.status_code}'
                    })
                elif response.status_code >= 400:
                    result['issues'].append({
                        'severity': 'warning',
                        'message': f'{name}: Erro 4xx - {response.status_code}'
                    })

                if response_time > 1000:
                    result['issues'].append({
                        'severity': 'warning',
                        'message': f'{name}: Resposta lenta ({response_time:.2f}ms)'
                    })

            except requests.exceptions.Timeout:
                endpoint_result['error'] = 'Timeout'
                result['issues'].append({
                    'severity': 'high',
                    'message': f'{name}: Timeout'
                })
            except requests.exceptions.ConnectionError:
                endpoint_result['error'] = 'Connection refused'
                result['issues'].append({
                    'severity': 'critical',
                    'message': f'{name}: Não acessível'
                })
            except Exception as e:
                endpoint_result['error'] = str(e)

            result['endpoints'].append(endpoint_result)

        return result

    def run_full_check(self) -> Dict[str, Any]:
        """Executa verificação completa de rede"""
        return {
            'timestamp': datetime.now().isoformat(),
            'internet_connectivity': self.check_internet_connectivity(),
            'dns_resolution': self.check_dns_resolution(),
            'open_ports': self.check_open_ports(),
            'external_apis': self.check_external_api_health()
        }


if __name__ == '__main__':
    monitor = NetworkMonitor({})
    results = monitor.run_full_check()

    import json
    print(json.dumps(results, indent=2))
