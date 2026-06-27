import flet as ft

from core.models import MarketCapInfo

SETORES_ACOES = [
    ("all", "Todos os setores"),
    ("bancos_financas", "Bancos & Finanças"),
    ("energia_saneamento", "Energia & Saneamento"),
    ("petroleo_gas", "Petróleo & Gás"),
    ("mineracao_siderurgia", "Mineração & Siderurgia"),
    ("agro_alimentos", "Agroindústria & Alimentos"),
    ("varejo_consumo", "Varejo & Consumo"),
    ("saude_educacao", "Saúde & Educação"),
    ("construcao_imobiliario", "Construção Civil"),
    ("tecnologia_telecom", "Tecnologia & Telecom"),
    ("logistica_transporte", "Logística & Transporte"),
    ("industria_bens", "Indústria & Bens"),
    ("outros", "Outros"),
]

SETORES_FIIS = [
    ("all", "Todos os setores"),
    ("papel", "Papel"),
    ("tijolo", "Tijolo"),
    ("misto", "Misto"),
    ("outros", "Outros"),
]

nomes_setores = {
    "all": "Todos os setores",
    "bancos_financas": "Bancos & Finanças",
    "energia_saneamento": "Energia & Saneamento",
    "petroleo_gas": "Petróleo & Gás",
    "mineracao_siderurgia": "Mineração & Siderurgia",
    "agro_alimentos": "Agroindústria & Alimentos",
    "varejo_consumo": "Varejo & Consumo",
    "saude_educacao": "Saúde & Educação",
    "construcao_imobiliario": "Construção Civil",
    "tecnologia_telecom": "Tecnologia & Telecom",
    "logistica_transporte": "Logística & Transporte",
    "industria_bens": "Indústria & Bens",
    "outros": "Outros",
    "financeiro": "Bancos & Finanças",
    "utilidade_publica": "Energia & Saneamento",
    "materiais_basicos": "Mineração & Siderurgia",
    "bens_industriais": "Indústria & Bens",
    "consumo_nao_ciclico": "Agroindústria & Alimentos",
    "consumo_ciclico": "Varejo & Consumo",
    "saude": "Saúde & Educação",
    "tecnologia": "Tecnologia & Telecom",
    "comunicacoes": "Tecnologia & Telecom",
    "imobiliario": "Construção Civil",
    "papel": "Papel",
    "tijolo": "Tijolo",
    "misto": "Misto",
}


def formatar_market_cap(mc) -> MarketCapInfo:
    """Formata market cap para exibicao em UI.

    Retorna MarketCapInfo dataclass com texto, categoria, color e bg.
    Retrocompativel: MarketCapInfo suporta acesso mc_data['texto']
    para codigo que ainda usa dict-style access.
    """
    if mc is None:
        return MarketCapInfo(
            texto="N/D",
            categoria="",
            color=ft.Colors.BLUE_GREY_400,
            bg=ft.Colors.TRANSPARENT,
        )

    if mc >= 1e12:
        texto = f"R$ {mc / 1e12:.2f}T"
    elif mc >= 1e9:
        texto = f"R$ {mc / 1e9:.2f}B"
    elif mc >= 1e6:
        texto = f"R$ {mc / 1e6:.2f}M"
    else:
        texto = f"R$ {mc}"

    if mc >= 10e9:
        cat = "Blue Chip"
        color = ft.Colors.BLUE_400
        bg = ft.Colors.with_opacity(0.1, ft.Colors.BLUE_400)
    elif mc >= 2e9:
        cat = "Mid Cap"
        color = ft.Colors.PURPLE_400
        bg = ft.Colors.with_opacity(0.1, ft.Colors.PURPLE_400)
    elif mc >= 500e6:
        cat = "Small Cap"
        color = ft.Colors.GREEN_400
        bg = ft.Colors.with_opacity(0.1, ft.Colors.GREEN_400)
    else:
        cat = "Micro Cap"
        color = ft.Colors.AMBER_400
        bg = ft.Colors.with_opacity(0.1, ft.Colors.AMBER_400)

    return MarketCapInfo(texto=texto, categoria=cat, color=color, bg=bg)


def get_yfinance_params(timeframe: str, sem_filtro: bool = False):
    """Retorna (period, interval) para yfinance.download baseado no timeframe.

    Timeframes suportados: '1d' (diario), '1s' (semanal).
    Timeframe '4h' foi removido da UI na Fase 1; referencias limpas na Fase 7.
    """
    mapping = {"1d": ("100d", "1d"), "1s": ("700d", "1wk")}
    period, interval = mapping.get(timeframe, ("100d", "1d"))

    if sem_filtro:
        # Periodos minimos para sem_filtro (sem indicadores ativos)
        min_mapping = {"1d": "100d", "1s": "700d"}
        period = min_mapping.get(timeframe, "100d")

    return period, interval


def formatar_tendencia_recente(qtd_candles, timeframe, tendencia):
    """Formata texto de tendencia recente (ex: 'Alta ha 3 dias').

    Timeframes suportados: '1d' (dia/dias), '1s' (sem/sem).
    """
    direcao = "Alta" if tendencia == "alta" else "Baixa"
    unidades = {"1d": ("dia", "dias"), "1s": ("sem", "sem")}
    sing, plur = unidades.get(timeframe, ("candle", "candles"))
    unidade = sing if qtd_candles == 1 else plur
    return f"{direcao} há {qtd_candles} {unidade}"
