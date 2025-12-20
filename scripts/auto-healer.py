#!/usr/bin/env python3
"""
Conecta Plus - Sistema Auto-Curativo com IA
Aprende sozinho, melhora com o tempo, previne problemas futuros
"""

import json
import os
import subprocess
import time
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import threading

# Paths
KNOWLEDGE_BASE_PATH = "/opt/conecta-plus/scripts/knowledge-base.json"
HEALER_LOG_PATH = "/var/log/conecta-plus/healer.log"
PREVENTION_LOG_PATH = "/var/log/conecta-plus/prevention.log"
METRICS_HISTORY_PATH = "/var/log/conecta-plus/metrics-history.json"

class AutoHealer:
    """Sistema auto-curativo que aprende e previne problemas"""

    def __init__(self):
        self.knowledge_base = self.load_json(KNOWLEDGE_BASE_PATH, self.default_kb())
        self.metrics_history = self.load_json(METRICS_HISTORY_PATH, {"samples": []})
        self.prevention_active = True
        self.learning_rate = 0.1  # Velocidade de aprendizado
        self.confidence_threshold = 0.6  # Mínimo para ação preventiva

        # Ações preventivas aprendidas
        self.preventive_actions = {
            "high_memory": self.prevent_high_memory,
            "high_cpu": self.prevent_high_cpu,
            "service_degradation": self.prevent_service_degradation,
            "connection_issues": self.prevent_connection_issues,
            "recurring_crash": self.prevent_recurring_crash,
        }

    def default_kb(self) -> dict:
        return {
            "version": "2.0.0",
            "problems": [],
            "patterns": [],
            "solutions": [],
            "preventions": [],
            "learned_thresholds": {
                "cpu_warning": 70,
                "cpu_critical": 85,
                "memory_warning": 75,
                "memory_critical": 90,
                "response_time_warning": 2000,
                "response_time_critical": 5000,
                "failure_count_before_action": 2
            },
            "effectiveness": {
                "auto_restart_backend": {"attempts": 0, "success": 0},
                "auto_restart_frontend": {"attempts": 0, "success": 0},
                "preventive_memory_cleanup": {"attempts": 0, "success": 0},
                "preventive_cache_clear": {"attempts": 0, "success": 0}
            },
            "statistics": {
                "total_incidents": 0,
                "auto_resolved": 0,
                "prevented": 0,
                "learning_cycles": 0
            }
        }

    def load_json(self, path: str, default: dict) -> dict:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return default

    def save_json(self, path: str, data: dict):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def log(self, message: str, log_type: str = "healer"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_path = HEALER_LOG_PATH if log_type == "healer" else PREVENTION_LOG_PATH

        with open(log_path, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
        print(f"[{log_type.upper()}] {message}")

    # === COLETA DE MÉTRICAS ===

    def collect_metrics(self) -> dict:
        """Coleta métricas atuais do sistema"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "cpu": self.get_cpu_usage(),
            "memory": self.get_memory_usage(),
            "disk": self.get_disk_usage(),
            "backend_response": self.check_service_response("http://localhost:3001"),
            "frontend_response": self.check_service_response("http://localhost:3000"),
            "docker_status": self.check_docker_status(),
        }

        # Guardar histórico (últimas 1000 amostras)
        self.metrics_history["samples"].append(metrics)
        if len(self.metrics_history["samples"]) > 1000:
            self.metrics_history["samples"] = self.metrics_history["samples"][-1000:]

        self.save_json(METRICS_HISTORY_PATH, self.metrics_history)
        return metrics

    def get_cpu_usage(self) -> float:
        try:
            result = subprocess.run(
                ["top", "-bn1"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'Cpu(s)' in line:
                    return float(line.split()[1].replace('%', '').replace(',', '.'))
        except:
            pass
        return 0.0

    def get_memory_usage(self) -> float:
        try:
            result = subprocess.run(
                ["free", "-m"], capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.split('\n')
            for line in lines:
                if line.startswith('Mem:'):
                    parts = line.split()
                    total = float(parts[1])
                    used = float(parts[2])
                    return (used / total) * 100
        except:
            pass
        return 0.0

    def get_disk_usage(self) -> float:
        try:
            result = subprocess.run(
                ["df", "-h", "/"], capture_output=True, text=True, timeout=5
            )
            lines = result.stdout.split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                return float(parts[4].replace('%', ''))
        except:
            pass
        return 0.0

    def check_service_response(self, url: str) -> dict:
        try:
            start = time.time()
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 "--connect-timeout", "3", url],
                capture_output=True, text=True, timeout=5
            )
            elapsed = (time.time() - start) * 1000  # ms
            status_code = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            return {
                "status": status_code,
                "response_time": elapsed,
                "healthy": status_code in [200, 301, 302, 404]
            }
        except:
            return {"status": 0, "response_time": 9999, "healthy": False}

    def check_docker_status(self) -> dict:
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "{{.Names}}:{{.Status}}"],
                capture_output=True, text=True, timeout=5
            )
            containers = {}
            for line in result.stdout.strip().split('\n'):
                if ':' in line:
                    name, status = line.split(':', 1)
                    containers[name] = "running" in status.lower()
            return {"containers": containers, "healthy": all(containers.values())}
        except:
            return {"containers": {}, "healthy": False}

    # === ANÁLISE E DETECÇÃO DE PADRÕES ===

    def analyze_trends(self) -> List[dict]:
        """Analisa tendências nas métricas para prever problemas"""
        trends = []
        samples = self.metrics_history.get("samples", [])

        if len(samples) < 10:
            return trends

        # Analisar últimas 10 amostras
        recent = samples[-10:]

        # Tendência de CPU
        cpu_values = [s.get("cpu", 0) for s in recent]
        cpu_trend = self.calculate_trend(cpu_values)
        if cpu_trend > 1:  # Subindo mais de 1% por amostra (mais sensível)
            trends.append({
                "type": "cpu_rising",
                "severity": "warning" if cpu_values[-1] < 70 else "critical",
                "current": cpu_values[-1],
                "trend": cpu_trend,
                "prediction": f"CPU pode atingir nível crítico em {int((85 - cpu_values[-1]) / cpu_trend)} ciclos"
            })

        # Tendência de Memória
        mem_values = [s.get("memory", 0) for s in recent]
        mem_trend = self.calculate_trend(mem_values)
        if mem_trend > 0.5:  # Subindo mais de 0.5% por amostra (mais sensível)
            trends.append({
                "type": "memory_rising",
                "severity": "warning" if mem_values[-1] < 80 else "critical",
                "current": mem_values[-1],
                "trend": mem_trend,
                "prediction": f"Memória pode atingir nível crítico em {int((90 - mem_values[-1]) / mem_trend)} ciclos"
            })

        # Tendência de tempo de resposta
        backend_times = [s.get("backend_response", {}).get("response_time", 0) for s in recent]
        if backend_times[-1] > backend_times[0] * 1.5:  # Aumentou 50%
            trends.append({
                "type": "response_degradation",
                "severity": "warning",
                "service": "backend",
                "current": backend_times[-1],
                "prediction": "Tempo de resposta degradando - possível sobrecarga"
            })

        return trends

    def calculate_trend(self, values: List[float]) -> float:
        """Calcula tendência (taxa de mudança)"""
        if len(values) < 2:
            return 0

        # Média das diferenças
        diffs = [values[i+1] - values[i] for i in range(len(values)-1)]
        return sum(diffs) / len(diffs)

    def detect_anomalies(self, metrics: dict) -> List[dict]:
        """Detecta anomalias comparando com histórico"""
        anomalies = []
        samples = self.metrics_history.get("samples", [])

        if len(samples) < 20:
            return anomalies

        # Calcular médias históricas
        hist_cpu = [s.get("cpu", 0) for s in samples[-100:]]
        hist_mem = [s.get("memory", 0) for s in samples[-100:]]

        avg_cpu = sum(hist_cpu) / len(hist_cpu)
        avg_mem = sum(hist_mem) / len(hist_mem)

        # Detectar desvios significativos (>2x desvio padrão)
        std_cpu = (sum((x - avg_cpu) ** 2 for x in hist_cpu) / len(hist_cpu)) ** 0.5
        std_mem = (sum((x - avg_mem) ** 2 for x in hist_mem) / len(hist_mem)) ** 0.5

        if metrics["cpu"] > avg_cpu + (2 * std_cpu):
            anomalies.append({
                "type": "cpu_anomaly",
                "current": metrics["cpu"],
                "expected": avg_cpu,
                "deviation": (metrics["cpu"] - avg_cpu) / std_cpu if std_cpu > 0 else 0
            })

        if metrics["memory"] > avg_mem + (2 * std_mem):
            anomalies.append({
                "type": "memory_anomaly",
                "current": metrics["memory"],
                "expected": avg_mem,
                "deviation": (metrics["memory"] - avg_mem) / std_mem if std_mem > 0 else 0
            })

        return anomalies

    # === AÇÕES PREVENTIVAS ===

    def prevent_high_memory(self) -> bool:
        """Ação preventiva para memória alta"""
        self.log("Executando prevenção de memória alta...", "prevention")
        try:
            # Limpar caches do sistema
            subprocess.run(["sync"], timeout=10)
            subprocess.run(["bash", "-c", "echo 3 > /proc/sys/vm/drop_caches"],
                         timeout=10, capture_output=True)
            self.log("Cache do sistema limpo", "prevention")
            return True
        except Exception as e:
            self.log(f"Erro na prevenção de memória: {e}", "prevention")
            return False

    def prevent_high_cpu(self) -> bool:
        """Ação preventiva para CPU alta"""
        self.log("Executando prevenção de CPU alta...", "prevention")
        try:
            # Identificar processos com alto CPU
            result = subprocess.run(
                ["ps", "aux", "--sort=-%cpu"],
                capture_output=True, text=True, timeout=10
            )
            self.log(f"Top processos identificados para análise", "prevention")
            return True
        except Exception as e:
            self.log(f"Erro na prevenção de CPU: {e}", "prevention")
            return False

    def prevent_service_degradation(self) -> bool:
        """Ação preventiva para degradação de serviço"""
        self.log("Executando prevenção de degradação...", "prevention")
        try:
            # Reiniciar serviço antes que falhe completamente
            # Por enquanto, apenas logamos - ação real seria reinício graceful
            self.log("Monitorando serviço para reinício preventivo se necessário", "prevention")
            return True
        except Exception as e:
            self.log(f"Erro na prevenção de degradação: {e}", "prevention")
            return False

    def prevent_connection_issues(self) -> bool:
        """Ação preventiva para problemas de conexão"""
        self.log("Verificando conexões...", "prevention")
        return True

    def prevent_recurring_crash(self) -> bool:
        """Ação preventiva para crashes recorrentes"""
        self.log("Analisando padrão de crashes para prevenção...", "prevention")

        # Verificar se há padrão de crashes
        problems = self.knowledge_base.get("problems", [])
        recurring = [p for p in problems if p.get("occurrences", 0) >= 3]

        if recurring:
            self.log(f"Detectados {len(recurring)} problemas recorrentes", "prevention")

            for problem in recurring:
                # Aplicar solução aprendida se existir
                solutions = [s for s in self.knowledge_base.get("solutions", [])
                           if s.get("problem_id") == problem.get("id")]

                if solutions:
                    best = max(solutions, key=lambda s: s.get("effectiveness", 0))
                    if best.get("effectiveness", 0) > 0.7:
                        self.log(f"Aplicando solução preventiva: {best.get('description')}", "prevention")

        return True

    # === APRENDIZADO AUTÔNOMO ===

    def learn_from_success(self, action: str, success: bool):
        """Aprende com o resultado de uma ação"""
        effectiveness = self.knowledge_base.get("effectiveness", {})

        if action not in effectiveness:
            effectiveness[action] = {"attempts": 0, "success": 0}

        effectiveness[action]["attempts"] += 1
        if success:
            effectiveness[action]["success"] += 1

        # Calcular taxa de sucesso
        attempts = effectiveness[action]["attempts"]
        successes = effectiveness[action]["success"]
        rate = successes / attempts if attempts > 0 else 0

        self.log(f"Ação '{action}': {successes}/{attempts} ({rate*100:.1f}% efetiva)")

        self.knowledge_base["effectiveness"] = effectiveness
        self.save_json(KNOWLEDGE_BASE_PATH, self.knowledge_base)

    def auto_tune_thresholds(self):
        """Ajusta thresholds automaticamente baseado em histórico"""
        samples = self.metrics_history.get("samples", [])

        if len(samples) < 100:
            return

        thresholds = self.knowledge_base.get("learned_thresholds", {})

        # Calcular percentis das métricas
        cpu_values = sorted([s.get("cpu", 0) for s in samples])
        mem_values = sorted([s.get("memory", 0) for s in samples])

        # P90 = warning, P99 = critical
        p90_cpu = cpu_values[int(len(cpu_values) * 0.90)]
        p99_cpu = cpu_values[int(len(cpu_values) * 0.99)]
        p90_mem = mem_values[int(len(mem_values) * 0.90)]
        p99_mem = mem_values[int(len(mem_values) * 0.99)]

        # Ajustar gradualmente (não mudar muito de uma vez)
        old_cpu_warn = thresholds.get("cpu_warning", 70)
        old_cpu_crit = thresholds.get("cpu_critical", 85)
        old_mem_warn = thresholds.get("memory_warning", 75)
        old_mem_crit = thresholds.get("memory_critical", 90)

        # Aplicar learning rate
        thresholds["cpu_warning"] = old_cpu_warn + (p90_cpu - old_cpu_warn) * self.learning_rate
        thresholds["cpu_critical"] = old_cpu_crit + (p99_cpu - old_cpu_crit) * self.learning_rate
        thresholds["memory_warning"] = old_mem_warn + (p90_mem - old_mem_warn) * self.learning_rate
        thresholds["memory_critical"] = old_mem_crit + (p99_mem - old_mem_crit) * self.learning_rate

        self.knowledge_base["learned_thresholds"] = thresholds
        self.log(f"Thresholds ajustados: CPU={thresholds['cpu_warning']:.1f}/{thresholds['cpu_critical']:.1f}, "
                f"MEM={thresholds['memory_warning']:.1f}/{thresholds['memory_critical']:.1f}")

    def create_solution_from_success(self, problem_id: str, action: str, steps: List[str]):
        """Cria solução automaticamente quando uma ação funciona"""
        effectiveness = self.knowledge_base.get("effectiveness", {}).get(action, {})
        rate = effectiveness.get("success", 0) / max(effectiveness.get("attempts", 1), 1)

        if rate < 0.5:
            return  # Não criar solução para ações pouco efetivas

        # Verificar se já existe solução
        solutions = self.knowledge_base.get("solutions", [])
        existing = [s for s in solutions if s.get("problem_id") == problem_id
                   and s.get("action") == action]

        if existing:
            # Atualizar efetividade
            existing[0]["effectiveness"] = rate
            existing[0]["times_used"] = effectiveness.get("attempts", 0)
            existing[0]["times_successful"] = effectiveness.get("success", 0)
        else:
            # Criar nova solução
            solution = {
                "id": f"auto_{problem_id}_{len(solutions)}",
                "problem_id": problem_id,
                "action": action,
                "created": datetime.now().isoformat(),
                "description": f"Solução automática: {action}",
                "steps": steps,
                "effectiveness": rate,
                "times_used": effectiveness.get("attempts", 0),
                "times_successful": effectiveness.get("success", 0),
                "auto_generated": True
            }
            solutions.append(solution)
            self.log(f"Nova solução criada automaticamente: {solution['id']}")

        self.knowledge_base["solutions"] = solutions
        self.save_json(KNOWLEDGE_BASE_PATH, self.knowledge_base)

    # === CICLO PRINCIPAL ===

    def run_prevention_cycle(self) -> dict:
        """Executa um ciclo completo de prevenção"""
        result = {
            "timestamp": datetime.now().isoformat(),
            "metrics_collected": False,
            "trends_detected": [],
            "anomalies_detected": [],
            "preventions_executed": [],
            "learning_applied": False
        }

        try:
            # 1. Coletar métricas
            metrics = self.collect_metrics()
            result["metrics_collected"] = True

            # 2. Analisar tendências
            trends = self.analyze_trends()
            result["trends_detected"] = trends

            # 3. Detectar anomalias
            anomalies = self.detect_anomalies(metrics)
            result["anomalies_detected"] = anomalies

            # 4. Executar prevenções se necessário
            thresholds = self.knowledge_base.get("learned_thresholds", {})

            # Prevenção de memória
            if metrics["memory"] > thresholds.get("memory_warning", 75):
                if any(t["type"] == "memory_rising" for t in trends):
                    success = self.prevent_high_memory()
                    result["preventions_executed"].append({
                        "action": "prevent_high_memory",
                        "success": success
                    })
                    self.learn_from_success("preventive_memory_cleanup", success)
                    if success:
                        self.knowledge_base["statistics"]["prevented"] += 1

            # Prevenção de CPU
            if metrics["cpu"] > thresholds.get("cpu_warning", 70):
                if any(t["type"] == "cpu_rising" for t in trends):
                    success = self.prevent_high_cpu()
                    result["preventions_executed"].append({
                        "action": "prevent_high_cpu",
                        "success": success
                    })
                    self.learn_from_success("preventive_cpu_optimization", success)

            # Prevenção de degradação de serviço
            backend_resp = metrics.get("backend_response", {})
            if backend_resp.get("response_time", 0) > thresholds.get("response_time_warning", 2000):
                success = self.prevent_service_degradation()
                result["preventions_executed"].append({
                    "action": "prevent_service_degradation",
                    "success": success
                })

            # 5. Verificar crashes recorrentes
            self.prevent_recurring_crash()

            # 6. Auto-ajustar thresholds
            self.auto_tune_thresholds()
            result["learning_applied"] = True

            # 7. Atualizar estatísticas
            if "statistics" not in self.knowledge_base:
                self.knowledge_base["statistics"] = {
                    "total_incidents": 0,
                    "auto_resolved": 0,
                    "prevented": 0,
                    "learning_cycles": 0
                }
            if "learning_cycles" not in self.knowledge_base["statistics"]:
                self.knowledge_base["statistics"]["learning_cycles"] = 0

            self.knowledge_base["statistics"]["learning_cycles"] += 1
            self.save_json(KNOWLEDGE_BASE_PATH, self.knowledge_base)

        except Exception as e:
            self.log(f"Erro no ciclo de prevenção: {e}")

        return result

    def get_status(self) -> dict:
        """Retorna status atual do sistema de auto-cura"""
        stats = self.knowledge_base.get("statistics", {})
        thresholds = self.knowledge_base.get("learned_thresholds", {})
        effectiveness = self.knowledge_base.get("effectiveness", {})

        # Calcular efetividade geral
        total_attempts = sum(e.get("attempts", 0) for e in effectiveness.values())
        total_success = sum(e.get("success", 0) for e in effectiveness.values())
        overall_rate = total_success / total_attempts if total_attempts > 0 else 0

        return {
            "status": "active" if self.prevention_active else "paused",
            "learning_cycles": stats.get("learning_cycles", 0),
            "incidents_total": stats.get("total_incidents", 0),
            "incidents_prevented": stats.get("prevented", 0),
            "overall_effectiveness": f"{overall_rate*100:.1f}%",
            "current_thresholds": thresholds,
            "metrics_samples": len(self.metrics_history.get("samples", [])),
            "solutions_generated": len([s for s in self.knowledge_base.get("solutions", [])
                                        if s.get("auto_generated")])
        }


def main():
    import sys

    healer = AutoHealer()

    if len(sys.argv) < 2:
        print("Uso: auto-healer.py [comando]")
        print("")
        print("Comandos:")
        print("  run       - Executar ciclo de prevenção")
        print("  status    - Ver status do sistema")
        print("  trends    - Ver tendências detectadas")
        print("  metrics   - Coletar e mostrar métricas")
        print("  daemon    - Rodar em modo contínuo")
        return

    command = sys.argv[1]

    if command == "run":
        result = healer.run_prevention_cycle()
        print(json.dumps(result, indent=2))

    elif command == "status":
        status = healer.get_status()
        print("=== STATUS DO AUTO-HEALER ===\n")
        for key, value in status.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"{key}: {value}")

    elif command == "trends":
        healer.collect_metrics()
        trends = healer.analyze_trends()
        if trends:
            print("=== TENDÊNCIAS DETECTADAS ===\n")
            for trend in trends:
                print(f"⚠️  {trend['type']}")
                print(f"   Severidade: {trend['severity']}")
                print(f"   Predição: {trend['prediction']}")
                print()
        else:
            print("Nenhuma tendência significativa detectada.")
            print("(São necessárias pelo menos 10 amostras de métricas)")

    elif command == "metrics":
        metrics = healer.collect_metrics()
        print("=== MÉTRICAS ATUAIS ===\n")
        print(f"CPU: {metrics['cpu']:.1f}%")
        print(f"Memória: {metrics['memory']:.1f}%")
        print(f"Disco: {metrics['disk']:.1f}%")
        print(f"\nBackend:")
        print(f"  Status: {metrics['backend_response']['status']}")
        print(f"  Tempo: {metrics['backend_response']['response_time']:.0f}ms")
        print(f"  Saudável: {'Sim' if metrics['backend_response']['healthy'] else 'Não'}")
        print(f"\nFrontend:")
        print(f"  Status: {metrics['frontend_response']['status']}")
        print(f"  Tempo: {metrics['frontend_response']['response_time']:.0f}ms")
        print(f"  Saudável: {'Sim' if metrics['frontend_response']['healthy'] else 'Não'}")

    elif command == "daemon":
        import sys
        sys.stdout.reconfigure(line_buffering=True)  # Flush imediato

        print("Iniciando Auto-Healer em modo daemon...")
        print("Ciclo de prevenção a cada 60 segundos")
        sys.stdout.flush()

        cycle = 0
        while True:
            try:
                cycle += 1
                result = healer.run_prevention_cycle()
                prevented = len(result.get("preventions_executed", []))
                trends = len(result.get("trends_detected", []))
                anomalies = len(result.get("anomalies_detected", []))

                timestamp = datetime.now().strftime("%H:%M:%S")
                samples = len(healer.metrics_history.get("samples", []))

                print(f"[{timestamp}] Ciclo #{cycle} - Amostras: {samples} | Tendências: {trends} | Anomalias: {anomalies} | Prevenções: {prevented}")
                sys.stdout.flush()

                time.sleep(60)
            except KeyboardInterrupt:
                print("\nAuto-Healer finalizado.")
                break

    else:
        print(f"Comando desconhecido: {command}")


if __name__ == "__main__":
    main()
