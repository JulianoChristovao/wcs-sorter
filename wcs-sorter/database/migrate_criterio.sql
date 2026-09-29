BEGIN;

-- Critério de roteamento no mapa
DO $$ BEGIN
    CREATE TYPE criterio_roteamento AS ENUM ('sigla', 'uf', 'filial');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE mapas
    ADD COLUMN IF NOT EXISTS criterio_roteamento criterio_roteamento NOT NULL DEFAULT 'sigla';

-- Campos flexíveis no pedido
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS sigla VARCHAR(50);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS uf VARCHAR(10);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS filial VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_pedidos_sigla ON pedidos(sigla);
CREATE INDEX IF NOT EXISTS idx_pedidos_uf ON pedidos(uf);
CREATE INDEX IF NOT EXISTS idx_pedidos_filial ON pedidos(filial);

-- Valor no mapeamento (substitui dependência exclusiva de rota_id)
ALTER TABLE mapeamento_rota_saida ADD COLUMN IF NOT EXISTS valor VARCHAR(100);

UPDATE mapeamento_rota_saida m
SET valor = r.codigo
FROM rotas r
WHERE m.rota_id = r.id AND (m.valor IS NULL OR m.valor = '');

UPDATE mapeamento_rota_saida m
SET valor = COALESCE(valor, 'SEM_VALOR')
WHERE valor IS NULL OR valor = '';

ALTER TABLE mapeamento_rota_saida ALTER COLUMN valor SET NOT NULL;

-- Ajusta unique constraint
ALTER TABLE mapeamento_rota_saida DROP CONSTRAINT IF EXISTS uq_mapa_rota;
ALTER TABLE mapeamento_rota_saida DROP CONSTRAINT IF EXISTS uq_mapa_valor;
ALTER TABLE mapeamento_rota_saida ADD CONSTRAINT uq_mapa_valor UNIQUE (mapa_id, valor);

-- rota_id passa a ser opcional
ALTER TABLE mapeamento_rota_saida ALTER COLUMN rota_id DROP NOT NULL;

-- Backfill pedidos
UPDATE pedidos SET sigla = rota_codigo WHERE sigla IS NULL AND rota_codigo IS NOT NULL;

COMMIT;
