"""
Conecta Plus - Repositórios Financeiros
Acesso a dados do módulo financeiro
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from uuid import UUID
import json

import sys
sys.path.append('..')
from database import fetch, fetchrow, fetchval, execute, records_to_list, record_to_dict


class BoletoRepository:
    """Repositório para operações com boletos"""

    @staticmethod
    async def list(
        condominio_id: str,
        status: Optional[str] = None,
        unidade_id: Optional[str] = None,
        competencia: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Lista boletos com filtros"""
        offset = (page - 1) * limit

        # Query base
        query = """
            SELECT
                b.id, b.unidade_id, b.referencia as competencia,
                b.valor, b.valor_juros as juros, b.valor_multa as multa,
                b.valor_desconto as desconto, b.valor_total,
                b.data_vencimento as vencimento, b.data_pagamento,
                b.status, b.tipo, b.descricao,
                b.linha_digitavel, b.codigo_barras,
                b.pix_copia_cola, b.pix_qrcode, b.pix_txid,
                b.nosso_numero, b.forma_pagamento,
                b.banco_id, b.banco_boleto_id,
                b.created_at, b.updated_at,
                u.numero as unidade_numero, u.bloco as unidade_bloco,
                usr.nome as morador_nome
            FROM financeiro.boletos b
            LEFT JOIN financeiro.unidades u ON b.unidade_id = u.id
            LEFT JOIN financeiro.moradores m ON m.unidade_id = u.id AND m.principal = true
            LEFT JOIN financeiro.usuarios usr ON m.usuario_id = usr.id
            WHERE b.condominio_id = $1
        """
        params = [condominio_id]
        param_count = 1

        if status:
            param_count += 1
            query += f" AND b.status = ${param_count}"
            params.append(status)

        if unidade_id:
            param_count += 1
            query += f" AND b.unidade_id = ${param_count}"
            params.append(unidade_id)

        if competencia:
            param_count += 1
            query += f" AND b.referencia = ${param_count}"
            params.append(competencia)

        # Count total
        count_query = query.replace(
            "SELECT \n                b.id, b.unidade_id",
            "SELECT COUNT(*)"
        ).split("FROM financeiro.boletos")[0] + "FROM financeiro.boletos" + query.split("FROM financeiro.boletos")[1]
        count_query = f"SELECT COUNT(*) FROM financeiro.boletos b WHERE b.condominio_id = $1"
        if status:
            count_query += f" AND b.status = $2"
        total = await fetchval(count_query, *params[:2 if status else 1])

        # Add order and pagination
        query += f" ORDER BY b.data_vencimento DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([limit, offset])

        rows = await fetch(query, *params)

        # Format results
        items = []
        for row in rows:
            item = record_to_dict(row)
            # Format unidade display
            if item.get('unidade_bloco') and item.get('unidade_numero'):
                item['unidade'] = f"Apt {item['unidade_numero']} - Bloco {item['unidade_bloco']}"
            item['morador'] = item.get('morador_nome', 'N/A')
            # Calculate days late
            if item['status'] == 'vencido' and item.get('vencimento'):
                dias_atraso = (date.today() - item['vencimento']).days
                item['dias_atraso'] = max(0, dias_atraso)
            items.append(item)

        return {
            "items": items,
            "total": total or 0,
            "page": page,
            "limit": limit,
            "pages": ((total or 0) + limit - 1) // limit
        }

    @staticmethod
    async def get_by_id(boleto_id: str) -> Optional[Dict]:
        """Busca boleto por ID"""
        query = """
            SELECT
                b.*,
                u.numero as unidade_numero, u.bloco as unidade_bloco,
                usr.nome as morador_nome, usr.email as morador_email,
                cb.banco_nome
            FROM financeiro.boletos b
            LEFT JOIN financeiro.unidades u ON b.unidade_id = u.id
            LEFT JOIN financeiro.moradores m ON m.unidade_id = u.id AND m.principal = true
            LEFT JOIN financeiro.usuarios usr ON m.usuario_id = usr.id
            LEFT JOIN financeiro.contas_bancarias cb ON b.banco_id = cb.id
            WHERE b.id = $1
        """
        row = await fetchrow(query, boleto_id)
        if row:
            item = record_to_dict(row)
            if item.get('unidade_bloco') and item.get('unidade_numero'):
                item['unidade'] = f"Apt {item['unidade_numero']} - Bloco {item['unidade_bloco']}"
            item['morador'] = item.get('morador_nome', 'N/A')
            return item
        return None

    @staticmethod
    async def create(
        condominio_id: str,
        unidade_id: str,
        valor: float,
        vencimento: str,
        descricao: str = "Taxa de Condomínio",
        tipo: str = "condominio",
        competencia: Optional[str] = None,
        banco_id: Optional[str] = None
    ) -> Dict:
        """Cria um novo boleto"""
        # Gerar competência se não fornecida
        if not competencia:
            venc_date = datetime.strptime(vencimento, "%Y-%m-%d")
            competencia = venc_date.strftime("%m/%Y")

        query = """
            INSERT INTO financeiro.boletos (
                condominio_id, unidade_id, referencia, valor,
                data_vencimento, descricao, tipo, status, banco_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'pendente', $8)
            RETURNING *
        """
        row = await fetchrow(
            query,
            condominio_id, unidade_id, competencia, valor,
            datetime.strptime(vencimento, "%Y-%m-%d").date(),
            descricao, tipo, banco_id
        )
        return record_to_dict(row)

    @staticmethod
    async def update(boleto_id: str, **kwargs) -> Optional[Dict]:
        """Atualiza um boleto"""
        allowed_fields = ['valor', 'data_vencimento', 'descricao', 'status',
                         'valor_juros', 'valor_multa', 'valor_desconto',
                         'linha_digitavel', 'codigo_barras', 'pix_copia_cola',
                         'nosso_numero', 'banco_boleto_id', 'banco_response']

        updates = []
        values = []
        param_count = 0

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                param_count += 1
                updates.append(f"{field} = ${param_count}")
                if field == 'banco_response' and isinstance(value, dict):
                    values.append(json.dumps(value))
                else:
                    values.append(value)

        if not updates:
            return await BoletoRepository.get_by_id(boleto_id)

        param_count += 1
        query = f"""
            UPDATE financeiro.boletos
            SET {', '.join(updates)}, updated_at = NOW()
            WHERE id = ${param_count}
            RETURNING *
        """
        values.append(boleto_id)

        row = await fetchrow(query, *values)
        return record_to_dict(row)

    @staticmethod
    async def update_status(boleto_id: str, status: str) -> bool:
        """Atualiza status do boleto"""
        await execute(
            "UPDATE financeiro.boletos SET status = $1, updated_at = NOW() WHERE id = $2",
            status, boleto_id
        )
        return True

    @staticmethod
    async def registrar_pagamento(
        boleto_id: str,
        valor_pago: float,
        data_pagamento: str,
        forma_pagamento: str
    ) -> Dict:
        """Registra pagamento de um boleto"""
        query = """
            UPDATE financeiro.boletos
            SET status = 'pago',
                valor_pago = $1,
                data_pagamento = $2,
                forma_pagamento = $3,
                updated_at = NOW()
            WHERE id = $4
            RETURNING *
        """
        row = await fetchrow(
            query, valor_pago,
            datetime.strptime(data_pagamento, "%Y-%m-%d").date(),
            forma_pagamento, boleto_id
        )
        return record_to_dict(row)

    @staticmethod
    async def get_resumo(condominio_id: str, mes: Optional[str] = None) -> Dict:
        """Retorna resumo de boletos"""
        # Define período
        if mes:
            referencia = mes
        else:
            referencia = datetime.now().strftime("%m/%Y")

        query = """
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'pago') as pagos,
                COUNT(*) FILTER (WHERE status = 'pendente') as pendentes,
                COUNT(*) FILTER (WHERE status = 'vencido') as vencidos,
                COALESCE(SUM(valor) FILTER (WHERE status = 'pago'), 0) as valor_pago,
                COALESCE(SUM(valor) FILTER (WHERE status = 'vencido'), 0) as valor_vencido,
                COALESCE(SUM(valor), 0) as valor_total
            FROM financeiro.boletos
            WHERE condominio_id = $1 AND referencia = $2
        """
        row = await fetchrow(query, condominio_id, referencia)
        return record_to_dict(row) if row else {}


