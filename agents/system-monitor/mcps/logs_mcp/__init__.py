"""
MCP: Logs Monitor
Tools para monitoramento e análise de logs
"""

import os
import subprocess
from typing import List, Dict, Any
from datetime import datetime, timedelta


class LogsMCP:
    """MCP para operações com logs"""

    def __init__(self):
        self.watched_files = {}

    def tail_log(self, filepath: str, lines: int = 100) -> List[str]:
        """
        Retorna últimas N linhas de um log

        Args:
            filepath: Caminho do arquivo de log
            lines: Número de linhas

        Returns:
            Lista de linhas
        """
        try:
            result = subprocess.run(
                ['tail', '-n', str(lines), filepath],
                capture_output=True,
                text=True
            )
            return result.stdout.splitlines()
        except Exception as e:
            return [f"Error reading log: {str(e)}"]

    def grep_log(self, filepath: str, pattern: str, lines: int = 100) -> List[str]:
        """
        Busca padrão em log

        Args:
            filepath: Caminho do log
            pattern: Padrão regex
            lines: Últimas N linhas para buscar

        Returns:
            Linhas que contêm o padrão
        """
        try:
            result = subprocess.run(
                ['tail', '-n', str(lines), filepath],
                capture_output=True,
                text=True
            )

            import re
            regex = re.compile(pattern, re.IGNORECASE)
            return [line for line in result.stdout.splitlines() if regex.search(line)]
        except Exception as e:
            return [f"Error grepping log: {str(e)}"]

    def watch_log(self, filepath: str) -> str:
        """
        Inicia monitoramento em tempo real de um log

        Args:
            filepath: Caminho do log

        Returns:
            ID do watcher
        """
        watcher_id = f"watcher_{len(self.watched_files)}"
        self.watched_files[watcher_id] = {
            'filepath': filepath,
            'started_at': datetime.now(),
            'last_position': os.path.getsize(filepath) if os.path.exists(filepath) else 0
        }
        return watcher_id

    def get_new_lines(self, watcher_id: str) -> List[str]:
        """
        Retorna novas linhas desde última verificação

        Args:
            watcher_id: ID do watcher

        Returns:
            Novas linhas
        """
        if watcher_id not in self.watched_files:
            return []

        watcher = self.watched_files[watcher_id]
        filepath = watcher['filepath']

        if not os.path.exists(filepath):
            return []

        current_size = os.path.getsize(filepath)
        last_position = watcher['last_position']

        if current_size < last_position:
            # Log foi rotacionado
            last_position = 0

        if current_size == last_position:
            return []

        # Ler novas linhas
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(last_position)
            new_lines = f.read().splitlines()

        # Atualizar posição
        watcher['last_position'] = current_size

        return new_lines

    def count_pattern(self, filepath: str, pattern: str, since_minutes: int = 60) -> int:
        """
        Conta ocorrências de padrão em período

        Args:
            filepath: Caminho do log
            pattern: Padrão a buscar
            since_minutes: Período em minutos

        Returns:
            Número de ocorrências
        """
        try:
            lines = self.tail_log(filepath, 10000)
            matches = self.grep_log(filepath, pattern, 10000)
            return len(matches)
        except Exception:
            return 0

    def rotate_log(self, filepath: str, max_size_mb: int = 100) -> bool:
        """
        Rotaciona log se ultrapassar tamanho máximo

        Args:
            filepath: Caminho do log
            max_size_mb: Tamanho máximo em MB

        Returns:
            True se rotacionou
        """
        try:
            if not os.path.exists(filepath):
                return False

            size_mb = os.path.getsize(filepath) / (1024 * 1024)

            if size_mb > max_size_mb:
                # Rotacionar
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = f"{filepath}.{timestamp}"

                os.rename(filepath, backup_path)

                # Comprimir backup
                subprocess.run(['gzip', backup_path], check=False)

                return True

            return False
        except Exception:
            return False


# Ferramentas disponíveis para o agente
def get_tools():
    """Retorna lista de ferramentas disponíveis"""
    mcp = LogsMCP()

    return {
        'tail_log': {
            'function': mcp.tail_log,
            'description': 'Get last N lines from a log file',
            'parameters': {
                'filepath': 'Path to log file',
                'lines': 'Number of lines (default: 100)'
            }
        },
        'grep_log': {
            'function': mcp.grep_log,
            'description': 'Search pattern in log file',
            'parameters': {
                'filepath': 'Path to log file',
                'pattern': 'Regex pattern to search',
                'lines': 'Number of lines to search (default: 100)'
            }
        },
        'watch_log': {
            'function': mcp.watch_log,
            'description': 'Start watching a log file for changes',
            'parameters': {
                'filepath': 'Path to log file'
            }
        },
        'get_new_lines': {
            'function': mcp.get_new_lines,
            'description': 'Get new lines from watched log',
            'parameters': {
                'watcher_id': 'Watcher ID from watch_log'
            }
        },
        'count_pattern': {
            'function': mcp.count_pattern,
            'description': 'Count occurrences of pattern in log',
            'parameters': {
                'filepath': 'Path to log file',
                'pattern': 'Pattern to count',
                'since_minutes': 'Period in minutes (default: 60)'
            }
        },
        'rotate_log': {
            'function': mcp.rotate_log,
            'description': 'Rotate log file if it exceeds max size',
            'parameters': {
                'filepath': 'Path to log file',
                'max_size_mb': 'Max size in MB (default: 100)'
            }
        }
    }


if __name__ == '__main__':
    # Teste
    mcp = LogsMCP()
    lines = mcp.tail_log('/tmp/nextjs-debug.log', 20)
    for line in lines:
        print(line)
