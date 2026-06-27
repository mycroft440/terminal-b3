import logging
import ui.flet_patches  # noqa: F401  # aplica monkey-patches ANTES de tudo
import flet as ft
from ui.state_manager import StateManager
from ui.main_page import get_dashboard_view


# Logging setup is now in __main__
def main_app(page: ft.Page):
    page.title = "Terminal B3 Pro"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0D1117"
    page.theme = ft.Theme(font_family="Inter, Roboto, sans-serif")

    state_manager = StateManager()

    def route_change(e):
        page.views.clear()
        route = page.route if page.route else "/"
        logging.info(f"Navigating to route: {route}")

        if route == "/":
            try:
                view = get_dashboard_view(page, state_manager)
                page.views.append(view)
                logging.info("Dashboard view appended successfully.")
            except Exception as ex:
                logging.exception(f"Erro crítico ao renderizar Dashboard: {ex}")
        page.update()

    def view_pop(view):
        if len(page.views) > 1:
            page.views.pop()
            top_view = page.views[-1]
            page.go(top_view.route)
        else:
            page.go("/")

    page.on_route_change = route_change
    page.on_view_pop = view_pop

    # Força a renderização inicial
    logging.info("Forçando renderização inicial da rota base.")
    route_change(None)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("debug.log", mode="a", encoding="utf-8"),
        ],
    )
    logging.info("===============================================")
    logging.info("INICIANDO TERMINAL B3 PRO (ROUTER ENABLED)...")
    try:
        import os

        base_dir = os.path.dirname(os.path.abspath(__file__))
        assets_path = os.path.join(base_dir, "assets")
        ft.run(main=main_app, assets_dir=assets_path)
    except Exception as e:
        logging.exception(f"Erro crítico na inicialização: {e}")
