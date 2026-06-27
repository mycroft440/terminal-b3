"""
Modelos de dados tipados para o Terminal B3 Pro.

Este modulo introduz dataclasses e TypedDicts para substituir os dicts
nao-tipados que circulam entre scanner -> state_manager -> cards -> dialogs.

IMPORTANTE - Estrategia de adocao incremental:
- Esta Fase 2 APENAS define os modelos. Nada consome ainda.
- A Fase 3+ ira substituir os dicts gradativamente, mantendo
  retrocompatibilidade via to_dict()/from_dict().
- O cache b3_evaluated_cache.json armazena dicts em formato camelCase
  (isAlta, qtdCandles, etc) - to_dict()/from_dict() sao compatíveis com
  esse formato para permitir migracao sem invalidar cache existente.

Convencao de nomes:
- Atributos Python em snake_case: is_alta, qtd_candles
- Chaves do dict (to_dict) em camelCase: isAlta, qtdCandles (compat com cache)
"""
from dataclasses import dataclass, field
from typing import Any, Optional, Literal, TypedDict


# ─── Tipos literais ─────────────────────────────────────────────────────────
MarketType = Literal["todos", "acoes", "fiis", "bdrs"]
Timeframe = Literal["1d", "1s"]  # "4h" removido da UI
AssetType = Literal["acao", "fii", "bdr", "b3"]
TrendDirection = Literal["alta", "baixa", "neutra"]
IndicatorName = Literal["MMS", "RSI", "STOCH"]


# ─── Ativo (substitui dict ativo em scanner.py:74-83 e brapi.py) ────────────
@dataclass
class Ativo:
    """Ativo financeiro (acao, FII, BDR, etc)."""
    codigo: str                              # "PETR4" (sem .SA)
    ticker: str                              # "PETR4.SA"
    nome: str
    setor: str = "outros"
    tipo: AssetType = "b3"
    volume: float = 0.0
    market_cap: float = 0.0
    setor_original: str = ""
    brapi_type: str = ""

    @classmethod
    def from_raw(cls, raw: dict, tipo: Optional[AssetType] = None) -> "Ativo":
        """Cria Ativo a partir de dict bruto (vindo de catalogo ou brapi)."""
        codigo = str(raw.get("codigo") or raw.get("ticker") or "")
        # Remove sufixo .SA case-insensitive (bug conhecido em services.scanner._codigo)
        if codigo.upper().endswith(".SA"):
            codigo = codigo[:-3]
        codigo = codigo.upper()
        return cls(
            codigo=codigo,
            ticker=raw.get("ticker") or f"{codigo}.SA",
            nome=raw.get("nome") or codigo,
            setor=raw.get("setor") or "outros",
            tipo=tipo or raw.get("tipo", "b3"),
            volume=float(raw.get("volume", 0) or 0),
            market_cap=float(raw.get("marketCap", raw.get("market_cap", 0)) or 0),
            setor_original=raw.get("setorOriginal", ""),
            brapi_type=raw.get("brapiType", ""),
        )

    def to_dict(self) -> dict:
        """Serializa para dict (formato catalogo/brapi)."""
        return {
            "codigo": self.codigo,
            "ticker": self.ticker,
            "nome": self.nome,
            "setor": self.setor,
            "tipo": self.tipo,
            "volume": self.volume,
            "marketCap": self.market_cap,
            "setorOriginal": self.setor_original,
            "brapiType": self.brapi_type,
        }


# ─── Indicador (substitui dicts em scanner.py:363-380) ──────────────────────
class IndicadorSinal(TypedDict):
    """Sinal de um indicador tecnico (MMS, RSI, STOCH).

    TypedDict (nao dataclass) porque e usado como item de lista em
    cache e JSON; mantem formato exato do dict original.
    """
    nome: IndicatorName
    sinal: int  # -1 (baixa), 0 (neutro), 1 (alta)


