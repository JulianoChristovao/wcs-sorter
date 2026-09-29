-- ============================================================
-- WCS Sorter - Schema PostgreSQL (versão completa / instalação limpa)
-- Sistema de Controle de Armazém (Warehouse Control System)
-- Integração Sorter ↔ WMS
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- ENUMS
-- ============================================================
CREATE TYPE user_role AS ENUM ('admin', 'gestor', 'operador');

CREATE TYPE pedido_status AS ENUM (
    'recebido',
    'pendente',
    'em_processamento',
    'separado',
    'enviado_wms',
    'erro',
    'cancelado'
);

CREATE TYPE criterio_roteamento AS ENUM ('sigla', 'uf', 'filial');

-- ============================================================
-- USUÁRIOS
-- ============================================================
CREATE TABLE usuarios (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username        VARCHAR(50) UNIQUE NOT NULL,
    email           VARCHAR(150) UNIQUE NOT NULL,
    nome_completo   VARCHAR(150) NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            user_role NOT NULL DEFAULT 'operador',
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login      TIMESTAMPTZ
);

CREATE INDEX idx_usuarios_username ON usuarios(username);
CREATE INDEX idx_usuarios_role ON usuarios(role);

-- ============================================================
-- MAPAS (N mapas; apenas um habilitado direciona o sorter)
-- Cada mapa trabalha com UM critério: sigla, uf ou filial
-- ============================================================
CREATE TABLE mapas (
    id                  SERIAL PRIMARY KEY,
    nome                VARCHAR(100) NOT NULL,
    descricao           VARCHAR(255),
    quantidade_saidas   INTEGER NOT NULL DEFAULT 8
                        CHECK (quantidade_saidas BETWEEN 1 AND 100),
    criterio_roteamento criterio_roteamento NOT NULL DEFAULT 'sigla',
    habilitado          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by          UUID REFERENCES usuarios(id)
);

CREATE INDEX idx_mapas_habilitado ON mapas(habilitado);

-- ============================================================
-- CONFIGURAÇÃO LEGADA DO SORTER
-- ============================================================
CREATE TABLE config_sorter (
    id                  SERIAL PRIMARY KEY,
    quantidade_saidas   INTEGER NOT NULL CHECK (quantidade_saidas BETWEEN 1 AND 100),
    descricao           VARCHAR(200),
    ativo               BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by          UUID REFERENCES usuarios(id)
);

