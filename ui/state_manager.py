import json
import os
import logging
import datetime
import tempfile
import copy
import threading
from typing import Dict, Any

from core import paths as _paths


class StateManager:
    def __init__(self) -> None:
        # Caminhos centralizados em core/paths.py (single source of truth).
        # Mantidos como atributos da instancia para retrocompatibilidade
        # com codigo que acessa self.BASE_DIR, self.DADOS_DIR, etc.
        self.BASE_DIR = _paths.BASE_DIR
        self.DADOS_DIR = _paths.DADOS_DIR
        self.CARTEIRAS_DIR = _paths.CARTEIRAS_DIR
        self.ANOTACOES_DIR = _paths.ANOTACOES_DIR
        self.ASSETS_DIR = _paths.ASSETS_DIR
        self.IMAGES_DIR = _paths.IMAGES_DIR
        self.UI_STATE_FILE = _paths.UI_STATE_FILE
        self.CARTEIRAS_FILE = _paths.CARTEIRAS_FILE
        self.FAV_FILE = _paths.FAV_FILE
        self.OCULTOS_FILE = _paths.OCULTOS_FILE
        self.NOTES_FILE = _paths.NOTES_FILE
        self.EVALUATED_CACHE_FILE = _paths.EVALUATED_CACHE_FILE

        # Lock reentrante para operacoes de save (write).
        # RLock permite que a mesma thread chame save_* recursivamente
        # (ex: save_ui_state chamado dentro de outro metodo que ja tem lock).
        #
        # IMPORTANTE: NAO usar este lock para leituras de self.state -
        # sao muito frequentes na UI e causariam contencao. Apenas saves
        # precisam ser serializados para evitar arquivos corrompidos.
        self._save_lock = threading.RLock()

        # Garante que diretorios existem (idempotente)
        _paths.ensure_data_dirs()

        self._migrate_old_files()

        self.default_state: Dict[str, Any] = {
            "market": "acoes",
            "timeframe": "1d",
            "sector": "all",
            "sort": "all",
            "search": "",
            "carteiras": {"Principal": {}},
            "ocultos": [],
            "mms_active": True,
            "mms_periodos": [20],
            "rsi_active": True,
            "stoch_active": False,
            "is_loading": False,
            "anotacoes": {},
        }

        self.state: Dict[str, Any] = copy.deepcopy(self.default_state)
        self.load_all()

    def _migrate_old_files(self):
        import shutil

        moves = [
            ("b3_ui_state.json", self.UI_STATE_FILE),
            ("b3_carteiras.json", self.CARTEIRAS_FILE),
            ("b3_ocultos.json", self.OCULTOS_FILE),
            ("b3_anotacoes.json", self.NOTES_FILE),
        ]
        for src, dst in moves:
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    shutil.move(src, dst)
                except Exception as e:
                    logging.error(f"Erro migrando {src}: {e}")

        if os.path.exists("anotacoes_imgs") and os.path.isdir("anotacoes_imgs"):
            for f in os.listdir("anotacoes_imgs"):
                src = os.path.join("anotacoes_imgs", f)
                dst = os.path.join(self.IMAGES_DIR, f)
                if not os.path.exists(dst):
                    try:
                        shutil.move(src, dst)
                    except Exception as e:
                        logging.error(f"Erro migrando imagem {src}: {e}")
            try:
                os.rmdir("anotacoes_imgs")
            except OSError:
                pass

    def load_all(self) -> None:
        # Load UI State
        try:
            if os.path.exists(self.UI_STATE_FILE):
                with open(self.UI_STATE_FILE, "r", encoding="utf-8") as f:
                    saved = json.loads(f.read().strip())
                    for k in [
                        "market",
                        "timeframe",
                        "sector",
                        "sort",
                        "mms_active",
                        "mms_periodos",
                        "rsi_active",
                        "stoch_active",
                    ]:
                        if k in saved:
                            self.state[k] = saved[k]
        except Exception as e:
            logging.error(f"Erro ao carregar estado da UI: {e}")

        # Load Carteiras
        try:
            hoje_str = datetime.date.today().isoformat()
            migrated = False

            if os.path.exists(self.CARTEIRAS_FILE):
                with open(self.CARTEIRAS_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        self.state["carteiras"] = json.loads(content)
            elif os.path.exists(self.FAV_FILE):
                with open(self.FAV_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        self.state["carteiras"] = {"Principal": json.loads(content)}
                        migrated = True

            # Migrate lists to dicts
            for cart_nome, ativos in list(self.state["carteiras"].items()):
                if isinstance(ativos, list):
                    self.state["carteiras"][cart_nome] = {t: hoje_str for t in ativos}
                    migrated = True

            if migrated:
                self.save_carteiras()
        except Exception as e:
            logging.error(f"Erro ao carregar carteiras: {e}")

        # Sanitize sort
        valid_sorts = {"all", "ocultos"}
        valid_sorts.update(f"cart_{c}" for c in self.state["carteiras"])
        if self.state["sort"] not in valid_sorts:
            self.state["sort"] = "all"

        # Sanitize timeframe (4h foi removido da UI; fallback para 1d)
        if self.state.get("timeframe") not in {"1d", "1s"}:
            self.state["timeframe"] = "1d"

        # Sanitize market ('todos' foi removido da UI; fallback para 'acoes')
        if self.state.get("market") not in {"acoes", "fiis", "bdrs"}:
            self.state["market"] = "acoes"

        # Load Ocultos
        try:
            if os.path.exists(self.OCULTOS_FILE):
                with open(self.OCULTOS_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        self.state["ocultos"] = json.loads(content)
        except Exception as e:
            logging.error(f"Erro ao carregar ocultos: {e}")

        # Load Anotacoes
        try:
            if os.path.exists(self.NOTES_FILE):
                with open(self.NOTES_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        raw = json.loads(content)
                        for k, v in raw.items():
                            if isinstance(v, str):
                                raw[k] = {"texto": v, "imagens": []}
                        self.state["anotacoes"] = raw
        except Exception as e:
            logging.error(f"Erro ao carregar anotações: {e}")

    def _atomic_save(self, filepath: str, data: Any) -> None:
        try:
            dir_name = os.path.dirname(filepath) or "."
            with tempfile.NamedTemporaryFile(
                "w", dir=dir_name, delete=False, encoding="utf-8"
            ) as tf:
                json.dump(data, tf)
                temp_name = tf.name
            os.replace(temp_name, filepath)
        except Exception as e:
            logging.error(f"Erro no salvamento atômico de {filepath}: {e}")
            if "temp_name" in locals() and os.path.exists(temp_name):
                os.remove(temp_name)

    def save_ui_state(self) -> None:
        # Lock para evitar que 2 threads escrevam no mesmo arquivo
        # simultaneamente (ex: UI thread + background worker)
        with self._save_lock:
            try:
                to_save = {
                    k: self.state[k]
                    for k in [
                        "market",
                        "timeframe",
                        "sector",
                        "sort",
                        "mms_active",
                        "mms_periodos",
                        "rsi_active",
                        "stoch_active",
                    ]
                }
                self._atomic_save(self.UI_STATE_FILE, to_save)
                logging.info("Estado da UI salvo com sucesso.")
            except Exception as e:
                logging.error(f"Erro ao salvar estado da UI: {e}")

    def save_carteiras(self) -> None:
        with self._save_lock:
            self._atomic_save(self.CARTEIRAS_FILE, self.state["carteiras"])

    def save_ocultos(self) -> None:
        with self._save_lock:
            self._atomic_save(self.OCULTOS_FILE, self.state["ocultos"])

    def save_notes(self) -> None:
        with self._save_lock:
            self._atomic_save(self.NOTES_FILE, self.state["anotacoes"])

    def load_evaluated_cache(self) -> Dict[str, Any]:
        """Carrega o cache persistente de ativos avaliados (por config_hash).
        Retorna dict vazio se nao existir ou estiver corrompido."""
        # Leitura usa lock para evitar ler arquivo enquanto outra thread
        # esta salvando (pode pegar arquivo parcialmente escrito)
        with self._save_lock:
            try:
                if os.path.exists(self.EVALUATED_CACHE_FILE):
                    with open(self.EVALUATED_CACHE_FILE, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            return json.loads(content)
            except Exception as e:
                logging.error(f"Erro ao carregar cache de ativos avaliados: {e}")
        return {}

    def save_evaluated_cache(self, cache: Dict[str, Any]) -> None:
        """Persiste o cache de ativos avaliados em disco.
        Chamado de tempos em tempos pela UI para sobreviver a reinicios."""
        with self._save_lock:
            try:
                self._atomic_save(self.EVALUATED_CACHE_FILE, cache)
            except Exception as e:
                logging.error(f"Erro ao salvar cache de ativos avaliados: {e}")

    def get_config_hash(self) -> str:
        p = self.state["mms_periodos"][0] if self.state["mms_periodos"] else 0
        return f"{self.state['market']}_{self.state['timeframe']}_{self.state['mms_active']}_{p}_{self.state['rsi_active']}_{self.state['stoch_active']}"
