-- ============================================================
-- Tabelas de Pedidos + Confirmação do Sorter (versão completa)
-- Pode rodar em banco já existente (IF NOT EXISTS / ADD COLUMN)
-- ============================================================

-- Pedidos
CREATE TABLE IF NOT EXISTS pedidos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    codigo_externo  VARCHAR(100),
    codigo_principal VARCHAR(100) NOT NULL,   -- etiqueta de rastreio
    rota_codigo     VARCHAR(100) NOT NULL,    -- valor de display / fallback
    sigla           VARCHAR(50),
    uf              VARCHAR(10),
    filial          VARCHAR(100),
    dados_originais JSONB NOT NULL,
    status          pedido_status NOT NULL DEFAULT 'pendente',
    prioridade      INTEGER NOT NULL DEFAULT 5,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processado_em   TIMESTAMPTZ,
    confirmado_em   TIMESTAMPTZ
);

-- Garante colunas em bases antigas
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS sigla VARCHAR(50);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS uf VARCHAR(10);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS filial VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_pedidos_codigo_principal ON pedidos(codigo_principal);
CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos(status);
CREATE INDEX IF NOT EXISTS idx_pedidos_rota ON pedidos(rota_codigo);
CREATE INDEX IF NOT EXISTS idx_pedidos_sigla ON pedidos(sigla);
CREATE INDEX IF NOT EXISTS idx_pedidos_uf ON pedidos(uf);
CREATE INDEX IF NOT EXISTS idx_pedidos_filial ON pedidos(filial);
CREATE INDEX IF NOT EXISTS idx_pedidos_created ON pedidos(created_at);

-- Etiquetas vinculadas
CREATE TABLE IF NOT EXISTS pedido_etiquetas (
    id          SERIAL PRIMARY KEY,
    pedido_id   UUID NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    codigo      VARCHAR(100) NOT NULL,
    tipo        VARCHAR(50) NOT NULL DEFAULT 'barcode',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pedido_etiquetas_codigo ON pedido_etiquetas(codigo);
CREATE INDEX IF NOT EXISTS idx_pedido_etiquetas_pedido ON pedido_etiquetas(pedido_id);

-- Confirmação do sorter (altura, largura, comprimento, peso, saída)
CREATE TABLE IF NOT EXISTS confirmacoes_sorter (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
CREATE INDEX IF NOT EXISTS idx_confirmacoes_pedido ON confirmacoes_sorter(pedido_id);
CREATE INDEX IF NOT EXISTS idx_confirmacoes_codigo ON confirmacoes_sorter(codigo);
