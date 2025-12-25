"""
MCP: Code Analyzer
Tools para análise de código fonte
"""

import os
import subprocess
from typing import Dict, Any, List
import re


class CodeAnalyzerMCP:
    """MCP para análise de código"""

    def __init__(self):
        self.cache = {}

    def find_files(self, directory: str, pattern: str = '*.ts') -> List[str]:
        """
        Encontra arquivos por padrão

        Args:
            directory: Diretório raiz
            pattern: Padrão de arquivo

        Returns:
            Lista de arquivos encontrados
        """
        try:
            result = subprocess.run(
                ['find', directory, '-name', pattern],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout.splitlines()
        except Exception:
            return []

    def search_code(self, directory: str, pattern: str, file_pattern: str = '*.ts') -> List[Dict[str, Any]]:
        """
        Busca padrão no código

        Args:
            directory: Diretório raiz
            pattern: Padrão regex
            file_pattern: Padrão de arquivos

        Returns:
            Lista de matches
        """
        try:
            result = subprocess.run(
                ['grep', '-rn', '-E', pattern, directory, '--include', file_pattern],
                capture_output=True,
                text=True,
                timeout=30
            )

            matches = []
            for line in result.stdout.splitlines()[:100]:  # Limitar a 100
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    matches.append({
                        'file': parts[0],
                        'line': parts[1],
                        'content': parts[2].strip()
                    })

            return matches
        except Exception:
            return []

    def count_lines(self, filepath: str) -> Dict[str, int]:
        """
        Conta linhas de um arquivo

        Args:
            filepath: Caminho do arquivo

        Returns:
            Estatísticas de linhas
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            total = len(lines)
            code = 0
            comments = 0
            blank = 0

            in_multiline_comment = False

            for line in lines:
                stripped = line.strip()

                if not stripped:
                    blank += 1
                    continue

                # Detectar comentários multiline
                if '/*' in stripped:
                    in_multiline_comment = True
                    comments += 1
                    continue

                if '*/' in stripped:
                    in_multiline_comment = False
                    comments += 1
                    continue

                if in_multiline_comment:
                    comments += 1
                    continue

                # Comentários de linha
                if stripped.startswith('//') or stripped.startswith('#'):
                    comments += 1
                    continue

                code += 1

            return {
                'total': total,
                'code': code,
                'comments': comments,
                'blank': blank,
                'ratio_comments': (comments / total * 100) if total > 0 else 0
            }

        except Exception:
            return {'total': 0, 'code': 0, 'comments': 0, 'blank': 0}

    def analyze_imports(self, filepath: str) -> Dict[str, Any]:
        """
        Analisa imports de um arquivo

        Args:
            filepath: Caminho do arquivo

        Returns:
            Análise de imports
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Detectar imports JavaScript/TypeScript
            import_pattern = r'import\s+.*?from\s+["\']([^"\']+)["\']'
            imports = re.findall(import_pattern, content)

            # Separar por tipo
            external = []
            internal = []

            for imp in imports:
                if imp.startswith('.'):
                    internal.append(imp)
                else:
                    external.append(imp)

            return {
                'total': len(imports),
                'external': external,
                'internal': internal,
                'external_count': len(external),
                'internal_count': len(internal)
            }

        except Exception:
            return {'total': 0, 'external': [], 'internal': [], 'external_count': 0, 'internal_count': 0}

    def detect_todos(self, directory: str) -> List[Dict[str, Any]]:
        """
        Detecta TODOs e FIXMEs no código

        Args:
            directory: Diretório raiz

        Returns:
            Lista de TODOs encontrados
        """
        try:
            result = subprocess.run(
                ['grep', '-rn', '-E', '(TODO|FIXME|XXX|HACK):', directory],
                capture_output=True,
                text=True,
                timeout=30
            )

            todos = []
            for line in result.stdout.splitlines()[:100]:
                parts = line.split(':', 3)
                if len(parts) >= 3:
                    match = re.search(r'(TODO|FIXME|XXX|HACK)', line, re.IGNORECASE)
                    todo_type = match.group(1) if match else 'TODO'

                    todos.append({
                        'file': parts[0],
                        'line': parts[1],
                        'type': todo_type,
                        'content': parts[2].strip() if len(parts) > 2 else ''
                    })

            return todos
        except Exception:
            return []

    def check_file_size(self, filepath: str) -> Dict[str, Any]:
        """
        Verifica tamanho de arquivo

        Args:
            filepath: Caminho do arquivo

        Returns:
            Informações de tamanho
        """
        try:
            size_bytes = os.path.getsize(filepath)
            lines = self.count_lines(filepath)

            return {
                'filepath': filepath,
                'size_bytes': size_bytes,
                'size_kb': size_bytes // 1024,
                'lines': lines['total'],
                'is_large': size_bytes > 100 * 1024,  # > 100KB
                'is_too_long': lines['total'] > 500  # > 500 lines
            }
        except Exception:
            return {'filepath': filepath, 'error': 'Could not check file'}

    def find_large_files(self, directory: str, min_kb: int = 100) -> List[Dict[str, Any]]:
        """
        Encontra arquivos grandes

        Args:
            directory: Diretório raiz
            min_kb: Tamanho mínimo em KB

        Returns:
            Lista de arquivos grandes
        """
        large_files = []

        try:
            for root, _, files in os.walk(directory):
                # Pular node_modules, .next, etc
                if 'node_modules' in root or '.next' in root or '.git' in root:
                    continue

                for file in files:
                    if file.endswith(('.ts', '.tsx', '.js', '.jsx', '.py')):
                        filepath = os.path.join(root, file)
                        info = self.check_file_size(filepath)

                        if info.get('size_kb', 0) >= min_kb:
                            large_files.append(info)

        except Exception:
            pass

        return sorted(large_files, key=lambda x: x.get('size_kb', 0), reverse=True)[:20]

    def analyze_complexity(self, filepath: str) -> Dict[str, Any]:
        """
        Analisa complexidade de código (simplificado)

        Args:
            filepath: Caminho do arquivo

        Returns:
            Métricas de complexidade
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Contar estruturas de controle (aproximação de complexidade ciclomática)
            control_structures = len(re.findall(
                r'\b(if|else|while|for|switch|case|catch)\b',
                content
            ))

            # Contar funções
            functions = len(re.findall(
                r'(function\s+\w+|const\s+\w+\s*=\s*\([^)]*\)\s*=>|\w+\s*\([^)]*\)\s*{)',
                content
            ))

            # Nesting level (aproximado)
            max_nesting = 0
            current_nesting = 0
            for char in content:
                if char == '{':
                    current_nesting += 1
                    max_nesting = max(max_nesting, current_nesting)
                elif char == '}':
                    current_nesting = max(0, current_nesting - 1)

            return {
                'filepath': filepath,
                'control_structures': control_structures,
                'functions': functions,
                'max_nesting_level': max_nesting,
                'complexity_score': control_structures + (max_nesting * 2),
                'is_complex': control_structures > 20 or max_nesting > 5
            }

        except Exception:
            return {'filepath': filepath, 'error': 'Could not analyze'}

    def get_codebase_stats(self, directory: str) -> Dict[str, Any]:
        """
        Retorna estatísticas gerais do codebase

        Args:
            directory: Diretório raiz

        Returns:
            Estatísticas completas
        """
        stats = {
            'timestamp': datetime.now().isoformat(),
            'directory': directory,
            'files_by_type': {},
            'total_lines': 0,
            'total_code_lines': 0,
            'total_files': 0,
            'large_files': [],
            'todos': []
        }

        try:
            from datetime import datetime

            # Contar arquivos por tipo
            for ext in ['.ts', '.tsx', '.js', '.jsx', '.py', '.css', '.html']:
                files = self.find_files(directory, f'*{ext}')
                stats['files_by_type'][ext] = len(files)
                stats['total_files'] += len(files)

            # TODOs
            stats['todos'] = self.detect_todos(directory)[:20]

            # Arquivos grandes
            stats['large_files'] = self.find_large_files(directory, 100)[:10]

        except Exception:
            pass

        return stats


# Ferramentas disponíveis para o agente
def get_tools():
    """Retorna lista de ferramentas disponíveis"""
    mcp = CodeAnalyzerMCP()

    return {
        'find_files': {
            'function': mcp.find_files,
            'description': 'Find files by pattern',
            'parameters': {
                'directory': 'Root directory',
                'pattern': 'File pattern (default: *.ts)'
            }
        },
        'search_code': {
            'function': mcp.search_code,
            'description': 'Search pattern in code',
            'parameters': {
                'directory': 'Root directory',
                'pattern': 'Regex pattern',
                'file_pattern': 'File pattern (default: *.ts)'
            }
        },
        'count_lines': {
            'function': mcp.count_lines,
            'description': 'Count lines in a file',
            'parameters': {
                'filepath': 'File path'
            }
        },
        'analyze_imports': {
            'function': mcp.analyze_imports,
            'description': 'Analyze imports in a file',
            'parameters': {
                'filepath': 'File path'
            }
        },
        'detect_todos': {
            'function': mcp.detect_todos,
            'description': 'Detect TODOs and FIXMEs in code',
            'parameters': {
                'directory': 'Root directory'
            }
        },
        'find_large_files': {
            'function': mcp.find_large_files,
            'description': 'Find large files in codebase',
            'parameters': {
                'directory': 'Root directory',
                'min_kb': 'Minimum size in KB (default: 100)'
            }
        },
        'analyze_complexity': {
            'function': mcp.analyze_complexity,
            'description': 'Analyze code complexity',
            'parameters': {
                'filepath': 'File path'
            }
        },
        'get_codebase_stats': {
            'function': mcp.get_codebase_stats,
            'description': 'Get overall codebase statistics',
            'parameters': {
                'directory': 'Root directory'
            }
        }
    }


if __name__ == '__main__':
    # Teste
    mcp = CodeAnalyzerMCP()
    stats = mcp.get_codebase_stats('/opt/conecta-plus/frontend/src')

    import json
    print(json.dumps(stats, indent=2))