-- ============================================================
-- SAÍDAS FÍSICAS DO SORTER
-- ============================================================
CREATE TABLE saidas (
    id              SERIAL PRIMARY KEY,
    numero          INTEGER NOT NULL UNIQUE CHECK (numero > 0),
    descricao       VARCHAR(100),
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- CATÁLOGO OPCIONAL DE VALORES DE ROTEAMENTO
-- ============================================================
CREATE TABLE rotas (
    id              SERIAL PRIMARY KEY,
    codigo          VARCHAR(50) UNIQUE NOT NULL,
    descricao       VARCHAR(150) NOT NULL,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rotas_codigo ON rotas(codigo);

-- ============================================================
-- MAPEAMENTO valor → saída (por mapa)
-- valor = sigla/UF/filial conforme criterio_roteamento do mapa
-- ============================================================
CREATE TABLE mapeamento_rota_saida (
    id              SERIAL PRIMARY KEY,
    mapa_id        INTEGER NOT NULL REFERENCES mapas(id) ON DELETE CASCADE,
    valor           VARCHAR(100) NOT NULL,
    rota_id         INTEGER REFERENCES rotas(id) ON DELETE SET NULL,
    saida_id        INTEGER NOT NULL REFERENCES saidas(id) ON DELETE CASCADE,
    prioridade      INTEGER NOT NULL DEFAULT 1,
    ativo           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by      UUID REFERENCES usuarios(id),
    UNIQUE (mapa_id, valor)
);

CREATE INDEX idx_mapeamento_mapa ON mapeamento_rota_saida(mapa_id);
CREATE INDEX idx_mapeamento_valor ON mapeamento_rota_saida(valor);
CREATE INDEX idx_mapeamento_saida ON mapeamento_rota_saida(saida_id);

-- ============================================================
-- PEDIDOS RECEBIDOS DO WMS
-- ============================================================
CREATE TABLE pedidos (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    codigo_externo   VARCHAR(100),
    codigo_principal VARCHAR(100) NOT NULL,   -- etiqueta de rastreio
    rota_codigo      VARCHAR(100) NOT NULL,   -- display / fallback
    sigla            VARCHAR(50),
    uf               VARCHAR(10),
    filial           VARCHAR(100),
    dados_originais  JSONB NOT NULL,
    status           pedido_status NOT NULL DEFAULT 'pendente',
    prioridade       INTEGER NOT NULL DEFAULT 5,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processado_em    TIMESTAMPTZ,
    confirmado_em    TIMESTAMPTZ
);

CREATE INDEX idx_pedidos_codigo_principal ON pedidos(codigo_principal);
CREATE INDEX idx_pedidos_status ON pedidos(status);
CREATE INDEX idx_pedidos_rota ON pedidos(rota_codigo);
CREATE INDEX idx_pedidos_sigla ON pedidos(sigla);
CREATE INDEX idx_pedidos_uf ON pedidos(uf);
CREATE INDEX idx_pedidos_filial ON pedidos(filial);
CREATE INDEX idx_pedidos_created ON pedidos(created_at DESC);

-- ============================================================
-- ETIQUETAS ASSOCIADAS AO PEDIDO
-- ============================================================
CREATE TABLE pedido_etiquetas (
    id              SERIAL PRIMARY KEY,
    pedido_id       UUID NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    codigo          VARCHAR(100) NOT NULL,
    tipo            VARCHAR(50) DEFAULT 'barcode',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pedido_id, codigo)
);

CREATE INDEX idx_pedido_etiquetas_codigo ON pedido_etiquetas(codigo);
CREATE INDEX idx_pedido_etiquetas_pedido ON pedido_etiquetas(pedido_id);

-- ============================================================
-- CONFIRMAÇÕES DO SORTER (altura, largura, comprimento, peso)
-- ============================================================
CREATE TABLE confirmacoes_sorter (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pedido_id       UUID NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    codigo          VARCHAR(100) NOT NULL,
    altura_cm       NUMERIC(10, 2),
    largura_cm      NUMERIC(10, 2),
    comprimento_cm  NUMERIC(10, 2),
    peso_kg         NUMERIC(10, 3),
    saida_numero    INTEGER NOT NULL,
    dados_brutos    JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_confirmacoes_pedido ON confirmacoes_sorter(pedido_id);
CREATE INDEX idx_confirmacoes_codigo ON confirmacoes_sorter(codigo);

-- ============================================================
-- LOG DE INTEGRAÇÃO COM WMS
-- ============================================================
CREATE TABLE log_integracao_wms (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pedido_id       UUID REFERENCES pedidos(id) ON DELETE SET NULL,
    tipo            VARCHAR(50) NOT NULL,
    payload         JSONB,
    resposta        JSONB,
    sucesso         BOOLEAN,
    mensagem_erro   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_log_wms_pedido ON log_integracao_wms(pedido_id);
CREATE INDEX idx_log_wms_created ON log_integracao_wms(created_at DESC);

-- ============================================================
-- LOG DE OPERAÇÕES DO SORTER
-- ============================================================
CREATE TABLE log_sorter (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tipo              VARCHAR(50) NOT NULL,
    payload_entrada   JSONB,
    payload_saida     JSONB,
    codigo_encontrado VARCHAR(100),
    saida_retornada   INTEGER,
    tempo_ms          INTEGER,
    sucesso           BOOLEAN NOT NULL DEFAULT TRUE,
    mensagem          TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_log_sorter_created ON log_sorter(created_at DESC);
CREATE INDEX idx_log_sorter_codigo ON log_sorter(codigo_encontrado);

-- ============================================================
-- AUDITORIA
-- ============================================================
CREATE TABLE auditoria (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    usuario_id       UUID REFERENCES usuarios(id),
    acao             VARCHAR(100) NOT NULL,
    tabela           VARCHAR(50),
    registro_id      VARCHAR(100),
    dados_anteriores JSONB,
    dados_novos      JSONB,
    ip_origem        VARCHAR(45),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_auditoria_usuario ON auditoria(usuario_id);
CREATE INDEX idx_auditoria_created ON auditoria(created_at DESC);

-- ============================================================
-- DADOS INICIAIS
-- ============================================================

INSERT INTO config_sorter (quantidade_saidas, descricao)
VALUES (8, 'Configuração padrão inicial');

INSERT INTO saidas (numero, descricao)
SELECT gs, 'Saída ' || gs FROM generate_series(1, 8) AS gs;

INSERT INTO mapas (nome, descricao, quantidade_saidas, criterio_roteamento, habilitado)
VALUES ('Mapa padrão', 'Configuração inicial por sigla', 8, 'sigla', TRUE);

INSERT INTO rotas (codigo, descricao) VALUES
    ('SAO', 'São Paulo - Capital'),
    ('CWB', 'Curitiba'),
    ('BHZ', 'Belo Horizonte'),
    ('RIO', 'Rio de Janeiro'),
    ('BSB', 'Brasília'),
    ('POA', 'Porto Alegre'),
    ('REC', 'Recife'),
    ('FOR', 'Fortaleza');

-- Mapeamento inicial por SIGLA (valor = código da rota)
INSERT INTO mapeamento_rota_saida (mapa_id, valor, rota_id, saida_id)
SELECT m.id, r.codigo, r.id, s.id
FROM mapas m
CROSS JOIN rotas r
JOIN saidas s ON s.numero =
    CASE r.codigo
        WHEN 'SAO' THEN 1
        WHEN 'CWB' THEN 2
        WHEN 'BHZ' THEN 3
        WHEN 'RIO' THEN 4
        WHEN 'BSB' THEN 5
        WHEN 'POA' THEN 6
        WHEN 'REC' THEN 7
        WHEN 'FOR' THEN 8
    END
WHERE m.habilitado = TRUE;

-- ============================================================
-- TRIGGERS updated_at
-- ============================================================
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_timestamp_usuarios
    BEFORE UPDATE ON usuarios
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_rotas
    BEFORE UPDATE ON rotas
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_mapeamento
    BEFORE UPDATE ON mapeamento_rota_saida
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_pedidos
    BEFORE UPDATE ON pedidos
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_config
    BEFORE UPDATE ON config_sorter
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

CREATE TRIGGER set_timestamp_mapas
    BEFORE UPDATE ON mapas
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- ============================================================
-- VIEW mapeamento ativo (mapa ONLINE)
-- ============================================================
CREATE OR REPLACE VIEW vw_mapeamento_ativo AS
SELECT
    mp.id AS mapa_id,
    mp.nome AS mapa_nome,
    mp.criterio_roteamento,
    m.valor,
    s.numero AS saida_numero,
    s.descricao AS saida_descricao,
    m.prioridade,
    m.ativo
FROM mapeamento_rota_saida m
JOIN mapas mp ON mp.id = m.mapa_id
JOIN saidas s ON s.id = m.saida_id
WHERE m.ativo = TRUE
  AND mp.habilitado = TRUE
  AND s.ativo = TRUE
ORDER BY m.valor, m.prioridade;
