"""
Skill: File System Watcher
Monitora mudanças em arquivos críticos, permissões, disk space
"""

import os
import subprocess
import hashlib
import json
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path


class FileSystemWatcher:
    """Monitora sistema de arquivos"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.critical_files = [
            '/opt/conecta-plus/backend/.env',
            '/opt/conecta-plus/frontend/.env.local',
            '/opt/conecta-plus/docker-compose.yml',
            '/etc/nginx/nginx.conf',
            '/etc/nginx/sites-enabled/conecta-plus.conf'
        ]
        self.critical_dirs = [
            '/opt/conecta-plus/backend',
            '/opt/conecta-plus/frontend',
            '/opt/conecta-plus/agents'
        ]

    def check_disk_space(self) -> Dict[str, Any]:
        """Verifica espaço em disco"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'partitions': [],
            'issues': []
        }

        try:
            df_cmd = subprocess.run(
                ['df', '-h'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if df_cmd.returncode == 0:
                lines = df_cmd.stdout.strip().split('\n')[1:]  # Pular header

                for line in lines:
                    parts = line.split()
                    if len(parts) >= 6:
                        partition = {
                            'filesystem': parts[0],
                            'size': parts[1],
                            'used': parts[2],
                            'available': parts[3],
                            'use_percent': parts[4].replace('%', ''),
                            'mounted_on': parts[5]
                        }

                        try:
                            use_pct = int(partition['use_percent'])

                            if use_pct > 90:
                                result['issues'].append({
                                    'severity': 'critical',
                                    'message': f'{partition["mounted_on"]}: {use_pct}% cheio - CRÍTICO'
                                })
                            elif use_pct > 80:
                                result['issues'].append({
                                    'severity': 'high',
                                    'message': f'{partition["mounted_on"]}: {use_pct}% cheio'
                                })
                            elif use_pct > 70:
                                result['issues'].append({
                                    'severity': 'warning',
                                    'message': f'{partition["mounted_on"]}: {use_pct}% cheio'
                                })

                        except ValueError:
                            pass

                        result['partitions'].append(partition)

        except Exception as e:
            result['issues'].append({
                'severity': 'high',
                'message': f'Erro ao verificar disco: {str(e)}'
            })

        return result

    def check_critical_files(self) -> Dict[str, Any]:
        """Verifica arquivos críticos"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'files': [],
            'issues': []
        }

        for file_path in self.critical_files:
            file_info = {
                'path': file_path,
                'exists': False,
                'readable': False,
                'writable': False,
                'size_bytes': 0
            }

            if os.path.exists(file_path):
                file_info['exists'] = True
                file_info['readable'] = os.access(file_path, os.R_OK)
                file_info['writable'] = os.access(file_path, os.W_OK)

                try:
                    stat_info = os.stat(file_path)
                    file_info['size_bytes'] = stat_info.st_size
                    file_info['permissions'] = oct(stat_info.st_mode)[-3:]
                    file_info['modified'] = datetime.fromtimestamp(stat_info.st_mtime).isoformat()

                    # Calcular hash
                    if file_info['readable'] and stat_info.st_size < 10 * 1024 * 1024:  # < 10MB
                        try:
                            with open(file_path, 'rb') as f:
                                file_hash = hashlib.md5(f.read()).hexdigest()
                            file_info['md5'] = file_hash
                        except:
                            pass

                except Exception as e:
                    file_info['error'] = str(e)

                # Alertar se não é legível
                if not file_info['readable']:
                    result['issues'].append({
                        'severity': 'high',
                        'message': f'Arquivo crítico não legível: {file_path}'
                    })

                # Alertar se arquivo .env tem permissões muito abertas
                if '.env' in file_path:
                    perms = file_info.get('permissions', '777')
                    if perms[-1] != '0':  # Outros tem permissão
                        result['issues'].append({
                            'severity': 'high',
                            'message': f'{file_path}: permissões inseguras ({perms}) - deve ser 600'
                        })

            else:
                result['issues'].append({
                    'severity': 'critical',
                    'message': f'Arquivo crítico não encontrado: {file_path}'
                })

            result['files'].append(file_info)

        return result

    def check_directory_permissions(self) -> Dict[str, Any]:
        """Verifica permissões de diretórios críticos"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'directories': [],
            'issues': []
        }

        for dir_path in self.critical_dirs:
            dir_info = {
                'path': dir_path,
                'exists': False,
                'readable': False,
                'writable': False,
                'executable': False
            }

            if os.path.exists(dir_path):
                dir_info['exists'] = True
                dir_info['readable'] = os.access(dir_path, os.R_OK)
                dir_info['writable'] = os.access(dir_path, os.W_OK)
                dir_info['executable'] = os.access(dir_path, os.X_OK)

                try:
                    stat_info = os.stat(dir_path)
                    dir_info['permissions'] = oct(stat_info.st_mode)[-3:]

                    # Contar arquivos
                    file_count = sum(1 for _ in Path(dir_path).rglob('*') if _.is_file())
                    dir_info['file_count'] = file_count

                except Exception as e:
                    dir_info['error'] = str(e)

                # Alertar se não é executável (não pode cd)
                if not dir_info['executable']:
                    result['issues'].append({
                        'severity': 'high',
                        'message': f'Diretório não executável: {dir_path}'
                    })

            else:
                result['issues'].append({
                    'severity': 'critical',
                    'message': f'Diretório crítico não encontrado: {dir_path}'
                })

            result['directories'].append(dir_info)

        return result

    def check_log_rotation(self) -> Dict[str, Any]:
        """Verifica rotação de logs"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'log_directories': [],
            'issues': []
        }

        log_dirs = [
            '/opt/conecta-plus/backend/logs',
            '/opt/conecta-plus/frontend/logs',
            '/opt/conecta-plus/agents/system-monitor/logs',
            '/var/log/nginx'
        ]

        for log_dir in log_dirs:
            if not os.path.exists(log_dir):
                continue

            dir_info = {
                'path': log_dir,
                'total_size_mb': 0,
                'file_count': 0,
                'largest_file_mb': 0
            }

            try:
                log_files = list(Path(log_dir).glob('*.log'))
                dir_info['file_count'] = len(log_files)

                total_size = 0
                largest = 0

                for log_file in log_files:
                    size = log_file.stat().st_size
                    total_size += size
                    if size > largest:
                        largest = size

                dir_info['total_size_mb'] = round(total_size / (1024 * 1024), 2)
                dir_info['largest_file_mb'] = round(largest / (1024 * 1024), 2)

                # Alertar se logs muito grandes
                if dir_info['total_size_mb'] > 1000:
                    result['issues'].append({
                        'severity': 'high',
                        'message': f'{log_dir}: {dir_info["total_size_mb"]}MB em logs - configure rotação'
                    })

                if dir_info['largest_file_mb'] > 100:
                    result['issues'].append({
                        'severity': 'warning',
                        'message': f'{log_dir}: arquivo de {dir_info["largest_file_mb"]}MB - rotacione logs'
                    })

            except Exception as e:
                dir_info['error'] = str(e)

            result['log_directories'].append(dir_info)

        # Verificar se logrotate está configurado
        logrotate_conf = '/etc/logrotate.d/conecta-plus'
        if not os.path.exists(logrotate_conf):
            result['issues'].append({
                'severity': 'warning',
                'message': 'Rotação de logs não configurada (/etc/logrotate.d/conecta-plus não existe)'
            })

        return result

    def check_temp_files(self) -> Dict[str, Any]:
        """Verifica arquivos temporários"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'temp_usage': {},
            'issues': []
        }

        temp_dirs = ['/tmp', '/var/tmp']

        for temp_dir in temp_dirs:
            if not os.path.exists(temp_dir):
                continue

            try:
                # Tamanho do /tmp
                size_cmd = subprocess.run(
                    ['du', '-sm', temp_dir],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if size_cmd.returncode == 0:
                    size_mb = int(size_cmd.stdout.split()[0])
                    result['temp_usage'][temp_dir] = size_mb

                    if size_mb > 5000:  # 5GB
                        result['issues'].append({
                            'severity': 'warning',
                            'message': f'{temp_dir}: {size_mb}MB - considere limpeza'
                        })

            except:
                pass

        return result

    def run_full_check(self) -> Dict[str, Any]:
        """Executa verificação completa do sistema de arquivos"""
        return {
            'timestamp': datetime.now().isoformat(),
            'disk_space': self.check_disk_space(),
            'critical_files': self.check_critical_files(),
            'directories': self.check_directory_permissions(),
            'log_rotation': self.check_log_rotation(),
            'temp_files': self.check_temp_files()
        }


if __name__ == '__main__':
    watcher = FileSystemWatcher({})
    results = watcher.run_full_check()
    print(json.dumps(results, indent=2))
