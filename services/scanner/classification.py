"""
Classificacao de ativos por codigo (sufixo numerico B3).

Regras:
    'acao'  - ultimo digito 3, 4, 5, 6, 7 ou 8
    'fii'   - termina em 11 (FIIs, Units, ETFs)
    'bdr'   - termina em 31, 32, 33, 34, 35 ou 39
    None    - fracionario (F), excluido (96) ou nao reconhecido
"""
from typing import Optional

# Sufixos de BDR (Brazilian Depositary Receipts)
BDR_SUFFIXES = ("31", "32", "33", "34", "35", "39")

# Sufixos excluidos (direitos de subscricao, recibos, etc)
EXCLUDED_SUFFIXES = ("96",)


def classificar_por_codigo(codigo: Optional[str]) -> Optional[str]:
    """Classifica o ativo EXCLUSIVAMENTE pelo sufixo numerico do codigo.

    Retorna:
        'acao'  - ultimo digito 3, 4, 5, 6, 7 ou 8
        'fii'   - termina em 11 (FIIs, Units, ETFs)
        'bdr'   - termina em 31, 32, 33, 34, 35 ou 39
        None    - fracionario (F), excluido (96) ou nao reconhecido
    """
    if not codigo or len(codigo) < 4:
        return None

    # Fracionario
    if codigo.endswith("F"):
        return None

    # Sufixos excluidos (direitos de subscricao, recibos, etc.)
    for suf in EXCLUDED_SUFFIXES:
        if codigo.endswith(suf):
            return None

    # BDRs: terminam em 31, 32, 33, 34, 35, 39
    for suf in BDR_SUFFIXES:
        if codigo.endswith(suf):
            return "bdr"

    # FIIs / Units / ETFs: terminam em 11
    if codigo.endswith("11"):
        return "fii"

    # Acoes: ultimo digito e 3, 4, 5, 6, 7 ou 8
    if codigo[-1] in "345678":
        return "acao"

    return None


def codigo(ativo: dict) -> str:
    """Extrai o codigo de um ativo (sem sufixo .SA, uppercase).

    Bug conhecido: .replace('.SA', '') e case-sensitive, entao 'petr4.sa'
    (lowercase) nao tem o .SA removido. Mantido para retrocompatibilidade.
    """
    return (
        str(ativo.get("codigo") or ativo.get("ticker") or "")
        .replace(".SA", "")
        .upper()
    )


def normalizar_ativo(ativo: dict, tipo: Optional[str] = None) -> dict:
    """Normaliza um dict de ativo preenchendo campos faltantes.

    Garante que codigo, ticker, nome e setor estejam presentes.
    """
    cod = codigo(ativo)
    item = {**ativo}
    item["codigo"] = cod
    item["ticker"] = item.get("ticker") or f"{cod}.SA"
    if tipo:
        item["tipo"] = tipo
    item["nome"] = item.get("nome") or cod
    item["setor"] = item.get("setor") or "outros"
    return item


def merge_por_codigo(*listas: list) -> list:
    """Merge de multiplas listas de ativos, deduplicando por codigo.

    Se o mesmo codigo aparece em mais de uma lista, ultima ocorrencia vence.
    """
    merged = {}
    for lista in listas:
        for ativo in lista:
            cod = codigo(ativo)
            if not cod:
                continue
            merged[cod] = normalizar_ativo(ativo)
    return list(merged.values())
