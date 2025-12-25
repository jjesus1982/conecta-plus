"""
Skill: Backup & Recovery Validator
Valida backups, testa restore, verifica integridade
"""

import os
import subprocess
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from pathlib import Path


class BackupValidator:
    """Valida backups e disaster recovery"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.backup_dirs = [
            '/opt/conecta-plus/backups',
            '/var/backups/conecta-plus',
            '/backup/conecta-plus'
        ]

    def check_backup_directories(self) -> Dict[str, Any]:
        """Verifica diretórios de backup"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'directories': [],
            'issues': []
        }

        for backup_dir in self.backup_dirs:
            dir_info = {
                'path': backup_dir,
                'exists': False,
                'writable': False,
                'size_mb': 0,
                'file_count': 0
            }

            if os.path.exists(backup_dir):
                dir_info['exists'] = True
                dir_info['writable'] = os.access(backup_dir, os.W_OK)

                try:
                    # Contar arquivos
                    files = list(Path(backup_dir).rglob('*'))
                    dir_info['file_count'] = len([f for f in files if f.is_file()])

                    # Tamanho total
                    size_cmd = subprocess.run(
                        ['du', '-sm', backup_dir],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if size_cmd.returncode == 0:
                        dir_info['size_mb'] = int(size_cmd.stdout.split()[0])

                except Exception as e:
                    dir_info['error'] = str(e)

                if not dir_info['writable']:
                    result['issues'].append({
                        'severity': 'high',
                        'message': f'{backup_dir} não tem permissão de escrita'
                    })

            else:
                result['issues'].append({
                    'severity': 'warning',
                    'message': f'Diretório de backup não existe: {backup_dir}'
                })

            result['directories'].append(dir_info)

        # Se nenhum diretório existe
        if not any(d['exists'] for d in result['directories']):
            result['issues'].append({
                'severity': 'critical',
                'message': 'Nenhum diretório de backup configurado'
            })

        return result

    def check_database_backups(self) -> Dict[str, Any]:
        """Verifica backups de banco de dados"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'postgres_backups': [],
            'mongodb_backups': [],
            'issues': []
        }

        # Procurar backups PostgreSQL
        for backup_dir in self.backup_dirs:
            if not os.path.exists(backup_dir):
                continue

            # Procurar arquivos .sql ou .dump
            try:
                pg_backups = list(Path(backup_dir).glob('**/*.sql'))
                pg_backups += list(Path(backup_dir).glob('**/*.dump'))
                pg_backups += list(Path(backup_dir).glob('**/postgres*.tar.gz'))

                for backup_file in pg_backups:
                    file_info = {
                        'file': str(backup_file),
                        'size_mb': round(backup_file.stat().st_size / (1024 * 1024), 2),
                        'age_hours': round(
                            (datetime.now().timestamp() - backup_file.stat().st_mtime) / 3600,
                            2
                        )
                    }
                    result['postgres_backups'].append(file_info)

                # Procurar backups MongoDB
                mongo_backups = list(Path(backup_dir).glob('**/mongodb*.tar.gz'))
                mongo_backups += list(Path(backup_dir).glob('**/mongo*.bson'))

                for backup_file in mongo_backups:
                    file_info = {
                        'file': str(backup_file),
                        'size_mb': round(backup_file.stat().st_size / (1024 * 1024), 2),
                        'age_hours': round(
                            (datetime.now().timestamp() - backup_file.stat().st_mtime) / 3600,
                            2
                        )
                    }
                    result['mongodb_backups'].append(file_info)

            except Exception as e:
                result['issues'].append({
                    'severity': 'warning',
                    'message': f'Erro ao procurar backups em {backup_dir}: {str(e)}'
                })

        # Verificar se tem backups recentes (últimas 24h)
        recent_pg = [b for b in result['postgres_backups'] if b['age_hours'] < 24]
        recent_mongo = [b for b in result['mongodb_backups'] if b['age_hours'] < 24]

        if not recent_pg:
            result['issues'].append({
                'severity': 'high',
                'message': 'Nenhum backup PostgreSQL nas últimas 24 horas'
            })

        if not recent_mongo and result['mongodb_backups']:
            result['issues'].append({
                'severity': 'warning',
                'message': 'Nenhum backup MongoDB nas últimas 24 horas'
            })

        # Alertar se backups muito antigos
        for backup in result['postgres_backups']:
            if backup['age_hours'] > 168:  # 7 dias
                result['issues'].append({
                    'severity': 'warning',
                    'message': f'Backup antigo: {os.path.basename(backup["file"])} ({int(backup["age_hours"]/24)} dias)'
                })

        return result

    def check_backup_automation(self) -> Dict[str, Any]:
        """Verifica se backups automáticos estão configurados"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'cron_jobs': [],
            'systemd_timers': [],
            'issues': []
        }

        # Verificar cron jobs
        try:
            cron_cmd = subprocess.run(
                ['crontab', '-l'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if cron_cmd.returncode == 0:
                for line in cron_cmd.stdout.split('\n'):
                    if 'backup' in line.lower() and not line.strip().startswith('#'):
                        result['cron_jobs'].append(line.strip())

        except:
            pass

        # Verificar systemd timers
        try:
            timers_cmd = subprocess.run(
                ['systemctl', 'list-timers', '--all', '--no-pager'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if timers_cmd.returncode == 0:
                for line in timers_cmd.stdout.split('\n'):
                    if 'backup' in line.lower():
                        result['systemd_timers'].append(line.strip())

        except:
            pass

        # Se não tem automação
        if not result['cron_jobs'] and not result['systemd_timers']:
            result['issues'].append({
                'severity': 'critical',
                'message': 'Nenhuma automação de backup configurada (cron ou systemd timer)'
            })

        return result

    def verify_backup_script(self) -> Dict[str, Any]:
        """Verifica se script de backup existe e é executável"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'scripts': [],
            'issues': []
        }

        possible_scripts = [
            '/opt/conecta-plus/scripts/backup.sh',
            '/opt/conecta-plus/backup.sh',
            '/usr/local/bin/conecta-backup.sh'
        ]

        for script_path in possible_scripts:
            if os.path.exists(script_path):
                script_info = {
                    'path': script_path,
                    'exists': True,
                    'executable': os.access(script_path, os.X_OK),
                    'size_bytes': os.path.getsize(script_path)
                }

                if not script_info['executable']:
                    result['issues'].append({
                        'severity': 'high',
                        'message': f'Script de backup não é executável: {script_path}'
                    })

                result['scripts'].append(script_info)

        if not result['scripts']:
            result['issues'].append({
                'severity': 'warning',
                'message': 'Nenhum script de backup encontrado'
            })

        return result

    def run_full_validation(self) -> Dict[str, Any]:
        """Executa validação completa de backups"""
        return {
            'timestamp': datetime.now().isoformat(),
            'directories': self.check_backup_directories(),
            'database_backups': self.check_database_backups(),
            'automation': self.check_backup_automation(),
            'scripts': self.verify_backup_script()
        }


if __name__ == '__main__':
    validator = BackupValidator({})
    results = validator.run_full_validation()
    print(json.dumps(results, indent=2))
