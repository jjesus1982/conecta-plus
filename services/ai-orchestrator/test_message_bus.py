#!/usr/bin/env python3
"""
Teste do Sistema de Comunicação Full-Duplex entre Agentes
Conecta Plus - Plataforma de Gestão Condominial

Testa:
- Registro de agentes no Message Bus
- Comunicação direta entre agentes
- Broadcast para todos os agentes
- Padrão Request/Response
- Publish/Subscribe
"""

import sys
import asyncio
from datetime import datetime
from typing import Dict, Any, List

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

def print_info(text: str):
    print(f"{Colors.CYAN}ℹ {text}{Colors.END}")


async def test_message_bus_import():
    """Testa importação do Message Bus"""
    try:
        from agents.core.message_bus import (
            AgentMessageBus,
            MessageType,
            MessagePriority,
            BusMessage,
            message_bus,
            StandardTopics,
            MessageBusAgentMixin,
        )
        print_success("Message Bus importado com sucesso")
        return True, message_bus
    except ImportError as e:
        print_error(f"Erro ao importar Message Bus: {e}")
        return False, None


async def test_agent_registration(bus):
    """Testa registro de agentes no bus"""
    print(f"\n{Colors.BOLD}Testando registro de agentes...{Colors.END}")

    # Registrar alguns agentes simulados
    test_agents = [
        ("cftv_cond001", "cftv", "cond001"),
        ("acesso_cond001", "acesso", "cond001"),
        ("financeiro_cond001", "financeiro", "cond001"),
        ("portaria_cond001", "portaria_virtual", "cond001"),
        ("emergencia_cond001", "emergencia", "cond001"),
        ("cftv_cond002", "cftv", "cond002"),
        ("financeiro_cond002", "financeiro", "cond002"),
    ]

    queues = {}
    success_count = 0

    for agent_id, agent_type, condominio_id in test_agents:
        try:
            queue = bus.register_agent(agent_id, agent_type, condominio_id)
            queues[agent_id] = queue
            success_count += 1
            print_success(f"Agente {agent_id} registrado")
        except Exception as e:
            print_error(f"Erro ao registrar {agent_id}: {e}")

    print_info(f"Total registrado: {success_count}/{len(test_agents)}")
    return success_count == len(test_agents), queues


async def test_direct_message(bus, queues):
    """Testa envio de mensagem direta entre agentes"""
    print(f"\n{Colors.BOLD}Testando mensagem direta...{Colors.END}")

    from agents.core.message_bus import MessageType, MessagePriority

    # Enviar mensagem de CFTV para Emergência
    sender = "cftv_cond001"
    receiver = "emergencia_cond001"
    content = {"alert": "Movimentação suspeita detectada", "camera_id": "CAM-001"}

    success = await bus.send(
        sender_id=sender,
        receiver_id=receiver,
        content=content,
        message_type=MessageType.DIRECT,
        priority=MessagePriority.HIGH,
    )

    if success:
        print_success(f"Mensagem enviada de {sender} para {receiver}")

        # Verificar se a mensagem chegou na fila
        queue = queues.get(receiver)
        if queue and not queue.empty():
            msg = await queue.get()
            print_success(f"Mensagem recebida: {msg.content}")
            return True
        else:
            print_error("Mensagem não chegou na fila do destinatário")
            return False
    else:
        print_error("Falha ao enviar mensagem")
        return False


async def test_broadcast(bus, queues):
    """Testa broadcast para todos os agentes"""
    print(f"\n{Colors.BOLD}Testando broadcast...{Colors.END}")

    from agents.core.message_bus import MessageType, MessagePriority

    sender = "cftv_cond001"
    content = {"event": "Sistema de monitoramento atualizado", "timestamp": datetime.now().isoformat()}

    delivered = await bus.broadcast(
        sender_id=sender,
        content=content,
        message_type=MessageType.BROADCAST,
        priority=MessagePriority.NORMAL,
        exclude_sender=True,
    )

    print_info(f"Mensagens entregues: {delivered}")

    # Verificar se as mensagens chegaram
    messages_received = 0
    for agent_id, queue in queues.items():
        if agent_id != sender and not queue.empty():
            await queue.get()  # Consumir mensagem
            messages_received += 1

    success = messages_received > 0
    if success:
        print_success(f"Broadcast recebido por {messages_received} agentes")
    else:
        print_error("Nenhum agente recebeu o broadcast")

    return success


async def test_condominio_broadcast(bus, queues):
    """Testa broadcast apenas para agentes de um condomínio"""
    print(f"\n{Colors.BOLD}Testando broadcast por condomínio...{Colors.END}")

    sender = "financeiro_cond001"
    content = {"notice": "Boletos de janeiro disponíveis"}

    delivered = await bus.broadcast(
        sender_id=sender,
        content=content,
        exclude_sender=True,
        condominio_id="cond001",  # Apenas para cond001
    )

    print_info(f"Mensagens entregues para cond001: {delivered}")

    # Verificar que apenas agentes de cond001 receberam
    cond001_received = 0
    cond002_received = 0

    for agent_id, queue in queues.items():
        if not queue.empty():
            msg = await queue.get()
            if "cond001" in agent_id:
                cond001_received += 1
            elif "cond002" in agent_id:
                cond002_received += 1

    success = cond001_received > 0 and cond002_received == 0
    if success:
        print_success(f"Broadcast isolado: {cond001_received} em cond001, {cond002_received} em cond002")
    else:
        print_error(f"Broadcast não isolado: {cond001_received} em cond001, {cond002_received} em cond002")

    return success


