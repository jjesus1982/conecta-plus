"""
Skill: Forensic Audit (Auditoria Forense)
Sistema de auditoria completa e transparente de todas as ações e decisões

Princípios:
- Registro imutável de todas as ações
- Cadeia de decisão documentada
- Timeline forense reconstituível
- Exportação para análise externa
"""

import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import gzip


class ForensicAudit:
    """
    Sistema de Auditoria Forense

    Registra:
    - Todas as ações do sistema
    - Decisões e suas razões
    - Estado antes/depois de mudanças
    - Métricas no momento da ação

    Permite:
    - Reconstruir timeline completa
    - Análise de incidentes
    - Auditoria de compliance
    - Exportação de relatórios
    """

    # Tipos de eventos auditáveis
    EVENT_TYPES = {
        'action': 'Ação executada',
        'decision': 'Decisão tomada',
        'detection': 'Detecção de problema',
        'correlation': 'Correlação identificada',
        'prediction': 'Predição gerada',
        'healing': 'Auto-healing executado',
        'rollback': 'Rollback executado',
        'escalation': 'Escalação de severidade',
        'alert': 'Alerta gerado',
        'metric': 'Métrica registrada',
        'state_change': 'Mudança de estado',
        'configuration': 'Mudança de configuração',
    }

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state_dir = Path('/opt/conecta-plus/agents/system-monitor/state')
        self.audit_dir = self.state_dir / 'audit'
        self.audit_dir.mkdir(parents=True, exist_ok=True)

        self.current_log_file = self.audit_dir / 'audit_current.json'
        self.chain_file = self.audit_dir / 'audit_chain.json'

        self.current_log = self._load_current_log()
        self.chain = self._load_chain()

        # Configuração
        self.audit_config = {
            'max_entries_per_file': 10000,
            'retention_days': 90,
            'compress_older_than_days': 7,
            'include_metrics': True,
            'include_stack_trace': False,  # Para debug
        }

    def _load_current_log(self) -> Dict[str, Any]:
        """Carrega log atual"""
        try:
            if self.current_log_file.exists():
                with open(self.current_log_file) as f:
                    return json.load(f)
        except:
            pass
        return {
            'entries': [],
            'metadata': {
                'created_at': datetime.now().isoformat(),
                'entry_count': 0,
                'last_entry': None
            }
        }

    def _save_current_log(self):
        """Salva log atual"""
        with open(self.current_log_file, 'w') as f:
            json.dump(self.current_log, f, indent=2, default=str)

    def _load_chain(self) -> Dict[str, Any]:
        """Carrega chain de auditoria"""
        try:
            if self.chain_file.exists():
                with open(self.chain_file) as f:
                    return json.load(f)
        except:
            pass
        return {
            'last_hash': None,
            'total_entries': 0,
            'files': []
        }

    def _save_chain(self):
        """Salva chain"""
        with open(self.chain_file, 'w') as f:
            json.dump(self.chain, f, indent=2, default=str)

    def _generate_entry_hash(self, entry: Dict[str, Any], previous_hash: str) -> str:
        """Gera hash para entrada (blockchain-like)"""
        content = json.dumps(entry, sort_keys=True, default=str)
        combined = f"{previous_hash or 'genesis'}:{content}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def log(
        self,
        event_type: str,
        action: str,
        details: Dict[str, Any],
        context: Dict[str, Any] = None,
        state_before: Dict[str, Any] = None,
        state_after: Dict[str, Any] = None,
        decision_chain: List[str] = None,
        related_entries: List[str] = None
    ) -> str:
        """
        Registra um evento de auditoria

        Args:
            event_type: Tipo do evento (action, decision, healing, etc)
            action: Descrição da ação
            details: Detalhes do evento
            context: Contexto do sistema no momento
            state_before: Estado antes da ação
            state_after: Estado depois da ação
            decision_chain: Cadeia de decisões que levou à ação
            related_entries: IDs de entradas relacionadas

        Returns:
            ID único da entrada de auditoria
        """
        now = datetime.now()

        # Criar entrada
        entry = {
            'id': f"audit_{now.strftime('%Y%m%d%H%M%S')}_{len(self.current_log['entries'])}",
            'timestamp': now.isoformat(),
            'event_type': event_type,
            'event_description': self.EVENT_TYPES.get(event_type, event_type),
            'action': action,
            'details': details,
            'context': context or {},
            'state_before': state_before,
            'state_after': state_after,
            'decision_chain': decision_chain or [],
            'related_entries': related_entries or [],
            'hash': None  # Será preenchido
        }

        # Gerar hash encadeado
        entry['hash'] = self._generate_entry_hash(
            entry, self.chain.get('last_hash')
        )

        # Adicionar ao log
        self.current_log['entries'].append(entry)
        self.current_log['metadata']['entry_count'] += 1
        self.current_log['metadata']['last_entry'] = entry['id']

        # Atualizar chain
        self.chain['last_hash'] = entry['hash']
        self.chain['total_entries'] += 1

        # Verificar rotação
        if len(self.current_log['entries']) >= self.audit_config['max_entries_per_file']:
            self._rotate_log()

        self._save_current_log()
        self._save_chain()

        return entry['id']

    def log_action(
        self,
        action: str,
        result: str,
        details: Dict[str, Any],
        success: bool = True
    ) -> str:
        """Shortcut para logar ação"""
        return self.log(
            event_type='action',
            action=action,
            details={
                'result': result,
                'success': success,
                **details
            }
        )

    def log_decision(
        self,
        decision: str,
        reason: str,
        alternatives: List[str] = None,
        chosen_action: str = None
    ) -> str:
        """Shortcut para logar decisão"""
        return self.log(
            event_type='decision',
            action=decision,
            details={
                'reason': reason,
                'alternatives_considered': alternatives or [],
                'chosen_action': chosen_action
            },
            decision_chain=[reason]
        )

    def log_healing(
        self,
        issue: Dict[str, Any],
        action_taken: str,
        result: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any],
        rollback_executed: bool = False
    ) -> str:
        """Shortcut para logar healing"""
        return self.log(
            event_type='healing',
            action=f"Healing: {action_taken}",
            details={
                'issue': issue,
                'action': action_taken,
                'result': result,
                'rollback_executed': rollback_executed
            },
            state_before=state_before,
            state_after=state_after,
            decision_chain=[
                f"Issue detected: {issue.get('type', 'unknown')}",
                f"Priority: {issue.get('priority', 'P4')}",
                f"Action chosen: {action_taken}",
                f"Result: {'Success' if result.get('success') else 'Failed'}"
            ]
        )

    def log_detection(
        self,
        detection_type: str,
        findings: List[Dict[str, Any]],
        source: str
    ) -> str:
        """Shortcut para logar detecção"""
        return self.log(
            event_type='detection',
            action=f"Detection: {detection_type}",
            details={
                'type': detection_type,
                'findings_count': len(findings),
                'findings': findings[:10],  # Primeiros 10
                'source': source
            }
        )

    def _rotate_log(self):
        """Rotaciona log atual para arquivo datado"""
        now = datetime.now()
        archive_name = f"audit_{now.strftime('%Y%m%d_%H%M%S')}.json"
        archive_path = self.audit_dir / archive_name

        # Salvar log atual
        with open(archive_path, 'w') as f:
            json.dump(self.current_log, f, indent=2, default=str)

        # Registrar no chain
        self.chain['files'].append({
            'filename': archive_name,
            'created_at': now.isoformat(),
            'entry_count': len(self.current_log['entries']),
            'first_hash': self.current_log['entries'][0]['hash'] if self.current_log['entries'] else None,
            'last_hash': self.current_log['entries'][-1]['hash'] if self.current_log['entries'] else None
        })

        # Resetar log atual
        self.current_log = {
            'entries': [],
            'metadata': {
                'created_at': now.isoformat(),
                'entry_count': 0,
                'last_entry': None,
                'previous_file': archive_name
            }
        }

        # Comprimir arquivos antigos
        self._compress_old_files()

    def _compress_old_files(self):
        """Comprime arquivos de auditoria antigos"""
        cutoff = datetime.now() - timedelta(days=self.audit_config['compress_older_than_days'])

        for json_file in self.audit_dir.glob('audit_*.json'):
            if json_file == self.current_log_file or json_file == self.chain_file:
                continue

            # Verificar idade
            try:
                mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
                if mtime < cutoff:
                    # Comprimir
                    gz_path = json_file.with_suffix('.json.gz')
                    with open(json_file, 'rb') as f_in:
                        with gzip.open(gz_path, 'wb') as f_out:
                            f_out.writelines(f_in)
                    json_file.unlink()
            except:
                pass

    def get_timeline(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        event_types: List[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtém timeline de eventos

        Args:
            start_time: Início do período
            end_time: Fim do período
            event_types: Filtrar por tipos de evento
            limit: Máximo de entradas

        Returns:
            Lista de entradas ordenadas por timestamp
        """
        entries = []

        # Coletar do log atual
        for entry in self.current_log.get('entries', []):
            if self._entry_matches_filter(entry, start_time, end_time, event_types):
                entries.append(entry)

        # Ordenar por timestamp
        entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return entries[:limit]

    def _entry_matches_filter(
        self,
        entry: Dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        event_types: List[str]
    ) -> bool:
        """Verifica se entrada corresponde aos filtros"""
        try:
            entry_time = datetime.fromisoformat(entry['timestamp'])

            if start_time and entry_time < start_time:
                return False
            if end_time and entry_time > end_time:
                return False
            if event_types and entry.get('event_type') not in event_types:
                return False

            return True
        except:
            return False

    def get_incident_timeline(
        self,
        incident_start: datetime,
        incident_end: datetime = None,
        include_context: bool = True
    ) -> Dict[str, Any]:
        """
        Reconstrói timeline de um incidente

        Args:
            incident_start: Início do incidente
            incident_end: Fim do incidente (ou agora)
            include_context: Incluir contexto expandido

        Returns:
            Timeline forense do incidente
        """
        if incident_end is None:
            incident_end = datetime.now()

        # Expandir janela para contexto
        if include_context:
            context_start = incident_start - timedelta(minutes=30)
            context_end = incident_end + timedelta(minutes=15)
        else:
            context_start = incident_start
            context_end = incident_end

        # Coletar entradas
        timeline_entries = self.get_timeline(
            start_time=context_start,
            end_time=context_end,
            limit=500
        )

        # Classificar entradas
        pre_incident = []
        during_incident = []
        post_incident = []

        for entry in timeline_entries:
            try:
                entry_time = datetime.fromisoformat(entry['timestamp'])
                if entry_time < incident_start:
                    pre_incident.append(entry)
                elif entry_time > incident_end:
                    post_incident.append(entry)
                else:
                    during_incident.append(entry)
            except:
                pass

        # Análise
        analysis = self._analyze_incident(during_incident)

        return {
            'incident_period': {
                'start': incident_start.isoformat(),
                'end': incident_end.isoformat(),
                'duration_minutes': (incident_end - incident_start).total_seconds() / 60
            },
            'pre_incident': {
                'count': len(pre_incident),
                'entries': pre_incident[:10]  # Últimos 10 antes
            },
            'during_incident': {
                'count': len(during_incident),
                'entries': during_incident
            },
            'post_incident': {
                'count': len(post_incident),
                'entries': post_incident[:5]  # Primeiros 5 depois
            },
            'analysis': analysis
        }

    def _analyze_incident(
        self,
        entries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analisa entradas de um incidente"""
        event_counts = defaultdict(int)
        actions_taken = []
        decisions_made = []
        healings = []

        for entry in entries:
            event_type = entry.get('event_type', 'unknown')
            event_counts[event_type] += 1

            if event_type == 'action':
                actions_taken.append({
                    'action': entry.get('action'),
                    'success': entry.get('details', {}).get('success', False),
                    'timestamp': entry.get('timestamp')
                })
            elif event_type == 'decision':
                decisions_made.append({
                    'decision': entry.get('action'),
                    'reason': entry.get('details', {}).get('reason'),
                    'timestamp': entry.get('timestamp')
                })
            elif event_type == 'healing':
                healings.append({
                    'action': entry.get('details', {}).get('action'),
                    'result': entry.get('details', {}).get('result'),
                    'rollback': entry.get('details', {}).get('rollback_executed', False),
                    'timestamp': entry.get('timestamp')
                })

        return {
            'event_summary': dict(event_counts),
            'total_actions': len(actions_taken),
            'successful_actions': sum(1 for a in actions_taken if a['success']),
            'decisions_count': len(decisions_made),
            'healings_count': len(healings),
            'healings_with_rollback': sum(1 for h in healings if h['rollback']),
            'key_decisions': decisions_made[:5],
            'key_actions': actions_taken[:5]
        }

    def export_report(
        self,
        start_time: datetime,
        end_time: datetime,
        format: str = 'json'
    ) -> Dict[str, Any]:
        """
        Exporta relatório de auditoria

        Args:
            start_time: Início do período
            end_time: Fim do período
            format: Formato ('json', 'summary')

        Returns:
            Relatório exportável
        """
        entries = self.get_timeline(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )

        if format == 'summary':
            return self._generate_summary_report(entries, start_time, end_time)

        return {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'period_start': start_time.isoformat(),
                'period_end': end_time.isoformat(),
                'total_entries': len(entries)
            },
            'entries': entries
        }

    def _generate_summary_report(
        self,
        entries: List[Dict[str, Any]],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Gera relatório resumido"""
        event_counts = defaultdict(int)
        hourly_activity = defaultdict(int)
        actions_success = {'success': 0, 'failure': 0}
        healings_summary = {'total': 0, 'success': 0, 'rollback': 0}

        for entry in entries:
            event_type = entry.get('event_type', 'unknown')
            event_counts[event_type] += 1

            # Atividade por hora
            try:
                hour = datetime.fromisoformat(entry['timestamp']).strftime('%Y-%m-%d %H:00')
                hourly_activity[hour] += 1
            except:
                pass

            # Contagem de ações
            if event_type == 'action':
                if entry.get('details', {}).get('success', False):
                    actions_success['success'] += 1
                else:
                    actions_success['failure'] += 1

            # Contagem de healings
            if event_type == 'healing':
                healings_summary['total'] += 1
                if entry.get('details', {}).get('result', {}).get('success', False):
                    healings_summary['success'] += 1
                if entry.get('details', {}).get('rollback_executed', False):
                    healings_summary['rollback'] += 1

        return {
            'report_type': 'summary',
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'duration_hours': (end_time - start_time).total_seconds() / 3600
            },
            'total_events': len(entries),
            'events_by_type': dict(event_counts),
            'hourly_activity': dict(hourly_activity),
            'actions': actions_success,
            'actions_success_rate': (
                actions_success['success'] /
                (actions_success['success'] + actions_success['failure'])
                if (actions_success['success'] + actions_success['failure']) > 0
                else 0
            ),
            'healings': healings_summary,
            'healings_success_rate': (
                healings_summary['success'] / healings_summary['total']
                if healings_summary['total'] > 0
                else 0
            )
        }

    def verify_chain_integrity(self) -> Dict[str, Any]:
        """Verifica integridade do chain de auditoria"""
        issues = []
        verified = 0

        entries = self.current_log.get('entries', [])
        previous_hash = None

        # Verificar primeiro entry
        if entries and self.chain['files']:
            last_file = self.chain['files'][-1]
            previous_hash = last_file.get('last_hash')

        for i, entry in enumerate(entries):
            expected_hash = self._generate_entry_hash(
                {k: v for k, v in entry.items() if k != 'hash'},
                previous_hash
            )

            if entry.get('hash') != expected_hash:
                issues.append({
                    'entry_id': entry.get('id'),
                    'index': i,
                    'issue': 'Hash mismatch',
                    'expected': expected_hash,
                    'actual': entry.get('hash')
                })
            else:
                verified += 1

            previous_hash = entry.get('hash')

        return {
            'total_entries': len(entries),
            'verified': verified,
            'issues': issues,
            'integrity': 'intact' if not issues else 'compromised',
            'verified_at': datetime.now().isoformat()
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de auditoria"""
        entries = self.current_log.get('entries', [])

        event_counts = defaultdict(int)
        for entry in entries:
            event_counts[entry.get('event_type', 'unknown')] += 1

        return {
            'current_log_entries': len(entries),
            'total_entries': self.chain.get('total_entries', 0),
            'archived_files': len(self.chain.get('files', [])),
            'events_by_type': dict(event_counts),
            'last_entry': self.current_log['metadata'].get('last_entry'),
            'chain_hash': self.chain.get('last_hash')
        }


if __name__ == '__main__':
    # Teste
    audit = ForensicAudit({})

    # Registrar alguns eventos
    audit.log_decision(
        decision="Executar healing",
        reason="Gap P4 detectado com rollback disponível",
        alternatives=["Ignorar", "Alertar humano"],
        chosen_action="clear_cache"
    )

    audit.log_healing(
        issue={'type': 'high_cache', 'priority': 'P4'},
        action_taken="clear_cache",
        result={'success': True},
        state_before={'cache_size': '1.2GB'},
        state_after={'cache_size': '0MB'}
    )

    audit.log_action(
        action="Monitor cycle completed",
        result="All checks passed",
        details={'gaps_found': 5, 'healed': 2},
        success=True
    )

    # Obter timeline
    print("=== Auditoria Forense ===\n")
    timeline = audit.get_timeline(limit=10)
    for entry in timeline:
        print(f"[{entry['event_type']}] {entry['action']}")
        print(f"  ID: {entry['id']}")
        print(f"  Hash: {entry['hash']}")
        print()

    # Verificar integridade
    integrity = audit.verify_chain_integrity()
    print(f"\nIntegridade: {integrity['integrity'].upper()}")
    print(f"Entradas verificadas: {integrity['verified']}/{integrity['total_entries']}")

    # Estatísticas
    print(f"\n=== Estatísticas ===")
    print(json.dumps(audit.get_statistics(), indent=2))
