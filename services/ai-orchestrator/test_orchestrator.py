#!/usr/bin/env python3
"""
Teste do AI Orchestrator com 36 Agentes
Conecta Plus - Plataforma de Gestão Condominial
"""

import sys
import asyncio
from typing import Dict, List, Tuple
from datetime import datetime

sys.path.insert(0, '/opt/conecta-plus')
sys.path.insert(0, '/opt/conecta-plus/services/ai-orchestrator')

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text: str):
    print(f"{Colors.CYAN}ℹ {text}{Colors.END}")


# Lista esperada de 36 agentes
EXPECTED_AGENTS = [
    # Segurança (1-5)
    "cftv", "acesso", "automacao", "alarme", "rede",
    # Portaria e Atendimento (6-8)
    "portaria_virtual", "voip", "atendimento",
    # RH e Gestão de Pessoas (9-10)
    "rh", "facilities",
    # Manutenção (11-12)
    "manutencao", "infraestrutura",
    # Gestão Condominial (13-16)
    "sindico", "financeiro", "assembleias", "reservas",
    # Moradores e Comunicação (17-19)
    "morador", "comunicacao", "encomendas",
    # Ocorrências e Compliance (20-22)
    "ocorrencias", "compliance", "analytics",
    # IA e Suporte (23-24)
    "visao_ia", "suporte",
    # Novos Agentes (25-36)
    "juridico", "imobiliario", "sustentabilidade", "social",
    "pet", "estacionamento", "emergencia", "conhecimento",
    "auditoria", "fornecedores", "valorizacao", "comercial"
]


def test_import_orchestrator() -> Tuple[bool, str]:
    """Testa importação do orchestrator"""
    try:
        from orchestrator import AIOrchestrator, AIOrchestrator2, orchestrator_v2
        return True, "Orchestrator importado com sucesso"
    except ImportError as e:
        return False, f"Erro ao importar orchestrator: {e}"


def test_agent_capabilities() -> Tuple[bool, str, Dict]:
    """Testa se todos os 36 agentes estão em AGENT_CAPABILITIES"""
    try:
        from orchestrator import AIOrchestrator

        capabilities = AIOrchestrator.AGENT_CAPABILITIES
        registered = set(capabilities.keys())
        expected = set(EXPECTED_AGENTS)

        missing = expected - registered
        extra = registered - expected

        details = {
            "total": len(registered),
            "expected": len(expected),
            "missing": list(missing),
            "extra": list(extra)
        }

        if missing:
            return False, f"Agentes faltando em CAPABILITIES: {missing}", details

        return True, f"Todos os {len(registered)} agentes registrados em CAPABILITIES", details

    except Exception as e:
        return False, f"Erro: {e}", {}


def test_agent_factories() -> Tuple[bool, str, Dict]:
    """Testa se todos os 36 agentes estão em AGENT_FACTORIES"""
    try:
        from orchestrator import AIOrchestrator2

        factories = AIOrchestrator2.AGENT_FACTORIES
        registered = set(factories.keys())
        expected = set(EXPECTED_AGENTS)

        missing = expected - registered
        extra = registered - expected

        details = {
            "total": len(registered),
            "expected": len(expected),
            "missing": list(missing),
            "extra": list(extra)
        }

        if missing:
            return False, f"Agentes faltando em FACTORIES: {missing}", details

        return True, f"Todos os {len(registered)} agentes registrados em FACTORIES", details

    except Exception as e:
        return False, f"Erro: {e}", {}


def test_agent_descriptions() -> Tuple[bool, str, Dict]:
    """Testa se todos os 36 agentes têm descrições"""
    try:
        from orchestrator import AIOrchestrator2

        descriptions = AIOrchestrator2.AGENT_DESCRIPTIONS
        registered = set(descriptions.keys())
        expected = set(EXPECTED_AGENTS)

        missing = expected - registered

        details = {
            "total": len(registered),
            "missing": list(missing)
        }

        if missing:
            return False, f"Agentes sem descrição: {missing}", details

        return True, f"Todos os {len(registered)} agentes têm descrições", details

    except Exception as e:
        return False, f"Erro: {e}", {}


