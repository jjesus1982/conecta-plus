"""
Skill: Cache Effectiveness Monitor
Monitora efetividade de cache (Redis), hit ratio, memory usage
"""

import subprocess
import json
from typing import Dict, Any
from datetime import datetime


class CacheMonitor:
    """Monitora cache Redis"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def get_redis_info(self) -> Dict[str, Any]:
        """Coleta informações detalhadas do Redis"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'available': False,
            'metrics': {},
            'issues': []
        }

        try:
            # INFO command
            info_cmd = subprocess.run(
                ['docker', 'exec', 'conecta-redis', 'redis-cli', 'INFO'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if info_cmd.returncode != 0:
                result['issues'].append({
                    'severity': 'critical',
                    'message': 'Redis não está respondendo'
                })
                return result

            result['available'] = True

            # Parse INFO output
            info_data = {}
            for line in info_cmd.stdout.split('\n'):
                if ':' in line and not line.startswith('#'):
                    key, value = line.split(':', 1)
                    info_data[key.strip()] = value.strip()

            # Métricas de memória
            if 'used_memory_human' in info_data:
                result['metrics']['memory_used'] = info_data['used_memory_human']

            if 'used_memory_peak_human' in info_data:
                result['metrics']['memory_peak'] = info_data['used_memory_peak_human']

            if 'maxmemory_human' in info_data:
                result['metrics']['memory_limit'] = info_data['maxmemory_human']

            if 'used_memory_rss_human' in info_data:
                result['metrics']['memory_rss'] = info_data['used_memory_rss_human']

            # Fragmentação de memória
            if 'mem_fragmentation_ratio' in info_data:
                frag_ratio = float(info_data['mem_fragmentation_ratio'])
                result['metrics']['fragmentation_ratio'] = frag_ratio

                if frag_ratio > 1.5:
                    result['issues'].append({
                        'severity': 'warning',
                        'message': f'Alta fragmentação de memória: {frag_ratio:.2f}'
                    })

            # Estatísticas de cache hit/miss
            if 'keyspace_hits' in info_data and 'keyspace_misses' in info_data:
                hits = int(info_data['keyspace_hits'])
                misses = int(info_data['keyspace_misses'])

                total = hits + misses

                if total > 0:
                    hit_rate = (hits / total) * 100
                    result['metrics']['cache_hit_rate'] = round(hit_rate, 2)
                    result['metrics']['total_hits'] = hits
                    result['metrics']['total_misses'] = misses

                    if hit_rate < 80:
                        result['issues'].append({
                            'severity': 'warning',
                            'message': f'Cache hit rate baixo: {hit_rate:.2f}% (ideal >90%)'
                        })

            # Número de chaves
            dbsize_cmd = subprocess.run(
                ['docker', 'exec', 'conecta-redis', 'redis-cli', 'DBSIZE'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if dbsize_cmd.returncode == 0:
                try:
                    keys_count = int(dbsize_cmd.stdout.strip().split()[-1])
                    result['metrics']['keys_count'] = keys_count
                except:
                    pass

            # Connected clients
            if 'connected_clients' in info_data:
                result['metrics']['connected_clients'] = int(info_data['connected_clients'])

            # Uptime
            if 'uptime_in_seconds' in info_data:
                uptime_seconds = int(info_data['uptime_in_seconds'])
                uptime_days = uptime_seconds / (60 * 60 * 24)
                result['metrics']['uptime_days'] = round(uptime_days, 2)

            # Evicted keys (keys removidas por falta de memória)
            if 'evicted_keys' in info_data:
                evicted = int(info_data['evicted_keys'])
                result['metrics']['evicted_keys'] = evicted

                if evicted > 1000:
                    result['issues'].append({
                        'severity': 'high',
                        'message': f'{evicted} keys evicted - memória insuficiente'
                    })
                elif evicted > 100:
                    result['issues'].append({
                        'severity': 'warning',
                        'message': f'{evicted} keys evicted - considere aumentar memória'
                    })

            # Expired keys
            if 'expired_keys' in info_data:
                result['metrics']['expired_keys'] = int(info_data['expired_keys'])

            # RDB save status
            if 'rdb_last_save_time' in info_data:
                last_save = int(info_data['rdb_last_save_time'])
                now = datetime.now().timestamp()
                hours_since_save = (now - last_save) / 3600

                result['metrics']['hours_since_last_save'] = round(hours_since_save, 2)

                if hours_since_save > 24:
                    result['issues'].append({
                        'severity': 'warning',
                        'message': f'Redis não fez save há {int(hours_since_save)} horas'
                    })

            # Verificar se persistence está habilitada
            if 'rdb_bgsave_in_progress' in info_data:
                result['metrics']['save_in_progress'] = bool(int(info_data['rdb_bgsave_in_progress']))

        except subprocess.TimeoutExpired:
            result['issues'].append({
                'severity': 'high',
                'message': 'Timeout ao consultar Redis'
            })
        except Exception as e:
            result['issues'].append({
                'severity': 'high',
                'message': f'Erro ao monitorar Redis: {str(e)}'
            })

        return result

    def check_cache_keys_distribution(self) -> Dict[str, Any]:
        """Verifica distribuição de chaves no cache"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'key_patterns': {},
            'issues': []
        }

        try:
            # Pegar sample de keys
            keys_cmd = subprocess.run(
                ['docker', 'exec', 'conecta-redis', 'redis-cli', '--scan', '--count', '100'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if keys_cmd.returncode == 0:
                keys = keys_cmd.stdout.strip().split('\n')
                result['sample_size'] = len(keys)

                # Agrupar por prefixo
                prefixes = {}
                for key in keys:
                    if ':' in key:
                        prefix = key.split(':')[0]
                        prefixes[prefix] = prefixes.get(prefix, 0) + 1

                result['key_patterns'] = prefixes

                # Verificar se tem chaves sem namespace
                keys_without_namespace = sum(1 for k in keys if ':' not in k)
                if keys_without_namespace > 0:
                    result['issues'].append({
                        'severity': 'low',
                        'message': f'{keys_without_namespace} chaves sem namespace (use prefixos)'
                    })

        except Exception as e:
            result['issues'].append({
                'severity': 'warning',
                'message': f'Erro ao analisar keys: {str(e)}'
            })

        return result

    def check_slow_log(self) -> Dict[str, Any]:
        """Verifica slow log do Redis"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'slow_commands': [],
            'issues': []
        }

        try:
            slowlog_cmd = subprocess.run(
                ['docker', 'exec', 'conecta-redis', 'redis-cli', 'SLOWLOG', 'GET', '10'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if slowlog_cmd.returncode == 0:
                # Parse slowlog output (formato: array de arrays)
                lines = slowlog_cmd.stdout.strip().split('\n')

                # Contar comandos
                result['slow_command_count'] = len([l for l in lines if l.strip().isdigit() and int(l) < 1000])

                if result['slow_command_count'] > 5:
                    result['issues'].append({
                        'severity': 'warning',
                        'message': f'{result["slow_command_count"]} comandos lentos detectados'
                    })

        except Exception as e:
            result['issues'].append({
                'severity': 'info',
                'message': f'Erro ao verificar slowlog: {str(e)}'
            })

        return result

    def run_full_check(self) -> Dict[str, Any]:
        """Executa verificação completa do cache"""
        return {
            'timestamp': datetime.now().isoformat(),
            'redis_info': self.get_redis_info(),
            'key_distribution': self.check_cache_keys_distribution(),
            'slow_log': self.check_slow_log()
        }


if __name__ == '__main__':
    monitor = CacheMonitor({})
    results = monitor.run_full_check()
    print(json.dumps(results, indent=2))
