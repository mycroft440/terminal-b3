"""
Orquestrador do dialog de Bloco de Notas.

Reune MarkdownEditor (editor + toolbar + preview) e ImageGallery (galeria +
lightbox + file picker) em um ft.AlertDialog com titulo, content, e acoes
Salvar/Cancelar. Expoe create_notes_dialog() que retorna (dialog, open_function).
"""
import logging
from datetime import datetime

import flet as ft
from ui.theme import AppColors
from ui.dialogs.notes.image_helpers import clear_image_cache
from ui.dialogs.notes.markdown_editor import MarkdownEditor
from ui.dialogs.notes.image_gallery import ImageGallery
import ui.flet_patches  # noqa: F401


def create_notes_dialog(
    page: ft.Page, state: dict, save_notes, render_list, images_dir: str
):
    """Cria dialog de Bloco de Notas com editor Markdown + galeria de imagens.

    Args:
        page: ft.Page
        state: state global do app (com 'anotacoes')
        save_notes: callback para persistir state['anotacoes']
        render_list: callback para re-renderizar lista de cards
        images_dir: diretorio onde imagens sao salvas

    Returns:
        tuple (dlg_nota, open_notes_dialog):
        - dlg_nota: ft.AlertDialog para adicionar a page.overlay
        - open_notes_dialog(ticker): funcao para abrir dialog para um ticker
    """
    current_note_ticker = [None]

    def _safe_page_update():
        """Atualiza a pagina ignorando erros (UI pode ter fechado)."""
        try:
            page.update()
        except Exception:
            pass

    # Componentes especializados
    editor = MarkdownEditor(page)
    gallery = ImageGallery(page, images_dir)

    # ─── ACOES ─────────────────────────────────────────────
    def fechar_notas(e):
        dlg_nota.open = False
        _safe_page_update()

    def salvar_notas(e):
        ticker = current_note_ticker[0]
        if ticker:
            texto = editor.get_text()
            imagens = gallery.get_images()
            if texto or imagens:
                agora = datetime.now().strftime("%d/%m/%Y as %H:%M")
                state["anotacoes"][ticker] = {
                    "texto": texto,
                    "imagens": imagens,
                    "updated_at": agora,
                }
                logging.info(f"Anotacao salva para: {ticker}")
            else:
                state["anotacoes"].pop(ticker, None)
                logging.info(f"Anotacao removida para: {ticker}")
            save_notes()
            render_list()
        dlg_nota.open = False
        _safe_page_update()

    # ─── DIALOG TITLE ──────────────────────────────────────
    dlg_nota_title_text = ft.Text(
        "Bloco de Notas",
        size=18,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.WHITE,
    )

    # ─── DIALOG PRINCIPAL ──────────────────────────────────
    dlg_nota = ft.AlertDialog(
        title=ft.Row(
            [
                ft.Container(
                    content=ft.Icon(
                        ft.Icons.EDIT_NOTE, color=AppColors.PRIMARY, size=22
                    ),
                    width=36,
                    height=36,
                    border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.15, AppColors.PRIMARY),
                    alignment=ft.alignment.center,
                ),
                ft.Column(
                    [
                        dlg_nota_title_text,
                        ft.Text(
                            "Editor de anotacoes com suporte a Markdown",
                            size=12,
                            color=AppColors.TEXT_MUTED,
                        ),
                    ],
                    spacing=2,
                ),
            ],
            spacing=12,
        ),
        content=ft.Container(
            content=ft.Column(
                [editor.nota_container, gallery.attachments_section],
                spacing=0,
                expand=True,
            ),
            width=750,
            height=520,
            padding=ft.Padding(5, 5, 5, 0),
        ),
        actions=[
            ft.TextButton(
                "Cancelar",
                on_click=fechar_notas,
                style=ft.ButtonStyle(color=AppColors.TEXT_SECONDARY),
            ),
            ft.Button(
                "Salvar",
                on_click=salvar_notas,
                bgcolor=AppColors.SUCCESS_DARK,
                color=ft.Colors.WHITE,
                icon=ft.Icons.SAVE,
                style=ft.ButtonStyle(
                    padding=ft.Padding(20, 12, 20, 12),
                    shape=ft.RoundedRectangleBorder(radius=8),
                ),
            ),
        ],
        shape=ft.RoundedRectangleBorder(radius=16),
        bgcolor="#0D1117",
        content_padding=ft.Padding(20, 10, 20, 5),
    )

    # ─── ABRIR DIALOG ──────────────────────────────────────
    def open_notes_dialog(ticker):
        current_note_ticker[0] = ticker
        dlg_nota_title_text.value = f"Notas - {ticker}"

        # Limpa cache de data URIs para garantir que imagens editadas no disco
        # sejam recarregadas (caso raro, mas garante consistencia)
        clear_image_cache()

        # Reset para modo edicao
        editor.reset_to_edit_mode()

        # Carrega nota existente (ou default vazio)
        nota_data = state["anotacoes"].get(
            ticker, {"texto": "", "imagens": [], "updated_at": ""}
        )
        if isinstance(nota_data, str):
            # Formato antigo: anotacoes eram strings
            nota_data = {"texto": nota_data, "imagens": [], "updated_at": ""}

        editor.set_text(nota_data.get("texto", ""))
        editor.set_timestamp(nota_data.get("updated_at", ""))

        # Carrega galeria
        gallery.clear()
        gallery.extend(nota_data.get("imagens", []))
        gallery.refresh_images()

        if dlg_nota not in page.overlay:
            page.overlay.append(dlg_nota)

        dlg_nota.open = True
        _safe_page_update()

    return dlg_nota, open_notes_dialog