def test_routing_keywords() -> Tuple[bool, str, List[Dict]]:
    """Testa roteamento por keywords para cada agente"""
    try:
        from orchestrator import AIOrchestrator

        # Mensagens de teste para cada agente
        test_messages = {
            "cftv": "Preciso ver as câmeras do estacionamento",
            "acesso": "Cadastrar biometria de novo morador",
            "automacao": "O portão não está abrindo",
            "alarme": "O alarme disparou na área comum",
            "rede": "A internet está lenta no bloco A",
            "portaria_virtual": "Tem um visitante na portaria",
            "voip": "Preciso transferir uma ligação para o ramal 200",
            "atendimento": "Quero falar com a central de atendimento",
            "rh": "Preciso calcular a folha do funcionário",
            "facilities": "A piscina precisa de limpeza",
            "manutencao": "Abrir ordem de serviço para conserto",
            "infraestrutura": "O servidor está fora do ar",
            "sindico": "O síndico precisa aprovar essa despesa",
            "financeiro": "Gerar boleto de condomínio",
            "assembleias": "Convocar assembleia para votação",
            "reservas": "Reservar o salão de festas",
            "morador": "Cadastrar novo morador na unidade 101",
            "comunicacao": "Enviar comunicado via whatsapp",
            "encomendas": "Chegou uma encomenda dos correios",
            "ocorrencias": "Registrar reclamação de barulho",
            "compliance": "Verificar conformidade com LGPD",
            "analytics": "Gerar relatório de indicadores",
            "visao_ia": "Detectar placa do veículo",
            "suporte": "Abrir ticket de suporte técnico",
            "juridico": "Consultar advogado sobre processo",
            "imobiliario": "Cadastrar imóvel para locação",
            "sustentabilidade": "Monitorar consumo de energia solar",
            "social": "Criar evento de festa junina",
            "pet": "Cadastrar cachorro do morador",
            "estacionamento": "Reservar vaga de estacionamento",
            "emergencia": "Socorro! Tem um incêndio no prédio",
            "conhecimento": "Qual é o horário da piscina? FAQ",
            "auditoria": "Realizar auditoria financeira",
            "fornecedores": "Solicitar cotação de fornecedor",
            "valorizacao": "Avaliar valorização do patrimônio",
            "comercial": "Agendar demo para cliente lead",
        }

        orch = AIOrchestrator()
        results = []
        correct = 0

        for expected_agent, message in test_messages.items():
            # Simular análise de keywords
            message_lower = message.lower()
            scores = {}

            for agent, config in orch.AGENT_CAPABILITIES.items():
                score = 0
                for keyword in config["keywords"]:
                    if keyword in message_lower:
                        score += 2
                for intent in config["intents"]:
                    if intent in message_lower:
                        score += 1
                if score > 0:
                    scores[agent] = score

            if scores:
                routed_agent = max(scores, key=scores.get)
                best_score = scores[routed_agent]
            else:
                routed_agent = "suporte"
                best_score = 0

            is_correct = routed_agent == expected_agent
            if is_correct:
                correct += 1

            results.append({
                "expected": expected_agent,
                "routed": routed_agent,
                "score": best_score,
                "correct": is_correct,
                "message": message[:40] + "..."
            })

        accuracy = (correct / len(test_messages)) * 100

        if accuracy >= 80:
            return True, f"Roteamento: {correct}/{len(test_messages)} corretos ({accuracy:.1f}%)", results
        else:
            return False, f"Roteamento: {correct}/{len(test_messages)} corretos ({accuracy:.1f}%)", results

    except Exception as e:
        return False, f"Erro: {e}", []


def test_factory_imports() -> Tuple[bool, str, Dict]:
    """Testa se as factories dos agentes podem ser importadas"""
    try:
        from orchestrator import AIOrchestrator2

        success = []
        failed = []

        for agent_type, factory_path in AIOrchestrator2.AGENT_FACTORIES.items():
            try:
                module_path, factory_name = factory_path.rsplit(":", 1)
                import_path = module_path.replace("-", "_")

                # Tentar importar o módulo
                module = __import__(import_path, fromlist=[factory_name])
                factory_func = getattr(module, factory_name)

                if callable(factory_func):
                    success.append(agent_type)
                else:
                    failed.append((agent_type, "Factory não é callable"))

            except ImportError as e:
                failed.append((agent_type, f"ImportError: {e}"))
            except AttributeError as e:
                failed.append((agent_type, f"AttributeError: {e}"))
            except Exception as e:
                failed.append((agent_type, f"Erro: {e}"))

        details = {
            "success": success,
            "failed": failed,
            "total": len(AIOrchestrator2.AGENT_FACTORIES),
            "success_count": len(success),
            "failed_count": len(failed)
        }

        if len(failed) == 0:
            return True, f"Todas as {len(success)} factories importadas com sucesso", details
        elif len(success) > len(failed):
            return True, f"{len(success)} factories OK, {len(failed)} falharam", details
        else:
            return False, f"{len(failed)} factories falharam", details

    except Exception as e:
        return False, f"Erro: {e}", {}


def test_orchestrator_v2_status() -> Tuple[bool, str, Dict]:
    """Testa o status do orchestrator V2"""
    try:
        from orchestrator import orchestrator_v2

        status = orchestrator_v2.get_status()

        checks = {
            "version": status.get("version") == "2.0",
            "total_agent_types": status.get("total_agent_types") == 36,
            "has_categories": "supported_agents" in status and "categories" in status["supported_agents"],
            "has_descriptions": "descriptions" in status.get("supported_agents", {}),
        }

        all_passed = all(checks.values())

        return all_passed, f"Status V2 validado: {sum(checks.values())}/{len(checks)} checks", {
            "status": status,
            "checks": checks
        }

    except Exception as e:
        return False, f"Erro: {e}", {}