class PagamentoRepository:
    """Repositório para operações com pagamentos"""

    @staticmethod
    async def create(
        condominio_id: str,
        boleto_id: str,
        unidade_id: str,
        valor_pago: float,
        data_pagamento: str,
        forma_pagamento: str,
        conta_bancaria_id: Optional[str] = None,
        valor_original: Optional[float] = None,
        valor_juros: float = 0,
        valor_multa: float = 0,
        valor_desconto: float = 0,
        autenticacao: Optional[str] = None,
        txid: Optional[str] = None,
        origem: str = "manual",
        registrado_por: Optional[str] = None,
        observacao: Optional[str] = None
    ) -> Dict:
        """Registra um novo pagamento"""
        query = """
            INSERT INTO financeiro.pagamentos (
                condominio_id, boleto_id, unidade_id, conta_bancaria_id,
                valor_original, valor_juros, valor_multa, valor_desconto, valor_pago,
                data_pagamento, forma_pagamento, autenticacao, txid,
                origem, registrado_por, observacao
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            RETURNING *
        """
        row = await fetchrow(
            query,
            condominio_id, boleto_id, unidade_id, conta_bancaria_id,
            valor_original or valor_pago, valor_juros, valor_multa, valor_desconto, valor_pago,
            datetime.strptime(data_pagamento, "%Y-%m-%d"),
            forma_pagamento, autenticacao, txid, origem, registrado_por, observacao
        )
        return record_to_dict(row)

    @staticmethod
    async def list(
        condominio_id: str,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict:
        """Lista pagamentos"""
        offset = (page - 1) * limit

        query = """
            SELECT p.*, u.numero as unidade_numero, u.bloco as unidade_bloco
            FROM financeiro.pagamentos p
            LEFT JOIN financeiro.unidades u ON p.unidade_id = u.id
            WHERE p.condominio_id = $1
        """
        params = [condominio_id]

        if data_inicio:
            params.append(datetime.strptime(data_inicio, "%Y-%m-%d").date())
            query += f" AND p.data_pagamento >= ${len(params)}"

        if data_fim:
            params.append(datetime.strptime(data_fim, "%Y-%m-%d").date())
            query += f" AND p.data_pagamento <= ${len(params)}"

        query += f" ORDER BY p.data_pagamento DESC LIMIT ${len(params)+1} OFFSET ${len(params)+2}"
        params.extend([limit, offset])

        rows = await fetch(query, *params)

        # Count
        count_query = "SELECT COUNT(*) FROM financeiro.pagamentos WHERE condominio_id = $1"
        total = await fetchval(count_query, condominio_id)

        return {
            "items": records_to_list(rows),
            "total": total or 0,
            "page": page,
            "limit": limit
        }


class LancamentoRepository:
    """Repositório para lançamentos financeiros"""

    @staticmethod
    async def list(
        condominio_id: str,
        tipo: Optional[str] = None,
        categoria_id: Optional[str] = None,
        data_inicio: Optional[str] = None,
        data_fim: Optional[str] = None,
        page: int = 1,
        limit: int = 20
    ) -> Dict:
        """Lista lançamentos"""
        offset = (page - 1) * limit

        query = """
            SELECT l.*, c.nome as categoria_nome, c.cor as categoria_cor
            FROM financeiro.lancamentos l
            LEFT JOIN financeiro.categorias_financeiras c ON l.categoria_id = c.id
            WHERE l.condominio_id = $1
        """
        params = [condominio_id]

        if tipo:
            params.append(tipo)
            query += f" AND l.tipo = ${len(params)}"

        if categoria_id:
            params.append(categoria_id)
            query += f" AND l.categoria_id = ${len(params)}"

        if data_inicio:
            params.append(datetime.strptime(data_inicio, "%Y-%m-%d").date())
            query += f" AND l.data_lancamento >= ${len(params)}"

        if data_fim:
            params.append(datetime.strptime(data_fim, "%Y-%m-%d").date())
            query += f" AND l.data_lancamento <= ${len(params)}"

        query += f" ORDER BY l.data_lancamento DESC LIMIT ${len(params)+1} OFFSET ${len(params)+2}"
        params.extend([limit, offset])

        rows = await fetch(query, *params)

        count_query = "SELECT COUNT(*) FROM financeiro.lancamentos WHERE condominio_id = $1"
        total = await fetchval(count_query, condominio_id)

        return {
            "items": records_to_list(rows),
            "total": total or 0,
            "page": page,
            "limit": limit
        }

    @staticmethod
    async def create(
        condominio_id: str,
        tipo: str,
        valor: float,
        descricao: str,
        data_lancamento: str,
        categoria_id: Optional[str] = None,
        conta_bancaria_id: Optional[str] = None,
        unidade_id: Optional[str] = None,
        data_vencimento: Optional[str] = None,
        fornecedor_nome: Optional[str] = None,
        fornecedor_documento: Optional[str] = None,
        documento_numero: Optional[str] = None,
        recorrente: bool = False,
        criado_por: Optional[str] = None
    ) -> Dict:
        """Cria um novo lançamento"""
        query = """
            INSERT INTO financeiro.lancamentos (
                condominio_id, tipo, valor, descricao, data_lancamento,
                categoria_id, conta_bancaria_id, unidade_id, data_vencimento,
                fornecedor_nome, fornecedor_documento, documento_numero,
                recorrente, criado_por, status
            ) VALUES ($1, $2::tipo_lancamento, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, 'pendente')
            RETURNING *
        """
        row = await fetchrow(
            query,
            condominio_id, tipo, valor, descricao,
            datetime.strptime(data_lancamento, "%Y-%m-%d").date(),
            categoria_id, conta_bancaria_id, unidade_id,
            datetime.strptime(data_vencimento, "%Y-%m-%d").date() if data_vencimento else None,
            fornecedor_nome, fornecedor_documento, documento_numero,
            recorrente, criado_por
        )
        return record_to_dict(row)

    @staticmethod
    async def get_resumo_periodo(
        condominio_id: str,
        data_inicio: str,
        data_fim: str
    ) -> Dict:
        """Retorna resumo de lançamentos por período"""
        query = """
            SELECT
                tipo,
                COUNT(*) as quantidade,
                SUM(valor) as total
            FROM financeiro.lancamentos
            WHERE condominio_id = $1
                AND data_lancamento >= $2
                AND data_lancamento <= $3
            GROUP BY tipo
        """
        rows = await fetch(
            query, condominio_id,
            datetime.strptime(data_inicio, "%Y-%m-%d").date(),
            datetime.strptime(data_fim, "%Y-%m-%d").date()
        )

        resultado = {"receitas": 0, "despesas": 0}
        for row in rows:
            if row['tipo'] == 'receita':
                resultado['receitas'] = float(row['total'] or 0)
            elif row['tipo'] == 'despesa':
                resultado['despesas'] = float(row['total'] or 0)

        resultado['saldo'] = resultado['receitas'] - resultado['despesas']
        return resultado


class CategoriaRepository:
    """Repositório para categorias financeiras"""

    @staticmethod
    async def list(condominio_id: Optional[str] = None, tipo: Optional[str] = None) -> Dict:
        """Lista categorias"""
        query = """
            SELECT * FROM financeiro.categorias_financeiras
            WHERE (condominio_id IS NULL OR condominio_id = $1) AND ativo = true
        """
        params = [condominio_id]

        if tipo:
            query += " AND tipo = $2::tipo_lancamento"
            params.append(tipo)

        query += " ORDER BY ordem, nome"

        rows = await fetch(query, *params)

        # Organiza por tipo
        resultado = {"receita": [], "despesa": []}
        for row in rows:
            item = record_to_dict(row)
            if item['tipo'] in resultado:
                resultado[item['tipo']].append(item)

        return resultado


class ContaBancariaRepository:
    """Repositório para contas bancárias"""

    @staticmethod
    async def list(condominio_id: str) -> List[Dict]:
        """Lista contas bancárias"""
        query = """
            SELECT * FROM financeiro.contas_bancarias
            WHERE condominio_id = $1 AND ativo = true
            ORDER BY principal DESC, banco_nome
        """
        rows = await fetch(query, condominio_id)
        return records_to_list(rows)

    @staticmethod
    async def get_by_id(conta_id: str) -> Optional[Dict]:
        """Busca conta por ID"""
        query = "SELECT * FROM financeiro.contas_bancarias WHERE id = $1"
        row = await fetchrow(query, conta_id)
        return record_to_dict(row)

    @staticmethod
    async def get_principal(condominio_id: str) -> Optional[Dict]:
        """Busca conta principal do condomínio"""
        query = """
            SELECT * FROM financeiro.contas_bancarias
            WHERE condominio_id = $1 AND principal = true AND ativo = true
        """
        row = await fetchrow(query, condominio_id)
        return record_to_dict(row)

    @staticmethod
    async def create(
        condominio_id: str,
        banco_codigo: str,
        banco_nome: str,
        agencia: str,
        conta: str,
        tipo: str = "conta_corrente",
        agencia_digito: Optional[str] = None,
        conta_digito: Optional[str] = None,
        titular: Optional[str] = None,
        documento: Optional[str] = None,
        principal: bool = False,
        integracao_tipo: Optional[str] = None,
        integracao_ambiente: str = "sandbox"
    ) -> Dict:
        """Cria uma nova conta bancária"""
        query = """
            INSERT INTO financeiro.contas_bancarias (
                condominio_id, banco_codigo, banco_nome, agencia, agencia_digito,
                conta, conta_digito, tipo, titular, documento, principal,
                integracao_tipo, integracao_ambiente
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::tipo_conta, $9, $10, $11, $12, $13)
            RETURNING *
        """
        row = await fetchrow(
            query,
            condominio_id, banco_codigo, banco_nome, agencia, agencia_digito,
            conta, conta_digito, tipo, titular, documento, principal,
            integracao_tipo, integracao_ambiente
        )
        return record_to_dict(row)

    @staticmethod
    async def update_integracao(
        conta_id: str,
        integracao_ativa: bool,
        integracao_tipo: str,
        integracao_ambiente: str,
        integracao_config: Dict
    ) -> Dict:
        """Atualiza configuração de integração"""
        query = """
            UPDATE financeiro.contas_bancarias
            SET integracao_ativa = $1,
                integracao_tipo = $2,
                integracao_ambiente = $3,
                integracao_config = $4,
                updated_at = NOW()
            WHERE id = $5
            RETURNING *
        """
        row = await fetchrow(
            query,
            integracao_ativa, integracao_tipo, integracao_ambiente,
            json.dumps(integracao_config), conta_id
        )
        return record_to_dict(row)


class AcordoRepository:
    """Repositório para acordos de pagamento"""

    @staticmethod
    async def list(condominio_id: str, status: Optional[str] = None) -> List[Dict]:
        """Lista acordos"""
        query = """
            SELECT a.*, u.numero as unidade_numero, u.bloco as unidade_bloco,
                   usr.nome as morador_nome
            FROM financeiro.acordos a
            LEFT JOIN financeiro.unidades u ON a.unidade_id = u.id
            LEFT JOIN financeiro.moradores m ON m.unidade_id = u.id AND m.principal = true
            LEFT JOIN financeiro.usuarios usr ON m.usuario_id = usr.id
            WHERE a.condominio_id = $1
        """
        params = [condominio_id]

        if status:
            query += " AND a.status = $2::status_acordo"
            params.append(status)

        query += " ORDER BY a.created_at DESC"

        rows = await fetch(query, *params)

        items = []
        for row in rows:
            item = record_to_dict(row)
            if item.get('unidade_bloco') and item.get('unidade_numero'):
                item['unidade'] = f"Apt {item['unidade_numero']} - Bloco {item['unidade_bloco']}"
            item['morador'] = item.get('morador_nome', 'N/A')
            items.append(item)

        return items

    @staticmethod
    async def create(
        condominio_id: str,
        unidade_id: str,
        boletos_originais: List[str],
        valor_original: float,
        valor_total: float,
        parcelas: int,
        valor_parcela: float,
        dia_vencimento: int,
        primeira_parcela: str,
        entrada: float = 0,
        valor_juros: float = 0,
        valor_multa: float = 0,
        valor_desconto: float = 0,
        negociado_por: str = "atendente",
        canal_negociacao: Optional[str] = None,
        criado_por: Optional[str] = None
    ) -> Dict:
        """Cria um novo acordo"""
        query = """
            INSERT INTO financeiro.acordos (
                condominio_id, unidade_id, boletos_originais,
                valor_original, valor_juros, valor_multa, valor_desconto, valor_total,
                entrada, parcelas, valor_parcela, dia_vencimento, primeira_parcela,
                negociado_por, canal_negociacao, criado_por, status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, 'proposta')
            RETURNING *
        """
        row = await fetchrow(
            query,
            condominio_id, unidade_id, boletos_originais,
            valor_original, valor_juros, valor_multa, valor_desconto, valor_total,
            entrada, parcelas, valor_parcela, dia_vencimento,
            datetime.strptime(primeira_parcela, "%Y-%m-%d").date(),
            negociado_por, canal_negociacao, criado_por
        )
        return record_to_dict(row)


class ConciliacaoRepository:
    """Repositório para conciliação bancária"""

    @staticmethod
    async def criar_importacao(
        condominio_id: str,
        conta_bancaria_id: str,
        arquivo_nome: str,
        arquivo_tipo: str,
        data_inicio: str,
        data_fim: str,
        importado_por: Optional[str] = None
    ) -> Dict:
        """Cria registro de importação de extrato"""
        query = """
            INSERT INTO financeiro.extrato_importacoes (
                condominio_id, conta_bancaria_id, arquivo_nome, arquivo_tipo,
                data_inicio, data_fim, importado_por, status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, 'processando')
            RETURNING *
        """
        row = await fetchrow(
            query,
            condominio_id, conta_bancaria_id, arquivo_nome, arquivo_tipo,
            datetime.strptime(data_inicio, "%Y-%m-%d").date(),
            datetime.strptime(data_fim, "%Y-%m-%d").date(),
            importado_por
        )
        return record_to_dict(row)

    @staticmethod
    async def inserir_transacao(
        importacao_id: str,
        condominio_id: str,
        conta_bancaria_id: str,
        data_transacao: str,
        tipo: str,  # 'C' ou 'D'
        valor: float,
        descricao: str,
        numero_documento: Optional[str] = None,
        dados_originais: Optional[Dict] = None
    ) -> Dict:
        """Insere uma transação do extrato"""
        query = """
            INSERT INTO financeiro.extrato_transacoes (
                importacao_id, condominio_id, conta_bancaria_id,
                data_transacao, tipo, valor, descricao,
                numero_documento, dados_originais, status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'pendente')
            RETURNING *
        """
        row = await fetchrow(
            query,
            importacao_id, condominio_id, conta_bancaria_id,
            datetime.strptime(data_transacao, "%Y-%m-%d").date(),
            tipo, valor, descricao, numero_documento,
            json.dumps(dados_originais) if dados_originais else None
        )
        return record_to_dict(row)

    @staticmethod
    async def get_transacoes_pendentes(condominio_id: str) -> List[Dict]:
        """Lista transações pendentes de conciliação"""
        query = """
            SELECT t.*, cb.banco_nome
            FROM financeiro.extrato_transacoes t
            JOIN financeiro.contas_bancarias cb ON t.conta_bancaria_id = cb.id
            WHERE t.condominio_id = $1 AND t.status = 'pendente'
            ORDER BY t.data_transacao DESC
        """
        rows = await fetch(query, condominio_id)
        return records_to_list(rows)

    @staticmethod
    async def conciliar_transacao(
        transacao_id: str,
        boleto_id: Optional[str] = None,
        lancamento_id: Optional[str] = None,
        pagamento_id: Optional[str] = None,
        confianca_match: float = 100,
        manual: bool = False,
        usuario_id: Optional[str] = None
    ) -> Dict:
        """Concilia uma transação"""
        status = 'conciliado_manual' if manual else 'conciliado_auto'

        query = """
            UPDATE financeiro.extrato_transacoes
            SET status = $1::status_conciliacao,
                boleto_id = $2,
                lancamento_id = $3,
                pagamento_id = $4,
                confianca_match = $5,
                match_manual = $6,
                match_por = $7,
                match_em = NOW(),
                updated_at = NOW()
            WHERE id = $8
            RETURNING *
        """
        row = await fetchrow(
            query,
            status, boleto_id, lancamento_id, pagamento_id,
            confianca_match, manual, usuario_id, transacao_id
        )
        return record_to_dict(row)


class WebhookRepository:
    """Repositório para logs de webhook"""

    @staticmethod
    async def registrar(
        origem: str,
        tipo: str,
        body: Dict,
        condominio_id: Optional[str] = None,
        url: Optional[str] = None,
        method: str = "POST",
        headers: Optional[Dict] = None
    ) -> Dict:
        """Registra um webhook recebido"""
        query = """
            INSERT INTO financeiro.webhooks_log (
                condominio_id, origem, tipo, url, method, headers, body
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """
        row = await fetchrow(
            query,
            condominio_id, origem, tipo, url, method,
            json.dumps(headers) if headers else None,
            json.dumps(body)
        )
        return record_to_dict(row)

    @staticmethod
    async def marcar_processado(
        webhook_id: str,
        resultado: str,
        erro_mensagem: Optional[str] = None,
        boleto_id: Optional[str] = None,
        pagamento_id: Optional[str] = None
    ):
        """Marca webhook como processado"""
        query = """
            UPDATE financeiro.webhooks_log
            SET processado = true,
                processado_em = NOW(),
                resultado = $1,
                erro_mensagem = $2,
                boleto_id = $3,
                pagamento_id = $4
            WHERE id = $5
        """
        await execute(query, resultado, erro_mensagem, boleto_id, pagamento_id, webhook_id)
