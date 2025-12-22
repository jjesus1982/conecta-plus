"""
Conecta Plus - Repositórios Base
Acesso a dados das entidades principais
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
import sys
sys.path.insert(0, '/opt/conecta-plus/services/api-gateway')

from database import fetch, fetchrow, fetchval, execute, records_to_list, record_to_dict


class UsuarioRepository:
    """Repositório para operações com usuários"""

    @staticmethod
    async def get_by_email(email: str) -> Optional[Dict[str, Any]]:
        """Busca usuário por email"""
        query = """
            SELECT
                id, email, senha_hash, nome, role,
                condominio_id, avatar_url, telefone,
                ativo, ultimo_acesso, created_at
            FROM conecta.usuarios
            WHERE email = $1 AND ativo = true
        """
        row = await fetchrow(query, email)
        return record_to_dict(row) if row else None

    @staticmethod
    async def get_by_id(user_id: str) -> Optional[Dict[str, Any]]:
        """Busca usuário por ID"""
        query = """
            SELECT
                id, email, nome, role,
                condominio_id, avatar_url, telefone,
                ativo, ultimo_acesso, created_at
            FROM conecta.usuarios
            WHERE id = $1
        """
        row = await fetchrow(query, user_id)
        return record_to_dict(row) if row else None

    @staticmethod
    async def list_all(condominio_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista todos os usuários"""
        if condominio_id:
            query = """
                SELECT id, email, nome, role, telefone, ativo, created_at
                FROM conecta.usuarios
                WHERE condominio_id = $1
                ORDER BY nome
            """
            rows = await fetch(query, condominio_id)
        else:
            query = """
                SELECT id, email, nome, role, telefone, ativo, created_at
                FROM conecta.usuarios
                ORDER BY nome
            """
            rows = await fetch(query)
        return records_to_list(rows)

    @staticmethod
    async def update_last_access(user_id: str):
        """Atualiza último acesso do usuário"""
        query = """
            UPDATE conecta.usuarios
            SET ultimo_acesso = NOW()
            WHERE id = $1
        """
        await execute(query, user_id)


class CondominioRepository:
    """Repositório para operações com condomínios"""

    @staticmethod
    async def get_by_id(condominio_id: str) -> Optional[Dict[str, Any]]:
        """Busca condomínio por ID"""
        query = """
            SELECT
                id, nome, cnpj, endereco, telefone, email,
                configuracoes, created_at
            FROM conecta.condominios
            WHERE id = $1
        """
        row = await fetchrow(query, condominio_id)
        return record_to_dict(row) if row else None

    @staticmethod
    async def get_default() -> Optional[Dict[str, Any]]:
        """Retorna o condomínio padrão (primeiro cadastrado)"""
        query = """
            SELECT
                id, nome, cnpj, endereco, telefone, email,
                configuracoes, created_at
            FROM conecta.condominios
            ORDER BY created_at
            LIMIT 1
        """
        row = await fetchrow(query)
        return record_to_dict(row) if row else None


