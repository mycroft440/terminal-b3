import flet as ft
import threading
import time
import logging
from core.config import SETORES_ACOES, SETORES_FIIS
from ui.theme import AppColors
from ui.components import dropdown_options, pill_button
from ui.dashboard.background_worker import BackgroundScannerWorker
from ui.dashboard.render import DashboardRenderer
from ui.dashboard.wallet_view import WalletView
import ui.flet_patches  # noqa: F401  # aplica monkey-patches de Flet >= 0.80


def get_dashboard_view(page: ft.Page, state_manager):
    def page_error_handler(e):
        logging.error(f"Flet UI Unhandled Error: {e.data}")

    page.on_error = page_error_handler

    state = state_manager.state
    save_ui_state = state_manager.save_ui_state

    # Sanitize state if it was saved with 'cripto'
    if state.get("market") == "cripto":
        state["market"] = "acoes"
        save_ui_state()

    # Carrega cache persistente de ativos avaliados do disco.
    # Isso permite que o app reabra instantaneamente com os dados do ultimo
    # download, sem precisar reprocessar todos os ativos via gerar_b3_chunks.
    # O cache yfinance (diskcache) continua sendo a fonte de verdade para os
    # candles; este cache so evita recomputar indicadores MMS/RSI/Stoch.
    persisted_evaluated = state_manager.load_evaluated_cache()
    if persisted_evaluated:
        logging.info(
            f"[CACHE PERSISTIDO] {sum(len(v) for v in persisted_evaluated.values())} "
            f"ativos avaliados carregados do disco em "
            f"{len(persisted_evaluated)} configuracoes."
        )

    app_cache = {
        "evaluated_assets": persisted_evaluated,  # key: config_hash, value: list of evaluated dicts
        "card_controls": {},  # key: ticker, value: Flet control
        "hist_fetch_id": 0,  # tracking for active threads
        "last_save_ts": time.time(),  # controle para salvar cache periodicamente
    }
    app_cache_lock = threading.Lock()
    bg_worker_running = [True]
    config_changed_event = threading.Event()

    # Alias local para state_manager.get_config_hash() - usa implementacao unica
    # em StateManager para evitar drift entre duas copias da mesma logica.
    def get_config_hash():
        return state_manager.get_config_hash()

    def on_disconnect(e):
        bg_worker_running[0] = False
        config_changed_event.set()

    page.on_disconnect = on_disconnect

    save_carteiras = state_manager.save_carteiras
    save_ocultos = state_manager.save_ocultos
    save_notes = state_manager.save_notes

    # ListViews independentes por mercado — cada um preserva seus cards em memoria.
    # Trocar de mercado alterna visibilidade (instantaneo, zero re-serialização).
    market_list_views = {}
    market_containers = {}
    for _mk in ["acoes", "fiis", "bdrs"]:
        _lv = ft.ListView(
            expand=True, spacing=8,
            padding=ft.Padding(left=16, top=8, right=16, bottom=16),
        )
        market_list_views[_mk] = _lv
        market_containers[_mk] = ft.Container(
            content=_lv, expand=True,
            visible=(state["market"] == _mk),
        )
    status_text = ft.Text(
        "Pronto.", color=ft.Colors.BLUE_GREY_500, size=11, italic=True
    )
    portfolio_stats_container = ft.Container(
        visible=False,
        padding=ft.Padding(16, 8, 16, 8),
        bgcolor=ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY_700),
    )

    def safe_update(ctrl):
        try:
            ctrl.update()
        except Exception:
            pass

    # Renderers independentes por mercado (lazy init, thread-safe)
    _market_renderers = {}
    _renderer_lock = threading.Lock()

    def get_dashboard_renderer():
        """Lazy init do DashboardRenderer para o mercado atual. Thread-safe."""
        mk = state["market"]
        if mk not in _market_renderers:
            with _renderer_lock:
                if mk not in _market_renderers:
                    _market_renderers[mk] = DashboardRenderer(
                        state=state,
                        app_cache=app_cache,
                        app_cache_lock=app_cache_lock,
                        list_view=market_list_views[mk],
                        page=page,
                        get_config_hash=get_config_hash,
                        portfolio_stats_container=portfolio_stats_container,
                        txt_ativos_count=txt_ativos_count,
                        txt_alta_count=txt_alta_count,
                        txt_baixa_count=txt_baixa_count,
                        open_add_carteira_dialog=open_add_carteira_dialog,
                        open_remove_carteira_dialog=open_remove_carteira_dialog,
                        open_notes_dialog=open_notes_dialog,
                        save_ocultos=save_ocultos,
                        on_voltar=lambda: select_sort("all"),
                    )
        return _market_renderers[mk]

    def _switch_market_view(market):
        """Alterna visibilidade do container do mercado ativo (instantaneo)."""
        for mk, cont in market_containers.items():
            new_visible = (mk == market)
            if cont.visible != new_visible:
                cont.visible = new_visible
                safe_update(cont)

    def _switch_to_wallet():
        """Alterna visibilidade para exibir a wallet view."""
        if dashboard_content.visible:
            dashboard_content.visible = False
            wallet_content.visible = True
            safe_update(dashboard_content)
            safe_update(wallet_content)

    def _switch_to_dashboard():
        """Alterna visibilidade para exibir o dashboard do mercado atual."""
        if wallet_content.visible:
            wallet_content.visible = False
            dashboard_content.visible = True
            safe_update(wallet_content)
            safe_update(dashboard_content)
        _switch_market_view(state["market"])

    def render_list():
        """Renderiza lista de cards via DashboardRenderer OU tabela via WalletView."""
        if str(state.get("sort", "")).startswith("cart_"):
            wv = get_wallet_view()
            wallet_content.content = wv.list_view
            _switch_to_wallet()
            wv.render()
        else:
            _switch_to_dashboard()
            get_dashboard_renderer().render()


    def background_scanner_worker():
        """Wrapper que instancia BackgroundScannerWorker e roda em loop.

        A logica foi extraida para ui.dashboard.background_worker.BackgroundScannerWorker
        para reduzir o tamanho do closure de get_dashboard_view e facilitar testes.
        """
        worker = BackgroundScannerWorker(
            state=state,
            app_cache=app_cache,
            app_cache_lock=app_cache_lock,
            state_manager=state_manager,
            status_text=status_text,
            page=page,
            config_changed_event=config_changed_event,
            bg_worker_running=bg_worker_running,
            get_config_hash=get_config_hash,
        )
        worker.run()


    def select_sort(s):
        logging.info(f"Usuário selecionou filtro: {s}")
        old_sort = state.get("sort", "")
        state["sort"] = s

        # NAO limpar card_controls ao trocar sort — isso forca reconstrucao
        # de 900+ cards causando travamento. Cards serao reusados do cache.
        # So limpar quando market/timeframe mudar (select_market/select_tf).

        entrou_carteira = s.startswith("cart_") and not old_sort.startswith("cart_")
        saiu_carteira = old_sort.startswith("cart_") and not s.startswith("cart_")

        if entrou_carteira:
            # Entrou em carteira: worker precisa carregar tickers da carteira
            state["is_loading"] = True
            save_ui_state()
            _update_sort_pills()
            config_changed_event.set()
            render_list()
        elif saiu_carteira:
            # Saiu de carteira: dashboard_content ja tem os cards em memoria.
            # Basta alternar visibilidade — ZERO re-serialização de cards.
            state["is_loading"] = False
            _update_sort_pills()
            _switch_to_dashboard()
            safe_update(sort_pills_row)
            # Persistencia em disco diferida (nao trava UI no _save_lock)
            threading.Thread(target=save_ui_state, daemon=True).start()
        else:
            # Troca dentro do mesmo contexto (ex: cart_A -> cart_B, all -> ocultos)
            _update_sort_pills()
            if old_sort == "ocultos" and s == "all":
                # Ocultos compartilha o mesmo list_view, controls foram
                # substituidos. Precisa re-renderizar em thread.
                safe_update(sort_pills_row)
                threading.Thread(target=render_list, daemon=True).start()
                threading.Thread(target=save_ui_state, daemon=True).start()
            else:
                save_ui_state()
                render_list()

    def get_sector_options_for_market(market):
        if market == "acoes" or market == "bdrs":
            return SETORES_ACOES
        if market == "fiis":
            return SETORES_FIIS
        return [("all", "Todos")]

    def update_sector_dropdown():
        sector_dropdown.options = dropdown_options(
            get_sector_options_for_market(state["market"])
        )
        sector_dropdown.value = state["sector"]
        sector_dropdown.disabled = False
        sector_dropdown.label = "Setor"

    def select_sector(sector):
        logging.info(f"Usuário selecionou setor: {sector}")
        state["sector"] = sector or "all"
        save_ui_state()
        render_list()

    def select_market(m):
        logging.info(f"Usuário selecionou mercado: {m}")
        state["market"] = m
        state["sector"] = "all"
        state["sort"] = "all"
        # Limpa termo de busca ao trocar de mercado
        state["search"] = ""
        if hasattr(search_input, "value"):
            search_input.value = ""
        # NAO limpar card_controls — tickers sao unicos por mercado,
        # preservar cache permite voltar ao mercado anterior instantaneamente.
        _update_market_pills()
        _update_sort_pills()
        update_sector_dropdown()
        # Troca visibilidade do mercado (instantaneo)
        _switch_market_view(m)
        # Verifica se mercado ja tem dados carregados no cache
        current_hash = state_manager.get_config_hash()
        with app_cache_lock:
            has_data = bool(app_cache["evaluated_assets"].get(current_hash))
        if has_data:
            # Mercado ja carregado — render do cache, sem acionar worker
            state["is_loading"] = False
            render_list()
        else:
            # Mercado nao carregado — acionar worker para download
            state["is_loading"] = True
            config_changed_event.set()
            render_list()
        # Persistencia diferida
        threading.Thread(target=save_ui_state, daemon=True).start()

    def select_tf(tf):
        logging.info(f"Usuário selecionou timeframe: {tf}")
        state["timeframe"] = tf
        state["is_loading"] = True
        # Limpa card_controls: cards do timeframe anterior tem dados errados (BUG 12)
        with app_cache_lock:
            app_cache["card_controls"].clear()
        save_ui_state()
        config_changed_event.set()
        render_list()

    # Debounce da pesquisa: so renderiza 300ms apos ultima tecla
    _search_timer = [None]

    def on_search(e):
        """Filtra lista por termo de busca com debounce de 300ms."""
        value = e.control.value if e and hasattr(e, "control") else ""
        # BUG 17: capturar market no momento do digitar para que o render
        # debounce use o market correto (evita race condition onde usuario
        # digita "PETR" no mercado acoes, troca para FIIs em 300ms, e a
        # busca "PETR" e aplicada aos FIIs)
        search_market = state.get("market", "")
        state["search"] = value

        # Cancela timer anterior (debounce)
        if _search_timer[0] is not None:
            _search_timer[0].cancel()

        def do_render():
            # So renderiza se o mercado nao mudou durante o debounce
            if state.get("market", "") == search_market:
                try:
                    page.pubsub.send_all({"type": "render_list"})
                except Exception:
                    pass

        _search_timer[0] = threading.Timer(0.3, do_render)
        _search_timer[0].daemon = True
        _search_timer[0].start()

    txt_ativos_count = ft.Text(
        "0 na tela", size=11, color=ft.Colors.BLUE_400, weight=ft.FontWeight.BOLD
    )
    txt_alta_count = ft.Text(
        "0 em alta", size=11, color=ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD
    )
    txt_baixa_count = ft.Text(
        "0 em baixa", size=11, color=ft.Colors.RED_400, weight=ft.FontWeight.BOLD
    )

    # ─── HEADER ───────────────────────────────────────────────
    header = ft.Container(
        content=ft.Row(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(
                                ft.Icons.SHOW_CHART_ROUNDED,
                                color=ft.Colors.WHITE,
                                size=22,
                            ),
                            bgcolor=ft.Colors.BLUE_600,
                            border_radius=10,
                            width=40,
                            height=40,
                            alignment=ft.alignment.center,
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    "Terminal B3 Pro",
                                    size=20,
                                    weight=ft.FontWeight.W_800,
                                    color=ft.Colors.WHITE,
                                ),
                                ft.Row(
                                    [
                                        ft.Text(
                                            "Motor de Confluência Multi-Mercado",
                                            size=11,
                                            weight=ft.FontWeight.W_400,
                                            color=ft.Colors.BLUE_GREY_500,
                                        ),
                                        txt_ativos_count,
                                        ft.Text(
                                            "•", size=11, color=ft.Colors.BLUE_GREY_700
                                        ),
                                        txt_alta_count,
                                        txt_baixa_count,
                                    ],
                                    spacing=10,
                                ),
                            ],
                            spacing=0,
                        ),
                    ],
                    spacing=12,
                ),
                # Botao de config movido para a toolbar (filters_row_1)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.Padding(left=20, top=16, right=20, bottom=12),
        gradient=ft.LinearGradient(
            begin=ft.alignment.top_left,
            end=ft.alignment.bottom_right,
            colors=["#0D1117", "#131A24"],
        ),
    )

    # ─── MARKET PILLS ─────────────────────────────────────────
    # "Todos Ativos" removido a pedido do usuario. Mercados separados:
    # Acoes B3, FIIs, BDRs.
    market_keys = ["acoes", "fiis", "bdrs"]
    market_labels = ["Ações B3", "FIIs", "BDRs"]

    # Sanitiza state['market'] se for 'todos' (legado) -> 'acoes'
    if state.get("market") == "todos":
        state["market"] = "acoes"
        save_ui_state()

    def _make_market_pill(key, label):
        return pill_button(
            label,
            selected=(state["market"] == key),
            on_click=lambda e, k=key: select_market(k),
            color_sel=ft.Colors.BLUE_700,
        )

    market_pills_row = ft.Row(
        [_make_market_pill(k, lbl) for k, lbl in zip(market_keys, market_labels)],
        spacing=6,
    )

    def _update_market_pills():
        for i, (k, _lbl) in enumerate(zip(market_keys, market_labels)):
            sel = state["market"] == k
            c = market_pills_row.controls[i]
            c.bgcolor = (
                ft.Colors.BLUE_700
                if sel
                else ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_700)
            )
            c.border = ft.border.all(
                1,
                ft.Colors.BLUE_700
                if sel
                else ft.Colors.with_opacity(0.3, ft.Colors.BLUE_GREY_600),
            )
            txt = c.content.controls[-1]
            txt.weight = ft.FontWeight.W_600 if sel else ft.FontWeight.W_400
            txt.color = ft.Colors.WHITE if sel else ft.Colors.BLUE_GREY_300

    # ─── TIMEFRAME DROPDOWN ───────────────────────────────────
    tf_dropdown = ft.Dropdown(
        options=[
            ft.dropdown.Option("1d"),
            ft.dropdown.Option("1s"),
        ],
        value=state["timeframe"] if state["timeframe"] in ("1d", "1s") else "1d",
        width=90,
        dense=True,
        on_select=lambda e: select_tf(e.control.value),
        bgcolor="#1A2332",
        color=ft.Colors.WHITE,
        border_color=ft.Colors.with_opacity(0.3, ft.Colors.BLUE_GREY_600),
        border_radius=10,
        text_size=12,
        label="Tempo",
        label_style=ft.TextStyle(size=10, color=ft.Colors.BLUE_GREY_500),
    )

    # ─── SECTOR DROPDOWN ──────────────────────────────────────
    sector_dropdown = ft.Dropdown(
        label="Setor",
        options=dropdown_options(get_sector_options_for_market(state["market"])),
        value=state["sector"],
        width=220,
        dense=True,
        on_select=lambda e: select_sector(e.control.value),
        bgcolor="#1A2332",
        color=ft.Colors.WHITE,
        border_color=ft.Colors.with_opacity(0.3, ft.Colors.BLUE_GREY_600),
        border_radius=10,
        text_size=12,
        label_style=ft.TextStyle(size=10, color=ft.Colors.BLUE_GREY_500),
    )

    # ─── SEARCH (compacta, width fixo) ──────────────────────
    search_input = ft.TextField(
        hint_text="Pesquisar...",
        prefix_icon=ft.Icons.SEARCH_ROUNDED,
        height=40,
        width=200,
        content_padding=ft.Padding(left=10, top=0, right=10, bottom=0),
        text_size=12,
        border_radius=10,
        on_change=on_search,
        bgcolor="#1A2332",
        border_color=ft.Colors.with_opacity(0.3, ft.Colors.BLUE_GREY_600),
        focused_border_color=ft.Colors.BLUE_500,
        color=ft.Colors.WHITE,
        hint_style=ft.TextStyle(size=12, color=ft.Colors.BLUE_GREY_600),
    )

    # ─── SORT PILLS (CARTEIRAS) ──────────────────────────────
    # Definido ANTES dos filters_row para poder ser referenciado
    def get_sort_keys_and_labels():
        keys = []
        labels = []
        colors = []

        for c_nome in state["carteiras"].keys():
            keys.append(f"cart_{c_nome}")
            labels.append(f"📂 {c_nome}")
            colors.append(ft.Colors.AMBER_600)

        keys.append("ocultos")
        labels.append("👁️ Ocultos")
        colors.append(ft.Colors.BLUE_GREY_600)

        return keys, labels, colors

    def _make_sort_pill(key, label, color):
        return pill_button(
            label,
            selected=(state["sort"] == key),
            on_click=lambda e, k=key: select_sort(k),
            color_sel=color,
        )

    def _build_sort_pills():
        pills = []

        # Botao "Voltar" - so aparece quando esta numa carteira ou ocultos
        if state.get("sort", "") != "all":
            voltar_btn = ft.TextButton(
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.ARROW_BACK_IOS, size=14, color=ft.Colors.WHITE),
                        ft.Text(
                            "Voltar",
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE,
                        ),
                    ],
                    spacing=4,
                    tight=True,
                ),
                on_click=lambda e: select_sort("all"),
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.BLUE_600,
                    padding=ft.Padding(14, 7, 14, 7),
                    shape=ft.RoundedRectangleBorder(radius=20),
                    side=ft.BorderSide(1, ft.Colors.BLUE_500),
                ),
            )
            pills.append(voltar_btn)

        # Carteiras e ocultos
        keys, labels, colors = get_sort_keys_and_labels()
        pills.extend(
            _make_sort_pill(k, lbl, c) for k, lbl, c in zip(keys, labels, colors)
        )

        # Botao Nova Carteira
        nova_carteira_pill = pill_button(
            "Nova Carteira",
            selected=False,
            on_click=lambda e: open_nova_carteira_dialog(),
            color_sel=ft.Colors.GREEN_500,
            icon=ft.Icons.ADD_ROUNDED,
        )
        pills.append(nova_carteira_pill)

        # Botao "Adicionar Ativo" - so aparece quando esta numa carteira
        if str(state.get("sort", "")).startswith("cart_"):
            add_asset_pill = pill_button(
                "Adicionar Ativo",
                selected=False,
                on_click=lambda e: open_add_asset_dialog(),
                color_sel=ft.Colors.CYAN_500,
                icon=ft.Icons.PERSON_ADD,
            )
            pills.append(add_asset_pill)

        return pills

    sort_pills_row = ft.Row(
        _build_sort_pills(), spacing=6, scroll=ft.ScrollMode.AUTO, expand=True
    )

    def _update_sort_pills():
        sort_pills_row.controls = _build_sort_pills()

    # ─── FILTERS ROW 1: Carteiras (sort pills) no topo ──────
    filters_row_1 = ft.Row(
        [sort_pills_row, status_text],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ─── FILTERS ROW 2: Market pills (Acoes/FIIs/BDRs) ──────
    filters_row_2 = ft.Row(
        [market_pills_row],
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ─── FILTERS ROW 3: Setor dropdown ──────────────────────
    filters_row_3 = ft.Row(
        [sector_dropdown],
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12,
    )

    # ─── FILTERS ROW 4: Pesquisa + Tempo + Config Indicadores ──
    filters_row_4 = ft.Row(
        [
            search_input,
            ft.Container(width=8),
            tf_dropdown,
            ft.IconButton(
                icon=ft.Icons.TUNE_ROUNDED,
                icon_color=ft.Colors.BLUE_200,
                icon_size=18,
                bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_600),
                tooltip="Configurar Indicadores",
                on_click=lambda e: open_config(e),
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
            ),
        ],
        alignment=ft.MainAxisAlignment.START,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ─── NOTES DIALOG ─────────────────────────────────────────
    from ui.dialogs.notes import create_notes_dialog

    dlg_nota, open_notes_dialog = create_notes_dialog(
        page, state, save_notes, render_list, state_manager.IMAGES_DIR
    )

    # ─── WALLET DIALOGS ───────────────────────────────
    from ui.dialogs.wallet import create_wallet_dialogs, AddAssetDialog

    wallet_actions = create_wallet_dialogs(
        page, state, save_carteiras, save_ui_state, render_list, _update_sort_pills
    )
    open_nova_carteira_dialog = wallet_actions["open_nova_carteira_dialog"]
    open_add_carteira_dialog = wallet_actions["open_add_carteira_dialog"]
    open_remove_carteira_dialog = wallet_actions["open_remove_carteira_dialog"]

    # Dialog de busca de ativos para adicionar a carteira
    add_asset_dialog = AddAssetDialog(
        page=page,
        state=state,
        save_carteiras=save_carteiras,
        update_sort_pills_callback=_update_sort_pills,
        render_list=render_list,
    )
    open_add_asset_dialog = add_asset_dialog.open

    # ─── CONFIG DIALOG ────────────────────────────────────────
    from ui.dialogs.settings_dialog import create_settings_dialog

    dlg_config, open_config = create_settings_dialog(
        page, state, save_ui_state, render_list, config_changed_event
    )

    # ─── TOOLBAR (top panel) ──────────────────────────────────
    toolbar = ft.Container(
        content=ft.Column(
            [
                header,
                ft.Divider(
                    height=1,
                    color=ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_500),
                ),
                ft.Container(
                    content=ft.Column(
                        [filters_row_1, filters_row_2, filters_row_3, filters_row_4], spacing=10
                    ),
                    padding=ft.Padding(left=20, top=12, right=20, bottom=14),
                ),
            ],
            spacing=0,
        ),
        bgcolor="#0F1620",
        border=ft.Border(
            bottom=ft.BorderSide(
                1, ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_500)
            ),
            top=ft.BorderSide(0, ft.Colors.TRANSPARENT),
            left=ft.BorderSide(0, ft.Colors.TRANSPARENT),
            right=ft.BorderSide(0, ft.Colors.TRANSPARENT),
        ),
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=20,
            color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK),
            offset=ft.Offset(0, 4),
        ),
    )

    # ─── WALLET VIEW (tabela exclusiva da carteira) ──────────
    wallet_view_instance = [None]
    _wallet_view_lock = threading.Lock()

    def get_wallet_view():
        """Lazy initialization do WalletView. Thread-safe (BUG 19)."""
        if wallet_view_instance[0] is None:
            with _wallet_view_lock:
                # Double-checked locking
                if wallet_view_instance[0] is None:
                    wallet_view_instance[0] = WalletView(
                        page=page,
                        state=state,
                        app_cache=app_cache,
                        app_cache_lock=app_cache_lock,
                        get_config_hash=get_config_hash,
                        open_remove_carteira_dialog=open_remove_carteira_dialog,
                        open_notes_dialog=open_notes_dialog,
                        render_list=render_list,
                        on_voltar=lambda: select_sort("all"),
                    )
        return wallet_view_instance[0]

    # ─── MAIN LAYOUT ─────────────────────────────────────────
    # Dashboard: Stack de containers por mercado (visibilidade alternada).
    # Cada mercado mantem seus cards em memoria — trocar mercado e instantaneo.
    # Wallet: container separado para a tabela de carteira.
    dashboard_content = ft.Container(
        content=ft.Stack(list(market_containers.values()), expand=True),
        expand=True,
        visible=True,
    )
    wallet_content = ft.Container(expand=True, visible=False)
    main_content = ft.Stack([dashboard_content, wallet_content], expand=True)

    main_column = ft.Column(
        [
            toolbar,
            portfolio_stats_container,
            main_content,
        ],
        spacing=0,
        expand=True,
    )

    if not getattr(page, "worker_started", False):
        setattr(page, "worker_started", True)
        worker_thread = threading.Thread(target=background_scanner_worker, daemon=True)
        worker_thread.start()

        def on_message(msg):
            if isinstance(msg, dict) and msg.get("type") == "render_list":
                render_list()

        page.pubsub.subscribe(on_message)

    # Render inicial local
    render_list()

    return ft.View(
        route="/", controls=[main_column], bgcolor=AppColors.BG_MAIN, padding=0
    )
