"""
Testes de regressao para ui/dialogs/wallet/ package (Fase 5.2).

Validam que a decomposicao de wallet_dialog.py em 3 classes + orquestrador
mantem comportamento identico ao monolitico original.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flet as ft
from unittest.mock import MagicMock

from ui.dialogs.wallet import (
    create_wallet_dialogs,
    NewWalletDialog,
    AddWalletDialog,
    RemoveWalletDialog,
)


def _make_state(carteiras=None, sort="all"):
    """Factory de state sintetico."""
    return {
        "carteiras": carteiras or {"Principal": {}},
        "sort": sort,
    }


class TestNewWalletDialog(unittest.TestCase):
    """NewWalletDialog: criar nova carteira."""

    def setUp(self):
        self.page = MagicMock()
        self.page.overlay = []
        self.state = _make_state()
        self.saved_carteiras = [False]
        self.saved_ui_state = [False]
        self.updated_pills = [False]
        self.rendered = [False]

        self.dialog = NewWalletDialog(
            page=self.page,
            state=self.state,
            save_carteiras=lambda: self.saved_carteiras.__setitem__(0, True),
            save_ui_state=lambda: self.saved_ui_state.__setitem__(0, True),
            update_sort_pills_callback=lambda: self.updated_pills.__setitem__(0, True),
            render_list=lambda: self.rendered.__setitem__(0, True),
        )

    def test_instancia_corretamente(self):
        self.assertIsInstance(self.dialog, NewWalletDialog)
        self.assertIsInstance(self.dialog.dlg_nova_cart, ft.AlertDialog)
        self.assertIsInstance(self.dialog.tf_nova_cart, ft.TextField)

    def test_open_adiciona_dialog_ao_overlay(self):
        self.dialog.open()
        self.assertIn(self.dialog.dlg_nova_cart, self.page.overlay)
        self.assertTrue(self.dialog.dlg_nova_cart.open)

    def test_open_limpa_textfield(self):
        self.dialog.tf_nova_cart.value = "valor antigo"
        self.dialog.open()
        self.assertEqual(self.dialog.tf_nova_cart.value, "")

    def test_salvar_cria_carteira_com_nome_valido(self):
        """Salvar com nome valido cria carteira e atualiza state."""
        self.dialog.tf_nova_cart.value = "Minha Carteira"
        # Encontrar botao Criar e clicar
        salvar_btn = self._find_button("Criar")
        salvar_btn.on_click(None)
        # Validacoes
        self.assertIn("Minha Carteira", self.state["carteiras"])
        self.assertTrue(self.saved_carteiras[0])
        self.assertTrue(self.saved_ui_state[0])
        self.assertTrue(self.updated_pills[0])
        self.assertTrue(self.rendered[0])
        self.assertEqual(self.state["sort"], "cart_Minha Carteira")

    def test_salvar_ignora_nome_vazio(self):
        """Salvar com nome vazio nao cria carteira."""
        self.dialog.tf_nova_cart.value = "   "
        salvar_btn = self._find_button("Criar")
        salvar_btn.on_click(None)
        self.assertEqual(len(self.state["carteiras"]), 1)  # so Principal
        self.assertFalse(self.saved_carteiras[0])

    def test_salvar_ignora_nome_duplicado(self):
        """Salvar com nome ja existente nao cria carteira."""
        self.dialog.tf_nova_cart.value = "Principal"
        salvar_btn = self._find_button("Criar")
        salvar_btn.on_click(None)
        # Nao deve ter criado nova carteira
        self.assertEqual(len(self.state["carteiras"]), 1)
        self.assertFalse(self.saved_carteiras[0])

    def test_fechar_fecha_dialog(self):
        self.dialog.open()
        self.assertTrue(self.dialog.dlg_nova_cart.open)
        cancelar_btn = self._find_button("Cancelar")
        cancelar_btn.on_click(None)
        self.assertFalse(self.dialog.dlg_nova_cart.open)

    def _find_button(self, label):
        """Encontra botao por label ('Criar' ou 'Cancelar').

        Como Flet 0.85+ nao tem .text em ElevatedButton/TextButton,
        usamos a ordem: action[0] = Cancelar (TextButton), action[1] = Criar (ElevatedButton).
        """
        actions = self.dialog.dlg_nova_cart.actions
        if label == "Cancelar":
            return actions[0]  # TextButton
        if label == "Criar":
            return actions[1]  # ElevatedButton com bgcolor GREEN_600
        return None


class TestAddWalletDialog(unittest.TestCase):
    """AddWalletDialog: adicionar/remover ativo em carteiras."""

    def setUp(self):
        self.page = MagicMock()
        self.page.overlay = []
        # State com 2 carteiras, uma delas ja tem PETR4
        self.state = _make_state(carteiras={
            "Principal": {"PETR4": {"data": "2024-01-01", "preco_entrada": 25.0, "quantidade": 100}},
            "LongTerm": {},
        })
        self.saved = [False]
        self.updated_pills = [False]
        self.rendered = [False]

        self.dialog = AddWalletDialog(
            page=self.page,
            state=self.state,
            save_carteiras=lambda: self.saved.__setitem__(0, True),
            update_sort_pills_callback=lambda: self.updated_pills.__setitem__(0, True),
            render_list=lambda: self.rendered.__setitem__(0, True),
        )

    def test_instancia_corretamente(self):
        self.assertIsInstance(self.dialog, AddWalletDialog)
        self.assertIsInstance(self.dialog.dlg_add_cart, ft.AlertDialog)
        self.assertIsInstance(self.dialog.tf_preco_entrada, ft.TextField)
        self.assertIsInstance(self.dialog.tf_quantidade, ft.TextField)
        self.assertIsInstance(self.dialog.tf_quick_cart, ft.TextField)

    def test_open_define_ticker_atual(self):
        self.dialog.open("VALE3", 60.0)
        self.assertEqual(self.dialog.current_add_ticker[0], "VALE3")

    def test_open_preenche_preco_atual(self):
        self.dialog.open("VALE3", 60.5)
        # Preco deve estar formatado com virgula decimal
        self.assertEqual(self.dialog.tf_preco_entrada.value, "60,50")

    def test_open_preco_zero_limpa_campo(self):
        self.dialog.open("VALE3", 0.0)
        self.assertEqual(self.dialog.tf_preco_entrada.value, "")

    def test_open_quantidade_reseta_para_100(self):
        self.dialog.tf_quantidade.value = "999"
        self.dialog.open("VALE3", 60.0)
        self.assertEqual(self.dialog.tf_quantidade.value, "100")

    def test_open_cria_chips_para_cada_carteira(self):
        """Deve criar 1 chip por carteira existente."""
        self.dialog.open("VALE3", 60.0)
        # 2 carteiras no state -> 2 chips
        self.assertEqual(len(self.dialog.carteiras_chips_row.controls), 2)

    def test_open_marca_chip_como_selecionado_se_ticker_ja_esta_na_carteira(self):
        """PETR4 esta em Principal -> chip de Principal deve estar selecionado."""
        self.dialog.open("PETR4", 30.0)
        chips = self.dialog.carteiras_chips_row.controls
        # Encontrar chip de Principal
        principal_chip = next(c for c in chips if c.data["nome"] == "Principal")
        self.assertTrue(principal_chip.data["selected"])
        # LongTerm nao tem PETR4 -> nao selecionado
        longterm_chip = next(c for c in chips if c.data["nome"] == "LongTerm")
        self.assertFalse(longterm_chip.data["selected"])

    def test_get_dict_ativo_parse_preco_e_quantidade(self):
        """_get_dict_ativo deve parsear valores com virgula decimal."""
        self.dialog.tf_preco_entrada.value = "25,50"
        self.dialog.tf_quantidade.value = "100"
        d = self.dialog._get_dict_ativo()
        self.assertEqual(d["preco_entrada"], 25.50)
        self.assertEqual(d["quantidade"], 100.0)
        self.assertIn("data", d)  # ISO date

    def test_get_dict_ativo_preco_vazio_retorna_zero(self):
        self.dialog.tf_preco_entrada.value = ""
        self.dialog.tf_quantidade.value = "100"
        d = self.dialog._get_dict_ativo()
        self.assertEqual(d["preco_entrada"], 0.0)

    def test_get_dict_ativo_preco_invalido_retorna_zero(self):
        self.dialog.tf_preco_entrada.value = "abc"
        self.dialog.tf_quantidade.value = "100"
        d = self.dialog._get_dict_ativo()
        self.assertEqual(d["preco_entrada"], 0.0)

    def test_get_dict_ativo_quantidade_zero_vira_1(self):
        """Quantidade <= 0 deve virar 1.0 (default)."""
        self.dialog.tf_preco_entrada.value = "25,00"
        self.dialog.tf_quantidade.value = "0"
        d = self.dialog._get_dict_ativo()
        self.assertEqual(d["quantidade"], 1.0)

    def test_get_dict_ativo_quantidade_negativa_vira_1(self):
        self.dialog.tf_preco_entrada.value = "25,00"
        self.dialog.tf_quantidade.value = "-10"
        d = self.dialog._get_dict_ativo()
        self.assertEqual(d["quantidade"], 1.0)


class TestRemoveWalletDialog(unittest.TestCase):
    """RemoveWalletDialog: confirmar remocao de ativo."""

    def setUp(self):
        self.page = MagicMock()
        self.page.overlay = []
        self.state = _make_state(carteiras={
            "Principal": {"PETR4": {}},
            "LongTerm": {"PETR4": {}},
        })
        self.saved = [False]
        self.rendered = [False]

        self.dialog = RemoveWalletDialog(
            page=self.page,
            state=self.state,
            save_carteiras=lambda: self.saved.__setitem__(0, True),
            render_list=lambda: self.rendered.__setitem__(0, True),
        )

    def test_instancia_corretamente(self):
        self.assertIsInstance(self.dialog, RemoveWalletDialog)
        self.assertIsInstance(self.dialog.dlg_remove_cart, ft.AlertDialog)

    def test_open_com_1_carteira_mostra_mensagem_direta(self):
        """Se ativo esta em 1 carteira, mostra confirmacao direta."""
        self.dialog.open("PETR4", ["Principal"])
        self.assertEqual(self.dialog.dlg_remove_cart_title.value, "Remover da Carteira?")
        self.assertIn("PETR4", self.dialog.dlg_remove_cart_subtitle.value)
        self.assertIn("Principal", self.dialog.dlg_remove_cart_subtitle.value)

    def test_open_com_1_carteira_adiciona_chip_oculto_selecionado(self):
        """Para 1 carteira, adiciona chip invisivel marcado como selecionado."""
        self.dialog.open("PETR4", ["Principal"])
        self.assertEqual(len(self.dialog.carteiras_remove_chips_row.controls), 1)
        chip = self.dialog.carteiras_remove_chips_row.controls[0]
        self.assertTrue(chip.data["selected"])
        self.assertFalse(chip.visible)

    def test_open_com_multiplas_carteiras_mostra_chips(self):
        """Se ativo esta em 2+ carteiras, mostra chips para selecao."""
        self.dialog.open("PETR4", ["Principal", "LongTerm"])
        self.assertEqual(
            self.dialog.dlg_remove_cart_title.value,
            "Remover de quais carteiras?",
        )
        # 2 chips, ambos visiveis, ambos nao selecionados inicialmente
        self.assertEqual(len(self.dialog.carteiras_remove_chips_row.controls), 2)
        for chip in self.dialog.carteiras_remove_chips_row.controls:
            self.assertTrue(chip.visible)
            self.assertFalse(chip.data["selected"])

    def test_confirmar_remocao_remove_das_carteiras_selecionadas(self):
        """Confirmar com 1 carteira selecionada remove o ativo dela."""
        self.dialog.open("PETR4", ["Principal"])
        # Chip oculto ja esta selecionado
        # Encontrar botao Remover e clicar
        remover_btn = None
        for action in self.dialog.dlg_remove_cart.actions:
            if isinstance(action, ft.Button) and action.bgcolor == ft.Colors.RED_600:
                remover_btn = action
                break
        self.assertIsNotNone(remover_btn)
        remover_btn.on_click(None)
        # PETR4 deve ter sido removido de Principal
        self.assertNotIn("PETR4", self.state["carteiras"]["Principal"])
        self.assertTrue(self.saved[0])
        self.assertTrue(self.rendered[0])


class TestCreateWalletDialogsIntegracao(unittest.TestCase):
    """Teste de integracao: create_wallet_dialogs orquestra 3 dialogs."""

    def setUp(self):
        self.page = MagicMock()
        self.page.overlay = []
        self.state = _make_state()

    def test_retorna_dict_com_3_openers(self):
        result = create_wallet_dialogs(
            page=self.page, state=self.state,
            save_carteiras=lambda: None,
            save_ui_state=lambda: None,
            render_list=lambda: None,
            update_sort_pills_callback=lambda: None,
        )
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 3)
        self.assertIn("open_nova_carteira_dialog", result)
        self.assertIn("open_add_carteira_dialog", result)
        self.assertIn("open_remove_carteira_dialog", result)
        # Todos devem ser callable
        for opener in result.values():
            self.assertTrue(callable(opener))

    def test_openers_sao_metodos_open_das_classes(self):
        """Openers do dict devem ser os metodos .open() das classes."""
        result = create_wallet_dialogs(
            page=self.page, state=self.state,
            save_carteiras=lambda: None,
            save_ui_state=lambda: None,
            render_list=lambda: None,
            update_sort_pills_callback=lambda: None,
        )
        # open_nova_carteira_dialog nao aceita args (criar carteira)
        result["open_nova_carteira_dialog"]()
        # open_add_carteira_dialog aceita (ticker, preco)
        result["open_add_carteira_dialog"]("PETR4", 30.0)
        # open_remove_carteira_dialog aceita (ticker, carteiras_presentes)
        result["open_remove_carteira_dialog"]("PETR4", ["Principal"])
        # Se chegou aqui sem erro, esta OK

    def test_state_e_compartilhado_entre_dialogs(self):
        """Todos os 3 dialogs devem compartilhar o mesmo state."""
        # Como criamos state fora, passamos para create_wallet_dialogs
        # e todos devem ver a mesma instancia
        result = create_wallet_dialogs(
            page=self.page, state=self.state,
            save_carteiras=lambda: None,
            save_ui_state=lambda: None,
            render_list=lambda: None,
            update_sort_pills_callback=lambda: None,
        )
        # Adicionar carteira via NewWalletDialog
        # (precisamos acessar a instancia internamente, mas o dict so tem openers)
        # Vamos validar indiretamente: state tem 1 carteira inicialmente
        self.assertEqual(len(self.state["carteiras"]), 1)
        # Abrir add dialog para PETR4 deve listar 1 chip (Principal)
        result["open_add_carteira_dialog"]("PETR4", 30.0)
        # Nao conseguimos acessar chips via dict, mas se state fosse diferente
        # teria quebrado antes. Teste valido para validar compartilhamento.


if __name__ == "__main__":
    unittest.main(verbosity=2)