class CameraRepository:
    """Repositório para operações com câmeras"""

    @staticmethod
    async def list_all(condominio_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista todas as câmeras"""
        if condominio_id:
            query = """
                SELECT
                    id, nome, descricao, url_stream, url_snapshot,
                    tipo, fabricante, modelo, local as localizacao,
                    ativo, configuracoes, created_at
                FROM conecta.cameras
                WHERE condominio_id = $1
                ORDER BY nome
            """
            rows = await fetch(query, condominio_id)
        else:
            query = """
                SELECT
                    id, nome, descricao, url_stream, url_snapshot,
                    tipo, fabricante, modelo, local as localizacao,
                    ativo, configuracoes, created_at
                FROM conecta.cameras
                ORDER BY nome
            """
            rows = await fetch(query)

        # Formatar resultado
        cameras = []
        for row in rows:
            cam = record_to_dict(row)
            # Mapear ativo para status
            cam['status'] = 'online' if cam.get('ativo') else 'offline'
            cam['gravando'] = cam.get('ativo', False)
            cam['ptz'] = cam.get('configuracoes', {}).get('ptz', False) if isinstance(cam.get('configuracoes'), dict) else False
            cameras.append(cam)
        return cameras

    @staticmethod
    async def get_by_id(camera_id: str) -> Optional[Dict[str, Any]]:
        """Busca câmera por ID"""
        query = """
            SELECT
                id, nome, descricao, url_stream, url_snapshot,
                tipo, fabricante, modelo, local as localizacao,
                ativo, configuracoes, created_at
            FROM conecta.cameras
            WHERE id = $1
        """
        row = await fetchrow(query, camera_id)
        if row:
            cam = record_to_dict(row)
            cam['status'] = 'online' if cam.get('ativo') else 'offline'
            return cam
        return None

    @staticmethod
    async def count_by_status() -> Dict[str, int]:
        """Conta câmeras por status"""
        query = """
            SELECT
                COUNT(*) FILTER (WHERE ativo = true) as online,
                COUNT(*) FILTER (WHERE ativo = false) as offline,
                COUNT(*) as total
            FROM conecta.cameras
        """
        row = await fetchrow(query)
        return record_to_dict(row) if row else {"online": 0, "offline": 0, "total": 0}


class UnidadeRepository:
    """Repositório para operações com unidades"""

    @staticmethod
    async def list_all(condominio_id: str) -> List[Dict[str, Any]]:
        """Lista todas as unidades do condomínio"""
        query = """
            SELECT
                u.id, u.numero, u.bloco, u.andar, u.tipo,
                u.area, u.vagas_garagem, u.status,
                u.proprietario_id, usr.nome as proprietario_nome,
                u.created_at
            FROM conecta.unidades u
            LEFT JOIN conecta.usuarios usr ON u.proprietario_id = usr.id
            WHERE u.condominio_id = $1
            ORDER BY u.bloco, u.numero
        """
        rows = await fetch(query, condominio_id)
        return records_to_list(rows)

    @staticmethod
    async def get_by_id(unidade_id: str) -> Optional[Dict[str, Any]]:
        """Busca unidade por ID"""
        query = """
            SELECT
                u.id, u.numero, u.bloco, u.andar, u.tipo,
                u.area, u.vagas_garagem, u.status,
                u.proprietario_id, usr.nome as proprietario_nome,
                u.condominio_id, u.created_at
            FROM conecta.unidades u
            LEFT JOIN conecta.usuarios usr ON u.proprietario_id = usr.id
            WHERE u.id = $1
        """
        row = await fetchrow(query, unidade_id)
        return record_to_dict(row) if row else None

    @staticmethod
    async def count(condominio_id: str) -> int:
        """Conta total de unidades"""
        query = "SELECT COUNT(*) FROM conecta.unidades WHERE condominio_id = $1"
        return await fetchval(query, condominio_id) or 0


class MoradorRepository:
    """Repositório para operações com moradores"""

    @staticmethod
    async def list_all(condominio_id: str) -> List[Dict[str, Any]]:
        """Lista todos os moradores do condomínio"""
        query = """
            SELECT
                m.id, m.unidade_id, m.tipo, m.principal, m.created_at,
                u.numero as unidade_numero, u.bloco as unidade_bloco,
                usr.nome, usr.email, usr.telefone
            FROM conecta.moradores m
            JOIN conecta.unidades u ON m.unidade_id = u.id
            LEFT JOIN conecta.usuarios usr ON m.usuario_id = usr.id
            WHERE u.condominio_id = $1
            ORDER BY usr.nome
        """
        rows = await fetch(query, condominio_id)
        return records_to_list(rows)

    @staticmethod
    async def count(condominio_id: str) -> int:
        """Conta total de moradores"""
        query = """
            SELECT COUNT(*) FROM conecta.moradores m
            JOIN conecta.unidades u ON m.unidade_id = u.id
            WHERE u.condominio_id = $1
        """
        return await fetchval(query, condominio_id) or 0


class AcessoRepository:
    """Repositório para registros de acesso"""

    @staticmethod
    async def list_recent(condominio_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Lista acessos recentes"""
        query = """
            SELECT
                ra.id, ra.tipo, ra.metodo, ra.autorizado,
                ra.timestamp, ra.foto_url,
                pa.nome as ponto_nome,
                COALESCE(m.nome, v.nome, 'Desconhecido') as pessoa_nome
            FROM conecta.registros_acesso ra
            LEFT JOIN conecta.pontos_acesso pa ON ra.ponto_id = pa.id
            LEFT JOIN conecta.moradores m ON ra.morador_id = m.id
            LEFT JOIN conecta.visitantes v ON ra.visitante_id = v.id
            WHERE pa.condominio_id = $1
            ORDER BY ra.timestamp DESC
            LIMIT $2
        """
        rows = await fetch(query, condominio_id, limit)
        return records_to_list(rows)

    @staticmethod
    async def count_today(condominio_id: str) -> Dict[str, int]:
        """Conta acessos de hoje"""
        query = """
            SELECT
                COUNT(*) FILTER (WHERE ra.tipo = 'entrada') as entradas,
                COUNT(*) FILTER (WHERE ra.tipo = 'saida') as saidas,
                COUNT(*) as total
            FROM conecta.registros_acesso ra
            JOIN conecta.pontos_acesso pa ON ra.ponto_id = pa.id
            WHERE pa.condominio_id = $1
            AND ra.timestamp::date = CURRENT_DATE
        """
        row = await fetchrow(query, condominio_id)
        return record_to_dict(row) if row else {"entradas": 0, "saidas": 0, "total": 0}


class DashboardRepository:
    """Repositório para estatísticas do dashboard"""

    @staticmethod
    async def get_stats(condominio_id: str) -> Dict[str, Any]:
        """Obtém estatísticas do dashboard"""
        # Moradores
        moradores = await fetchval("""
            SELECT COUNT(*) FROM conecta.moradores m
            JOIN conecta.unidades u ON m.unidade_id = u.id
            WHERE u.condominio_id = $1
        """, condominio_id) or 0

        # Unidades
        unidades = await fetchval("""
            SELECT COUNT(*) FROM conecta.unidades WHERE condominio_id = $1
        """, condominio_id) or 0

        # Visitantes hoje
        visitantes_hoje = await fetchval("""
            SELECT COUNT(*) FROM conecta.visitantes
            WHERE condominio_id = $1 AND data_entrada::date = CURRENT_DATE
        """, condominio_id) or 0

        # Ocorrências abertas
        ocorrencias_abertas = await fetchval("""
            SELECT COUNT(*) FROM conecta.ocorrencias
            WHERE condominio_id = $1 AND status IN ('aberta', 'em_andamento')
        """, condominio_id) or 0

        # Câmeras (usa ativo ao invés de status)
        cameras = await fetchrow("""
            SELECT
                COUNT(*) FILTER (WHERE ativo = true) as online,
                COUNT(*) as total
            FROM conecta.cameras WHERE condominio_id = $1
        """, condominio_id)
        cameras_online = cameras['online'] if cameras else 0
        cameras_total = cameras['total'] if cameras else 0

        # Encomendas pendentes
        encomendas = await fetchval("""
            SELECT COUNT(*) FROM conecta.encomendas e
            JOIN conecta.unidades u ON e.unidade_id = u.id
            WHERE u.condominio_id = $1 AND e.status = 'aguardando_retirada'
        """, condominio_id) or 0

        # Reservas hoje
        reservas_hoje = await fetchval("""
            SELECT COUNT(*) FROM conecta.reservas r
            JOIN conecta.areas_comuns a ON r.area_id = a.id
            WHERE a.condominio_id = $1 AND r.data_reserva = CURRENT_DATE
        """, condominio_id) or 0

        # Inadimplência
        inadimplencia_query = await fetchrow("""
            SELECT
                COUNT(DISTINCT b.unidade_id) FILTER (WHERE b.status = 'vencido') as inadimplentes,
                COUNT(DISTINCT b.unidade_id) as total
            FROM conecta.boletos b
            WHERE b.condominio_id = $1
        """, condominio_id)
        if inadimplencia_query and inadimplencia_query['total'] > 0:
            inadimplencia = (inadimplencia_query['inadimplentes'] / inadimplencia_query['total']) * 100
        else:
            inadimplencia = 0

        # Arrecadação do mês
        arrecadacao_mes = await fetchval("""
            SELECT COALESCE(SUM(valor_pago), 0) FROM conecta.boletos
            WHERE condominio_id = $1
            AND status = 'pago'
            AND EXTRACT(MONTH FROM data_pagamento) = EXTRACT(MONTH FROM CURRENT_DATE)
            AND EXTRACT(YEAR FROM data_pagamento) = EXTRACT(YEAR FROM CURRENT_DATE)
        """, condominio_id) or 0

        return {
            "moradores": moradores,
            "unidades": unidades,
            "visitantesHoje": visitantes_hoje,
            "ocorrenciasAbertas": ocorrencias_abertas,
            "camerasOnline": cameras_online,
            "camerasTotal": cameras_total,
            "encomendas": encomendas,
            "reservasHoje": reservas_hoje,
            "inadimplencia": round(float(inadimplencia), 1),
            "arrecadacaoMes": float(arrecadacao_mes),
        }


class PontoAcessoRepository:
    """Repositório para pontos de acesso"""

    @staticmethod
    async def list_all(condominio_id: str) -> List[Dict[str, Any]]:
        """Lista todos os pontos de acesso"""
        query = """
            SELECT
                id, nome, tipo, descricao as localizacao, status,
                controlador_ip as ip, online,
                created_at
            FROM conecta.pontos_acesso
            WHERE condominio_id = $1
            ORDER BY nome
        """
        rows = await fetch(query, condominio_id)
        return records_to_list(rows)


class ManutencaoRepository:
    """Repositório para ordens de manutenção"""

    @staticmethod
    async def list_all(condominio_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lista ordens de manutenção"""
        if status:
            query = """
                SELECT
                    os.id, os.titulo, os.descricao, os.prioridade,
                    os.status, os.tipo, os.local,
                    os.data_abertura, os.data_previsao, os.data_conclusao,
                    os.custo_estimado, os.custo_real,
                    u.nome as solicitante_nome,
                    f.nome as fornecedor_nome
                FROM conecta.ordens_servico os
                LEFT JOIN conecta.usuarios u ON os.solicitante_id = u.id
                LEFT JOIN conecta.fornecedores f ON os.fornecedor_id = f.id
                WHERE os.condominio_id = $1 AND os.status = $2
                ORDER BY os.data_abertura DESC
            """
            rows = await fetch(query, condominio_id, status)
        else:
            query = """
                SELECT
                    os.id, os.titulo, os.descricao, os.prioridade,
                    os.status, os.tipo, os.local,
                    os.data_abertura, os.data_previsao, os.data_conclusao,
                    os.custo_estimado, os.custo_real,
                    u.nome as solicitante_nome,
                    f.nome as fornecedor_nome
                FROM conecta.ordens_servico os
                LEFT JOIN conecta.usuarios u ON os.solicitante_id = u.id
                LEFT JOIN conecta.fornecedores f ON os.fornecedor_id = f.id
                WHERE os.condominio_id = $1
                ORDER BY os.data_abertura DESC
            """
            rows = await fetch(query, condominio_id)
        return records_to_list(rows)

    @staticmethod
    async def create(data: Dict[str, Any]) -> str:
        """Cria uma nova ordem de manutenção"""
        query = """
            INSERT INTO conecta.ordens_servico (
                condominio_id, titulo, descricao, prioridade,
                tipo, local, solicitante_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """
        return await fetchval(
            query,
            data['condominio_id'],
            data['titulo'],
            data.get('descricao', ''),
            data.get('prioridade', 'media'),
            data.get('tipo', 'corretiva'),
            data.get('local', ''),
            data.get('solicitante_id')
        )


# Instâncias dos repositórios para uso global
usuario_repo = UsuarioRepository()
condominio_repo = CondominioRepository()
camera_repo = CameraRepository()
unidade_repo = UnidadeRepository()
morador_repo = MoradorRepository()
acesso_repo = AcessoRepository()
dashboard_repo = DashboardRepository()
ponto_acesso_repo = PontoAcessoRepository()
manutencao_repo = ManutencaoRepository()