async def test_request_response(bus, queues):
    """Testa padrão request/response"""
    print(f"\n{Colors.BOLD}Testando request/response...{Colors.END}")

    sender = "portaria_cond001"
    receiver = "financeiro_cond001"

    # Criar task para simular resposta do financeiro
    async def responder():
        queue = queues.get(receiver)
        if queue:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=5.0)
                # Simular resposta
                await bus.respond(
                    sender_id=receiver,
                    original_message=msg,
                    content={"status": "ok", "inadimplente": False, "unidade": "101"}
                )
            except asyncio.TimeoutError:
                pass

    # Iniciar responder em background
    responder_task = asyncio.create_task(responder())

    # Enviar request
    response = await bus.request(
        sender_id=sender,
        receiver_id=receiver,
        content={"query": "verificar_inadimplencia", "unidade": "101"},
        timeout=5.0,
    )

    await responder_task

    if response:
        print_success(f"Resposta recebida: {response}")
        return True
    else:
        print_error("Timeout aguardando resposta")
        return False


async def test_publish_subscribe(bus, queues):
    """Testa padrão publish/subscribe"""
    print(f"\n{Colors.BOLD}Testando publish/subscribe...{Colors.END}")

    from agents.core.message_bus import StandardTopics

    # Inscrever agentes em tópicos
    bus.subscribe("emergencia_cond001", StandardTopics.SECURITY_ALERT)
    bus.subscribe("portaria_cond001", StandardTopics.SECURITY_ALERT)
    bus.subscribe("cftv_cond001", StandardTopics.SECURITY_ALERT)

    print_info("Agentes inscritos em security.alert")

    # Publicar evento
    delivered = await bus.publish(
        sender_id="acesso_cond001",
        topic=StandardTopics.SECURITY_ALERT,
        content={"alert": "Tentativa de acesso negado", "local": "Portão principal"},
    )

    print_info(f"Evento publicado para {delivered} inscritos")

    # Verificar recebimento
    received = 0
    for agent_id in ["emergencia_cond001", "portaria_cond001", "cftv_cond001"]:
        queue = queues.get(agent_id)
        if queue and not queue.empty():
            await queue.get()
            received += 1

    success = received > 0
    if success:
        print_success(f"Evento recebido por {received} inscritos")
    else:
        print_error("Nenhum inscrito recebeu o evento")

    return success


async def test_metrics(bus):
    """Testa métricas do message bus"""
    print(f"\n{Colors.BOLD}Testando métricas...{Colors.END}")

    metrics = bus.get_metrics()
    status = bus.get_status()

    print_info(f"Métricas: {metrics}")
    print_info(f"Agentes registrados: {status.get('agents_registered', 0)}")

    success = metrics.get("messages_sent", 0) > 0
    if success:
        print_success("Métricas sendo coletadas corretamente")
    else:
        print_error("Métricas não registradas")

    return success


async def test_get_agents(bus):
    """Testa busca de agentes por tipo e condomínio"""
    print(f"\n{Colors.BOLD}Testando busca de agentes...{Colors.END}")

    # Buscar agentes por tipo
    cftv_agents = bus.get_agents_by_type("cftv")
    print_info(f"Agentes CFTV: {cftv_agents}")

    # Buscar agentes por condomínio
    cond001_agents = bus.get_agents_by_condominio("cond001")
    print_info(f"Agentes em cond001: {cond001_agents}")

    success = len(cftv_agents) >= 1 and len(cond001_agents) >= 1
    if success:
        print_success("Busca de agentes funcionando")
    else:
        print_error("Busca de agentes não funcionou")

    return success


async def run_tests():
    """Executa todos os testes"""
    print_header("TESTE DO MESSAGE BUS - COMUNICAÇÃO FULL-DUPLEX")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    results = []

    # 1. Importação
    success, bus = await test_message_bus_import()
    results.append(("Importação", success))

    if not success or not bus:
        print_error("Não foi possível continuar sem o Message Bus")
        return

    # Reset para testes limpos
    bus.reset()
    await bus.start()

    # 2. Registro de agentes
    success, queues = await test_agent_registration(bus)
    results.append(("Registro de Agentes", success))

    # 3. Mensagem direta
    success = await test_direct_message(bus, queues)
    results.append(("Mensagem Direta", success))

    # 4. Broadcast
    success = await test_broadcast(bus, queues)
    results.append(("Broadcast", success))

    # 5. Broadcast por condomínio
    success = await test_condominio_broadcast(bus, queues)
    results.append(("Broadcast Condomínio", success))

    # 6. Request/Response
    success = await test_request_response(bus, queues)
    results.append(("Request/Response", success))

    # 7. Publish/Subscribe
    success = await test_publish_subscribe(bus, queues)
    results.append(("Publish/Subscribe", success))

    # 8. Métricas
    success = await test_metrics(bus)
    results.append(("Métricas", success))

    # 9. Busca de agentes
    success = await test_get_agents(bus)
    results.append(("Busca de Agentes", success))

    # Limpar
    await bus.stop()

    # Resumo
    print_header("RESUMO DOS TESTES")

    passed = sum(1 for _, s in results if s)
    failed = len(results) - passed

    for name, success in results:
        if success:
            print_success(name)
        else:
            print_error(name)

    print(f"\n{Colors.BOLD}Total: {passed}/{len(results)} testes passaram{Colors.END}")

    if passed == len(results):
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 TODOS OS TESTES PASSARAM!{Colors.END}")
        print(f"{Colors.GREEN}Comunicação full-duplex entre agentes funcionando!{Colors.END}")
    else:
        print(f"\n{Colors.YELLOW}⚠ {failed} teste(s) falharam{Colors.END}")

    return passed, failed


if __name__ == "__main__":
    passed, failed = asyncio.run(run_tests())
    sys.exit(0 if failed == 0 else 1)