# ─── ResultadoAvaliacao (substitui dict em scanner.py:179-196 e 404-420) ────
@dataclass
class ResultadoAvaliacao:
    """Resultado de avaliar um ativo com indicadores tecnicos.

    Formato camelCase no to_dict()/from_dict() para compatibilidade
    com o cache b3_evaluated_cache.json existente.
    """
    ativo: dict  # Dict bruto do ativo (sera Ativo tipado na Fase 3)
    fechamento: float = 0.0
    variacao: float = 0.0
    variacao_7d: float = 0.0
    variacao_30d: float = 0.0
    is_alta: bool = True
    indicadores: list = field(default_factory=list)
    sem_filtro: bool = False
    sem_dados: bool = False
    sem_confluencia: bool = False
    qtd_candles: int = 0
    tempo_tendencia: str = ""
    tendencia: TrendDirection = "neutra"
    market_cap: float = 0.0
    volume_spike: bool = False
    data_variacao: str = ""

    def to_dict(self) -> dict:
        """Serializa para dict em formato camelCase (compat com cache)."""
        return {
            "ativo": self.ativo,
            "fechamento": self.fechamento,
            "variacao": self.variacao,
            "variacao_7d": self.variacao_7d,
            "variacao_30d": self.variacao_30d,
            "isAlta": self.is_alta,
            "indicadores": self.indicadores,
            "semFiltro": self.sem_filtro,
            "semDados": self.sem_dados,
            "semConfluencia": self.sem_confluencia,
            "qtdCandles": self.qtd_candles,
            "tempoTendencia": self.tempo_tendencia,
            "tendencia": self.tendencia,
            "marketCap": self.market_cap,
            "volumeSpike": self.volume_spike,
            "dataVariacao": self.data_variacao,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ResultadoAvaliacao":
        """Deserializa de dict (formato camelCase do cache)."""
        return cls(
            ativo=d.get("ativo", {}),
            fechamento=d.get("fechamento", 0.0),
            variacao=d.get("variacao", 0.0),
            variacao_7d=d.get("variacao_7d", 0.0),
            variacao_30d=d.get("variacao_30d", 0.0),
            is_alta=d.get("isAlta", True),
            indicadores=d.get("indicadores", []),
            sem_filtro=d.get("semFiltro", False),
            sem_dados=d.get("semDados", False),
            sem_confluencia=d.get("semConfluencia", False),
            qtd_candles=d.get("qtdCandles", 0),
            tempo_tendencia=d.get("tempoTendencia", ""),
            tendencia=d.get("tendencia", "neutra"),
            market_cap=d.get("marketCap", 0.0),
            volume_spike=d.get("volumeSpike", False),
            data_variacao=d.get("dataVariacao", ""),
        )


# ─── PosicaoCarteira (substitui dict em wallet_dialog.py:114-118) ───────────
@dataclass
class PosicaoCarteira:
    """Posicao de um ativo em uma carteira do usuario."""
    data: str                       # ISO date "2025-01-15"
    preco_entrada: float
    quantidade: float

    def to_dict(self) -> dict:
        return {
            "data": self.data,
            "preco_entrada": self.preco_entrada,
            "quantidade": self.quantidade,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PosicaoCarteira":
        return cls(
            data=d.get("data", ""),
            preco_entrada=float(d.get("preco_entrada", 0) or 0),
            quantidade=float(d.get("quantidade", 0) or 0),
        )


# ─── Anotacao (substitui dict em notes_dialog.py:361-365) ───────────────────
@dataclass
class Anotacao:
    """Anotacao de texto + imagens anexadas para um ticker."""
    texto: str = ""
    imagens: list = field(default_factory=list)
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "texto": self.texto,
            "imagens": self.imagens,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: Any) -> "Anotacao":
        """Deserializa. Aceita str (formato antigo) ou dict (formato novo)."""
        if isinstance(d, str):
            # Formato antigo: anotacoes eram apenas o texto
            return cls(texto=d, imagens=[], updated_at="")
        return cls(
            texto=d.get("texto", ""),
            imagens=d.get("imagens", []),
            updated_at=d.get("updated_at", ""),
        )


# ─── MarketCapInfo (substitui retorno dict de formatar_market_cap) ──────────
@dataclass
class MarketCapInfo:
    """Informacao formatada de market cap para exibicao em UI."""
    texto: str                       # "R$ 1.23B"
    categoria: str                   # "Blue Chip", "Mid Cap", etc
    color: Any                       # ft.Colors.X (str ou enum)
    bg: Any                          # bgcolor para badge

    def to_dict(self) -> dict:
        """Serializa para dict (retrocompatibilidade com cards.py)."""
        return {
            "texto": self.texto,
            "categoria": self.categoria,
            "color": self.color,
            "bg": self.bg,
        }

    # ─── Compatibilidade com acesso tipo dict ────────────────────────────
    # Permite que codigo existente continue usando mc_data["texto"] durante
    # a transicao para a nova API mc_data.texto
    def __getitem__(self, key: str) -> Any:
        mapping = {
            "texto": self.texto,
            "categoria": self.categoria,
            "color": self.color,
            "bg": self.bg,
        }
        if key not in mapping:
            raise KeyError(f"MarketCapInfo nao tem chave '{key}'")
        return mapping[key]

    def __contains__(self, key: str) -> bool:
        return key in {"texto", "categoria", "color", "bg"}


# ─── UIState (subset tipado de state para configuracao da UI) ───────────────
@dataclass
class UIState:
    """Estado persistivel da UI (salvo em b3_ui_state.json)."""
    market: MarketType = "todos"
    timeframe: Timeframe = "1d"
    sector: str = "all"
    sort: str = "all"
    search: str = ""
    mms_active: bool = True
    mms_periodos: list = field(default_factory=lambda: [20])
    rsi_active: bool = True
    stoch_active: bool = False
    is_loading: bool = False

    def to_dict(self) -> dict:
        return {
            "market": self.market,
            "timeframe": self.timeframe,
            "sector": self.sector,
            "sort": self.sort,
            "search": self.search,
            "mms_active": self.mms_active,
            "mms_periodos": self.mms_periodos,
            "rsi_active": self.rsi_active,
            "stoch_active": self.stoch_active,
            "is_loading": self.is_loading,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UIState":
        return cls(
            market=d.get("market", "todos"),
            timeframe=d.get("timeframe", "1d"),
            sector=d.get("sector", "all"),
            sort=d.get("sort", "all"),
            search=d.get("search", ""),
            mms_active=d.get("mms_active", True),
            mms_periodos=d.get("mms_periodos", [20]),
            rsi_active=d.get("rsi_active", True),
            stoch_active=d.get("stoch_active", False),
            is_loading=d.get("is_loading", False),
        )


__all__ = [
    # Tipos literais
    "MarketType",
    "Timeframe",
    "AssetType",
    "TrendDirection",
    "IndicatorName",
    # Dataclasses
    "Ativo",
    "ResultadoAvaliacao",
    "PosicaoCarteira",
    "Anotacao",
    "MarketCapInfo",
    "UIState",
    # TypedDicts
    "IndicadorSinal",
]
