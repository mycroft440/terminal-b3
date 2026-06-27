import flet as ft
import os
import subprocess
import sys
import logging
import psutil

from core import paths as _paths


def create_settings_dialog(
    page, state, save_ui_state, render_list, config_changed_event
):
    def _safe_page_update():
        """Atualiza a pagina ignorando erros (UI pode ter fechado)."""
        try:
            page.update()
        except Exception:
            pass

    def save_config(e):
        logging.info("Salvando configuração de indicadores.")
        state["mms_active"] = cb_mms.value
        try:
            p = int(tf_mms_periodo.value)
            state["mms_periodos"] = [p] if p > 0 else [20]
        except Exception as ex:
            logging.warning(f"Entrada inválida para MMS: {ex}")
            state["mms_periodos"] = [20]
        state["rsi_active"] = cb_rsi.value
        state["stoch_active"] = cb_stoch.value
        state["is_loading"] = True
        save_ui_state()
        dlg_config.open = False
        _safe_page_update()
        config_changed_event.set()
        render_list()
        _safe_page_update()

    cb_mms = ft.Checkbox(label="Filtro de Tendência (MMS)", value=state["mms_active"])
    tf_mms_periodo = ft.TextField(
        label="Períodos",
        value=str(state["mms_periodos"][0]),
        width=80,
        height=40,
        text_size=12,
        content_padding=8,
    )
    row_mms = ft.Row([cb_mms, tf_mms_periodo], alignment=ft.MainAxisAlignment.START)

    cb_rsi = ft.Checkbox(label="Oscilador Momentum (RSI)", value=state["rsi_active"])
    cb_stoch = ft.Checkbox(label="Estocástico Lento", value=state["stoch_active"])

    _pid_file_path = _paths.PID_FILE

    def check_bg_service_running():
        if os.path.exists(_pid_file_path):
            try:
                with open(_pid_file_path, "r") as f:
                    pid = int(f.read().strip())
                if psutil.pid_exists(pid):
                    return True
                else:
                    os.remove(_pid_file_path)
                    return False
            except Exception:
                return False
        return False

    def toggle_bg_service(e):
        if check_bg_service_running():
            try:
                with open(_pid_file_path, "r") as f:
                    pid = int(f.read().strip())
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/F", "/PID", str(pid)], capture_output=True
                    )
                else:
                    import signal

                    os.kill(pid, signal.SIGTERM)
            except Exception as ex:
                logging.warning(f"Erro ao parar bg service (pode já estar morto): {ex}")
            finally:
                if os.path.exists(_pid_file_path):
                    os.remove(_pid_file_path)
            btn_toggle_bg.text = "Ligar Serviço em Segundo Plano"
            btn_toggle_bg.bgcolor = ft.Colors.BLUE_GREY_700
            btn_toggle_bg.icon = ft.Icons.PLAY_ARROW
        else:
            try:
                subprocess.Popen(
                    [
                        sys.executable,
                        os.path.join(
                            _paths.BASE_DIR, "services", "background_service.py"
                        ),
                    ],
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            except Exception as e:
                import traceback

                tb = traceback.format_exc()
                logging.error(f"Erro ao iniciar bg service: {e}\n{tb}")
            btn_toggle_bg.text = "Parar Serviço em Segundo Plano"
            btn_toggle_bg.bgcolor = ft.Colors.RED_700
            btn_toggle_bg.icon = ft.Icons.STOP
        dlg_config.update()

    btn_toggle_bg = ft.Button(
        "Parar Serviço em Segundo Plano"
        if check_bg_service_running()
        else "Ligar Serviço em Segundo Plano",
        icon=ft.Icons.STOP if check_bg_service_running() else ft.Icons.PLAY_ARROW,
        bgcolor=ft.Colors.RED_700
        if check_bg_service_running()
        else ft.Colors.BLUE_GREY_700,
        color=ft.Colors.WHITE,
        on_click=toggle_bg_service,
    )

    dlg_config = ft.AlertDialog(
        title=ft.Text("Setup de Algoritmo"),
        content=ft.Column(
            [row_mms, cb_rsi, cb_stoch, ft.Divider(), btn_toggle_bg], tight=True
        ),
        actions=[
            ft.Button(
                "Salvar e Compilar Confluências",
                on_click=save_config,
                bgcolor=ft.Colors.BLUE_600,
                color=ft.Colors.WHITE,
            )
        ],
    )

    def open_config(e=None):
        logging.info("Usuário abriu popup de configuração.")
        if dlg_config not in page.overlay:
            page.overlay.append(dlg_config)
        dlg_config.open = True
        _safe_page_update()

    return dlg_config, open_config
