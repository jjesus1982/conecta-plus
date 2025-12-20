-- ============================================
-- Conecta Plus - Script de Inicialização PostgreSQL
-- Cria databases e extensões necessárias
-- ============================================

-- Criar extensões úteis
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Criar databases adicionais se necessário
-- Database para logs/auditoria (opcional)
-- CREATE DATABASE conecta_logs;

-- Database para testes (opcional)
-- CREATE DATABASE conecta_test;

-- Configurar timezone
SET timezone = 'America/Sao_Paulo';

-- Criar schema para organização
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS network;
CREATE SCHEMA IF NOT EXISTS guardian;
CREATE SCHEMA IF NOT EXISTS messaging;

-- Comentário informativo
COMMENT ON DATABASE conecta_db IS 'Banco de dados principal do Conecta Plus';
COMMENT ON SCHEMA core IS 'Entidades principais do sistema';
COMMENT ON SCHEMA auth IS 'Autenticação e autorização';
COMMENT ON SCHEMA network IS 'Gestão de rede (MikroTik, UniFi)';
COMMENT ON SCHEMA guardian IS 'Monitoramento de câmeras e IA';
COMMENT ON SCHEMA messaging IS 'Mensageria (WhatsApp, Telegram, Email)';

-- Garantir que o usuário tem acesso aos schemas
GRANT ALL ON SCHEMA core TO conecta_user;
GRANT ALL ON SCHEMA auth TO conecta_user;
GRANT ALL ON SCHEMA network TO conecta_user;
GRANT ALL ON SCHEMA guardian TO conecta_user;
GRANT ALL ON SCHEMA messaging TO conecta_user;

-- Mensagem de sucesso
DO $$
BEGIN
    RAISE NOTICE 'Conecta Plus - Banco de dados inicializado com sucesso!';
END $$;
