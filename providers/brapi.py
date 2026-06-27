import requests
from services.cache import cache


def _map_setor(setor_raw):
    texto = (setor_raw or "").lower()

    regras = [
        (
            ("bank", "finance", "financial", "insurance", "investment"),
            "bancos_financas",
        ),
        (
            ("electric", "utilities", "utility", "water", "saneamento", "energia"),
            "energia_saneamento",
        ),
        (("oil", "gas", "petroleum", "petroleo", "combust"), "petroleo_gas"),
        (
            (
                "mining",
                "steel",
                "basic materials",
                "mineracao",
                "siderurgia",
                "metals",
                "iron",
            ),
            "mineracao_siderurgia",
        ),
        (
            (
                "agriculture",
                "food",
                "beverage",
                "agro",
                "carnes",
                "non-durables",
                "consumer defensive",
            ),
            "agro_alimentos",
        ),
        (
            (
                "retail",
                "consumer",
                "leisure",
                "apparel",
                "durables",
                "varejo",
                "consumo ciclico",
                "consumer cyclical",
            ),
            "varejo_consumo",
        ),
        (
            ("health", "medical", "pharma", "education", "educacao", "saude"),
            "saude_educacao",
        ),
        (
            ("real estate", "property", "construcao", "imobiliario", "properties"),
            "construcao_imobiliario",
        ),
        (
            (
                "technology",
                "software",
                "electronic",
                "internet",
                "telecom",
                "communication",
            ),
            "tecnologia_telecom",
        ),
        (
            ("transportation", "logistics", "logistica", "transporte", "airlines"),
            "logistica_transporte",
        ),
        (
            (
                "machinery",
                "aerospace",
                "industrial",
                "industrials",
                "manufacturing",
                "bens industriais",
            ),
            "industria_bens",
        ),
    ]

    for termos, setor in regras:
        if any(termo in texto for termo in termos):
            return setor
    return "outros"


@cache.memoize(expire=3600)
def fetch_brapi_assets():
    """Busca a lista ampla da B3 na brapi preservando metadados de tipo."""
    try:
        r = requests.get(
            "https://brapi.dev/api/quote/list?sortBy=volume&sortOrder=desc", timeout=20
        )
        r.raise_for_status()
        data = r.json()
        ativos = []
        for item in data.get("stocks", []):
            ticker = item.get("stock", "")
            if not ticker:
                continue
            nome = item.get("name", ticker)
            brapi_type = item.get("type") or item.get("stockType") or ""
            ativos.append(
                {
                    "nome": nome,
                    "ticker": f"{ticker}.SA",
                    "codigo": ticker,
                    "tipo": "b3",
                    "brapiType": brapi_type,
                    "setor": _map_setor(item.get("sector")),
                    "setorOriginal": item.get("sector") or "",
                    "volume": item.get("volume", 0),
                    "marketCap": item.get("market_cap", 0),
                }
            )
        return ativos
    except Exception:
        return []


def get_brapi_market_caps():
    try:
        # Reutilizamos os dados de fetch_brapi_assets (que já faz cache de 1h)
        # para evitar fazer a mesma requisição pesada para a API novamente.
        ativos = fetch_brapi_assets()
        return {item["codigo"]: item.get("marketCap", 0) for item in ativos}
    except Exception:
        return {}
