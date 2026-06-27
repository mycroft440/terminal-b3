"""
Servico de background para pre-aquecer cache de mercado.

Roda em processo separado (subprocess.Popen a partir de settings_dialog.py)
e atualiza cache yfinance a cada 5 minutos para o mercado + timeframe
configurados no estado da UI.

Antes da Fase 6.2: tinha get_state() duplicando logica de StateManager.
Agora: usa StateManager.load_all() + extrai apenas campos necessarios.
"""
import time
import os
import logging

from services.scanner import gerar_chunks_ativos
from core import paths as _paths
from ui.state_manager import StateManager

UI_STATE_FILE = _paths.UI_STATE_FILE
PID_FILE = _paths.PID_FILE

# Intervalo de atualizacao do cache (5 minutos)
CACHE_REFRESH_INTERVAL = 300


def get_state() -> dict:
    """Carrega estado da UI usando StateManager (fonte unica de verdade).

    Retorna apenas campos relevantes para o background service:
    market, timeframe, mms_active, mms_periodos, rsi_active, stoch_active.

    Substitui implementacao anterior que duplicava logica de parsing JSON
    do StateManager, evitando drift entre processos.
    """
    sm = StateManager()
    state = sm.state
    return {
        "market": state.get("market", "acoes"),
        "timeframe": state.get("timeframe", "1d"),
        "mms_active": state.get("mms_active", True),
        "mms_periodos": state.get("mms_periodos", [20]),
        "rsi_active": state.get("rsi_active", True),
        "stoch_active": state.get("stoch_active", False),
    }


def run_service():
    """Loop principal do servico de background.

    A cada CACHE_REFRESH_INTERVAL segundos:
    1. Carrega estado da UI (market, timeframe, filtros)
    2. Atualiza cache para mercado + timeframe atuais
    3. Atualiza cache fallback para 1d (se timeframe atual != 1d)
    4. Sleep e repete
    """
    logging.info("Servico de background iniciado.")
    # Grava o PID para podermos matar depois
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    try:
        while True:
            state = get_state()
            market = state["market"]
            tf = state["timeframe"]
            mms = state["mms_periodos"] if state["mms_active"] else []
            rsi = state["rsi_active"]
            stoch = state["stoch_active"]

            logging.info(f"Atualizando cache para mercado={market}, tf={tf}...")

            try:
                gen = gerar_chunks_ativos(
                    tf, market, "all", mms, rsi, stoch, False, exclude_tickers=set()
                )
                for chunk in gen:
                    pass  # O generator ja faz o download e salva no cache
                logging.info(f"Cache atualizado com sucesso para {market} ({tf}).")
            except Exception as e:
                logging.error(f"Erro na varredura do background service: {e}")

            # Atualiza tambem um segundo timeframe longo como fallback
            # (ex: 1d se nao for o principal)
            if tf != "1d":
                logging.info(
                    f"Atualizando cache para mercado={market}, tf=1d (fallback)..."
                )
                try:
                    gen2 = gerar_chunks_ativos(
                        "1d",
                        market,
                        "all",
                        mms,
                        rsi,
                        stoch,
                        False,
                        exclude_tickers=set(),
                    )
                    for _ in gen2:
                        pass
                except Exception as e:
                    logging.error(f"Erro no fallback do background service: {e}")

            # Sleep
            time.sleep(CACHE_REFRESH_INTERVAL)
    finally:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [BG_SERVICE] %(message)s",
        handlers=[logging.FileHandler("debug.log", mode="a", encoding="utf-8")],
    )
    run_service()
