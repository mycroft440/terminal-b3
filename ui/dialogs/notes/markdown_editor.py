"""
Editor de texto Markdown com toolbar e toggle de preview.

Classe MarkdownEditor encapsula:
- TextField multiline (tf_nota)
- Markdown preview (md_preview)
- Toolbar de formatacao (bold, italic, code, heading, list, checklist, separator)
- Toggle edit/preview
- Contadores (caracteres/linhas) e timestamp
"""
import flet as ft
from ui.theme import AppColors
import ui.flet_patches  # noqa: F401


class MarkdownEditor:
    """Editor de texto Markdown com toolbar e toggle preview/edicao.

    Atributos publicos (acessados pelo orquestrador note_dialog):
        tf_nota: ft.TextField multiline
        md_preview: ft.Markdown
        preview_scroll: ft.Container (visivel apenas em modo preview)
        format_toolbar: ft.Row com IconButton de formatacao
        btn_toggle_preview: ft.TextButton para alternar edit/preview
        char_counter: ft.Text com contagem de caracteres/linhas
        lbl_timestamp: ft.Text com data de ultima edicao
        nota_container: ft.Container principal (header + body + footer)
        is_preview_mode: bool (False = edit, True = preview)
    """

    def __init__(self, page: ft.Page):
        self.page = page
        self.is_preview_mode = False

        # ─── EDITOR DE TEXTO PRINCIPAL ─────────────────────────
        self.tf_nota = ft.TextField(
            multiline=True,
            min_lines=22,
            max_lines=30,
            text_size=14,
            hint_text=(
                "Comece a escrever suas anotacoes aqui...\n\n"
                "Dicas:\n"
                "* Use **texto** para negrito\n"
                "* Use *texto* para italico\n"
                "* Use - item para listas\n"
                "* Use # Titulo para cabecalhos"
            ),
            hint_style=ft.TextStyle(
                color=ft.Colors.with_opacity(0.4, ft.Colors.BLUE_GREY_300),
                size=13,
            ),
            bgcolor=ft.Colors.TRANSPARENT,
            color=ft.Colors.WHITE,
            border=ft.InputBorder.NONE,
            content_padding=ft.Padding(20, 16, 20, 16),
            cursor_color=AppColors.PRIMARY,
            text_style=ft.TextStyle(font_family="Consolas, monospace", height=1.6),
            expand=True,
        )

        # ─── MARKDOWN PREVIEW ──────────────────────────────────
        self.md_preview = ft.Markdown(
            value="",
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            code_theme=ft.MarkdownCodeTheme.ATOM_ONE_DARK,
        )

        self.preview_scroll = ft.Container(
            content=ft.Column([self.md_preview], scroll=ft.ScrollMode.AUTO, expand=True),
            expand=True,
            padding=ft.Padding(20, 16, 20, 16),
            visible=False,
        )

        # ─── CONTADORES E TIMESTAMP ────────────────────────────
        self.char_counter = ft.Text("0 caracteres", size=11, color=AppColors.TEXT_MUTED)
        self.lbl_timestamp = ft.Text("", size=11, color=AppColors.TEXT_MUTED, italic=True)

        self.tf_nota.on_change = self._on_text_change

        # ─── TOOLBAR DE FORMATACAO ─────────────────────────────
        self.format_toolbar = self._build_toolbar()

        # ─── TOGGLE PREVIEW/EDIT ───────────────────────────────
        self.btn_toggle_preview = ft.TextButton(
            "Visualizar",
            icon=ft.Icons.PREVIEW,
            on_click=self.toggle_preview,
            icon_color=AppColors.WARNING,
            style=ft.ButtonStyle(
                color=AppColors.WARNING,
                padding=ft.Padding(12, 8, 12, 8),
            ),
        )

        # ─── CONTAINER PRINCIPAL (header + body + footer) ──────
        self.nota_container = self._build_container()

    # ─── Construtores internos ─────────────────────────────────────────


    def _safe_page_update(self):
        """Atualiza a pagina ignorando erros (UI pode ter fechado)."""
        try:
            self.page.update()
        except Exception:
            pass

    def _build_toolbar(self) -> ft.Row:
        """Constroi toolbar com botoes de formatacao Markdown."""
        toolbar_divider = ft.Container(
            width=1,
            height=20,
            bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_500),
            margin=ft.Margin(4, 0, 4, 0),
        )

        return ft.Row(
            [
                self._toolbar_btn(ft.Icons.FORMAT_BOLD, "Negrito (**texto**)", self.fmt_bold),
                self._toolbar_btn(ft.Icons.FORMAT_ITALIC, "Italico (*texto*)", self.fmt_italic),
                self._toolbar_btn(ft.Icons.CODE, "Codigo inline (`codigo`)", self.fmt_code),
                toolbar_divider,
                self._toolbar_btn(ft.Icons.TITLE, "Cabecalho (## Titulo)", self.fmt_heading),
                self._toolbar_btn(ft.Icons.FORMAT_LIST_BULLETED, "Lista (- item)", self.fmt_list),
                self._toolbar_btn(ft.Icons.CHECKLIST, "Checklist (- [ ] tarefa)", self.fmt_checklist),
                self._toolbar_btn(ft.Icons.HORIZONTAL_RULE, "Separador (---)", self.fmt_separator),
            ],
            spacing=2,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _toolbar_btn(self, icon, tooltip: str, on_click) -> ft.IconButton:
        return ft.IconButton(
            icon=icon,
            icon_size=16,
            icon_color=AppColors.TEXT_SECONDARY,
            tooltip=tooltip,
            on_click=on_click,
            width=32,
            height=32,
            style=ft.ButtonStyle(
                padding=0,
                shape=ft.RoundedRectangleBorder(radius=6),
                overlay_color=ft.Colors.with_opacity(0.1, ft.Colors.WHITE),
            ),
        )

    def _build_container(self) -> ft.Container:
        """Constroi container principal com header + body + footer."""
        editor_header = ft.Container(
            content=ft.Row(
                [self.format_toolbar, self.btn_toggle_preview],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(12, 8, 8, 8),
            border=ft.Border(
                bottom=ft.BorderSide(
                    1, ft.Colors.with_opacity(0.1, ft.Colors.BLUE_GREY_500)
                ),
                top=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                left=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                right=ft.BorderSide(0, ft.Colors.TRANSPARENT),
            ),
        )

        editor_body = ft.Container(
            content=ft.Stack(
                [self.tf_nota, self.preview_scroll],
                expand=True,
            ),
            expand=True,
        )

        editor_footer = ft.Container(
            content=ft.Row(
                [self.char_counter, self.lbl_timestamp],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.Padding(16, 6, 16, 6),
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.with_opacity(0.1, ft.Colors.BLUE_GREY_500)),
                bottom=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                left=ft.BorderSide(0, ft.Colors.TRANSPARENT),
                right=ft.BorderSide(0, ft.Colors.TRANSPARENT),
            ),
        )

        return ft.Container(
            content=ft.Column(
                [editor_header, editor_body, editor_footer],
                spacing=0,
                expand=True,
            ),
            bgcolor="#151C28",
            border_radius=12,
            border=ft.border.all(1, ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_500)),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=12,
                color=ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
                offset=ft.Offset(0, 4),
            ),
            expand=True,
        )

    # ─── Callbacks de formatacao ───────────────────────────────────────

    def _on_text_change(self, e):
        text = self.tf_nota.value or ""
        length = len(text)
        lines = text.count("\n") + 1
        self.char_counter.value = f"{length} caracteres · {lines} linhas"
        self.char_counter.update()

    def insert_format(self, prefix: str, suffix: str = "", placeholder: str = "texto"):
        """Insere formatacao markdown no campo de texto."""
        current = self.tf_nota.value or ""
        self.tf_nota.value = current + f"{prefix}{placeholder}{suffix}"
        self._on_text_change(None)
        self._safe_page_update()

    def fmt_bold(self, e):
        self.insert_format("**", "**", "negrito")

    def fmt_italic(self, e):
        self.insert_format("*", "*", "italico")

    def fmt_heading(self, e):
        self.insert_format("\n## ", "", "Titulo")

    def fmt_list(self, e):
        self.insert_format("\n- ", "", "item da lista")

    def fmt_checklist(self, e):
        self.insert_format("\n- [ ] ", "", "tarefa")

    def fmt_code(self, e):
        self.insert_format("`", "`", "codigo")

    def fmt_separator(self, e):
        current = self.tf_nota.value or ""
        self.tf_nota.value = current + "\n\n---\n\n"
        self._on_text_change(None)
        self._safe_page_update()

    # ─── Toggle preview/edit ───────────────────────────────────────────

    def toggle_preview(self, e):
        """Alterna entre modo edicao e modo preview."""
        self.is_preview_mode = not self.is_preview_mode
        if self.is_preview_mode:
            self.md_preview.value = (
                self.tf_nota.value
                if self.tf_nota.value and self.tf_nota.value.strip()
                else "*Nenhuma anotacao ainda.*"
            )
            self.tf_nota.visible = False
            self.preview_scroll.visible = True
            self.format_toolbar.visible = False
            self.btn_toggle_preview.icon = ft.Icons.EDIT
            self.btn_toggle_preview.text = "Editar"
            self.btn_toggle_preview.icon_color = AppColors.PRIMARY
        else:
            self.tf_nota.visible = True
            self.preview_scroll.visible = False
            self.format_toolbar.visible = True
            self.btn_toggle_preview.icon = ft.Icons.PREVIEW
            self.btn_toggle_preview.text = "Visualizar"
            self.btn_toggle_preview.icon_color = AppColors.WARNING
        self._safe_page_update()

    # ─── API para o orquestrador ───────────────────────────────────────

    def reset_to_edit_mode(self):
        """Reseta para modo edicao (chamado ao abrir dialog)."""
        self.is_preview_mode = False
        self.tf_nota.visible = True
        self.preview_scroll.visible = False
        self.format_toolbar.visible = True
        self.btn_toggle_preview.icon = ft.Icons.PREVIEW
        self.btn_toggle_preview.text = "Visualizar"
        self.btn_toggle_preview.icon_color = AppColors.WARNING

    def set_text(self, texto: str):
        """Define texto do editor e atualiza contador."""
        self.tf_nota.value = texto
        # Atualiza contador manualmente (nao dispara on_change)
        length = len(texto)
        lines = texto.count("\n") + 1
        self.char_counter.value = f"{length} caracteres · {lines} linhas"

    def get_text(self) -> str:
        """Retorna texto do editor (strip)."""
        return self.tf_nota.value.strip() if self.tf_nota.value else ""

    def set_timestamp(self, updated_at: str):
        """Define label de timestamp ('Editado: DD/MM/AAAA')."""
        if updated_at:
            self.lbl_timestamp.value = f"Editado: {updated_at}"
        else:
            self.lbl_timestamp.value = ""
