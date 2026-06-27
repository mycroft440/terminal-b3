"""
Helpers para carregar imagens como data URIs base64.

Flet 0.85+ nao carrega arquivos locais via src=path absoluto quando estao
fora do assets_dir configurado em ft.app.run(). Como as imagens das
anotacoes sao salvas em dados/anotacoes/imgs/ (fora de /assets/), precisamos
ler o arquivo e converter para data URI base64, que e universalmente suportado.
"""
import os
import base64
import logging


# Mapeamento de extensao -> MIME type
_MIME_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}

# Cache em memoria de data URIs ja carregados (key: caminho absoluto)
_DATA_URI_CACHE: dict[str, str] = {}


def load_image_as_data_uri(path: str) -> str | None:
    """Carrega uma imagem do disco e retorna como data URI base64.

    Retorna None se o arquivo nao existir ou nao puder ser lido.
    Usa cache em memoria para evitar re-leitura a cada refresh_images().
    """
    if not path or not os.path.exists(path):
        logging.warning(f"[Notes] Imagem nao encontrada: {path}")
        return None

    # Verifica cache primeiro
    abs_path = os.path.abspath(path)
    if abs_path in _DATA_URI_CACHE:
        return _DATA_URI_CACHE[abs_path]

    ext = os.path.splitext(path)[1].lower()
    mime = _MIME_MAP.get(ext, "image/png")

    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        data_uri = f"data:{mime};base64,{data}"
        _DATA_URI_CACHE[abs_path] = data_uri
        return data_uri
    except Exception as e:
        logging.error(f"[Notes] Erro ao ler imagem {path}: {e}")
        return None


def clear_image_cache(path: str | None = None) -> None:
    """Limpa cache de data URIs. Se path fornecido, remove so esse."""
    if path:
        abs_path = os.path.abspath(path)
        _DATA_URI_CACHE.pop(abs_path, None)
    else:
        _DATA_URI_CACHE.clear()


# Retrocompatibilidade: aliases com _prefix (codigo antigo usava _load_image_as_data_uri)
_load_image_as_data_uri = load_image_as_data_uri
_clear_image_cache = clear_image_cache
