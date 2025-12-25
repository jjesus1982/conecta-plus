"""
Skill: Database Performance Monitor
Monitora performance de banco de dados, queries lentas, deadlocks, índices
"""

import subprocess
import json
from typing import Dict, Any, List
from datetime import datetime


class DatabaseMonitor:
    """Monitora performance e saúde do banco de dados"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.slow_query_threshold = 1000  # ms

    def check_postgres_health(self) -> Dict[str, Any]:
        """Verifica saúde do PostgreSQL"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'database': 'PostgreSQL',
            'status': 'unknown',
            'metrics': {},
            'issues': []
        }

        try:
            # Verificar se está rodando
            status_cmd = subprocess.run(
                ['docker', 'exec', 'conecta-postgres', 'pg_isready'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if status_cmd.returncode == 0:
                results['status'] = 'healthy'
            else:
                results['status'] = 'unhealthy'
                results['issues'].append({
                    'severity': 'critical',
                    'message': 'PostgreSQL não está aceitando conexões'
                })
                return results

            # Número de conexões ativas
            conn_query = """SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"""
            conn_result = subprocess.run(
                ['docker', 'exec', 'conecta-postgres', 'psql', '-U', 'postgres', '-t', '-c', conn_query],
                capture_output=True,
                text=True,
                timeout=5
            )

            if conn_result.returncode == 0:
                active_connections = int(conn_result.stdout.strip())
                results['metrics']['active_connections'] = active_connections

                if active_connections > 100:
                    results['issues'].append({
                        'severity': 'warning',
                        'message': f'Número alto de conexões ativas: {active_connections}'
                    })

            # Tamanho do banco de dados
            size_query = """SELECT pg_database_size('postgres');"""
            size_result = subprocess.run(
                ['docker', 'exec', 'conecta-postgres', 'psql', '-U', 'postgres', '-t', '-c', size_query],
                capture_output=True,
                text=True,
                timeout=5
            )

            if size_result.returncode == 0:
                db_size_bytes = int(size_result.stdout.strip())
                db_size_mb = db_size_bytes / (1024 * 1024)
                results['metrics']['database_size_mb'] = round(db_size_mb, 2)

            # Verificar locks e deadlocks
            locks_query = """SELECT count(*) FROM pg_locks WHERE NOT granted;"""
            locks_result = subprocess.run(
                ['docker', 'exec', 'conecta-postgres', 'psql', '-U', 'postgres', '-t', '-c', locks_query],
                capture_output=True,
                text=True,
                timeout=5
            )

            if locks_result.returncode == 0:
                blocked_locks = int(locks_result.stdout.strip())
                results['metrics']['blocked_locks'] = blocked_locks

                if blocked_locks > 5:
                    results['issues'].append({
                        'severity': 'high',
                        'message': f'Deadlocks detectados: {blocked_locks} queries bloqueadas'
                    })

            # Cache hit ratio
            cache_query = """
            SELECT
                round(100.0 * sum(blks_hit) / NULLIF(sum(blks_hit + blks_read), 0), 2) as cache_hit_ratio
            FROM pg_stat_database;
            """
            cache_result = subprocess.run(
                ['docker', 'exec', 'conecta-postgres', 'psql', '-U', 'postgres', '-t', '-c', cache_query],
                capture_output=True,
                text=True,
                timeout=5
            )

            if cache_result.returncode == 0 and cache_result.stdout.strip():
                try:
                    cache_hit_ratio = float(cache_result.stdout.strip())
                    results['metrics']['cache_hit_ratio'] = cache_hit_ratio

                    if cache_hit_ratio < 90:
                        results['issues'].append({
                            'severity': 'warning',
                            'message': f'Cache hit ratio baixo: {cache_hit_ratio}% (ideal >95%)'
                        })
                except ValueError:
                    pass

        except subprocess.TimeoutExpired:
            results['status'] = 'timeout'
            results['issues'].append({
                'severity': 'critical',
                'message': 'Timeout ao consultar PostgreSQL'
            })
        except Exception as e:
            results['status'] = 'error'
            results['issues'].append({
                'severity': 'critical',
                'message': f'Erro ao monitorar PostgreSQL: {str(e)}'
            })

        return results

    def check_redis_health(self) -> Dict[str, Any]:
        """Verifica saúde do Redis"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'database': 'Redis',
            'status': 'unknown',
            'metrics': {},
            'issues': []
        }

        try:
            # PING
            ping_result = subprocess.run(
                ['docker', 'exec', 'conecta-redis', 'redis-cli', 'PING'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if 'PONG' in ping_result.stdout:
                results['status'] = 'healthy'
            else:
                results['status'] = 'unhealthy'
                results['issues'].append({
                    'severity': 'critical',
                    'message': 'Redis não está respondendo'
                })
                return results

            # Memória usada
            info_result = subprocess.run(
                ['docker', 'exec', 'conecta-redis', 'redis-cli', 'INFO', 'memory'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if info_result.returncode == 0:
                for line in info_result.stdout.split('\n'):
                    if line.startswith('used_memory_human:'):
                        results['metrics']['memory_used'] = line.split(':')[1].strip()
                    elif line.startswith('used_memory_peak_human:'):
                        results['metrics']['memory_peak'] = line.split(':')[1].strip()

            # Número de chaves
            dbsize_result = subprocess.run(
                ['docker', 'exec', 'conecta-redis', 'redis-cli', 'DBSIZE'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if dbsize_result.returncode == 0:
                keys_count = int(dbsize_result.stdout.strip().split()[-1])
                results['metrics']['keys_count'] = keys_count

            # Connected clients
            clients_result = subprocess.run(
                ['docker', 'exec', 'conecta-redis', 'redis-cli', 'CLIENT', 'LIST'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if clients_result.returncode == 0:
                connected_clients = len(clients_result.stdout.strip().split('\n'))
                results['metrics']['connected_clients'] = connected_clients

        except Exception as e:
            results['status'] = 'error'
            results['issues'].append({
                'severity': 'high',
                'message': f'Erro ao monitorar Redis: {str(e)}'
            })

        return results

    def check_mongodb_health(self) -> Dict[str, Any]:
        """Verifica saúde do MongoDB"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'database': 'MongoDB',
            'status': 'unknown',
            'metrics': {},
            'issues': []
        }

        try:
            # Server status
            status_cmd = subprocess.run(
                ['docker', 'exec', 'conecta-mongodb', 'mongosh', '--quiet', '--eval',
                 'JSON.stringify(db.serverStatus())'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if status_cmd.returncode == 0:
                try:
                    status_data = json.loads(status_cmd.stdout)
                    results['status'] = 'healthy'

                    # Conexões
                    if 'connections' in status_data:
                        results['metrics']['current_connections'] = status_data['connections'].get('current', 0)
                        results['metrics']['available_connections'] = status_data['connections'].get('available', 0)

                    # Memória
                    if 'mem' in status_data:
                        results['metrics']['memory_resident_mb'] = status_data['mem'].get('resident', 0)
                        results['metrics']['memory_virtual_mb'] = status_data['mem'].get('virtual', 0)

                except json.JSONDecodeError:
                    results['status'] = 'error'
                    results['issues'].append({
                        'severity': 'warning',
                        'message': 'Erro ao parsear status do MongoDB'
                    })

            # Database stats
            dbstats_cmd = subprocess.run(
                ['docker', 'exec', 'conecta-mongodb', 'mongosh', '--quiet', '--eval',
                 'JSON.stringify(db.stats())'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if dbstats_cmd.returncode == 0:
                try:
                    db_stats = json.loads(dbstats_cmd.stdout)
                    results['metrics']['collections'] = db_stats.get('collections', 0)
                    results['metrics']['data_size_mb'] = round(db_stats.get('dataSize', 0) / (1024 * 1024), 2)
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            results['status'] = 'error'
            results['issues'].append({
                'severity': 'high',
                'message': f'Erro ao monitorar MongoDB: {str(e)}'
            })

        return results

    def check_all_databases(self) -> Dict[str, Any]:
        """Verifica todos os bancos de dados"""
        return {
            'timestamp': datetime.now().isoformat(),
            'postgres': self.check_postgres_health(),
            'redis': self.check_redis_health(),
            'mongodb': self.check_mongodb_health()
        }


if __name__ == '__main__':
    monitor = DatabaseMonitor({})
    results = monitor.check_all_databases()
    print(json.dumps(results, indent=2))
