"""
Centraliza todos os caminhos de arquivos e diretorios do projeto.

Antes deste modulo, o calculo de BASE_DIR estava duplicado em 4+ arquivos
(catalog.py, state_manager.py, background_service.py, settings_dialog.py).
Agora todos importam de core.paths para evitar drift e inconsistencias.

Usar:
    from core.paths import BASE_DIR, DADOS_DIR, ATIVOS_PATH, IMAGES_DIR, ...

Os diretorios DADOS_DIR, CARTEIRAS_DIR, ANOTACOES_DIR, IMAGES_DIR sao
criados automaticamente na importacao do modulo (idempotente).
"""
import os

# ─── Diretorios base ────────────────────────────────────────────────────────
# BASE_DIR = raiz do projeto (onde esta main.py e ativos.json)
# Calculado a partir de __file__ (core/paths.py -> dirname 2x = raiz)
BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Diretorios de dados (nao versionados, em .gitignore)
DADOS_DIR: str = os.path.join(BASE_DIR, "dados")
CARTEIRAS_DIR: str = os.path.join(DADOS_DIR, "carteiras")
ANOTACOES_DIR: str = os.path.join(DADOS_DIR, "anotacoes")
IMAGES_DIR: str = os.path.join(ANOTACOES_DIR, "imgs")

# Diretorio de assets (versionado, com fontes/imagens estaticas)
ASSETS_DIR: str = os.path.join(BASE_DIR, "assets")

# ─── Arquivos de dados runtime ──────────────────────────────────────────────
ATIVOS_PATH: str = os.path.join(BASE_DIR, "ativos.json")
UI_STATE_FILE: str = os.path.join(DADOS_DIR, "b3_ui_state.json")
CARTEIRAS_FILE: str = os.path.join(CARTEIRAS_DIR, "b3_carteiras.json")
OCULTOS_FILE: str = os.path.join(DADOS_DIR, "b3_ocultos.json")
NOTES_FILE: str = os.path.join(ANOTACOES_DIR, "b3_anotacoes.json")
EVALUATED_CACHE_FILE: str = os.path.join(DADOS_DIR, "b3_evaluated_cache.json")
PID_FILE: str = os.path.join(BASE_DIR, "bg_service.pid")

# Arquivo legado (migrado para CARTEIRAS_DIR em _migrate_old_files)
FAV_FILE: str = "b3_favoritos.json"

# ─── Cache do yfinance (diskcache) ─────────────────────────────────────────
YFINANCE_CACHE_DIR: str = os.path.join(DADOS_DIR, "yfinance_cache")


def ensure_data_dirs() -> None:
    """Cria diretorios de dados se nao existirem. Idempotente."""
    for d in [DADOS_DIR, CARTEIRAS_DIR, ANOTACOES_DIR, IMAGES_DIR]:
        os.makedirs(d, exist_ok=True)


# Cria diretorios na importacao do modulo para garantir que estao disponiveis
ensure_data_dirs()
