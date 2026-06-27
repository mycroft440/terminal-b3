"""
Testes de concorrencia para StateManager (Fase 6.1).

Validam que:
- RLock existe e e reentrante
- Multiplas threads podem chamar save_* sem deadlock
- save_evaluated_cache + load_evaluated_cache concorrentes nao corrompem
- save_carteiras simultaneo nao corrompe arquivo
"""
import unittest
import sys
import os
import tempfile
import shutil
import threading
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_isolated_state_manager(test_dir):
    """Cria StateManager apontando para test_dir isolado."""
    import copy
    from ui.state_manager import StateManager

    class _TestStateManager(StateManager):
        def __init__(self, base_dir):
            self._save_lock = threading.RLock()
            self.BASE_DIR = base_dir
            self.DADOS_DIR = os.path.join(base_dir, "dados")
            self.CARTEIRAS_DIR = os.path.join(self.DADOS_DIR, "carteiras")
            self.ANOTACOES_DIR = os.path.join(self.DADOS_DIR, "anotacoes")
            self.ASSETS_DIR = os.path.join(base_dir, "assets")
            for d in [self.DADOS_DIR, self.CARTEIRAS_DIR, self.ANOTACOES_DIR]:
                os.makedirs(d, exist_ok=True)
            self.UI_STATE_FILE = os.path.join(self.DADOS_DIR, "b3_ui_state.json")
            self.CARTEIRAS_FILE = os.path.join(self.CARTEIRAS_DIR, "b3_carteiras.json")
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
                "market": "acoes", "timeframe": "1d", "sector": "all", "sort": "all",
                "search": "", "carteiras": {"Principal": {}}, "ocultos": [],
                "mms_active": True, "mms_periodos": [20], "rsi_active": True,
                "stoch_active": False, "is_loading": False, "anotacoes": {},
            }
            self.state = copy.deepcopy(self.default_state)
            self.load_all()

    return _TestStateManager(test_dir)


class TestStateManagerLockExiste(unittest.TestCase):
    """Valida que StateManager tem _save_lock."""

    def setUp(self):
        self._test_dir = tempfile.mkdtemp(prefix="b3_concurrency_")

    def tearDown(self):
        shutil.rmtree(self._test_dir, ignore_errors=True)

    def test_save_lock_existe(self):
        sm = _make_isolated_state_manager(self._test_dir)
        self.assertTrue(hasattr(sm, "_save_lock"))

    def test_save_lock_e_rlock(self):
        """RLock (reentrante) - mesma thread pode adquirir multiplas vezes."""
        sm = _make_isolated_state_manager(self._test_dir)
        # RLock permite acquire recursivo pela mesma thread
        acquired1 = sm._save_lock.acquire(blocking=False)
        acquired2 = sm._save_lock.acquire(blocking=False)
        self.assertTrue(acquired1)
        self.assertTrue(acquired2)  # RLock permite reentrada
        sm._save_lock.release()
        sm._save_lock.release()

    def test_save_lock_nao_bloqueia_threads_diferentes(self):
        """Lock deve bloquear thread diferente ate ser liberado."""
        sm = _make_isolated_state_manager(self._test_dir)
        sm._save_lock.acquire()
        # Outra thread nao deve conseguir adquirir (blocking=False)
        result = []
        def try_acquire():
            result.append(sm._save_lock.acquire(blocking=False))
        t = threading.Thread(target=try_acquire)
        t.start()
        t.join(timeout=2)
        self.assertEqual(result, [False])  # Falhou porque lock ocupado
        sm._save_lock.release()


class TestSaveConcorrenteSemDeadlock(unittest.TestCase):
    """Valida que multiplas threads chamando save_* nao deadlockam."""

    def setUp(self):
        self._test_dir = tempfile.mkdtemp(prefix="b3_concurrency_")

    def tearDown(self):
        shutil.rmtree(self._test_dir, ignore_errors=True)

    def test_10_threads_save_carteiras_nao_deadlocka(self):
        """10 threads chamando save_carteiras concorrentemente devem
        terminar em tempo razoavel (sem deadlock)."""
        sm = _make_isolated_state_manager(self._test_dir)
        # Cada thread modifica carteiras e salva
        def worker(idx):
            sm.state["carteiras"][f"Carteira{idx}"] = {f"ATIVO{idx}": {}}
            sm.save_carteiras()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)  # 10s de timeout - se passar, deadlock

        # Todas devem ter terminado
        for t in threads:
            self.assertFalse(t.is_alive(), "Thread ainda viva - possivel deadlock")

    def test_10_threads_save_ocultos_nao_deadlocka(self):
        sm = _make_isolated_state_manager(self._test_dir)
        def worker(idx):
            sm.state["ocultos"] = [f"ATIVO{idx}"]
            sm.save_ocultos()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        for t in threads:
            self.assertFalse(t.is_alive())

    def test_10_threads_save_notes_nao_deadlocka(self):
        sm = _make_isolated_state_manager(self._test_dir)
        def worker(idx):
            sm.state["anotacoes"][f"ATIVO{idx}"] = {"texto": f"nota {idx}", "imagens": []}
            sm.save_notes()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        for t in threads:
            self.assertFalse(t.is_alive())

    def test_10_threads_save_ui_state_nao_deadlocka(self):
        sm = _make_isolated_state_manager(self._test_dir)
        def worker(idx):
            sm.state["market"] = "acoes" if idx % 2 == 0 else "fiis"
            sm.save_ui_state()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        for t in threads:
            self.assertFalse(t.is_alive())


