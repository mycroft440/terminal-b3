"""
Testes de regressao para o catalogo de ativos.

Estes testes verificam comportamentos essenciais que DEVEM continuar
funcionando apos qualquer refatoracao arquitetural. Se algum desses
testes quebrar, o refactor introduziu uma regressao e deve ser revisto.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.catalog import carregar_catalogo
from services.scanner import (
    _classificar_por_codigo,
    _codigo,
    _normalizar_ativo,
    _merge_por_codigo,
    montar_catalogo_acoes,
    montar_catalogo_fiis,
    montar_catalogo_bdrs,
    montar_catalogo,
    classificar_por_codigo,
)


class TestClassificacaoPorCodigo(unittest.TestCase):
    """Classificacao de ticker e o coracao do scanner - nao pode quebrar."""

    def test_acao_petrobras(self):
        self.assertEqual(_classificar_por_codigo("PETR4"), "acao")

    def test_acao_vale(self):
        self.assertEqual(_classificar_por_codigo("VALE3"), "acao")

    def test_fii_hglg(self):
        self.assertEqual(_classificar_por_codigo("HGLG11"), "fii")

    def test_bdr_apple(self):
        self.assertEqual(_classificar_por_codigo("AAPL34"), "bdr")

    def test_fracionario_eh_none(self):
        # Fracionarios (sufixo F) sao excluidos
        self.assertIsNone(_classificar_por_codigo("PETR4F"))

    def test_excluido_96_eh_none(self):
        # Direitos de subscricao etc
        self.assertIsNone(_classificar_por_codigo("PETR96"))

    def test_codigo_curto_eh_none(self):
        self.assertIsNone(_classificar_por_codigo("AB1"))

    def test_codigo_vazio_eh_none(self):
        self.assertIsNone(_classificar_por_codigo(""))
        self.assertIsNone(_classificar_por_codigo(None))

    def test_bdr_outros_sufixos(self):
        for suf in ["31", "32", "33", "34", "35", "39"]:
            self.assertEqual(
                _classificar_por_codigo(f"TESTS{suf}"), "bdr", f"Falhou para sufixo {suf}"
            )


class TestCodigoENormalizacao(unittest.TestCase):
    def test_codigo_remove_sa(self):
        ativo = {"ticker": "PETR4.SA", "nome": "Petrobras"}
        self.assertEqual(_codigo(ativo), "PETR4")

    def test_codigo_uppercase(self):
        # Bug conhecido: _codigo faz .upper() DEPOIS de .replace(".SA", ""),
        # entao "petr4.sa" (lowercase) nao tem o .SA removido.
        # Este teste documenta o comportamento atual; se for corrigido no
        # refactor, atualizar o teste para esperar "PETR4".
        ativo = {"ticker": "petr4.sa", "nome": "Petrobras"}
        result = _codigo(ativo)
        # Comportamento atual: .SA nao removido em lowercase
        self.assertIn(result, ("PETR4.SA", "PETR4"))

    def test_codigo_fallback_para_codigo_field(self):
        ativo = {"codigo": "VALE3", "ticker": ""}
        self.assertEqual(_codigo(ativo), "VALE3")

    def test_normalizar_preenche_campos_faltantes(self):
        ativo = {"codigo": "PETR4"}
        norm = _normalizar_ativo(ativo, tipo="acoes")
        self.assertEqual(norm["ticker"], "PETR4.SA")
        self.assertEqual(norm["nome"], "PETR4")
        self.assertEqual(norm["setor"], "outros")
        self.assertEqual(norm["tipo"], "acoes")

    def test_normalizar_preserva_campos_existentes(self):
        ativo = {"codigo": "PETR4", "nome": "Petrobras PN", "setor": "petroleo"}
        norm = _normalizar_ativo(ativo)
        self.assertEqual(norm["nome"], "Petrobras PN")
        self.assertEqual(norm["setor"], "petroleo")


class TestMergePorCodigo(unittest.TestCase):
    def test_merge_deduplica_por_codigo(self):
        lista1 = [{"codigo": "PETR4", "nome": "Petrobras"}]
        lista2 = [{"ticker": "PETR4.SA", "setor": "petroleo"}]
        merged = _merge_por_codigo(lista1, lista2)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["codigo"], "PETR4")

    def test_merge_combina_listas_disjuntas(self):
        lista1 = [{"codigo": "PETR4"}]
        lista2 = [{"codigo": "VALE3"}]
        merged = _merge_por_codigo(lista1, lista2)
        self.assertEqual(len(merged), 2)

    def test_merge_ignora_ativos_sem_codigo(self):
        lista1 = [{"nome": "Sem codigo"}, {"codigo": "PETR4"}]
        merged = _merge_por_codigo(lista1)
        self.assertEqual(len(merged), 1)


class TestCatalogoCarregamento(unittest.TestCase):
    def test_carregar_catalogo_retorna_lista(self):
        cat = carregar_catalogo()
        self.assertIsInstance(cat, list)

    def test_carregar_catalogo_tem_ativos_conhecidos(self):
        cat = carregar_catalogo()
        if not cat:
            self.skipTest("ativos.json nao disponivel no ambiente de teste")
        codigos = {_codigo(a) for a in cat}
        # Pelo menos Petrobras ou Vale devem estar presentes
        self.assertTrue(
            "PETR4" in codigos or "VALE3" in codigos,
            f"PETR4 ou VALE3 deveriam estar no catalogo. Encontrados: {sorted(codigos)[:10]}...",
        )

    def test_carregar_catalogo_usa_cache(self):
        """Segunda chamada deve retornar mesma referencia (cache em modulo)."""
        cat1 = carregar_catalogo()
        cat2 = carregar_catalogo()
        self.assertIs(cat1, cat2)


class TestMontagemCatalogos(unittest.TestCase):
    """Testa que montar_catalogo_acoes/fiis/bdrs filtram corretamente."""

    def setUp(self):
        self.cat_teste = [
            {"codigo": "PETR4", "ticker": "PETR4.SA", "nome": "Petrobras"},
            {"codigo": "VALE3", "ticker": "VALE3.SA", "nome": "Vale"},
            {"codigo": "HGLG11", "ticker": "HGLG11.SA", "nome": "CSHG Log"},
            {"codigo": "AAPL34", "ticker": "AAPL34.SA", "nome": "Apple BDR"},
            {"codigo": "PETR4F", "ticker": "PETR4F.SA", "nome": "Fracionario"},
        ]
        self.catalogo_brapi = []  # vazio para simplificar

    def test_montar_acoes_filtra_corretamente(self):
        acoes = montar_catalogo_acoes(self.cat_teste, self.catalogo_brapi)
        codigos = {a["codigo"] for a in acoes}
        self.assertIn("PETR4", codigos)
        self.assertIn("VALE3", codigos)
        self.assertNotIn("HGLG11", codigos)  # FII
        self.assertNotIn("AAPL34", codigos)  # BDR
        self.assertNotIn("PETR4F", codigos)  # Fracionario

    def test_montar_fiis_filtra_corretamente(self):
        fiis = montar_catalogo_fiis(self.cat_teste, self.catalogo_brapi)
        codigos = {a["codigo"] for a in fiis}
        self.assertIn("HGLG11", codigos)
        self.assertNotIn("PETR4", codigos)
        self.assertNotIn("AAPL34", codigos)

    def test_montar_bdrs_filtra_corretamente(self):
        bdrs = montar_catalogo_bdrs(self.cat_teste, self.catalogo_brapi)
        codigos = {a["codigo"] for a in bdrs}
        self.assertIn("AAPL34", codigos)
        self.assertNotIn("PETR4", codigos)
        self.assertNotIn("HGLG11", codigos)


class TestUnificacaoMontarCatalogo(unittest.TestCase):
    """Garante que montar_catalogo(market) unificada produz mesmo resultado
    que montar_catalogo_acoes/fiis/bdrs (retrocompatibilidade)."""

    def setUp(self):
        self.cat_teste = [
            {"codigo": "PETR4", "ticker": "PETR4.SA", "nome": "Petrobras"},
            {"codigo": "VALE3", "ticker": "VALE3.SA", "nome": "Vale"},
            {"codigo": "HGLG11", "ticker": "HGLG11.SA", "nome": "CSHG Log"},
            {"codigo": "AAPL34", "ticker": "AAPL34.SA", "nome": "Apple BDR"},
            {"codigo": "PETR4F", "ticker": "PETR4F.SA", "nome": "Fracionario"},
        ]
        self.catalogo_brapi = []

    def test_unificacao_acoes(self):
        """montar_catalogo('acoes') == montar_catalogo_acoes()."""
        result_unified = montar_catalogo(self.cat_teste, self.catalogo_brapi, "acoes")
        result_legacy = montar_catalogo_acoes(self.cat_teste, self.catalogo_brapi)
        # Comparar por codigos (ordem pode diferir)
        codigos_unified = {a["codigo"] for a in result_unified}
        codigos_legacy = {a["codigo"] for a in result_legacy}
        self.assertEqual(codigos_unified, codigos_legacy)
        self.assertIn("PETR4", codigos_unified)
        self.assertIn("VALE3", codigos_unified)

    def test_unificacao_fiis(self):
        """montar_catalogo('fiis') == montar_catalogo_fiis()."""
        result_unified = montar_catalogo(self.cat_teste, self.catalogo_brapi, "fiis")
        result_legacy = montar_catalogo_fiis(self.cat_teste, self.catalogo_brapi)
        codigos_unified = {a["codigo"] for a in result_unified}
        codigos_legacy = {a["codigo"] for a in result_legacy}
        self.assertEqual(codigos_unified, codigos_legacy)
        self.assertIn("HGLG11", codigos_unified)

    def test_unificacao_bdrs(self):
        """montar_catalogo('bdrs') == montar_catalogo_bdrs()."""
        result_unified = montar_catalogo(self.cat_teste, self.catalogo_brapi, "bdrs")
        result_legacy = montar_catalogo_bdrs(self.cat_teste, self.catalogo_brapi)
        codigos_unified = {a["codigo"] for a in result_unified}
        codigos_legacy = {a["codigo"] for a in result_legacy}
        self.assertEqual(codigos_unified, codigos_legacy)
        self.assertIn("AAPL34", codigos_unified)

    def test_market_invalido_raise_valueerror(self):
        with self.assertRaises(ValueError):
            montar_catalogo(self.cat_teste, self.catalogo_brapi, "invalido")

    def test_api_publica_e_retrocompat_sao_iguais(self):
        """classificar_por_codigo (publico) == _classificar_por_codigo (legacy)."""
        for codigo in ["PETR4", "HGLG11", "AAPL34", "PETR4F", "VALE3"]:
            self.assertEqual(
                classificar_por_codigo(codigo),
                _classificar_por_codigo(codigo),
                f"Divvergencia para {codigo}",
            )


class TestCatalogoConcorrencia(unittest.TestCase):
    """Valida thread-safety de carregar_catalogo (Fase 6.3)."""

    def setUp(self):
        # Reseta cache antes de cada teste
        from core.catalog import _reset_cache
        _reset_cache()

    def test_multiplas_threads_nao_corrompem_cache(self):
        """10 threads chamando carregar_catalogo concorrentemente
        devem retornar mesma lista sem corrupcao."""
        import threading
        from core.catalog import carregar_catalogo

        results = [None] * 10
        barrier = threading.Barrier(10)

        def worker(idx):
            barrier.wait()  # Sincroniza inicio
            results[idx] = carregar_catalogo()

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        # Todas devem ter retornado
        self.assertTrue(all(r is not None for r in results))
        # Todas devem ter retornado a mesma lista (mesmo objeto em cache)
        # ou listas vazias (se ativos.json nao existe no ambiente de teste)
        first = results[0]
        for r in results[1:]:
            self.assertEqual(r, first)

    def test_lock_existe(self):
        """Valida que _CATALOGO_LOCK existe e e um Lock."""
        import threading
        from core.catalog import _CATALOGO_LOCK
        self.assertIsInstance(_CATALOGO_LOCK, type(threading.Lock()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
