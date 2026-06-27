import flet as ft


class AppColors:
    # Backgrounds
    BG_MAIN = "#0F1620"
    BG_CARD = "#141D2B"
    BG_TOOLBAR = "#0F1620"
    BG_NOTE = "#151C28"

    # Texts
    TEXT_PRIMARY = ft.Colors.WHITE
    TEXT_SECONDARY = ft.Colors.BLUE_GREY_300
    TEXT_MUTED = ft.Colors.BLUE_GREY_500
    TEXT_NOTE = ft.Colors.BLUE_GREY_100

    # Accents & Semantics
    PRIMARY = ft.Colors.BLUE_400
    PRIMARY_DARK = ft.Colors.BLUE_600
    SUCCESS = ft.Colors.GREEN_400
    SUCCESS_DARK = ft.Colors.GREEN_600
    SUCCESS_BG = ft.Colors.GREEN_900
    DANGER = ft.Colors.RED_400
    DANGER_DARK = ft.Colors.RED_600
    DANGER_BG = ft.Colors.RED_900
    WARNING = ft.Colors.AMBER_400
    WARNING_DARK = ft.Colors.AMBER_600
    WARNING_BG = ft.Colors.AMBER_900

    # Borders & Dividers
    BORDER = ft.Colors.with_opacity(0.12, ft.Colors.BLUE_GREY_600)
    DIVIDER = ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_500)

    # Indicators
    IND_MMS = ft.Colors.BLUE_400
    IND_RSI = ft.Colors.GREEN_400
    IND_STOCH = ft.Colors.PURPLE_400


class AppStyles:
    @staticmethod
    def card_decoration():
        return {
            "border_radius": 12,
            "bgcolor": AppColors.BG_CARD,
            "border": ft.border.all(1, AppColors.BORDER),
        }

    @staticmethod
    def pill_decoration(color=AppColors.TEXT_MUTED, selected=False):
        bg = (
            ft.Colors.with_opacity(0.15, color)
            if selected
            else ft.Colors.with_opacity(0.05, ft.Colors.WHITE)
        )
        border_c = color if selected else ft.Colors.with_opacity(0.1, ft.Colors.WHITE)
        return {
            "border_radius": 20,
            "bgcolor": bg,
            "border": ft.border.all(1, border_c),
            "padding": ft.Padding(12, 8, 12, 8),
        }
