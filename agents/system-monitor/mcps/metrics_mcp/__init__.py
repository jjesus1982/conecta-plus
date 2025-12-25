"""
MCP: System Metrics
Tools para coletar métricas do sistema
"""

import psutil
import subprocess
from typing import Dict, Any, List
from datetime import datetime


class MetricsMCP:
    """MCP para métricas do sistema"""

    def __init__(self):
        self.history = []

    def get_cpu_usage(self) -> Dict[str, Any]:
        """
        Retorna uso de CPU

        Returns:
            Dicionário com métricas de CPU
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'percent': psutil.cpu_percent(interval=1),
            'per_cpu': psutil.cpu_percent(interval=1, percpu=True),
            'count': psutil.cpu_count(),
            'load_avg': psutil.getloadavg()
        }

    def get_memory_usage(self) -> Dict[str, Any]:
        """
        Retorna uso de memória

        Returns:
            Dicionário com métricas de memória
        """
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        return {
            'timestamp': datetime.now().isoformat(),
            'total_mb': mem.total // (1024 * 1024),
            'available_mb': mem.available // (1024 * 1024),
            'used_mb': mem.used // (1024 * 1024),
            'percent': mem.percent,
            'swap_total_mb': swap.total // (1024 * 1024),
            'swap_used_mb': swap.used // (1024 * 1024),
            'swap_percent': swap.percent
        }

    def get_disk_usage(self, path: str = '/') -> Dict[str, Any]:
        """
        Retorna uso de disco

        Args:
            path: Caminho para verificar

        Returns:
            Dicionário com métricas de disco
        """
        disk = psutil.disk_usage(path)

        return {
            'timestamp': datetime.now().isoformat(),
            'path': path,
            'total_gb': disk.total // (1024 * 1024 * 1024),
            'used_gb': disk.used // (1024 * 1024 * 1024),
            'free_gb': disk.free // (1024 * 1024 * 1024),
            'percent': disk.percent
        }

    def get_network_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas de rede

        Returns:
            Dicionário com métricas de rede
        """
        net_io = psutil.net_io_counters()

        return {
            'timestamp': datetime.now().isoformat(),
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'errors_in': net_io.errin,
            'errors_out': net_io.errout,
            'drops_in': net_io.dropin,
            'drops_out': net_io.dropout
        }

    def get_process_info(self, name: str) -> List[Dict[str, Any]]:
        """
        Retorna informações sobre processos

        Args:
            name: Nome do processo para buscar

        Returns:
            Lista de processos encontrados
        """
        processes = []

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                if name.lower() in proc.info['name'].lower():
                    processes.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_percent': proc.info['memory_percent'],
                        'status': proc.info['status']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return processes

    def get_top_processes(self, limit: int = 10, sort_by: str = 'cpu') -> List[Dict[str, Any]]:
        """
        Retorna top processos por CPU ou memória

        Args:
            limit: Número de processos
            sort_by: 'cpu' ou 'memory'

        Returns:
            Lista de processos
        """
        processes = []

        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'username']):
            try:
                pinfo = proc.info
                pinfo['cpu_percent'] = proc.cpu_percent(interval=0.1)
                processes.append(pinfo)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Ordenar
        if sort_by == 'memory':
            processes.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
        else:
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)

        return processes[:limit]

    def check_port(self, port: int) -> Dict[str, Any]:
        """
        Verifica se porta está em uso

        Args:
            port: Número da porta

        Returns:
            Informações sobre a porta
        """
        connections = psutil.net_connections()

        for conn in connections:
            if conn.laddr.port == port:
                try:
                    proc = psutil.Process(conn.pid) if conn.pid else None
                    return {
                        'port': port,
                        'in_use': True,
                        'pid': conn.pid,
                        'process': proc.name() if proc else 'unknown',
                        'status': conn.status
                    }
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return {
                        'port': port,
                        'in_use': True,
                        'pid': conn.pid,
                        'process': 'unknown',
                        'status': conn.status
                    }

        return {
            'port': port,
            'in_use': False
        }

    def get_uptime(self) -> Dict[str, Any]:
        """
        Retorna uptime do sistema

        Returns:
            Informações de uptime
        """
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time

        return {
            'boot_time': boot_time.isoformat(),
            'uptime_seconds': int(uptime.total_seconds()),
            'uptime_human': str(uptime).split('.')[0]  # Remove microseconds
        }

    def get_system_info(self) -> Dict[str, Any]:
        """
        Retorna informações completas do sistema

        Returns:
            Dicionário com todas as métricas
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'cpu': self.get_cpu_usage(),
            'memory': self.get_memory_usage(),
            'disk': self.get_disk_usage('/'),
            'network': self.get_network_stats(),
            'uptime': self.get_uptime(),
            'top_processes_cpu': self.get_top_processes(5, 'cpu'),
            'top_processes_memory': self.get_top_processes(5, 'memory')
        }

    def record_metrics(self):
        """Registra métricas no histórico"""
        metrics = self.get_system_info()
        self.history.append(metrics)

        # Manter apenas últimas 100 entradas
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Retorna resumo das métricas históricas"""
        if not self.history:
            return {}

        cpu_values = [m['cpu']['percent'] for m in self.history]
        mem_values = [m['memory']['percent'] for m in self.history]

        return {
            'count': len(self.history),
            'cpu': {
                'avg': sum(cpu_values) / len(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values)
            },
            'memory': {
                'avg': sum(mem_values) / len(mem_values),
                'max': max(mem_values),
                'min': min(mem_values)
            }
        }


# Ferramentas disponíveis para o agente
def get_tools():
    """Retorna lista de ferramentas disponíveis"""
    mcp = MetricsMCP()

    return {
        'get_cpu_usage': {
            'function': mcp.get_cpu_usage,
            'description': 'Get CPU usage metrics'
        },
        'get_memory_usage': {
            'function': mcp.get_memory_usage,
            'description': 'Get memory usage metrics'
        },
        'get_disk_usage': {
            'function': mcp.get_disk_usage,
            'description': 'Get disk usage metrics',
            'parameters': {
                'path': 'Path to check (default: /)'
            }
        },
        'get_network_stats': {
            'function': mcp.get_network_stats,
            'description': 'Get network statistics'
        },
        'get_process_info': {
            'function': mcp.get_process_info,
            'description': 'Get information about specific processes',
            'parameters': {
                'name': 'Process name to search'
            }
        },
        'get_top_processes': {
            'function': mcp.get_top_processes,
            'description': 'Get top processes by CPU or memory',
            'parameters': {
                'limit': 'Number of processes (default: 10)',
                'sort_by': 'Sort by cpu or memory (default: cpu)'
            }
        },
        'check_port': {
            'function': mcp.check_port,
            'description': 'Check if a port is in use',
            'parameters': {
                'port': 'Port number to check'
            }
        },
        'get_uptime': {
            'function': mcp.get_uptime,
            'description': 'Get system uptime'
        },
        'get_system_info': {
            'function': mcp.get_system_info,
            'description': 'Get complete system information'
        }
    }


if __name__ == '__main__':
    # Teste
    mcp = MetricsMCP()
    info = mcp.get_system_info()

    import json
    print(json.dumps(info, indent=2))
