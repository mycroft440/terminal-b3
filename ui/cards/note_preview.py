"""Preview de nota tecnica no card (filled state ou empty state)."""
import flet as ft
from ui.theme import AppColors
import ui.flet_patches  # noqa: F401


def build_note_preview(state: dict, codigo_ativo: str, open_notes_dialog) -> ft.Container:
    """Constroi preview de nota tecnica para o card.

    Estados:
    - Filled: se ativo tem nota (texto ou imagens), mostra preview clicavel
      com icone EDIT_DOCUMENT, titulo 'Nota Técnica', preview do texto
      (80 chars max) e sombra sutil
    - Empty: se nao tem nota, mostra CTA 'Adicionar análise / nota técnica'
      com icone ADD_COMMENT_OUTLINED e estilo italic

    Args:
        state: state global (com anotacoes)
        codigo_ativo: codigo do ativo
        open_notes_dialog: callback(ticker) para abrir bloco de notas

    Returns:
        ft.Container clicavel que abre bloco de notas
    """
    nota_data = state.get("anotacoes", {}).get(codigo_ativo)
    if isinstance(nota_data, str):
        # Formato antigo: anotacoes eram apenas strings
        nota_texto = nota_data
        nota_imgs = []
    elif isinstance(nota_data, dict):
        nota_texto = nota_data.get("texto", "")
        nota_imgs = nota_data.get("imagens", [])
    else:
        nota_texto = ""
        nota_imgs = []

    if nota_texto or nota_imgs:
        preview_text = nota_texto[:80] + ("..." if len(nota_texto) > 80 else "")
        if not preview_text and nota_imgs:
            preview_text = "📸 Imagens Anexadas"

        middle_content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.EDIT_DOCUMENT, size=12, color=ft.Colors.BLUE_400),
                        ft.Text(
                            "Nota Técnica",
                            size=10,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_400,
                        ),
                        ft.Container(expand=True),
                        ft.Icon(
                            ft.Icons.EDIT_OUTLINED,
                            size=12,
                            color=ft.Colors.with_opacity(0.5, ft.Colors.BLUE_GREY_400),
                        ),
                    ],
                    spacing=4,
                ),
                ft.Text(
                    preview_text,
                    size=12,
                    color=AppColors.TEXT_NOTE,
                    max_lines=2,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
            ],
            spacing=2,
        )

        return ft.Container(
            content=middle_content,
            padding=ft.Padding(12, 8, 12, 8),
            border_radius=8,
            bgcolor=AppColors.BG_NOTE,
            border=ft.border.all(1, ft.Colors.with_opacity(0.2, ft.Colors.BLUE_GREY_500)),
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=6,
                color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                offset=ft.Offset(0, 2),
            ),
            on_click=lambda _: open_notes_dialog(codigo_ativo),
            tooltip="Visualizar/Editar anotação completa",
        )

    # Empty state
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(ft.Icons.ADD_COMMENT_OUTLINED, size=14, color=ft.Colors.BLUE_GREY_500),
                ft.Text(
                    "Adicionar análise / nota técnica",
                    size=11,
                    color=ft.Colors.BLUE_GREY_500,
                    italic=True,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=6,
        ),
        padding=ft.Padding(12, 8, 12, 8),
        border_radius=8,
        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY_300),
        border=ft.border.all(1, ft.Colors.with_opacity(0.1, ft.Colors.BLUE_GREY_500)),
        on_click=lambda _: open_notes_dialog(codigo_ativo),
        tooltip="Criar nova anotação",
    )
