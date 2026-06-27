"""
Testes de regressao para StateManager.

Garantem que o estado da UI, carteiras, ocultos, anotacoes e o novo
cache de ativos avaliados continuam funcionando apos refatoracoes.

Cada teste roda em diretorio temporario isolado (via subclass que
sobrescreve os paths) para nao poluir dados/ reais do projeto.
"""
import unittest
import sys
import os
import json
import tempfile
import shutil
import copy

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_isolated_state_manager(test_dir):
    """Cria StateManager apontando para test_dir isolado.
    O StateManager original calcula BASE_DIR pelo __file__, entao precisamos
    sobrescrever os atributos de path antes do load_all()."""
    import threading
    from ui.state_manager import StateManager

    class _TestStateManager(StateManager):
        def __init__(self, base_dir):
            # Lock reentrante (igual ao StateManager.__init__)
            self._save_lock = threading.RLock()
            self.BASE_DIR = base_dir
            self.DADOS_DIR = os.path.join(base_dir, "dados")
            self.CARTEIRAS_DIR = os.path.join(self.DADOS_DIR, "carteiras")
            self.ANOTACOES_DIR = os.path.join(self.DADOS_DIR, "anotacoes")
            self.ASSETS_DIR = os.path.join(base_dir, "assets")
            for d in [self.DADOS_DIR, self.CARTEIRAS_DIR, self.ANOTACOES_DIR]:
                os.makedirs(d, exist_ok=True)
            self.UI_STATE_FILE = os.path.join(self.DADOS_DIR, "b3_ui_state.json")
            self.CARTEIRAS_FILE = os.path.join(
                self.CARTEIRAS_DIR, "b3_carteiras.json"
            )
            self.FAV_FILE = "b3_favoritos.json"
            self.OCULTOS_FILE = os.path.join(self.DADOS_DIR, "b3_ocultos.json")
            self.NOTES_FILE = os.path.join(self.ANOTACOES_DIR, "b3_anotacoes.json")
            self.IMAGES_DIR = os.path.join(self.ANOTACOES_DIR, "imgs")
            if not os.path.exists(self.IMAGES_DIR):
                os.makedirs(self.IMAGES_DIR, exist_ok=True)
            self.EVALUATED_CACHE_FILE = os.path.join(
                self.DADOS_DIR, "b3_evaluated_cache.json"
            )
            self.default_state = {
                "market": "acoes",
                "timeframe": "1d",
                "sector": "all",
                "sort": "all",
                "search": "",
                "carteiras": {"Principal": {}},
                "ocultos": [],
                "mms_active": True,
                "mms_periodos": [20],
                "rsi_active": True,
                "stoch_active": False,
                "is_loading": False,
                "anotacoes": {},
            }
            self.state = copy.deepcopy(self.default_state)
            self.load_all()

    return _TestStateManager(test_dir)


