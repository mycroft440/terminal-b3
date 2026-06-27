"""
Galeria de imagens anexadas com lightbox e file picker.

Classe ImageGallery encapsula:
- Galeria de thumbnails (110x110, fit COVER)
- Lightbox para ampliar imagem ao clicar
- File picker para adicionar novas imagens
- Placeholder visual para imagens com arquivo faltante
- Cache de data URIs (via image_helpers)
"""
import os
import time
import shutil
import logging
import flet as ft

from ui.dialogs.notes.image_helpers import (
    load_image_as_data_uri,
    clear_image_cache,
)
import ui.flet_patches  # noqa: F401


class ImageGallery:
    """Galeria de imagens com lightbox e file picker.

    Atributos publicos:
        images_row: ft.Row com thumbnails (adicionar ao dialog)
        attachments_section: ft.Container com header + images_row
        current_images: list[str] de caminhos das imagens anexadas

    Args:
        page: ft.Page
        images_dir: diretorio onde imagens sao salvas (state_manager.IMAGES_DIR)
    """

    def __init__(self, page: ft.Page, images_dir: str):
        self.page = page
        self.images_dir = images_dir
        self.current_images: list[str] = []

        # ─── GALERIA DE IMAGENS ────────────────────────────────
        self.images_row = ft.Row(wrap=True, spacing=10, run_spacing=10)

        # ─── LIGHTBOX ──────────────────────────────────────────
        self.img_lightbox = ft.Image(src="", fit=ft.BoxFit.CONTAIN, expand=True)
        self.dlg_lightbox = self._build_lightbox_dialog()

        # ─── FILE PICKER ───────────────────────────────────────
        self.file_picker = ft.FilePicker()

        # ─── SECAO DE ANEXOS (header + galeria) ────────────────
        self.attachments_section = self._build_attachments_section()

    # ─── Construtores internos ─────────────────────────────────────────


    def _safe_page_update(self):
        """Atualiza a pagina ignorando erros (UI pode ter fechado)."""
        try:
            self.page.update()
        except Exception:
            pass

    def _build_lightbox_dialog(self) -> ft.AlertDialog:
        """Constroi dialog de lightbox para ampliar imagem."""
        return ft.AlertDialog(
            content=ft.Container(
                content=self.img_lightbox,
                width=1000,
                height=700,
                padding=0,
                margin=0,
                alignment=ft.alignment.center,
            ),
            content_padding=0,
            bgcolor=ft.Colors.TRANSPARENT,
            actions=[
                ft.IconButton(
                    ft.Icons.CLOSE,
                    icon_color=ft.Colors.WHITE,
                    icon_size=30,
                    on_click=self._close_lightbox,
                    bgcolor=ft.Colors.BLACK54,
                )
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER,
        )

    def _build_attachments_section(self) -> ft.Container:
        """Constroi secao de anexos com botao Adicionar."""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Row(
                                [
                                    ft.Icon(
                                        ft.Icons.ATTACH_FILE,
                                        size=14,
                                        color=ft.Colors.BLUE_GREY_400,
                                    ),
                                    ft.Text(
                                        "Anexos",
                                        size=12,
                                        color=ft.Colors.BLUE_GREY_400,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                ],
                                spacing=6,
                            ),
                            ft.TextButton(
                                "Adicionar",
                                icon=ft.Icons.ADD_PHOTO_ALTERNATE_OUTLINED,
                                on_click=self.pick_images_click,
                                icon_color=ft.Colors.BLUE_400,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.BLUE_400,
                                    padding=ft.Padding(8, 4, 8, 4),
                                ),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.images_row,
                ],
                spacing=8,
            ),
            padding=ft.Padding(0, 8, 0, 0),
        )

    # ─── Lightbox ──────────────────────────────────────────────────────

    def _close_lightbox(self, e):
        self.dlg_lightbox.open = False
        self._safe_page_update()

    def open_lightbox(self, src: str):
        """Abre lightbox com imagem ampliada."""
        # Carrega como data URI para garantir exibicao em qualquer plataforma
        data_uri = load_image_as_data_uri(src)
        self.img_lightbox.src = data_uri if data_uri else src
        if self.dlg_lightbox not in self.page.overlay:
            self.page.overlay.append(self.dlg_lightbox)
        self.dlg_lightbox.open = True
        self._safe_page_update()

    # ─── Galeria ───────────────────────────────────────────────────────

    def refresh_images(self):
        """Reconstroi thumbnails da galeria a partir de current_images."""
        self.images_row.controls.clear()
        for img_path in self.current_images:
            data_uri = load_image_as_data_uri(img_path)
            img_card = self._build_image_card(img_path, data_uri)
            self.images_row.controls.append(img_card)
        self._safe_page_update()

    def _build_image_card(self, img_path: str, data_uri: str | None) -> ft.Stack:
        """Constroi card de imagem (thumbnail + botao remover).

        Se data_uri for None (arquivo nao encontrado), mostra placeholder.
        """
        # Closure captura img_path para callback
        def remove_img(e, p=img_path):
            if p in self.current_images:
                self.current_images.remove(p)
            if os.path.exists(p):
                try:
                    os.remove(p)
                    clear_image_cache(p)
                except Exception:
                    pass
            self.refresh_images()

        def on_img_click(e, p=img_path):
            self.open_lightbox(p)

        if data_uri is None:
            # Placeholder para arquivo nao encontrado
            return ft.Stack(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Icon(
                                    ft.Icons.IMAGE_NOT_SUPPORTED,
                                    color=ft.Colors.RED_400,
                                    size=28,
                                ),
                                ft.Text(
                                    "Arquivo\nnao encontrado",
                                    size=9,
                                    color=ft.Colors.RED_300,
                                    text_align=ft.TextAlign.CENTER,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=4,
                        ),
                        width=110,
                        height=110,
                        border_radius=10,
                        bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.RED_900),
                        border=ft.border.all(
                            1, ft.Colors.with_opacity(0.3, ft.Colors.RED_700)
                        ),
                    ),
                    self._build_remove_button(remove_img),
                ]
            )

        # Imagem normal
        container = ft.Container(
            content=ft.Image(
                src=data_uri,
                width=110,
                height=110,
                fit=ft.BoxFit.COVER,
                border_radius=10,
            ),
            on_click=on_img_click,
            tooltip="Clique para ampliar",
            border_radius=10,
            border=ft.border.all(
                1, ft.Colors.with_opacity(0.15, ft.Colors.WHITE)
            ),
        )
        # cursor precisa ser definido apos construcao (Flet 0.85+ nao aceita no __init__)
        try:
            container.cursor = ft.MouseCursor.CLICK
        except Exception:
            pass  # retrocompatibilidade com versoes antigas
        return ft.Stack(
            [
                container,
                self._build_remove_button(remove_img),
            ]
        )

    def _build_remove_button(self, on_click) -> ft.Container:
        """Botao X vermelho no canto superior direito do thumbnail."""
        return ft.Container(
            ft.IconButton(
                ft.Icons.CLOSE,
                icon_size=12,
                icon_color=ft.Colors.WHITE,
                bgcolor=ft.Colors.with_opacity(0.85, ft.Colors.RED_600),
                width=22,
                height=22,
                style=ft.ButtonStyle(padding=0),
                on_click=on_click,
            ),
            alignment=ft.alignment.top_right,
            padding=3,
        )

    # ─── File picker ───────────────────────────────────────────────────

    def pick_images_click(self, e):
        """Abre file picker para selecionar imagens (multiplas)."""
        if self.file_picker not in self.page.overlay:
            self.page.overlay.append(self.file_picker)
            self.page.update()
        try:
            result = self.file_picker.pick_files(
                allow_multiple=True,
                allowed_extensions=["png", "jpg", "jpeg", "gif", "webp"],
            )
        except Exception as ex:
            logging.error(f"Erro ao abrir file picker: {ex}")
            return
        if not result:
            return
        for f in result:
            filename = f"{int(time.time())}_{f.name}"
            dest_path = os.path.join(self.images_dir, filename)
            try:
                shutil.copy(f.path, dest_path)
                self.current_images.append(dest_path)
            except Exception as ex:
                logging.error(f"Erro ao copiar imagem: {ex}")
        self.refresh_images()

    # ─── API para o orquestrador ───────────────────────────────────────

    def clear(self):
        """Limpa current_images (nao remove arquivos do disco)."""
        self.current_images.clear()

    def extend(self, imagens: list):
        """Adiciona lista de caminhos a current_images."""
        self.current_images.extend(imagens)

    def get_images(self) -> list:
        """Retorna copia da lista de imagens."""
        return list(self.current_images)
