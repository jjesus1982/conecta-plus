#!/usr/bin/env python3
"""
Conecta Plus - Sistema de Monitoramento Inteligente com Aprendizado
Aprende com erros, cria base de conhecimento, previne problemas futuros
"""

import json
import os
import re
import hashlib
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import subprocess

# Paths
KNOWLEDGE_BASE_PATH = "/opt/conecta-plus/scripts/knowledge-base.json"
ALERTS_LOG_PATH = "/var/log/conecta-plus/alerts.log"
METRICS_LOG_PATH = "/var/log/conecta-plus/metrics.log"
LEARNING_LOG_PATH = "/var/log/conecta-plus/learning.log"

class SmartMonitor:
    """Sistema de monitoramento inteligente com aprendizado"""

    def __init__(self):
        self.knowledge_base = self.load_knowledge_base()
        self.patterns_cache = {}
        self.prediction_threshold = 0.7  # 70% confiança para alertar

    def load_knowledge_base(self) -> dict:
        """Carrega a base de conhecimento"""
        try:
            with open(KNOWLEDGE_BASE_PATH, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "version": "1.0.0",
                "last_updated": "",
                "problems": [],
                "patterns": [],
                "solutions": [],
                "statistics": {
                    "total_incidents": 0,
                    "auto_resolved": 0,
                    "manual_resolved": 0,
                    "prevention_success": 0
                }
            }

    def save_knowledge_base(self):
        """Salva a base de conhecimento"""
        self.knowledge_base["last_updated"] = datetime.now().isoformat()
        with open(KNOWLEDGE_BASE_PATH, 'w') as f:
            json.dump(self.knowledge_base, f, indent=2, ensure_ascii=False)

    def log_learning(self, message: str):
        """Registra atividade de aprendizado"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LEARNING_LOG_PATH, 'a') as f:
            f.write(f"[{timestamp}] {message}\n")
        print(f"[LEARN] {message}")

    def generate_problem_id(self, error_type: str, service: str, details: str) -> str:
        """Gera ID único para um problema"""
        content = f"{error_type}:{service}:{details}"
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def analyze_alerts_log(self) -> List[dict]:
        """Analisa o log de alertas e extrai incidentes"""
        incidents = []

        try:
            with open(ALERTS_LOG_PATH, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            return incidents

        current_incident = None

        for line in lines:
            # Parse timestamp e tipo
            match = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[(\w+)\] (.+)', line)
            if not match:
                continue

            timestamp_str, level, message = match.groups()
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")

            # Detectar início de incidente (CRITICAL)
            if level == "CRITICAL":
                # Identificar serviço e tipo de erro
                service = "unknown"
                error_type = "unknown"

                if "Backend" in message:
                    service = "backend"
                elif "Frontend" in message:
                    service = "frontend"
                elif "Container" in message:
                    service = "docker"
                elif "Porta" in message:
                    service = "network"
                elif "CPU" in message or "Memória" in message:
                    service = "system"

                if "não responde" in message:
                    error_type = "service_down"
                elif "não está rodando" in message:
                    error_type = "container_stopped"
                elif "não está em uso" in message:
                    error_type = "port_not_listening"
                elif "alta" in message:
                    error_type = "resource_high"

                current_incident = {
                    "id": self.generate_problem_id(error_type, service, message),
                    "timestamp": timestamp_str,
                    "service": service,
                    "error_type": error_type,
                    "message": message,
                    "resolved": False,
                    "resolution_time": None,
                    "resolution_method": None
                }
                incidents.append(current_incident)

            # Detectar resolução (SUCCESS)
            elif level == "SUCCESS" and current_incident:
                current_incident["resolved"] = True
                current_incident["resolution_time"] = timestamp_str

                if "reiniciado" in message:
                    current_incident["resolution_method"] = "auto_restart"
                else:
                    current_incident["resolution_method"] = "auto_fix"

                current_incident = None

        return incidents

    def learn_from_incidents(self, incidents: List[dict]):
        """Aprende com os incidentes e atualiza a base de conhecimento"""

        for incident in incidents:
            problem_id = incident["id"]

            # Verificar se já conhecemos esse problema
            existing_problem = None
            for p in self.knowledge_base["problems"]:
                if p["id"] == problem_id:
                    existing_problem = p
                    break

            if existing_problem:
                # Atualizar estatísticas do problema conhecido
                existing_problem["occurrences"] += 1
                existing_problem["last_seen"] = incident["timestamp"]

                if incident["resolved"]:
                    existing_problem["times_auto_resolved"] += 1

                    # Calcular tempo médio de resolução
                    if incident["resolution_time"]:
                        start = datetime.strptime(incident["timestamp"], "%Y-%m-%d %H:%M:%S")
                        end = datetime.strptime(incident["resolution_time"], "%Y-%m-%d %H:%M:%S")
                        resolution_seconds = (end - start).total_seconds()

                        # Média móvel
                        old_avg = existing_problem.get("avg_resolution_time")
                        if old_avg is None:
                            existing_problem["avg_resolution_time"] = resolution_seconds
                        else:
                            existing_problem["avg_resolution_time"] = (old_avg + resolution_seconds) / 2

                self.log_learning(f"Problema conhecido atualizado: {problem_id} (ocorrências: {existing_problem['occurrences']})")
            else:
                # Novo problema - adicionar à base
                new_problem = {
                    "id": problem_id,
                    "service": incident["service"],
                    "error_type": incident["error_type"],
                    "message_pattern": incident["message"],
                    "first_seen": incident["timestamp"],
                    "last_seen": incident["timestamp"],
                    "occurrences": 1,
                    "times_auto_resolved": 1 if incident["resolved"] else 0,
                    "avg_resolution_time": None,
                    "known_causes": [],
                    "prevention_tips": []
                }

                # Adicionar causas e dicas baseado no tipo de erro
                if incident["error_type"] == "service_down":
                    new_problem["known_causes"] = [
                        "Crash da aplicação",
                        "Falta de memória",
                        "Erro de código",
                        "Dependência indisponível"
                    ]
                    new_problem["prevention_tips"] = [
                        "Monitorar uso de memória",
                        "Implementar health checks internos",
                        "Adicionar circuit breakers"
                    ]
                elif incident["error_type"] == "container_stopped":
                    new_problem["known_causes"] = [
                        "OOM Kill (falta de memória)",
                        "Erro no entrypoint",
                        "Dependência de rede falhou"
                    ]
                    new_problem["prevention_tips"] = [
                        "Configurar limites de memória adequados",
                        "Usar restart policies no Docker",
                        "Implementar graceful shutdown"
                    ]
                elif incident["error_type"] == "port_not_listening":
                    new_problem["known_causes"] = [
                        "Processo não iniciou",
                        "Porta já em uso por outro processo",
                        "Erro de binding"
                    ]
                    new_problem["prevention_tips"] = [
                        "Verificar conflitos de porta antes de iniciar",
                        "Usar wait-for-it scripts"
                    ]

                self.knowledge_base["problems"].append(new_problem)
                self.knowledge_base["statistics"]["total_incidents"] += 1

                if incident["resolved"]:
                    self.knowledge_base["statistics"]["auto_resolved"] += 1

                self.log_learning(f"Novo problema aprendido: {problem_id} ({incident['service']}/{incident['error_type']})")

        # Detectar padrões
        self.detect_patterns()

        # Salvar base atualizada
        self.save_knowledge_base()

    def detect_patterns(self):
        """Detecta padrões nos problemas (horários, sequências, correlações)"""

        problems = self.knowledge_base["problems"]

        if len(problems) < 2:
            return

        # Padrão 1: Problemas que ocorrem juntos
        service_pairs = defaultdict(int)
        for i, p1 in enumerate(problems):
            for p2 in problems[i+1:]:
                if p1["service"] != p2["service"]:
                    pair = tuple(sorted([p1["service"], p2["service"]]))
                    service_pairs[pair] += 1

        for pair, count in service_pairs.items():
            if count >= 2:  # Correlação significativa
                pattern_id = f"correlation_{pair[0]}_{pair[1]}"

                existing = any(p["id"] == pattern_id for p in self.knowledge_base["patterns"])
                if not existing:
                    new_pattern = {
                        "id": pattern_id,
                        "type": "service_correlation",
                        "services": list(pair),
                        "description": f"Problemas em {pair[0]} frequentemente acompanham problemas em {pair[1]}",
                        "occurrences": count,
                        "recommendation": f"Ao detectar problema em {pair[0]}, verificar preventivamente {pair[1]}"
                    }
                    self.knowledge_base["patterns"].append(new_pattern)
                    self.log_learning(f"Padrão detectado: {pattern_id}")

        # Padrão 2: Problemas recorrentes (mesmo problema múltiplas vezes)
        for problem in problems:
            if problem["occurrences"] >= 3:
                pattern_id = f"recurring_{problem['id']}"

                existing = any(p["id"] == pattern_id for p in self.knowledge_base["patterns"])
                if not existing:
                    new_pattern = {
                        "id": pattern_id,
                        "type": "recurring_problem",
                        "problem_id": problem["id"],
                        "service": problem["service"],
                        "occurrences": problem["occurrences"],
                        "description": f"Problema recorrente em {problem['service']}: {problem['error_type']}",
                        "recommendation": "Investigar causa raiz - problema está se repetindo frequentemente"
                    }
                    self.knowledge_base["patterns"].append(new_pattern)
                    self.log_learning(f"Problema recorrente detectado: {problem['service']}/{problem['error_type']}")

    def create_solution(self, problem_id: str, description: str, steps: List[str],
                       prevention: List[str], effectiveness: float = 0.5):
        """Cria uma solução para um problema"""

        solution = {
            "id": f"sol_{problem_id}_{len(self.knowledge_base['solutions'])}",
            "problem_id": problem_id,
            "created": datetime.now().isoformat(),
            "description": description,
            "steps": steps,
            "prevention": prevention,
            "effectiveness": effectiveness,  # 0-1, atualizado com uso
            "times_used": 0,
            "times_successful": 0
        }

        self.knowledge_base["solutions"].append(solution)
        self.save_knowledge_base()
        self.log_learning(f"Nova solução registrada: {solution['id']}")

        return solution

    def get_solution_for_problem(self, service: str, error_type: str) -> Optional[dict]:
        """Busca a melhor solução para um problema"""

        # Encontrar problema na base
        matching_problem = None
        for problem in self.knowledge_base["problems"]:
            if problem["service"] == service and problem["error_type"] == error_type:
                matching_problem = problem
                break

        if not matching_problem:
            return None

        # Buscar soluções para este problema
        solutions = [s for s in self.knowledge_base["solutions"]
                    if s["problem_id"] == matching_problem["id"]]

        if not solutions:
            # Retornar dicas genéricas do problema
            return {
                "type": "generic",
                "causes": matching_problem.get("known_causes", []),
                "prevention": matching_problem.get("prevention_tips", [])
            }

        # Retornar solução mais efetiva
        best_solution = max(solutions, key=lambda s: s["effectiveness"])
        return {
            "type": "learned",
            "solution": best_solution
        }

    def predict_failure(self) -> List[dict]:
        """Prediz possíveis falhas baseado em padrões aprendidos"""

        predictions = []

        # Verificar padrões de correlação
        for pattern in self.knowledge_base["patterns"]:
            if pattern["type"] == "service_correlation":
                # Se um serviço do par teve problema recente, alertar sobre o outro
                # (Implementação simplificada - em produção, verificar logs recentes)
                predictions.append({
                    "type": "correlation_risk",
                    "pattern": pattern,
                    "confidence": 0.6,
                    "message": pattern["recommendation"]
                })

        # Verificar problemas recorrentes
        for pattern in self.knowledge_base["patterns"]:
            if pattern["type"] == "recurring_problem":
                problem = next((p for p in self.knowledge_base["problems"]
                              if p["id"] == pattern["problem_id"]), None)
                if problem:
                    # Se problema ocorre frequentemente, alta chance de ocorrer novamente
                    predictions.append({
                        "type": "recurring_risk",
                        "service": problem["service"],
                        "error_type": problem["error_type"],
                        "occurrences": problem["occurrences"],
                        "confidence": min(0.9, 0.3 + (problem["occurrences"] * 0.1)),
                        "message": f"Alto risco de {problem['error_type']} em {problem['service']} (ocorreu {problem['occurrences']}x)"
                    })

        return [p for p in predictions if p["confidence"] >= self.prediction_threshold]

    def generate_report(self) -> str:
        """Gera relatório da base de conhecimento"""

        kb = self.knowledge_base
        stats = kb["statistics"]

        report = []
        report.append("=" * 60)
        report.append("   CONECTA PLUS - RELATÓRIO DE APRENDIZADO")
        report.append("=" * 60)
        report.append(f"\nÚltima atualização: {kb['last_updated'] or 'Nunca'}")

        # Estatísticas
        report.append("\n### ESTATÍSTICAS ###")
        report.append(f"Total de incidentes: {stats['total_incidents']}")
        report.append(f"Resolvidos automaticamente: {stats['auto_resolved']}")
        report.append(f"Resolvidos manualmente: {stats['manual_resolved']}")
        report.append(f"Prevenções bem-sucedidas: {stats['prevention_success']}")

        if stats['total_incidents'] > 0:
            auto_rate = (stats['auto_resolved'] / stats['total_incidents']) * 100
            report.append(f"Taxa de auto-resolução: {auto_rate:.1f}%")

        # Problemas conhecidos
        report.append(f"\n### PROBLEMAS CONHECIDOS ({len(kb['problems'])}) ###")
        for problem in kb["problems"]:
            report.append(f"\n[{problem['id']}] {problem['service']}/{problem['error_type']}")
            report.append(f"  Ocorrências: {problem['occurrences']}")
            report.append(f"  Auto-resolvido: {problem['times_auto_resolved']}x")
            if problem.get('avg_resolution_time'):
                report.append(f"  Tempo médio resolução: {problem['avg_resolution_time']:.1f}s")
            if problem.get('known_causes'):
                report.append(f"  Causas conhecidas: {', '.join(problem['known_causes'][:2])}")

        # Padrões detectados
        report.append(f"\n### PADRÕES DETECTADOS ({len(kb['patterns'])}) ###")
        for pattern in kb["patterns"]:
            report.append(f"\n[{pattern['type']}] {pattern['description']}")
            report.append(f"  Recomendação: {pattern['recommendation']}")

        # Soluções
        report.append(f"\n### SOLUÇÕES REGISTRADAS ({len(kb['solutions'])}) ###")
        for solution in kb["solutions"]:
            report.append(f"\n[{solution['id']}] {solution['description']}")
            report.append(f"  Efetividade: {solution['effectiveness']*100:.0f}%")
            report.append(f"  Usada: {solution['times_used']}x (sucesso: {solution['times_successful']}x)")

        # Predições
        predictions = self.predict_failure()
        if predictions:
            report.append(f"\n### ALERTAS PREDITIVOS ({len(predictions)}) ###")
            for pred in predictions:
                report.append(f"\n⚠️  {pred['message']}")
                report.append(f"   Confiança: {pred['confidence']*100:.0f}%")

        report.append("\n" + "=" * 60)

        return "\n".join(report)

    def run_learning_cycle(self):
        """Executa um ciclo completo de aprendizado"""

        self.log_learning("Iniciando ciclo de aprendizado...")

        # 1. Analisar logs
        incidents = self.analyze_alerts_log()
        self.log_learning(f"Analisados {len(incidents)} incidentes")

        # 2. Aprender com incidentes
        if incidents:
            self.learn_from_incidents(incidents)

        # 3. Gerar predições
        predictions = self.predict_failure()
        if predictions:
            self.log_learning(f"Geradas {len(predictions)} predições de risco")

        # 4. Gerar relatório
        report = self.generate_report()

        self.log_learning("Ciclo de aprendizado concluído")

        return report


def main():
    """Função principal"""
    import sys

    monitor = SmartMonitor()

    if len(sys.argv) < 2:
        print("Uso: smart-monitor.py [comando]")
        print("")
        print("Comandos:")
        print("  learn       - Executar ciclo de aprendizado")
        print("  report      - Gerar relatório")
        print("  predict     - Mostrar predições de falhas")
        print("  solution    - Buscar solução para problema")
        print("  problems    - Listar problemas conhecidos")
        print("  patterns    - Listar padrões detectados")
        return

    command = sys.argv[1]

    if command == "learn":
        report = monitor.run_learning_cycle()
        print(report)

    elif command == "report":
        print(monitor.generate_report())

    elif command == "predict":
        predictions = monitor.predict_failure()
        if predictions:
            print("=== PREDIÇÕES DE FALHA ===\n")
            for pred in predictions:
                print(f"⚠️  {pred['message']}")
                print(f"   Tipo: {pred['type']}")
                print(f"   Confiança: {pred['confidence']*100:.0f}%")
                print()
        else:
            print("Nenhuma predição de falha no momento.")

    elif command == "solution":
        if len(sys.argv) < 4:
            print("Uso: smart-monitor.py solution <service> <error_type>")
            print("Exemplo: smart-monitor.py solution backend service_down")
            return

        service = sys.argv[2]
        error_type = sys.argv[3]

        solution = monitor.get_solution_for_problem(service, error_type)
        if solution:
            print(f"=== SOLUÇÃO PARA {service}/{error_type} ===\n")
            if solution["type"] == "learned":
                sol = solution["solution"]
                print(f"Descrição: {sol['description']}")
                print(f"Efetividade: {sol['effectiveness']*100:.0f}%")
                print("\nPassos:")
                for i, step in enumerate(sol['steps'], 1):
                    print(f"  {i}. {step}")
                print("\nPrevenção:")
                for tip in sol['prevention']:
                    print(f"  • {tip}")
            else:
                print("Causas possíveis:")
                for cause in solution["causes"]:
                    print(f"  • {cause}")
                print("\nDicas de prevenção:")
                for tip in solution["prevention"]:
                    print(f"  • {tip}")
        else:
            print(f"Nenhuma solução encontrada para {service}/{error_type}")

    elif command == "problems":
        print("=== PROBLEMAS CONHECIDOS ===\n")
        for problem in monitor.knowledge_base["problems"]:
            print(f"[{problem['id']}]")
            print(f"  Serviço: {problem['service']}")
            print(f"  Tipo: {problem['error_type']}")
            print(f"  Ocorrências: {problem['occurrences']}")
            print(f"  Último: {problem['last_seen']}")
            print()

    elif command == "patterns":
        print("=== PADRÕES DETECTADOS ===\n")
        for pattern in monitor.knowledge_base["patterns"]:
            print(f"[{pattern['id']}]")
            print(f"  Tipo: {pattern['type']}")
            print(f"  {pattern['description']}")
            print(f"  Recomendação: {pattern['recommendation']}")
            print()

    else:
        print(f"Comando desconhecido: {command}")


if __name__ == "__main__":
    main()
