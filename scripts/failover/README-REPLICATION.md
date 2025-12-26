# PostgreSQL Streaming Replication - Conecta Plus

## Visao Geral

Configuracao de alta disponibilidade usando PostgreSQL Streaming Replication.

- **Master**: `conecta-postgres` (porta 5432)
- **Replica**: `conecta-postgres-replica` (porta 5433)
- **Modo**: Hot Standby (replica aceita queries de leitura)

## Arquitetura

```
                    ┌─────────────────┐
                    │   Aplicacoes    │
                    │  (api-gateway,  │
                    │   orchestrator) │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │    PgBouncer    │ (opcional)
                    │    porta 6432   │
                    └───────┬─┬───────┘
                            │ │
            ┌───────────────┘ └───────────────┐
            │ WRITE                      READ │
            ▼                                 ▼
    ┌───────────────┐               ┌───────────────┐
    │    MASTER     │──── WAL ─────>│   REPLICA     │
    │  porta 5432   │   Streaming   │  porta 5433   │
    └───────────────┘               └───────────────┘
```

## Arquivos de Configuracao

| Arquivo | Descricao |
|---------|-----------|
| `/opt/conecta-plus/config/postgres/postgresql.conf` | Config do master |
| `/opt/conecta-plus/config/postgres/pg_hba.conf` | Regras de acesso |
| `/opt/conecta-plus/config/postgres/init/02-setup-replication.sql` | Setup inicial |
| `/opt/conecta-plus/infrastructure/docker/docker-compose.replica.yml` | Compose da replica |
| `/opt/conecta-plus/infrastructure/docker/config/postgres-replica/postgresql.conf` | Config da replica |

## Scripts de Gerenciamento

| Script | Descricao |
|--------|-----------|
| `./scripts/failover/setup-master.sh` | Configura master para replicacao |
| `./scripts/failover/check-replication.sh` | Verifica status da replicacao |
| `./scripts/failover/promote-replica.sh` | Promove replica para master (failover) |

---

## PASSO A PASSO: Ativar Replicacao

### 1. Preparar o Master

```bash
cd /opt/conecta-plus

# Reiniciar postgres com nova configuracao
docker compose down postgres
docker compose up -d postgres

# Aguardar inicializacao
sleep 10

# Executar setup do master
./scripts/failover/setup-master.sh
```

### 2. Verificar Master

```bash
# Verificar se wal_level esta correto
docker exec conecta-postgres psql -U conecta_user -d conecta_db -c "SHOW wal_level;"
# Deve retornar: replica

# Verificar slots
docker exec conecta-postgres psql -U conecta_user -d conecta_db -c "SELECT * FROM pg_replication_slots;"
# Deve mostrar: replica_slot

# Verificar usuario replicator
docker exec conecta-postgres psql -U conecta_user -d conecta_db -c "SELECT rolname, rolreplication FROM pg_roles WHERE rolname='replicator';"
```

### 3. Iniciar a Replica

```bash
cd /opt/conecta-plus/infrastructure/docker

# Iniciar replica
docker compose -f docker-compose.replica.yml up -d postgres-replica

# Aguardar inicializacao (pode demorar - faz pg_basebackup)
docker logs -f conecta-postgres-replica
```

### 4. Verificar Replicacao

```bash
# Usar script de verificacao
/opt/conecta-plus/scripts/failover/check-replication.sh

# Ou verificar manualmente no master
docker exec conecta-postgres psql -U conecta_user -d conecta_db -c "SELECT * FROM pg_stat_replication;"

# Verificar na replica
docker exec conecta-postgres-replica psql -U conecta_user -d conecta_db -c "SELECT pg_is_in_recovery();"
# Deve retornar: t (true = esta em modo standby)
```

---

## PASSO A PASSO: Failover Manual

### Quando Usar

- Master nao responde
- Master precisa de manutencao prolongada
- Desastre no servidor do master

### Procedimento

```bash
# 1. Verificar status
/opt/conecta-plus/scripts/failover/check-replication.sh

# 2. Executar failover (modo dry-run primeiro)
/opt/conecta-plus/scripts/failover/promote-replica.sh --dry-run

# 3. Se OK, executar de verdade
/opt/conecta-plus/scripts/failover/promote-replica.sh

# 4. Atualizar conexoes (MANUAL)
# Editar .env ou docker-compose.yml para apontar para replica:
# DATABASE_URL: postgresql://user:pass@postgres-replica:5432/db

# 5. Reiniciar servicos
docker compose restart api-gateway auth-service ai-orchestrator integration-hub

# 6. Verificar logs
docker compose logs -f api-gateway | grep -i postgres
```

### Apos Failover

1. **Parar antigo master** (se ainda rodando):
   ```bash
   docker stop conecta-postgres
   ```

2. **Reconstruir master como replica** (opcional):
   ```bash
   # Remover dados antigos
   docker volume rm conecta-postgres-data

   # Reconfigurar como replica do novo master
   # (processo inverso)
   ```

---

## Monitoramento

### Metricas Importantes

| Metrica | Query | Limite |
|---------|-------|--------|
| Lag em bytes | `SELECT pg_wal_lsn_diff(sent_lsn, replay_lsn) FROM pg_stat_replication;` | < 16MB |
| Lag em segundos | `SELECT extract(epoch from now() - pg_last_xact_replay_timestamp());` (na replica) | < 30s |
| Conexoes de replicacao | `SELECT count(*) FROM pg_stat_replication;` | >= 1 |
| Slots ativos | `SELECT count(*) FROM pg_replication_slots WHERE active;` | >= 1 |

### Alertas Recomendados (Prometheus/Grafana)

```yaml
# Adicionar ao prometheus/alert_rules.yml
groups:
  - name: postgres_replication
    rules:
      - alert: PostgresReplicaDown
        expr: pg_stat_replication_pg_wal_lsn_diff == 0 or absent(pg_stat_replication_pg_wal_lsn_diff)
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL replica offline"

      - alert: PostgresReplicationLag
        expr: pg_stat_replication_pg_wal_lsn_diff > 16777216
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "PostgreSQL replication lag > 16MB"
```

---

## Troubleshooting

### Replica nao conecta

```bash
# Verificar logs da replica
docker logs conecta-postgres-replica

# Verificar conectividade
docker exec conecta-postgres-replica pg_isready -h postgres -U replicator

# Verificar pg_hba.conf no master
docker exec conecta-postgres cat /etc/postgresql/pg_hba.conf | grep replication
```

### Lag muito alto

```bash
# Verificar I/O do disco
docker stats conecta-postgres conecta-postgres-replica

# Aumentar wal_keep_size no master
# Editar postgresql.conf: wal_keep_size = 256MB
docker compose restart postgres
```

### Split-brain (dois masters)

**CUIDADO**: Situacao critica!

1. Identificar qual tem dados mais recentes
2. Parar um deles imediatamente
3. Reconciliar dados manualmente se necessario
4. Reconstruir replicacao

---

## Credenciais

| Usuario | Senha | Uso |
|---------|-------|-----|
| replicator | `repl_conecta_2024_secure` | Conexao de replicacao |

**IMPORTANTE**: Altere a senha em producao!

```bash
# No master
docker exec conecta-postgres psql -U conecta_user -d conecta_db -c \
  "ALTER ROLE replicator WITH PASSWORD 'NOVA_SENHA_SEGURA';"

# Atualizar na replica (postgresql.auto.conf ou docker-compose)
```

---

## Contato

Em caso de problemas criticos:
- Verificar logs: `/opt/conecta-plus/logs/`
- Script de failover cria log em: `/opt/conecta-plus/logs/failover-*.log`