class TestStateManager(unittest.TestCase):
    """Tests isolados do StateManager sem tocar em arquivos reais."""

    def setUp(self):
        self._test_dir = tempfile.mkdtemp(prefix="b3_test_case_")

    def tearDown(self):
        shutil.rmtree(self._test_dir, ignore_errors=True)

    def test_estado_inicial_tem_defaults(self):
        sm = _make_isolated_state_manager(self._test_dir)
        state = sm.state
        self.assertEqual(state["market"], "acoes")
        self.assertEqual(state["timeframe"], "1d")
        self.assertEqual(state["sector"], "all")
        self.assertEqual(state["sort"], "all")
        self.assertEqual(state["carteiras"], {"Principal": {}})
        self.assertEqual(state["ocultos"], [])
        self.assertEqual(state["anotacoes"], {})
        self.assertTrue(state["mms_active"])
        self.assertEqual(state["mms_periodos"], [20])
        self.assertTrue(state["rsi_active"])
        self.assertFalse(state["stoch_active"])

    def test_timeframe_eh_sanitizado(self):
        sm = _make_isolated_state_manager(self._test_dir)
        with open(sm.UI_STATE_FILE, "w") as f:
            json.dump({"timeframe": "4h", "market": "acoes"}, f)
        sm2 = _make_isolated_state_manager(self._test_dir)
        self.assertEqual(sm2.state["timeframe"], "1d")

    def test_sort_invalido_eh_sanitizado(self):
        sm = _make_isolated_state_manager(self._test_dir)
        sm.state["sort"] = "cart_INEXISTENTE"
        sm.save_ui_state()
        sm2 = _make_isolated_state_manager(self._test_dir)
        self.assertEqual(sm2.state["sort"], "all")

    def test_save_e_load_carteiras_preserva_dados(self):
        sm = _make_isolated_state_manager(self._test_dir)
        sm.state["carteiras"]["Minha"] = {
            "PETR4": {"data": "2024-01-01", "preco_entrada": 30.0, "quantidade": 100}
        }
        sm.save_carteiras()
        sm2 = _make_isolated_state_manager(self._test_dir)
        self.assertIn("Minha", sm2.state["carteiras"])
        self.assertEqual(
            sm2.state["carteiras"]["Minha"]["PETR4"]["preco_entrada"], 30.0
        )

    def test_save_e_load_ocultos(self):
        sm = _make_isolated_state_manager(self._test_dir)
        sm.state["ocultos"] = ["PETR4", "VALE3"]
        sm.save_ocultos()
        sm2 = _make_isolated_state_manager(self._test_dir)
        self.assertEqual(sm2.state["ocultos"], ["PETR4", "VALE3"])

    def test_save_e_load_anotacoes(self):
        sm = _make_isolated_state_manager(self._test_dir)
        sm.state["anotacoes"]["PETR4"] = {
            "texto": "Nota de teste",
            "imagens": ["/caminho/img.png"],
            "updated_at": "01/01/2024",
        }
        sm.save_notes()
        sm2 = _make_isolated_state_manager(self._test_dir)
        nota = sm2.state["anotacoes"]["PETR4"]
        self.assertEqual(nota["texto"], "Nota de teste")
        self.assertEqual(nota["imagens"], ["/caminho/img.png"])

    def test_migracao_anotacao_string_para_dict(self):
        sm = _make_isolated_state_manager(self._test_dir)
        with open(sm.NOTES_FILE, "w") as f:
            json.dump({"PETR4": "Nota antiga"}, f)
        sm2 = _make_isolated_state_manager(self._test_dir)
        self.assertIsInstance(sm2.state["anotacoes"]["PETR4"], dict)
        self.assertEqual(sm2.state["anotacoes"]["PETR4"]["texto"], "Nota antiga")
        self.assertEqual(sm2.state["anotacoes"]["PETR4"]["imagens"], [])

    def test_evaluated_cache_save_e_load(self):
        sm = _make_isolated_state_manager(self._test_dir)
        cache_teste = {
            "acoes_1d_True_20_True_False": [
                {"ativo": {"ticker": "PETR4.SA"}, "fechamento": 30.0},
                {"ativo": {"ticker": "VALE3.SA"}, "fechamento": 60.0},
            ],
            "fiis_1d_True_20_True_False": [
                {"ativo": {"ticker": "HGLG11.SA"}, "fechamento": 160.0},
            ],
        }
        sm.save_evaluated_cache(cache_teste)
        loaded = sm.load_evaluated_cache()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(len(loaded["acoes_1d_True_20_True_False"]), 2)

    def test_evaluated_cache_vazio_quando_inexistente(self):
        sm = _make_isolated_state_manager(self._test_dir)
        loaded = sm.load_evaluated_cache()
        self.assertEqual(loaded, {})

    def test_get_config_hash_eh_deterministico(self):
        sm = _make_isolated_state_manager(self._test_dir)
        h1 = sm.get_config_hash()
        h2 = sm.get_config_hash()
        self.assertEqual(h1, h2)

    def test_get_config_hash_muda_com_timeframe(self):
        sm = _make_isolated_state_manager(self._test_dir)
        h1 = sm.get_config_hash()
        sm.state["timeframe"] = "1s"
        h2 = sm.get_config_hash()
        self.assertNotEqual(h1, h2)

    def test_get_config_hash_muda_com_filtros(self):
        sm = _make_isolated_state_manager(self._test_dir)
        h1 = sm.get_config_hash()
        sm.state["rsi_active"] = not sm.state["rsi_active"]
        h2 = sm.get_config_hash()
        self.assertNotEqual(h1, h2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
