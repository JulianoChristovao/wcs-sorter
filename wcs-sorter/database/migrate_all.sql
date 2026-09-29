-- ============================================================
-- MIGRAÇÃO COMPLETA WCS Sorter
-- Corrige colunas faltantes: pedidos.sigla/uf/filial e mapas.criterio_roteamento
-- ============================================================

BEGIN;

-- ---------- Enum critério de roteamento ----------
DO $$ BEGIN
    CREATE TYPE criterio_roteamento AS ENUM ('sigla', 'uf', 'filial');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ---------- Mapas ----------
CREATE TABLE IF NOT EXISTS mapas (
    id                  SERIAL PRIMARY KEY,
    nome                VARCHAR(100) NOT NULL,
    descricao           VARCHAR(255),
    quantidade_saidas   INTEGER NOT NULL DEFAULT 8,
    criterio_roteamento criterio_roteamento NOT NULL DEFAULT 'sigla',
    habilitado          BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by          UUID
);

ALTER TABLE mapas ADD COLUMN IF NOT EXISTS criterio_roteamento criterio_roteamento;
UPDATE mapas SET criterio_roteamento = 'sigla' WHERE criterio_roteamento IS NULL;
ALTER TABLE mapas ALTER COLUMN criterio_roteamento SET DEFAULT 'sigla';
ALTER TABLE mapas ALTER COLUMN criterio_roteamento SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_mapas_habilitado ON mapas(habilitado);

-- ---------- Pedidos ----------
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS sigla  VARCHAR(50);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS uf     VARCHAR(10);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS filial VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_pedidos_sigla  ON pedidos(sigla);
CREATE INDEX IF NOT EXISTS idx_pedidos_uf     ON pedidos(uf);
CREATE INDEX IF NOT EXISTS idx_pedidos_filial ON pedidos(filial);

UPDATE pedidos
SET sigla = rota_codigo
WHERE sigla IS NULL AND rota_codigo IS NOT NULL;

-- ---------- Mapeamento valor → saída ----------
ALTER TABLE mapeamento_rota_saida ADD COLUMN IF NOT EXISTS mapa_id INTEGER;
ALTER TABLE mapeamento_rota_saida ADD COLUMN IF NOT EXISTS valor VARCHAR(100);

-- Garante pelo menos um mapa padrão
INSERT INTO mapas (nome, descricao, quantidade_saidas, criterio_roteamento, habilitado)
SELECT 'Mapa padrão', 'Criado pela migração', 8, 'sigla', TRUE
WHERE NOT EXISTS (SELECT 1 FROM mapas);

UPDATE mapeamento_rota_saida m
SET mapa_id = (SELECT id FROM mapas ORDER BY habilitado DESC, id ASC LIMIT 1)
WHERE mapa_id IS NULL;

UPDATE mapeamento_rota_saida m
SET valor = r.codigo
FROM rotas r
WHERE m.rota_id = r.id
  AND (m.valor IS NULL OR m.valor = '');

UPDATE mapeamento_rota_saida
SET valor = COALESCE(NULLIF(valor, ''), 'SEM_VALOR')
WHERE valor IS NULL OR valor = '';

-- Ajusta constraints (ignora se já existirem)
DO $$ BEGIN
    ALTER TABLE mapeamento_rota_saida
        ALTER COLUMN mapa_id SET NOT NULL;
EXCEPTION WHEN others THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE mapeamento_rota_saida
        ALTER COLUMN valor SET NOT NULL;
EXCEPTION WHEN others THEN NULL;
END $$;

ALTER TABLE mapeamento_rota_saida DROP CONSTRAINT IF EXISTS uq_rota_saida;
ALTER TABLE mapeamento_rota_saida DROP CONSTRAINT IF EXISTS uq_mapa_rota;
ALTER TABLE mapeamento_rota_saida DROP CONSTRAINT IF EXISTS uq_mapa_valor;

DO $$ BEGIN
    ALTER TABLE mapeamento_rota_saida
        ADD CONSTRAINT uq_mapa_valor UNIQUE (mapa_id, valor);
EXCEPTION
    WHEN duplicate_object THEN NULL;
    WHEN unique_violation THEN NULL;
END $$;

DO $$ BEGIN
    ALTER TABLE mapeamento_rota_saida
        ALTER COLUMN rota_id DROP NOT NULL;
EXCEPTION WHEN others THEN NULL;
END $$;

CREATE INDEX IF NOT EXISTS idx_mapeamento_mapa ON mapeamento_rota_saida(mapa_id);
CREATE INDEX IF NOT EXISTS idx_mapeamento_valor ON mapeamento_rota_saida(valor);

-- ---------- Confirmações sorter ----------
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

COMMIT;

-- Verificação
SELECT 'pedidos.sigla' AS col, COUNT(*) FROM information_schema.columns WHERE table_name='pedidos' AND column_name='sigla'
UNION ALL
SELECT 'pedidos.uf', COUNT(*) FROM information_schema.columns WHERE table_name='pedidos' AND column_name='uf'
UNION ALL
SELECT 'pedidos.filial', COUNT(*) FROM information_schema.columns WHERE table_name='pedidos' AND column_name='filial'
UNION ALL
SELECT 'mapas.criterio_roteamento', COUNT(*) FROM information_schema.columns WHERE table_name='mapas' AND column_name='criterio_roteamento'
UNION ALL
SELECT 'mapeamento.valor', COUNT(*) FROM information_schema.columns WHERE table_name='mapeamento_rota_saida' AND column_name='valor';
