# PostgreSQL Streaming Replication - Conecta Plus

## Visao Geral

Configuracao de alta disponibilidade usando PostgreSQL Streaming Replication.

- **Master**: `conecta-postgres` (porta 5432)
- **Replica**: `conecta-postgres-replica` (porta 5433)
- **Modo**: Hot Standby (replica aceita queries de leitura)

## Arquitetura

```
                    +-------------------+
                    |    Aplicacoes     |
                    |   (api-gateway,   |
                    |   orchestrator)   |
                    +--------+----------+
                             |
                    +--------v----------+
                    |    Load Balancer  |
                    |      (nginx)      |
                    +--------+----------+
                             |
            +----------------+----------------+
            |                                 |
            v WRITE                      READ v
    +---------------+               +---------------+
    |    MASTER     |---- WAL ----->|   REPLICA     |
    |  porta 5432   |   Streaming   |  porta 5433   |
    | conecta-      |               | conecta-      |
    | postgres      |               | postgres-     |
    +---------------+               | replica       |
                                    +---------------+
```

## Arquivos de Configuracao

| Arquivo | Descricao |
|---------|-----------|
| `/opt/conecta-plus/config/postgres/postgresql.conf` | Config do master |
| `/opt/conecta-plus/config/postgres/pg_hba.conf` | Regras de acesso |
| `/opt/conecta-plus/config/postgres/init/02-setup-replication.sql` | Setup inicial |
| `/opt/conecta-plus/docker-compose.yml` | Compose com master e replica |

## Scripts de Gerenciamento

| Script | Descricao |
|--------|-----------|
| `check-replication.sh` | Verifica status da replicacao |
| `promote-replica.sh` | Promove replica para master (failover emergencial) |
| `switchover.sh` | Troca planejada entre master e replica |
| `rebuild-replica.sh` | Reconstroi replica a partir do master |
| `auto-failover.sh` | Monitora e executa failover automatico |
| `setup-master.sh` | Configura master para replicacao |

---

## INICIO RAPIDO

### Iniciar Replicacao

```bash
cd /opt/conecta-plus

# Iniciar master e replica
docker compose up -d postgres postgres-replica

# Verificar status (aguarde 1-2 minutos para sincronizar)
./scripts/failover/check-replication.sh
```

A replica ira automaticamente:
1. Detectar que nao tem dados
2. Executar pg_basebackup do master
3. Configurar-se como standby
4. Iniciar streaming replication

---

## CENARIOS DE USO

### 1. Failover de Emergencia (Master caiu)

```bash
# 1. Verificar que master esta offline
docker exec conecta-postgres pg_isready
# Deve falhar

# 2. Verificar replica
docker exec conecta-postgres-replica pg_isready
# Deve responder

# 3. Modo dry-run primeiro
./scripts/failover/promote-replica.sh --dry-run

# 4. Executar failover
./scripts/failover/promote-replica.sh

# 5. Atualizar conexoes (ver secao "Atualizando Conexoes")
```

### 2. Switchover Planejado (Manutencao)

```bash
# Troca limpa entre master e replica
./scripts/failover/switchover.sh

# Isso ira:
# - Bloquear novas conexoes
# - Aguardar sincronizacao
# - Promover replica
# - Parar master antigo
```

### 3. Reconstruir Replica

```bash
# Apos failover ou problema na replica
./scripts/failover/rebuild-replica.sh

# Isso ira:
# - Parar replica
# - Limpar dados
# - Fazer novo basebackup
# - Reconfigurar como standby
```

### 4. Monitoramento Automatico

```bash
# Em foreground
./scripts/failover/auto-failover.sh

# Em background (daemon)
./scripts/failover/auto-failover.sh --daemon --interval 15

# Verificar logs
tail -f /opt/conecta-plus/logs/auto-failover.log
```

---

## ATUALIZANDO CONEXOES APOS FAILOVER

Apos promover a replica, voce DEVE atualizar as conexoes dos servicos.

### Opcao 1: Editar .env

```bash
# Antes (master)
DATABASE_URL=postgresql://conecta:senha@postgres:5432/conecta_plus

# Depois (replica promovida)
DATABASE_URL=postgresql://conecta:senha@postgres-replica:5432/conecta_plus
```

### Opcao 2: Usar porta externa

```bash
# Antes
DATABASE_URL=postgresql://conecta:senha@localhost:5432/conecta_plus

# Depois
DATABASE_URL=postgresql://conecta:senha@localhost:5433/conecta_plus
```

### Reiniciar Servicos

```bash
docker compose restart api-gateway auth-service ai-orchestrator integration-hub
```

---

## VERIFICACAO DE STATUS

### Script Automatico

```bash
./scripts/failover/check-replication.sh
```

### Comandos Manuais

```bash
# No MASTER - Ver replicas conectadas
docker exec conecta-postgres psql -U conecta_user -d conecta_db -c \
    "SELECT application_name, state, sent_lsn, replay_lsn
     FROM pg_stat_replication;"

# Na REPLICA - Verificar se esta em standby
docker exec conecta-postgres-replica psql -U conecta_user -d conecta_db -c \
    "SELECT pg_is_in_recovery();"
# Deve retornar: t (true)

# Na REPLICA - Ver lag
docker exec conecta-postgres-replica psql -U conecta_user -d conecta_db -c \
    "SELECT now() - pg_last_xact_replay_timestamp() as lag;"

# Verificar slots de replicacao
docker exec conecta-postgres psql -U conecta_user -d conecta_db -c \
    "SELECT slot_name, active FROM pg_replication_slots;"
```

