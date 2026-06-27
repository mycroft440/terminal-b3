import os
import json
import threading
from typing import Any, List

from core import paths as _paths

# Cache em memoria do catalogo de ativos (carregado de ativos.json).
# Lock necessario porque bg_service e UI thread podem chamar
# carregar_catalogo() concorrentemente na inicializacao.
_CATALOGO_CACHE: List[Any] = []
_CATALOGO_LOCK = threading.Lock()
_ATIVOS_PATH = _paths.ATIVOS_PATH


def carregar_catalogo() -> List[Any]:
    """Carrega catalogo de ativos de ativos.json com cache em memoria.

    Thread-safe: usa Lock para evitar race condition quando bg_service e
    UI thread chamam concorrentemente na inicializacao.

    Returns:
        Lista de ativos (cada ativo e um dict com codigo, ticker, nome, etc).
        Lista vazia se ativos.json nao existir ou estiver corrompido.
    """
    global _CATALOGO_CACHE
    # Fast path: se cache ja populado, retorna sem adquirir lock
    # (leitura de referencia em Python e atomica)
    if _CATALOGO_CACHE:
        return _CATALOGO_CACHE

    # Slow path: precisa carregar do disco - adquire lock
    with _CATALOGO_LOCK:
        # Double-checked locking: pode ter sido populado por outra thread
        # enquanto esperavamos o lock
        if _CATALOGO_CACHE:
            return _CATALOGO_CACHE

        try:
            if os.path.exists(_ATIVOS_PATH):
                with open(_ATIVOS_PATH, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        _CATALOGO_CACHE = json.loads(content)
                        return _CATALOGO_CACHE
            return []
        except Exception:
            return []


def _reset_cache() -> None:
    """Reseta cache do catalogo. Usado apenas em testes."""
    global _CATALOGO_CACHE
    with _CATALOGO_LOCK:
        _CATALOGO_CACHE = []
