"""
Testes de regressao para ui/cards/ package (Fase 4.1 + 4.2).

Validam que a decomposicao de create_card em 7 sub-modulos mantem
comportamento identico ao cards.py monolitico original.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flet as ft
from unittest.mock import MagicMock

from ui.cards import (
    create_card,
    compute_trend_style,
    TrendStyle,
    build_actions,
    build_indicator_tags,
    build_badges,
    build_variation_col,
    build_note_preview,
)


def _make_dado(
    is_alta=True,
    sem_dados=False,
    sem_confluencia=False,
    tendencia="alta",
    volume_spike=False,
    market_cap=500e9,
    tipo="acoes",
    setor="petroleo",
    nome=None,
    **kwargs,
):
    """Factory de dado sintetico para testes."""
    dado = {
        "ativo": {
            "codigo": "PETR4",
            "ticker": "PETR4.SA",
            "nome": nome or "Petrobras PN",
            "tipo": tipo,
            "setor": setor,
        },
        "isAlta": is_alta,
        "marketCap": market_cap,
        "fechamento": 30.0,
        "variacao": 1.5,
        "variacao_7d": 3.2,
        "variacao_30d": -0.5,
        "indicadores": [{"nome": "MMS", "sinal": 1}],
        "semFiltro": False,
        "semDados": sem_dados,
        "semConfluencia": sem_confluencia,
        "qtdCandles": 5,
        "tempoTendencia": "3 dias",
        "tendencia": tendencia,
        "volumeSpike": volume_spike,
        "dataVariacao": "15-01-24",
    }
    dado.update(kwargs)
    return dado


def _make_state(carteiras=None, ocultos=None, anotacoes=None):
    """Factory de state sintetico para testes."""
    return {
        "carteiras": carteiras or {"Principal": {}},
        "ocultos": ocultos or [],
        "anotacoes": anotacoes or {},
        "sort": "all",
    }


class TestTrendStyle(unittest.TestCase):
    """compute_trend_style e o coracao do card - nao pode quebrar."""

    def test_tendencia_alta_confirmada(self):
        d = _make_dado(is_alta=True, sem_dados=False, sem_confluencia=False, tendencia="alta")
        t = compute_trend_style(d)
        self.assertIsInstance(t, TrendStyle)
        self.assertEqual(t.texto_status, "TEND ALTA")
        self.assertEqual(t.icone_seta, "▲")
        self.assertEqual(t.cor_texto, ft.Colors.GREEN_400)
        self.assertEqual(t.cor_gradiente, ft.Colors.GREEN_900)

    def test_tendencia_baixa_confirmada(self):
        d = _make_dado(is_alta=False, sem_dados=False, sem_confluencia=False, tendencia="baixa")
        t = compute_trend_style(d)
        self.assertEqual(t.texto_status, "TEND BAIXA")
        self.assertEqual(t.icone_seta, "▼")
        self.assertEqual(t.cor_texto, ft.Colors.RED_400)

    def test_sem_dados(self):
        d = _make_dado(sem_dados=True)
        t = compute_trend_style(d)
        self.assertEqual(t.texto_status, "SEM DADOS")
        self.assertEqual(t.icone_seta, "•")
        self.assertEqual(t.cor_texto, ft.Colors.BLUE_GREY_400)

    def test_sem_confluencia_alta(self):
        """Sem confluencia mas em alta - mostra DIÁRIO em verde."""
        d = _make_dado(is_alta=True, sem_confluencia=True, sem_dados=False)
        t = compute_trend_style(d)
        self.assertEqual(t.texto_status, "DIÁRIO")
        self.assertEqual(t.icone_seta, "▲")
        self.assertEqual(t.cor_texto, ft.Colors.GREEN_400)

    def test_sem_confluencia_baixa(self):
        d = _make_dado(is_alta=False, sem_confluencia=True, sem_dados=False)
        t = compute_trend_style(d)
        self.assertEqual(t.texto_status, "DIÁRIO")
        self.assertEqual(t.cor_texto, ft.Colors.RED_400)

    def test_sem_dados_tem_prioridade_sobre_sem_confluencia(self):
        """Se sem_dados=True, status deve ser SEM DADOS independente de semConfluencia."""
        d = _make_dado(sem_dados=True, sem_confluencia=True)
        t = compute_trend_style(d)
        self.assertEqual(t.texto_status, "SEM DADOS")


class TestBuildActions(unittest.TestCase):
    """build_actions cria coluna com favorito + ocultar."""

    def test_retorna_column_com_2_icon_buttons(self):
        actions = build_actions(
            codigo_ativo="PETR4", is_fav=False, is_oculto=False,
            preco_atual=30.0, state=_make_state(),
            active_wallet=None,
            open_add_carteira_dialog=lambda t, p: None,
            open_remove_carteira_dialog=lambda t, c: None,
            save_ocultos=lambda: None,
            render_list=lambda: None,
        )
        self.assertIsInstance(actions, ft.Column)
        # Deve ter 2 IconButton: favorito + ocultar
        self.assertEqual(len(actions.controls), 2)
        self.assertIsInstance(actions.controls[0], ft.IconButton)
        self.assertIsInstance(actions.controls[1], ft.IconButton)

    def test_favorito_destacado_quando_is_fav(self):
        actions = build_actions(
            codigo_ativo="PETR4", is_fav=True, is_oculto=False,
            preco_atual=30.0, state=_make_state(),
            active_wallet=None,
            open_add_carteira_dialog=lambda t, p: None,
            open_remove_carteira_dialog=lambda t, c: None,
            save_ocultos=lambda: None,
            render_list=lambda: None,
        )
        fav_icon = actions.controls[0]
        # Quando is_fav=True, icone deve ser STAR_ROUNDED (preenchido)
        self.assertEqual(fav_icon.icon, ft.Icons.STAR_ROUNDED)
        # Cor deve ser AMBER_400 (destacado)
        self.assertEqual(fav_icon.icon_color, ft.Colors.AMBER_400)

    def test_ocultar_destacado_quando_is_oculto(self):
        actions = build_actions(
            codigo_ativo="PETR4", is_fav=False, is_oculto=True,
            preco_atual=30.0, state=_make_state(),
            active_wallet=None,
            open_add_carteira_dialog=lambda t, p: None,
            open_remove_carteira_dialog=lambda t, c: None,
            save_ocultos=lambda: None,
            render_list=lambda: None,
        )
        hide_icon = actions.controls[1]
        self.assertEqual(hide_icon.icon, ft.Icons.VISIBILITY_OFF)
        self.assertEqual(hide_icon.icon_color, ft.Colors.RED_400)


class TestBuildIndicatorTags(unittest.TestCase):
    """build_indicator_tags cria tags MMS/RSI/STOCH + SemConfluencia + VolAnomalo."""

    def test_tag_mms_alta(self):
        d = _make_dado()
        d["indicadores"] = [{"nome": "MMS", "sinal": 1}]
        tags = build_indicator_tags(d)
        self.assertIsInstance(tags, ft.Row)
        self.assertEqual(len(tags.controls), 1)
        # Container com Row [Text(MMS), Text(▲)]
        container = tags.controls[0]
        self.assertIsInstance(container, ft.Container)

    def test_tag_volume_anomalo_adicionada(self):
        d = _make_dado(volume_spike=True)
        tags = build_indicator_tags(d)
        # Deve ter: 1 tag MMS + 1 tag Vol Anômalo = 2
        self.assertEqual(len(tags.controls), 2)

    def test_tag_sem_confluencia_adicionada(self):
        d = _make_dado(sem_confluencia=True)
        tags = build_indicator_tags(d)
        # Deve ter: 1 tag MMS + 1 tag Sem Confluência = 2
        self.assertEqual(len(tags.controls), 2)

    def test_sem_tags_quando_sem_filtro(self):
        """Quando semFiltro=True, nao mostra tags de indicadores."""
        d = _make_dado()
        d["semFiltro"] = True
        tags = build_indicator_tags(d)
        # SemFiltro nao adiciona tags de indicadores, mas pode adicionar
        # Sem Confluencia ou Vol Anômalo se aplicavel
        # Para nosso dado base, semFiltro=True e semConfluencia=False
        # entao deve ter 0 tags
        self.assertEqual(len(tags.controls), 0)


class TestBuildBadges(unittest.TestCase):
    """build_badges cria badges codigo + PnL + setor + market_cap."""

    def test_badge_codigo_sempre_presente(self):
        from core.config import formatar_market_cap
        d = _make_dado()
        mc_data = formatar_market_cap(d["marketCap"])
        badges = build_badges(
            d, _make_state(), None, mc_data, "PETR4", 30.0
        )
        self.assertIsInstance(badges, ft.Row)
        # Deve ter pelo menos: codigo + setor + market_cap = 3 badges
        self.assertGreaterEqual(len(badges.controls), 3)

    def test_badge_pnl_adicionado_quando_carteira_ativa(self):
        from core.config import formatar_market_cap
        d = _make_dado()
        # State com carteira ativa contendo PETR4 com preco_entrada
        state = _make_state(carteiras={"Minha": {"PETR4": {"preco_entrada": 25.0, "quantidade": 100}}})
        mc_data = formatar_market_cap(d["marketCap"])
        badges = build_badges(
            d, state, "Minha", mc_data, "PETR4", 30.0
        )
        # Deve ter: codigo + PnL + setor + market_cap = 4 badges
        self.assertEqual(len(badges.controls), 4)

    def test_badge_pnl_nao_adicionado_se_preco_entrada_zero(self):
        from core.config import formatar_market_cap
        d = _make_dado()
        state = _make_state(carteiras={"Minha": {"PETR4": {"preco_entrada": 0, "quantidade": 100}}})
        mc_data = formatar_market_cap(d["marketCap"])
        badges = build_badges(
            d, state, "Minha", mc_data, "PETR4", 30.0
        )
        # Sem PnL: codigo + setor + market_cap = 3 badges
        self.assertEqual(len(badges.controls), 3)


class TestBuildVariationCol(unittest.TestCase):
    """build_variation_col cria coluna direita com variacao %."""

    def test_retorna_column(self):
        d = _make_dado()
        t = compute_trend_style(d)
        col = build_variation_col(d, t)
        self.assertIsInstance(col, ft.Column)

    def test_variacao_positiva_em_verde(self):
        d = _make_dado()
        d["variacao"] = 2.5
        t = compute_trend_style(d)
        col = build_variation_col(d, t)
        # Primeiro control e Text com variacao em W_800 (22pt)
        text_var = col.controls[0]
        self.assertIsInstance(text_var, ft.Text)
        self.assertIn("+2.50%", text_var.value)
        self.assertEqual(text_var.color, ft.Colors.GREEN_400)

    def test_variacao_negativa_em_vermelho(self):
        d = _make_dado()
        d["variacao"] = -1.5
        t = compute_trend_style(d)
        col = build_variation_col(d, t)
        text_var = col.controls[0]
        self.assertIn("-1.50%", text_var.value)
        self.assertEqual(text_var.color, ft.Colors.RED_400)


class TestBuildNotePreview(unittest.TestCase):
    """build_note_preview cria filled state ou empty state."""

    def test_empty_state_quando_sem_nota(self):
        container = build_note_preview(_make_state(), "PETR4", lambda t: None)
        self.assertIsInstance(container, ft.Container)
        # Empty state tem Row com ADD_COMMENT_OUTLINED icon
        content = container.content
        self.assertIsInstance(content, ft.Row)
        self.assertEqual(content.controls[0].icon, ft.Icons.ADD_COMMENT_OUTLINED)

    def test_filled_state_com_texto(self):
        state = _make_state(anotacoes={"PETR4": {"texto": "Compra em 25, alvo 35", "imagens": []}})
        container = build_note_preview(state, "PETR4", lambda t: None)
        # Filled state tem Column com Row (header) + Text (preview)
        content = container.content
        self.assertIsInstance(content, ft.Column)
        # Segundo control deve ser Text com preview
        preview_text = content.controls[1]
        self.assertIsInstance(preview_text, ft.Text)
        self.assertIn("Compra em 25", preview_text.value)

    def test_filled_state_formato_antigo_string(self):
        """Anotacoes antigas eram strings - devem virar filled state."""
        state = _make_state(anotacoes={"PETR4": "Nota antiga"})
        container = build_note_preview(state, "PETR4", lambda t: None)
        content = container.content
        self.assertIsInstance(content, ft.Column)
        preview_text = content.controls[1]
        self.assertIn("Nota antiga", preview_text.value)

    def test_preview_trunca_texto_longo(self):
        """Texto > 80 chars deve ser truncado com '...'."""
        texto_longo = "A" * 200
        state = _make_state(anotacoes={"PETR4": {"texto": texto_longo, "imagens": []}})
        container = build_note_preview(state, "PETR4", lambda t: None)
        content = container.content
        preview_text = content.controls[1]
        self.assertIn("...", preview_text.value)
        # Preview deve ser no maximo 80 + 3 = 83 chars
        self.assertLessEqual(len(preview_text.value), 83)


class TestCreateCardIntegracao(unittest.TestCase):
    """Teste de integracao: create_card orquestra todos sub-componentes."""

    def test_retorna_container_com_gradiente(self):
        d = _make_dado()
        card = create_card(
            dado=d, state=_make_state(), page=MagicMock(),
            render_list=lambda: None,
            open_add_carteira_dialog=lambda t, p: None,
            open_remove_carteira_dialog=lambda t, c: None,
            open_notes_dialog=lambda t: None,
            save_ocultos=lambda: None, active_wallet=None,
        )
        self.assertIsInstance(card, ft.Container)
        # Card tem gradient baseado em trend.cor_texto
        self.assertIsNotNone(card.gradient)

    def test_card_com_dado_completo_nao_quebra(self):
        """Card com todos campos preenchidos deve renderizar sem erro."""
        d = _make_dado(
            is_alta=True, sem_dados=False, sem_confluencia=False,
            tendencia="alta", volume_spike=True,
            market_cap=50e9, tipo="acoes", setor="petroleo",
        )
        # State com carteira ativa e nota anexada
        state = _make_state(
            carteiras={"Minha": {"PETR4": {"preco_entrada": 25.0, "quantidade": 100}}},
            anotacoes={"PETR4": {"texto": "Nota de teste", "imagens": []}},
        )
        card = create_card(
            dado=d, state=state, page=MagicMock(),
            render_list=lambda: None,
            open_add_carteira_dialog=lambda t, p: None,
            open_remove_carteira_dialog=lambda t, c: None,
            open_notes_dialog=lambda t: None,
            save_ocultos=lambda: None, active_wallet="Minha",
        )
        self.assertIsInstance(card, ft.Container)

    def test_card_sem_dados_nao_quebra(self):
        """Card com semDados=True deve renderizar com estado neutro."""
        d = _make_dado(sem_dados=True)
        card = create_card(
            dado=d, state=_make_state(), page=MagicMock(),
            render_list=lambda: None,
            open_add_carteira_dialog=lambda t, p: None,
            open_remove_carteira_dialog=lambda t, c: None,
            open_notes_dialog=lambda t: None,
            save_ocultos=lambda: None, active_wallet=None,
        )
        self.assertIsInstance(card, ft.Container)


if __name__ == "__main__":
    unittest.main(verbosity=2)
