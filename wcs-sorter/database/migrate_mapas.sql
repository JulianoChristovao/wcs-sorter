-- Migração: suporte a N mapas com flag habilitado
-- Execute no banco existente (uma vez):
--   docker compose exec -T db psql -U wcs_user -d wcs_db < database/migrate_mapas.sql
-- Ou via:
--   Get-Content database\migrate_mapas.sql | docker compose exec -T db psql -U wcs_user -d wcs_db

BEGIN;

CREATE TABLE IF NOT EXISTS mapas (
    id              SERIAL PRIMARY KEY,
    nome            VARCHAR(100) NOT NULL,
    descricao       VARCHAR(255),
    quantidade_saidas INTEGER NOT NULL DEFAULT 8,
    habilitado      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by      UUID REFERENCES usuarios(id)
);

CREATE INDEX IF NOT EXISTS idx_mapas_habilitado ON mapas(habilitado);

-- Mapa padrão a partir da config atual
INSERT INTO mapas (nome, descricao, quantidade_saidas, habilitado)
SELECT
    'Mapa padrão',
    COALESCE(descricao, 'Migrado da configuração inicial'),
    quantidade_saidas,
    TRUE
FROM config_sorter
WHERE ativo = TRUE
ORDER BY id DESC
LIMIT 1;

-- Se não havia config, cria mapa default
INSERT INTO mapas (nome, descricao, quantidade_saidas, habilitado)
SELECT 'Mapa padrão', 'Mapa inicial', 8, TRUE
WHERE NOT EXISTS (SELECT 1 FROM mapas);

-- Adiciona mapa_id aos mapeamentos existentes
ALTER TABLE mapeamento_rota_saida
    ADD COLUMN IF NOT EXISTS mapa_id INTEGER REFERENCES mapas(id) ON DELETE CASCADE;

UPDATE mapeamento_rota_saida m
SET mapa_id = (SELECT id FROM mapas WHERE habilitado = TRUE ORDER BY id LIMIT 1)
WHERE mapa_id IS NULL;

-- Remove constraint antiga e cria nova
ALTER TABLE mapeamento_rota_saida DROP CONSTRAINT IF EXISTS uq_rota_saida;
ALTER TABLE mapeamento_rota_saida DROP CONSTRAINT IF EXISTS uq_mapa_rota;

-- Garante NOT NULL após preenchimento
ALTER TABLE mapeamento_rota_saida
    ALTER COLUMN mapa_id SET NOT NULL;

ALTER TABLE mapeamento_rota_saida
    ADD CONSTRAINT uq_mapa_rota UNIQUE (mapa_id, rota_id);

CREATE INDEX IF NOT EXISTS idx_mapeamento_mapa ON mapeamento_rota_saida(mapa_id);

COMMIT;
