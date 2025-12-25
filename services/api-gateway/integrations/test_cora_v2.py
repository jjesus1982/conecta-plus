#!/usr/bin/env python3
"""
Script de teste para validar os novos métodos V2 do cliente Cora Bank

Testa:
- Carnês (boletos parcelados)
- Transferências bancárias
- Pagamento de impostos (DARF e GPS)
- Consulta de dados da conta
- Lista de bancos
- Novos webhooks V2
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Adiciona diretório parent ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.cora_bank import criar_cliente_cora_mock, CoraBankClient


async def test_criar_carne():
    """Testa criação de carnê (boletos parcelados)"""
    print("\n" + "=" * 60)
    print("TESTE: Criar Carnê (3 parcelas de R$ 850,00)")
    print("=" * 60)

    client = criar_cliente_cora_mock()

    resultado = await client.criar_carne(
        valor_total=2550.00,
        numero_parcelas=3,
        data_primeiro_vencimento=(datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
        pagador={
            "nome": "Carlos Silva",
            "documento": "12345678900",
            "email": "carlos@example.com"
        },
        descricao="Condomínio 01/2025 - Carnê"
    )

    print(f"✅ Carnê criado com sucesso!")
    print(f"   ID do Carnê: {resultado['carne_id']}")
    print(f"   Valor Total: R$ {resultado['valor_total']:.2f}")
    print(f"   Número de Parcelas: {resultado['numero_parcelas']}")
    print(f"\n📋 Boletos gerados:")

    for boleto in resultado['boletos']:
        print(f"   • Parcela {boleto['parcela']}/{resultado['numero_parcelas']}")
        print(f"     - ID: {boleto['id']}")
        print(f"     - Valor: R$ {boleto['valor']:.2f}")
        print(f"     - Vencimento: {boleto['vencimento']}")
        print(f"     - Nosso Número: {boleto['nosso_numero']}")
        print(f"     - Status: {boleto['status']}")

    assert len(resultado['boletos']) == 3, "Deve gerar 3 boletos"
    assert resultado['boletos'][0]['valor'] == 850.00, "Cada parcela deve ser R$ 850,00"

    await client.close()
    return True


async def test_transferencias():
    """Testa transferências bancárias"""
    print("\n" + "=" * 60)
    print("TESTE: Transferências Bancárias")
    print("=" * 60)

    client = criar_cliente_cora_mock()

    # 1. Criar transferência
    print("\n1️⃣  Criando transferência TED...")
    transferencia = await client.criar_transferencia(
        valor=5000.00,
        beneficiario={
            "nome": "Fornecedor ABC Ltda",
            "documento": "12345678000199",
            "tipo_pessoa": "PJ",
            "banco": "001",
            "agencia": "1234",
            "conta": "567890",
            "digito": "1",
            "tipo_conta": "CHECKING"
        },
        descricao="Pagamento de serviços",
        tipo="TED"
    )

    print(f"✅ Transferência criada!")
    print(f"   ID: {transferencia['id']}")
    print(f"   Status: {transferencia['status']}")
    print(f"   Valor: R$ {transferencia['valor']:.2f}")
    print(f"   Beneficiário: {transferencia['beneficiario']}")
    print(f"   Tipo: {transferencia['tipo']}")

    # 2. Listar transferências
    print("\n2️⃣  Listando transferências...")
    lista = await client.listar_transferencias(
        data_inicio=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        data_fim=datetime.now().strftime("%Y-%m-%d")
    )

    print(f"✅ {lista['total']} transferências encontradas:")
    for t in lista['items']:
        print(f"   • {t['beneficiario']} - R$ {t['valor']:.2f} ({t['tipo']}) - {t['status']}")

    # 3. Listar bancos
    print("\n3️⃣  Listando bancos disponíveis...")
    bancos = await client.listar_bancos()

    print(f"✅ {len(bancos)} bancos disponíveis:")
    for banco in bancos[:5]:  # Mostra apenas 5
        print(f"   • {banco['codigo']} - {banco['nome']}")

    assert transferencia['status'] in ["PROCESSING", "COMPLETED"], "Status deve ser válido"
    assert len(bancos) > 0, "Deve retornar lista de bancos"

    await client.close()
    return True


async def test_impostos():
    """Testa pagamento de impostos (DARF e GPS)"""
    print("\n" + "=" * 60)
    print("TESTE: Pagamento de Impostos")
    print("=" * 60)

    client = criar_cliente_cora_mock()

    # 1. Pagar DARF
    print("\n1️⃣  Pagando DARF...")
    darf = await client.pagar_darf(
        codigo_receita="0190",
        periodo_apuracao="2025-01",
        valor_principal=1500.00,
        valor_multa=30.00,
        valor_juros=15.00,
        numero_referencia="REF123456"
    )

    print(f"✅ DARF pago com sucesso!")
    print(f"   ID: {darf['id']}")
    print(f"   Status: {darf['status']}")
    print(f"   Valor Principal: R$ {darf['valor_principal']:.2f}")
    print(f"   Multa: R$ {darf['valor_multa']:.2f}")
    print(f"   Juros: R$ {darf['valor_juros']:.2f}")
    print(f"   Valor Total: R$ {darf['valor_total']:.2f}")
    print(f"   Nº Autenticação: {darf['numero_autenticacao']}")

    # 2. Pagar GPS
    print("\n2️⃣  Pagando GPS...")
    gps = await client.pagar_gps(
        codigo_pagamento="2100",
        competencia="2025-01",
        identificador="12345678900",
        valor=500.00
    )

    print(f"✅ GPS pago com sucesso!")
    print(f"   ID: {gps['id']}")
    print(f"   Status: {gps['status']}")
    print(f"   Valor: R$ {gps['valor']:.2f}")
    print(f"   Competência: {gps['competencia']}")
    print(f"   Nº Autenticação: {gps['numero_autenticacao']}")

    assert darf['valor_total'] == 1545.00, "Valor total DARF incorreto"
    assert gps['valor'] == 500.00, "Valor GPS incorreto"

    await client.close()
    return True


async def test_dados_conta():
    """Testa consulta de dados da conta"""
    print("\n" + "=" * 60)
    print("TESTE: Consultar Dados da Conta")
    print("=" * 60)

    client = criar_cliente_cora_mock()

    dados = await client.consultar_dados_conta()

    print(f"✅ Dados da conta consultados:")
    print(f"   ID: {dados['id']}")
    print(f"   Nome: {dados['nome']}")
    print(f"   Documento: {dados['documento']}")
    print(f"   Tipo Pessoa: {dados['tipo_pessoa']}")
    print(f"   Banco: {dados['banco']}")
    print(f"   Agência: {dados['agencia']}")
    print(f"   Conta: {dados['conta']}-{dados['digito']}")
    print(f"   Status: {dados['status']}")
    print(f"   Data Criação: {dados['data_criacao']}")

    assert dados['banco'] == "403", "Código do banco Cora deve ser 403"
    assert dados['status'] == "ACTIVE", "Conta deve estar ativa"

    await client.close()
    return True


async def test_webhooks_v2():
    """Testa processamento de webhooks V2"""
    print("\n" + "=" * 60)
    print("TESTE: Processamento de Webhooks V2")
    print("=" * 60)

    # 1. Webhook payment.created
    print("\n1️⃣  Webhook: payment.created")
    webhook1 = {
        "type": "payment.created",
        "id": "evt_001",
        "data": {
            "id": "pay_123",
            "amount": 85000,
            "payment_type": "BOLETO",
            "status": "PROCESSING",
            "created_at": "2025-01-15T10:30:00Z"
        }
    }

    resultado1 = CoraBankClient.processar_webhook(webhook1)
    print(f"✅ {resultado1}")
    assert resultado1['tipo'] == "pagamento_criado"
    assert resultado1['valor'] == 850.00

    # 2. Webhook payment.failed
    print("\n2️⃣  Webhook: payment.failed")
    webhook2 = {
        "type": "payment.failed",
        "id": "evt_002",
        "data": {
            "id": "pay_124",
            "failure_reason": "Saldo insuficiente",
            "error_code": "INSUFFICIENT_FUNDS",
            "failed_at": "2025-01-15T10:35:00Z"
        }
    }

    resultado2 = CoraBankClient.processar_webhook(webhook2)
    print(f"✅ {resultado2}")
    assert resultado2['tipo'] == "pagamento_falhou"
    assert resultado2['motivo'] == "Saldo insuficiente"

    # 3. Webhook transfer.completed
    print("\n3️⃣  Webhook: transfer.completed")
    webhook3 = {
        "type": "transfer.completed",
        "id": "evt_003",
        "data": {
            "id": "trans_456",
            "amount": 500000,
            "transfer_type": "TED",
            "beneficiary": {"name": "Fornecedor XYZ"},
            "completed_at": "2025-01-15T11:00:00Z"
        }
    }

    resultado3 = CoraBankClient.processar_webhook(webhook3)
    print(f"✅ {resultado3}")
    assert resultado3['tipo'] == "transferencia_concluida"
    assert resultado3['valor'] == 5000.00

    # 4. Webhook transfer.failed
    print("\n4️⃣  Webhook: transfer.failed")
    webhook4 = {
        "type": "transfer.failed",
        "id": "evt_004",
        "data": {
            "id": "trans_457",
            "failure_reason": "Conta de destino inválida",
            "error_code": "INVALID_ACCOUNT",
            "failed_at": "2025-01-15T11:05:00Z"
        }
    }

    resultado4 = CoraBankClient.processar_webhook(webhook4)
    print(f"✅ {resultado4}")
    assert resultado4['tipo'] == "transferencia_falhou"

    # 5. Webhook installment.paid
    print("\n5️⃣  Webhook: installment.paid")
    webhook5 = {
        "type": "installment.paid",
        "id": "evt_005",
        "data": {
            "id": "inst_789",
            "installment_plan_id": "carne_001",
            "installment_number": 1,
            "paid_amount": 85000,
            "paid_at": "2025-01-15T12:00:00Z"
        }
    }

    resultado5 = CoraBankClient.processar_webhook(webhook5)
    print(f"✅ {resultado5}")
    assert resultado5['tipo'] == "parcela_paga"
    assert resultado5['numero_parcela'] == 1

    print("\n✅ Todos os webhooks V2 processados corretamente!")
    return True


async def main():
    """Executa todos os testes"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "TESTES - CLIENTE CORA BANK V2" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")

    testes = [
        ("Criar Carnê", test_criar_carne),
        ("Transferências Bancárias", test_transferencias),
        ("Pagamento de Impostos", test_impostos),
        ("Dados da Conta", test_dados_conta),
        ("Webhooks V2", test_webhooks_v2)
    ]

    resultados = []

    for nome, teste in testes:
        try:
            sucesso = await teste()
            resultados.append((nome, sucesso, None))
        except Exception as e:
            resultados.append((nome, False, str(e)))
            print(f"\n❌ ERRO no teste '{nome}': {e}")

    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)

    total = len(resultados)
    sucessos = sum(1 for _, sucesso, _ in resultados if sucesso)
    falhas = total - sucessos

    for nome, sucesso, erro in resultados:
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"{status} - {nome}")
        if erro:
            print(f"         Erro: {erro}")

    print("\n" + "-" * 60)
    print(f"Total: {total} testes")
    print(f"✅ Sucesso: {sucessos}")
    print(f"❌ Falhas: {falhas}")
    print(f"Taxa de Sucesso: {(sucessos/total)*100:.1f}%")
    print("=" * 60 + "\n")

    if falhas > 0:
        sys.exit(1)
    else:
        print("🎉 TODOS OS TESTES PASSARAM COM SUCESSO! 🎉\n")
        print("✅ Cliente Cora V2 está pronto para uso!")
        print("\nPróximos passos:")
        print("  1. Implementar modelos de banco de dados (Etapa 1)")
        print("  2. Criar repositórios (Etapa 2)")
        print("  3. Implementar API endpoints (Etapa 3)")
        print("  4. Configurar webhooks (Etapa 4)")
        print("  5. Desenvolver frontend (Etapas 5-6)\n")


if __name__ == "__main__":
    asyncio.run(main())
