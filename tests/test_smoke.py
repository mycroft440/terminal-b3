import unittest
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SmokeTest(unittest.TestCase):
    def test_imports(self):
        """Verifica que todos os modulos principais conseguem ser importados
        sem erros de sintaxe ou dependencias faltantes."""
        try:
            import main  # noqa: F401
            import ui.state_manager  # noqa: F401
            import ui.main_page  # noqa: F401
            import services.scanner  # noqa: F401
            import core.catalog  # noqa: F401

            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Smoke test failed on imports: {e}")


if __name__ == "__main__":
    unittest.main()