---

## METRICAS E ALERTAS

### Metricas Importantes

| Metrica | Query | Limite |
|---------|-------|--------|
| Lag em bytes | `SELECT pg_wal_lsn_diff(sent_lsn, replay_lsn) FROM pg_stat_replication;` | < 16MB |
| Lag em segundos | `SELECT extract(epoch from now() - pg_last_xact_replay_timestamp());` | < 30s |
| Replicas ativas | `SELECT count(*) FROM pg_stat_replication;` | >= 1 |

### Alertas Prometheus

Adicione ao `/opt/conecta-plus/monitoring/prometheus/alert_rules.yml`:

```yaml
groups:
  - name: postgres_replication
    rules:
      - alert: PostgresReplicaOffline
        expr: absent(pg_stat_replication_replay_lsn)
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Replica PostgreSQL offline"
          description: "Nenhuma replica conectada ao master"

      - alert: PostgresReplicationLagHigh
        expr: pg_replication_lag_seconds > 30
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Lag de replicacao alto"
          description: "Lag: {{ $value }}s"

      - alert: PostgresReplicationLagCritical
        expr: pg_replication_lag_seconds > 300
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Lag de replicacao critico"
          description: "Lag: {{ $value }}s - Risco de perda de dados em failover"
```

---

## TROUBLESHOOTING

### Replica nao conecta ao master

```bash
# 1. Verificar logs
docker logs conecta-postgres-replica

# 2. Testar conectividade
docker exec conecta-postgres-replica pg_isready -h postgres -p 5432

# 3. Testar autenticacao do replicator
docker exec conecta-postgres-replica psql \
    "host=postgres port=5432 user=replicator password=repl_conecta_2024_secure dbname=replication" \
    -c "IDENTIFY_SYSTEM"

# 4. Verificar pg_hba.conf no master
docker exec conecta-postgres cat /etc/postgresql/pg_hba.conf | grep replication
```

### Lag muito alto

```bash
# 1. Verificar I/O
docker stats conecta-postgres conecta-postgres-replica

# 2. Verificar rede
docker exec conecta-postgres-replica ping postgres

# 3. Aumentar wal_keep_size
# Editar /opt/conecta-plus/config/postgres/postgresql.conf
# wal_keep_size = 256MB
docker compose restart postgres
```

### Slot de replicacao nao existe

```bash
# Criar slot manualmente
docker exec conecta-postgres psql -U conecta_user -d conecta_db -c \
    "SELECT pg_create_physical_replication_slot('replica_slot');"
```

### Split-brain (dois masters)

**SITUACAO CRITICA!**

1. Identificar qual tem transacoes mais recentes:
   ```bash
   docker exec conecta-postgres psql -U conecta_user -d conecta_db -c \
       "SELECT pg_current_wal_lsn();"

   docker exec conecta-postgres-replica psql -U conecta_user -d conecta_db -c \
       "SELECT pg_current_wal_lsn();"
   ```

2. Parar imediatamente o que tiver LSN menor

3. Reconstruir como replica:
   ```bash
   ./scripts/failover/rebuild-replica.sh
   ```

---

## CREDENCIAIS

| Usuario | Senha | Uso |
|---------|-------|-----|
| conecta_user | (veja .env) | Aplicacao |
| replicator | `repl_conecta_2024_secure` | Replicacao |

**IMPORTANTE**: Em producao, altere a senha do replicator:

```bash
# No master
docker exec conecta-postgres psql -U conecta_user -d conecta_db -c \
    "ALTER ROLE replicator WITH PASSWORD 'NOVA_SENHA_SEGURA';"

# Atualizar REPLICATOR_PASSWORD no .env
# Reconstruir replica
./scripts/failover/rebuild-replica.sh
```

---

## BACKUP E RECOVERY

### Backup do Master

```bash
# Backup logico (pg_dump)
docker exec conecta-postgres pg_dump -U conecta_user conecta_db > backup.sql

# Backup fisico (pg_basebackup)
docker exec conecta-postgres pg_basebackup -U replicator -D /backups/base -Fp -Xs -P
```

### Point-in-Time Recovery (PITR)

Para habilitar PITR, ative archive_mode no master:

```ini
# postgresql.conf
archive_mode = on
archive_command = 'cp %p /backups/archive/%f'
```

---

## LOGS

| Local | Descricao |
|-------|-----------|
| `/opt/conecta-plus/logs/auto-failover.log` | Log do monitor automatico |
| `/opt/conecta-plus/logs/failover-*.log` | Logs de failover executados |
| `/opt/conecta-plus/logs/rebuild-replica-*.log` | Logs de reconstrucao |
| `/opt/conecta-plus/logs/switchover-*.log` | Logs de switchover |
| `docker logs conecta-postgres` | Logs do master |
| `docker logs conecta-postgres-replica` | Logs da replica |
