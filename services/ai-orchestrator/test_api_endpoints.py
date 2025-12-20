#!/usr/bin/env python3
"""
Teste dos Endpoints da API do AI Orchestrator
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8002"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.CYAN}ℹ {text}{Colors.END}")

def test_endpoint(method, path, data=None, expected_status=200, description=""):
    """Testa um endpoint da API"""
    url = f"{BASE_URL}{path}"

    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            print_error(f"Método {method} não suportado")
            return False, None

        success = response.status_code == expected_status

        if success:
            print_success(f"{method} {path} -> {response.status_code}")
            if description:
                print_info(f"  {description}")
        else:
            print_error(f"{method} {path} -> {response.status_code} (esperado {expected_status})")
            print_info(f"  Response: {response.text[:200]}")

        try:
            return success, response.json()
        except:
            return success, response.text

    except requests.exceptions.ConnectionError:
        print_error(f"Conexão recusada para {url}")
        return False, None
    except Exception as e:
        print_error(f"Erro: {e}")
        return False, None


def run_tests():
    print_header("TESTE DOS ENDPOINTS DA API")
    print(f"Base URL: {BASE_URL}")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = []

    # ==================== V1 ENDPOINTS ====================
    print(f"\n{Colors.BOLD}=== ENDPOINTS V1 ==={Colors.END}")

    # GET /status
    success, data = test_endpoint("GET", "/status", description="Status do orchestrator V1")
    results.append(("GET /status", success))
    if success and data:
        print_info(f"  Agentes disponíveis: {len(data.get('agents_available', []))}")

    # GET /agents
    success, data = test_endpoint("GET", "/agents", description="Lista de agentes V1")
    results.append(("GET /agents", success))
    if success and data:
        print_info(f"  Total: {len(data)} agentes")

    # ==================== V2 ENDPOINTS ====================
    print(f"\n{Colors.BOLD}=== ENDPOINTS V2 ==={Colors.END}")

    # GET /v2/status
    success, data = test_endpoint("GET", "/v2/status", description="Status do orchestrator V2")
    results.append(("GET /v2/status", success))
    if success and data:
        print_info(f"  Version: {data.get('version')}, Running: {data.get('is_running')}")
        print_info(f"  Agent Types: {data.get('total_agent_types')}")

    # GET /v2/supported-agents
    success, data = test_endpoint("GET", "/v2/supported-agents", description="Lista de agentes suportados")
    results.append(("GET /v2/supported-agents", success))
    if success and data:
        print_info(f"  Total: {data.get('total')} agentes")
        print_info(f"  Categorias: {list(data.get('categories', {}).keys())}")

    # GET /v2/agents
    success, data = test_endpoint("GET", "/v2/agents", description="Lista de agentes ativos")
    results.append(("GET /v2/agents", success))

    # ==================== MESSAGE BUS ENDPOINTS ====================
    print(f"\n{Colors.BOLD}=== ENDPOINTS MESSAGE BUS ==={Colors.END}")

    # GET /v2/message/bus-status
    success, data = test_endpoint("GET", "/v2/message/bus-status", description="Status do Message Bus")
    results.append(("GET /v2/message/bus-status", success))
    if success and data:
        print_info(f"  Available: {data.get('available')}, Running: {data.get('is_running')}")
        print_info(f"  Agents Registered: {data.get('agents_registered')}")
        print_info(f"  Topics: {data.get('topics')}")

    # POST /v2/message/send (sem agentes, deve falhar graciosamente)
    success, data = test_endpoint("POST", "/v2/message/send",
        data={
            "sender_id": "orchestrator",
            "receiver_id": "test_agent",
            "content": {"test": "message"},
            "message_type": "direct",
            "priority": "normal"
        },
        expected_status=200,
        description="Envio de mensagem (destinatário não existe)"
    )
    results.append(("POST /v2/message/send", success))
    if success and data:
        print_info(f"  Result: {data}")

    # POST /v2/message/broadcast
    success, data = test_endpoint("POST", "/v2/message/broadcast",
        data={
            "sender_id": "orchestrator",
            "content": {"event": "test_broadcast"},
            "priority": "normal"
        },
        description="Broadcast (apenas orchestrator registrado)"
    )
    results.append(("POST /v2/message/broadcast", success))
    if success and data:
        print_info(f"  Delivered: {data.get('delivered_count', 0)}")

    # POST /v2/message/publish
    success, data = test_endpoint("POST", "/v2/message/publish",
        data={
            "sender_id": "orchestrator",
            "topic": "system.status",
            "content": {"status": "test"},
            "priority": "normal"
        },
        description="Publicar evento em tópico"
    )
    results.append(("POST /v2/message/publish", success))
    if success and data:
        print_info(f"  Delivered: {data.get('delivered_count', 0)}")

    # POST /v2/message/subscribe
    success, data = test_endpoint("POST", "/v2/message/subscribe",
        data={
            "agent_id": "orchestrator",
            "topic": "test.topic"
        },
        description="Inscrever em tópico"
    )
    results.append(("POST /v2/message/subscribe", success))
    if success and data:
        print_info(f"  Success: {data.get('success')}")

    # GET /v2/message/agents-by-type
    success, data = test_endpoint("GET", "/v2/message/agents-by-type/orchestrator",
        description="Buscar agentes por tipo"
    )
    results.append(("GET /v2/message/agents-by-type/{type}", success))
    if success and data:
        print_info(f"  Found: {data.get('count', 0)} agentes do tipo '{data.get('agent_type')}'")

    # GET /v2/message/agents-in-condominio (usando * que é o orchestrator)
    success, data = test_endpoint("GET", "/v2/message/agents-in-condominio/*",
        description="Buscar agentes por condomínio"
    )
    results.append(("GET /v2/message/agents-in-condominio/{id}", success))
    if success and data:
        print_info(f"  Found: {data.get('count', 0)} agentes no condomínio '*'")

    # ==================== RESUMO ====================
    print_header("RESUMO DOS TESTES")

    passed = sum(1 for _, s in results if s)
    failed = len(results) - passed

    for name, success in results:
        if success:
            print_success(name)
        else:
            print_error(name)

    print(f"\n{Colors.BOLD}Total: {passed}/{len(results)} endpoints funcionando{Colors.END}")

    if passed == len(results):
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 TODOS OS ENDPOINTS FUNCIONANDO!{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}⚠ {failed} endpoint(s) com problemas{Colors.END}")

    return passed, failed


if __name__ == "__main__":
    run_tests()
