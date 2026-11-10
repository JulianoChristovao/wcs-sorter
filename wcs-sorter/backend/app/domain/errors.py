"""Erros de negócio do domínio WCS (sem dependência de HTTP/ORM)."""


class DomainError(Exception):
    """Erro de regra de negócio do domínio."""


class CriterioInvalidoError(DomainError):
    """Critério de roteamento fora de sigla | uf | filial."""


class ConflitoDestinosError(DomainError):
    """Códigos válidos apontam para destinos distintos (RN-03)."""


class SemRotaError(DomainError):
    """Nenhum código conhecido ou sem mapeamento no mapa ONLINE (RN-02/RF-04)."""


class MapeamentoDuplicadoError(DomainError):
    """Mesmo valor já mapeado para outra saída no mapa (RN-06)."""


class MapaInvalidoError(DomainError):
    """Mapa ausente, inválido ou sem critério utilizável."""