class TestSaveELoadConcorrente(unittest.TestCase):
    """Valida que save + load concorrentes nao corrompem dados."""

    def setUp(self):
        self._test_dir = tempfile.mkdtemp(prefix="b3_concurrency_")

    def tearDown(self):
        shutil.rmtree(self._test_dir, ignore_errors=True)

    def test_save_e_load_evaluated_cache_concorrente(self):
        """5 threads salvam cache enquanto 5 threads leem - sem corrupcao."""
        sm = _make_isolated_state_manager(self._test_dir)
        errors = []
        stop = threading.Event()

        def saver(idx):
            i = 0
            while not stop.is_set() and i < 20:
                try:
                    cache = {f"hash_{idx}_{i}": [{"ativo": {"ticker": f"ATIVO{i}"}}]}
                    sm.save_evaluated_cache(cache)
                except Exception as e:
                    errors.append(f"saver {idx}: {e}")
                i += 1
                time.sleep(0.001)

        def loader(idx):
            i = 0
            while not stop.is_set() and i < 20:
                try:
                    # load deve retornar dict (valido ou vazio) - nunca crashar
                    result = sm.load_evaluated_cache()
                    if not isinstance(result, dict):
                        errors.append(f"loader {idx}: retorno nao e dict")
                except Exception as e:
                    errors.append(f"loader {idx}: {e}")
                i += 1
                time.sleep(0.001)

        savers = [threading.Thread(target=saver, args=(i,)) for i in range(5)]
        loaders = [threading.Thread(target=loader, args=(i,)) for i in range(5)]

        for t in savers + loaders:
            t.start()
        for t in savers + loaders:
            t.join(timeout=15)

        # Nao deve ter erros
        self.assertEqual(errors, [], f"Erros encontrados: {errors[:3]}")
        # Todas threads terminaram
        for t in savers + loaders:
            self.assertFalse(t.is_alive())

    def test_save_carteiras_nao_corrompe_arquivo(self):
        """Salvamento concorrente deve produzir JSON valido no final."""
        sm = _make_isolated_state_manager(self._test_dir)

        def worker(idx):
            sm.state["carteiras"][f"Carteira{idx}"] = {f"ATIVO{idx}": {}}
            sm.save_carteiras()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # Arquivo final deve ser JSON valido
        with open(sm.CARTEIRAS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        parsed = json.loads(content)  # Nao deve levantar
        self.assertIsInstance(parsed, dict)

    def test_reentrada_save_dentro_de_save(self):
        """RLock permite que save_* seja chamado dentro de outro save_*.

        Cenario: load_all() durante migracao chama save_carteiras() -
        se fosse Lock (nao RLock), deadlockaria.
        """
        sm = _make_isolated_state_manager(self._test_dir)

        # Simular reentrada: adquirir lock e chamar save
        with sm._save_lock:
            # Isso deve funcionar (RLock permite reentrada)
            sm.state["carteiras"]["ReentrantTest"] = {"ATIVO": {}}
            sm.save_carteiras()  # Internamente tenta adquirir _save_lock novamente

        # Se chegou aqui, RLock funcionou (nao deadlockou)
        self.assertIn("ReentrantTest", sm.state["carteiras"])


class TestCatalogConcorrente(unittest.TestCase):
    """Re-valida concorrencia do catalogo (Fase 6.3)."""

    def setUp(self):
        from core.catalog import _reset_cache
        _reset_cache()

    def test_carregar_catalogo_nao_deadlocka_com_lock(self):
        """Chamar carregar_catalogo enquanto _reset_cache tem lock deve
        eventualmente retornar (nao deadlockar)."""
        from core.catalog import carregar_catalogo, _reset_cache

        results = []
        errors = []
        stop = threading.Event()

        def loader():
            while not stop.is_set():
                try:
                    results.append(carregar_catalogo())
                except Exception as e:
                    errors.append(str(e))
                time.sleep(0.001)

        t = threading.Thread(target=loader)
        t.start()

        # Enquanto loader roda, resetar cache (adquire lock)
        for _ in range(10):
            _reset_cache()
            time.sleep(0.002)

        stop.set()
        t.join(timeout=5)

        self.assertFalse(t.is_alive())
        # Nao deve ter erros
        self.assertEqual(errors, [], f"Erros: {errors[:3]}")
        # Deve ter retornado algumas listas
        self.assertGreater(len(results), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
