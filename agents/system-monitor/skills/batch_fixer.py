"""
Skill: Batch Fixer
Corrige múltiplos problemas de uma vez em lote
"""

import subprocess
from typing import Dict, Any, List
from datetime import datetime


class BatchFixer:
    """Correção em lote para múltiplos problemas"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def fix_all_missing_pip_packages(self, gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Instala todos os pacotes pip faltando de uma vez"""
        result = {
            'problem': 'Multiple missing pip packages',
            'action': 'Batch install all missing packages',
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'details': ''
        }

        # Coletar todos os pacotes faltando
        missing_packages = []
        for gap in gaps:
            if gap.get('type') == 'missing_pip_package' and gap.get('severity') == 'high':
                package = gap.get('package', '')
                if package:
                    missing_packages.append(package)

        if not missing_packages:
            result['success'] = True
            result['details'] = 'No missing packages to install'
            return result

        try:
            # Instalar todos de uma vez
            packages_str = ' '.join(missing_packages)
            install = subprocess.run(
                f'pip3 install {packages_str}',
                shell=True,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos
            )

            if install.returncode == 0:
                result['success'] = True
                result['details'] = f'Installed {len(missing_packages)} packages: {", ".join(missing_packages)}'
            else:
                result['details'] = f'Error installing: {install.stderr[:200]}'

        except Exception as e:
            result['details'] = f'Error: {str(e)}'

        return result

    def fix_all_outdated_npm_packages(self, gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Atualiza todos os pacotes npm desatualizados de uma vez"""
        result = {
            'problem': 'Multiple outdated npm packages',
            'action': 'Batch update all outdated packages',
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'details': ''
        }

        # Coletar pacotes desatualizados
        outdated_packages = []
        for gap in gaps:
            if gap.get('type') == 'outdated_npm':
                package = gap.get('package', '')
                if package:
                    outdated_packages.append(package)

        if not outdated_packages:
            result['success'] = True
            result['details'] = 'No outdated packages to update'
            return result

        try:
            frontend_dir = '/opt/conecta-plus/frontend'

            # Atualizar todos de uma vez
            packages_str = ' '.join([f'{p}@latest' for p in outdated_packages])
            update = subprocess.run(
                f'npm install {packages_str}',
                shell=True,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=frontend_dir
            )

            if update.returncode == 0:
                result['success'] = True
                result['details'] = f'Updated {len(outdated_packages)} packages: {", ".join(outdated_packages)}'
            else:
                result['details'] = f'Error updating: {update.stderr[:200]}'

        except Exception as e:
            result['details'] = f'Error: {str(e)}'

        return result

    def fix_all_debug_code(self, gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Remove console.log de todos os arquivos de uma vez"""
        result = {
            'problem': 'Debug code in multiple files',
            'action': 'Remove all console.log statements',
            'timestamp': datetime.now().isoformat(),
            'success': False,
            'details': ''
        }

        # Coletar arquivos com debug code
        debug_files = []
        for gap in gaps:
            if gap.get('type') == 'debug_code':
                file_path = gap.get('file', '')
                if file_path:
                    debug_files.append(file_path)

        if not debug_files:
            result['success'] = True
            result['details'] = 'No debug code found'
            return result

        try:
            import re

            files_fixed = 0
            total_removed = 0

            for file_path in debug_files:
                try:
                    with open(file_path, 'r') as f:
                        content = f.read()

                    original_lines = content.count('\n')
                    new_content = re.sub(
                        r'^\s*console\.(log|debug|info|warn)\(.*\);\s*$',
                        '',
                        content,
                        flags=re.MULTILINE
                    )

                    if new_content != content:
                        with open(file_path, 'w') as f:
                            f.write(new_content)

                        removed = original_lines - new_content.count('\n')
                        total_removed += removed
                        files_fixed += 1

                except:
                    continue

            if files_fixed > 0:
                result['success'] = True
                result['details'] = f'Removed {total_removed} console.log from {files_fixed} files'
            else:
                result['details'] = 'No console.log statements found'
                result['success'] = True

        except Exception as e:
            result['details'] = f'Error: {str(e)}'

        return result

    def fix_batch(self, gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Executa todas as correções em lote"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'fixes': [],
            'total_attempted': 0,
            'total_successful': 0
        }

        # 1. Instalar todos os pacotes pip de uma vez
        pip_result = self.fix_all_missing_pip_packages(gaps)
        if pip_result:
            results['fixes'].append(pip_result)
            results['total_attempted'] += 1
            if pip_result['success']:
                results['total_successful'] += 1

        # 2. Atualizar todos os pacotes npm de uma vez
        npm_result = self.fix_all_outdated_npm_packages(gaps)
        if npm_result:
            results['fixes'].append(npm_result)
            results['total_attempted'] += 1
            if npm_result['success']:
                results['total_successful'] += 1

        # 3. Remover todo o debug code
        debug_result = self.fix_all_debug_code(gaps)
        if debug_result:
            results['fixes'].append(debug_result)
            results['total_attempted'] += 1
            if debug_result['success']:
                results['total_successful'] += 1

        return results


if __name__ == '__main__':
    import json

    fixer = BatchFixer({})

    test_gaps = [
        {'type': 'missing_pip_package', 'severity': 'high', 'package': 'pytest'},
        {'type': 'missing_pip_package', 'severity': 'high', 'package': 'black'},
        {'type': 'outdated_npm', 'package': 'react'},
        {'type': 'debug_code', 'file': '/tmp/test.ts'}
    ]

    result = fixer.fix_batch(test_gaps)
    print(json.dumps(result, indent=2))
