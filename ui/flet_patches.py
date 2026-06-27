"""
Patches de compatibilidade para Flet >= 0.80.

A partir da versao 0.80 do Flet, varias APIs de conveniencia foram
removidas (ft.border.all, ft.alignment.center, ft.padding.symmetric,
ft.margin.symmetric). Este modulo restaura essas APIs via monkey-patch
para que o codigo existente continue funcionando sem refactor massivo.

IMPORTACAO OBRIGATORIA:
    Este modulo deve ser importado ANTES de qualquer outro modulo do
    projeto que use `flet`. O entry point `main.py` faz isso no topo:

        import ui.flet_patches  # noqa: F401  # aplica monkey-patches

    Sem essa importacao, codigo que use ft.alignment.center, ft.border.all,
    ft.padding.symmetric ou ft.margin.symmetric quebra em runtime.
"""
import flet as ft


def apply_patches() -> None:
    """Aplica todos os patches de compatibilidade. Idempotente."""

    # ─── ft.border.all ─────────────────────────────────────────────
    if hasattr(ft, "border") and not hasattr(ft.border, "all"):

        def _border_all(width, color):
            return ft.Border(
                top=ft.BorderSide(width, color),
                right=ft.BorderSide(width, color),
                bottom=ft.BorderSide(width, color),
                left=ft.BorderSide(width, color),
            )

        ft.border.all = _border_all

    # ─── ft.alignment (center, top_left, etc.) ────────────────────
    if hasattr(ft, "alignment") and not hasattr(ft.alignment, "center"):

        class _AlignmentPatch:
            center = ft.Alignment(0, 0)
            top_left = ft.Alignment(-1, -1)
            top_center = ft.Alignment(0, -1)
            top_right = ft.Alignment(1, -1)
            center_left = ft.Alignment(-1, 0)
            center_right = ft.Alignment(1, 0)
            bottom_left = ft.Alignment(-1, 1)
            bottom_center = ft.Alignment(0, 1)
            bottom_right = ft.Alignment(1, 1)
            Alignment = ft.Alignment

        ft.alignment = _AlignmentPatch()

    # ─── ft.padding.symmetric / only / all ────────────────────────
    if hasattr(ft, "padding") and not hasattr(ft.padding, "symmetric"):

        class _PaddingPatch:
            def symmetric(self, horizontal=0, vertical=0):
                return ft.Padding(
                    left=horizontal, top=vertical, right=horizontal, bottom=vertical
                )

            def only(self, left=0, top=0, right=0, bottom=0):
                return ft.Padding(left=left, top=top, right=right, bottom=bottom)

            def all(self, value):
                return ft.Padding(left=value, top=value, right=value, bottom=value)

        ft.padding = _PaddingPatch()

    # ─── ft.margin.symmetric / only / all ─────────────────────────
    if hasattr(ft, "margin") and not hasattr(ft.margin, "symmetric"):

        class _MarginPatch:
            def symmetric(self, horizontal=0, vertical=0):
                return ft.Margin(
                    left=horizontal, top=vertical, right=horizontal, bottom=vertical
                )

            def only(self, left=0, top=0, right=0, bottom=0):
                return ft.Margin(left=left, top=top, right=right, bottom=bottom)

            def all(self, value):
                return ft.Margin(left=value, top=value, right=value, bottom=value)

        ft.margin = _MarginPatch()


# Aplica os patches automaticamente na importacao do modulo.
# Isso garante que `import ui.flet_patches` seja suficiente.
apply_patches()