def test_supported_agents_method() -> Tuple[bool, str, Dict]:
    """Testa o método get_supported_agents"""
    try:
        from orchestrator import orchestrator_v2

        agents = orchestrator_v2.get_supported_agents()
        count = orchestrator_v2.get_agent_count()

        if count == 36 and len(agents) == 36:
            return True, f"get_supported_agents retornou {count} agentes", {"agents": agents}
        else:
            return False, f"Esperado 36, retornou {count}", {"agents": agents}

    except Exception as e:
        return False, f"Erro: {e}", {}


async def test_simple_route() -> Tuple[bool, str, List]:
    """Testa o método _simple_route"""
    try:
        from orchestrator import orchestrator_v2

        test_cases = [
            ("Tem uma emergência no prédio!", "emergencia"),
            ("O alarme disparou", "alarme"),
            ("Visitante na portaria", "portaria_virtual"),
            ("Gerar boleto", "financeiro"),
            ("Conserto do elevador", "manutencao"),
            ("Reservar churrasqueira", "reservas"),
            ("Encomenda chegou", "encomendas"),
            ("Reclamação de barulho", "ocorrencias"),
            ("Consultar advogado", "juridico"),
            ("Vaga de garagem", "estacionamento"),
            ("Meu cachorro precisa vacinar", "pet"),
            ("Votação da assembleia", "assembleias"),
            ("Ajuda com o sistema", "conhecimento"),
            ("Central de atendimento", "atendimento"),
        ]

        results = []
        correct = 0

        for message, expected in test_cases:
            routed = orchestrator_v2._simple_route(message)
            is_correct = routed == expected
            if is_correct:
                correct += 1
            results.append({
                "message": message,
                "expected": expected,
                "routed": routed,
                "correct": is_correct
            })

        accuracy = (correct / len(test_cases)) * 100

        return accuracy >= 70, f"Simple route: {correct}/{len(test_cases)} ({accuracy:.1f}%)", results

    except Exception as e:
        return False, f"Erro: {e}", []


def run_tests():
    """Executa todos os testes"""
    print_header("TESTE DO AI ORCHESTRATOR - 36 AGENTES")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    tests = [
        ("Importação do Orchestrator", test_import_orchestrator),
        ("AGENT_CAPABILITIES (36 agentes)", test_agent_capabilities),
        ("AGENT_FACTORIES (36 agentes)", test_agent_factories),
        ("AGENT_DESCRIPTIONS (36 agentes)", test_agent_descriptions),
        ("Roteamento por Keywords", test_routing_keywords),
        ("Import das Factories", test_factory_imports),
        ("Status do Orchestrator V2", test_orchestrator_v2_status),
        ("Método get_supported_agents", test_supported_agents_method),
    ]

    results = []
    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n{Colors.BOLD}Testando: {name}{Colors.END}")
        try:
            result = test_func()
            success, message, details = result if len(result) == 3 else (*result, {})

            if success:
                print_success(message)
                passed += 1
            else:
                print_error(message)
                failed += 1

                # Mostrar detalhes de falha
                if isinstance(details, dict) and details.get("missing"):
                    print_warning(f"  Faltando: {details['missing']}")
                if isinstance(details, dict) and details.get("failed"):
                    for agent, error in details.get("failed", [])[:5]:
                        print_warning(f"  {agent}: {error}")

            results.append((name, success, message))

        except Exception as e:
            print_error(f"Exceção: {e}")
            failed += 1
            results.append((name, False, str(e)))

    # Teste assíncrono
    print(f"\n{Colors.BOLD}Testando: Simple Route (async){Colors.END}")
    try:
        success, message, details = asyncio.run(test_simple_route())
        if success:
            print_success(message)
            passed += 1
        else:
            print_error(message)
            failed += 1
            # Mostrar erros
            for r in details:
                if not r.get("correct"):
                    print_warning(f"  '{r['message']}' -> esperado '{r['expected']}', obteve '{r['routed']}'")
        results.append(("Simple Route", success, message))
    except Exception as e:
        print_error(f"Exceção: {e}")
        failed += 1

    # Resumo final
    print_header("RESUMO DOS TESTES")

    total = passed + failed
    percentage = (passed / total) * 100 if total > 0 else 0

    print(f"Total de testes: {total}")
    print(f"{Colors.GREEN}Passou: {passed}{Colors.END}")
    print(f"{Colors.RED}Falhou: {failed}{Colors.END}")
    print(f"Taxa de sucesso: {percentage:.1f}%")

    if percentage == 100:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 TODOS OS TESTES PASSARAM!{Colors.END}")
    elif percentage >= 80:
        print(f"\n{Colors.YELLOW}{Colors.BOLD}⚠ MAIORIA DOS TESTES PASSOU{Colors.END}")
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}❌ MUITOS TESTES FALHARAM{Colors.END}")

    return passed, failed


if __name__ == "__main__":
    passed, failed = run_tests()
    sys.exit(0 if failed == 0 else 1)
