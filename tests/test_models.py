"""
Testes de regressao para core/models.py.

Validam que dataclasses tem formato compativel com dicts existentes
(to_dict/from_dict round-trip) para permitir migracao incremental sem
invalidar cache b3_evaluated_cache.json ou outros arquivos persistentes.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import (
    Ativo,
    ResultadoAvaliacao,
    PosicaoCarteira,
    Anotacao,
    MarketCapInfo,
    UIState,
    IndicadorSinal,
)


class TestAtivo(unittest.TestCase):
    def test_criacao_basica(self):
        a = Ativo(codigo="PETR4", ticker="PETR4.SA", nome="Petrobras")
        self.assertEqual(a.codigo, "PETR4")
        self.assertEqual(a.ticker, "PETR4.SA")
        self.assertEqual(a.setor, "outros")
        self.assertEqual(a.tipo, "b3")

    def test_from_raw_dict_completo(self):
        raw = {
            "codigo": "PETR4",
            "ticker": "PETR4.SA",
            "nome": "Petrobras PN",
            "setor": "petroleo",
            "tipo": "acoes",
            "volume": 1000000,
            "marketCap": 500000000000,
        }
        a = Ativo.from_raw(raw)
        self.assertEqual(a.codigo, "PETR4")
        self.assertEqual(a.nome, "Petrobras PN")
        self.assertEqual(a.setor, "petroleo")
        self.assertEqual(a.volume, 1000000.0)
        self.assertEqual(a.market_cap, 500000000000.0)

    def test_from_raw_remove_sa_e_uppercase(self):
        raw = {"ticker": "petr4.sa"}
        a = Ativo.from_raw(raw)
        self.assertEqual(a.codigo, "PETR4")
        self.assertEqual(a.ticker, "petr4.sa")  # ticker preservado
        self.assertEqual(a.nome, "PETR4")  # fallback para codigo

    def test_from_raw_com_tipo_parametro(self):
        raw = {"codigo": "HGLG11"}
        a = Ativo.from_raw(raw, tipo="fii")
        self.assertEqual(a.tipo, "fii")

    def test_from_raw_ticker_fallback(self):
        """Se ticker nao vier, gera a partir de codigo."""
        raw = {"codigo": "VALE3"}
        a = Ativo.from_raw(raw)
        self.assertEqual(a.ticker, "VALE3.SA")

    def test_to_dict_round_trip(self):
        a = Ativo(codigo="PETR4", ticker="PETR4.SA", nome="Petrobras", setor="petroleo")
        d = a.to_dict()
        a2 = Ativo(
            codigo=d["codigo"],
            ticker=d["ticker"],
            nome=d["nome"],
            setor=d["setor"],
            tipo=d.get("tipo", "b3"),
            volume=d.get("volume", 0),
            market_cap=d.get("marketCap", 0),
        )
        self.assertEqual(a, a2)


class TestResultadoAvaliacao(unittest.TestCase):
    def test_to_dict_tem_chaves_camelcase(self):
        """Cache b3_evaluated_cache.json usa camelCase (isAlta, qtdCandles).
        to_dict() DEVE produzir essas chaves para retrocompatibilidade."""
        r = ResultadoAvaliacao(
            ativo={"ticker": "PETR4.SA"},
            fechamento=30.0,
            is_alta=True,
            qtd_candles=5,
        )
        d = r.to_dict()
        # Chaves camelCase obrigatorias (compat com cache existente)
        self.assertIn("isAlta", d)
        self.assertIn("qtdCandles", d)
        self.assertIn("semFiltro", d)
        self.assertIn("semDados", d)
        self.assertIn("semConfluencia", d)
        self.assertIn("tempoTendencia", d)
        self.assertIn("marketCap", d)
        self.assertIn("volumeSpike", d)
        self.assertIn("dataVariacao", d)
        self.assertIn("variacao_7d", d)
        self.assertIn("variacao_30d", d)
        # Nao deve ter chaves snake_case
        self.assertNotIn("is_alta", d)
        self.assertNotIn("qtd_candles", d)

    def test_from_dict_aceita_camelcase(self):
        d = {
            "ativo": {"ticker": "PETR4.SA"},
            "fechamento": 30.0,
            "isAlta": True,
            "qtdCandles": 5,
            "tendencia": "alta",
            "marketCap": 500000000000,
        }
        r = ResultadoAvaliacao.from_dict(d)
        self.assertEqual(r.fechamento, 30.0)
        self.assertTrue(r.is_alta)
        self.assertEqual(r.qtd_candles, 5)
        self.assertEqual(r.tendencia, "alta")
        self.assertEqual(r.market_cap, 500000000000)

    def test_round_trip_to_dict_from_dict(self):
        """to_dict -> from_dict -> to_dict deve ser idempotente."""
        r1 = ResultadoAvaliacao(
            ativo={"ticker": "PETR4.SA", "codigo": "PETR4"},
            fechamento=30.0,
            variacao=1.5,
            variacao_7d=3.2,
            variacao_30d=-0.5,
            is_alta=True,
            indicadores=[{"nome": "MMS", "sinal": 1}],
            sem_filtro=False,
            sem_dados=False,
            sem_confluencia=False,
            qtd_candles=5,
            tempo_tendencia="3 dias",
            tendencia="alta",
            market_cap=500e9,
            volume_spike=True,
            data_variacao="2024-01-15",
        )
        d1 = r1.to_dict()
        r2 = ResultadoAvaliacao.from_dict(d1)
        d2 = r2.to_dict()
        self.assertEqual(d1, d2)

    def test_from_dict_aceita_dict_vazio(self):
        """from_dict deve ter defaults seguros."""
        r = ResultadoAvaliacao.from_dict({})
        self.assertEqual(r.fechamento, 0.0)
        self.assertTrue(r.is_alta)  # default True (igual _montar_resultado_sem_dados)
        self.assertEqual(r.qtd_candles, 0)
        self.assertEqual(r.tendencia, "neutra")


class TestPosicaoCarteira(unittest.TestCase):
    def test_criacao_basica(self):
        p = PosicaoCarteira(data="2024-01-15", preco_entrada=30.0, quantidade=100)
        self.assertEqual(p.data, "2024-01-15")
        self.assertEqual(p.preco_entrada, 30.0)
        self.assertEqual(p.quantidade, 100)

    def test_to_dict_round_trip(self):
        p = PosicaoCarteira(data="2024-01-15", preco_entrada=30.5, quantidade=100)
        d = p.to_dict()
        p2 = PosicaoCarteira.from_dict(d)
        self.assertEqual(p, p2)

    def test_from_dict_com_valores_invalidos(self):
        """from_dict deve converter strings numericas e lidar com None."""
        d = {"data": "2024-01-15", "preco_entrada": "30.5", "quantidade": None}
        p = PosicaoCarteira.from_dict(d)
        self.assertEqual(p.preco_entrada, 30.5)
        self.assertEqual(p.quantidade, 0.0)


class TestAnotacao(unittest.TestCase):
    def test_criacao_basica(self):
        a = Anotacao(texto="Nota de teste", imagens=["/path/img.png"])
        self.assertEqual(a.texto, "Nota de teste")
        self.assertEqual(len(a.imagens), 1)

    def test_to_dict_round_trip(self):
        a = Anotacao(texto="Nota", imagens=["img1.png", "img2.png"], updated_at="01/01/2024")
        d = a.to_dict()
        a2 = Anotacao.from_dict(d)
        self.assertEqual(a, a2)

    def test_from_dict_aceita_string_formato_antigo(self):
        """Anotacoes antigas eram apenas strings; from_dict deve aceitar."""
        a = Anotacao.from_dict("Nota antiga sem imagens")
        self.assertEqual(a.texto, "Nota antiga sem imagens")
        self.assertEqual(a.imagens, [])
        self.assertEqual(a.updated_at, "")

    def test_from_dict_aceita_dict_vazio(self):
        a = Anotacao.from_dict({})
        self.assertEqual(a.texto, "")
        self.assertEqual(a.imagens, [])


class TestMarketCapInfo(unittest.TestCase):
    def test_criacao_basica(self):
        mc = MarketCapInfo(
            texto="R$ 1.23B",
            categoria="Blue Chip",
            color="#2196F3",
            bg="#0D47A1",
        )
        self.assertEqual(mc.texto, "R$ 1.23B")
        self.assertEqual(mc.categoria, "Blue Chip")

    def test_to_dict_retorna_dict_compativel(self):
        """to_dict deve retornar dict com mesmas chaves que codigo antigo
        esperava: texto, categoria, color, bg."""
        mc = MarketCapInfo(texto="R$ 1.23B", categoria="Blue Chip", color="blue", bg="darkblue")
        d = mc.to_dict()
        self.assertIn("texto", d)
        self.assertIn("categoria", d)
        self.assertIn("color", d)
        self.assertIn("bg", d)

    def test_acesso_dict_compativel(self):
        """MarketCapInfo deve suportar mc_data['texto'] para retrocompat
        com cards.py durante a transicao."""
        mc = MarketCapInfo(texto="R$ 1.23B", categoria="Blue Chip", color="blue", bg="darkblue")
        # Acesso tipo dict
        self.assertEqual(mc["texto"], "R$ 1.23B")
        self.assertEqual(mc["categoria"], "Blue Chip")
        self.assertEqual(mc["color"], "blue")
        self.assertEqual(mc["bg"], "darkblue")
        # Acesso tipo atributo
        self.assertEqual(mc.texto, "R$ 1.23B")

    def test_contains_funciona(self):
        mc = MarketCapInfo(texto="X", categoria="", color="", bg="")
        self.assertIn("texto", mc)
        self.assertIn("categoria", mc)
        self.assertNotIn("invalid_key", mc)

    def test_getitem_chave_invalida_raise_keyerror(self):
        mc = MarketCapInfo(texto="X", categoria="", color="", bg="")
        with self.assertRaises(KeyError):
            _ = mc["chave_inexistente"]


class TestUIState(unittest.TestCase):
    def test_defaults_corretos(self):
        """Defaults devem bater com defaults do StateManager."""
        s = UIState()
        self.assertEqual(s.market, "todos")
        self.assertEqual(s.timeframe, "1d")
        self.assertEqual(s.sector, "all")
        self.assertEqual(s.sort, "all")
        self.assertEqual(s.search, "")
        self.assertTrue(s.mms_active)
        self.assertEqual(s.mms_periodos, [20])
        self.assertTrue(s.rsi_active)
        self.assertFalse(s.stoch_active)
        self.assertFalse(s.is_loading)

    def test_to_dict_round_trip(self):
        s = UIState(
            market="acoes",
            timeframe="1s",
            sector="petroleo",
            sort="cart_Principal",
            search="PETR",
            mms_active=False,
            mms_periodos=[50],
            rsi_active=False,
            stoch_active=True,
        )
        d = s.to_dict()
        s2 = UIState.from_dict(d)
        self.assertEqual(s, s2)

    def test_from_dict_aceita_parcial(self):
        """from_dict deve aceitar dict parcial e aplicar defaults."""
        d = {"market": "acoes", "timeframe": "1s"}
        s = UIState.from_dict(d)
        self.assertEqual(s.market, "acoes")
        self.assertEqual(s.timeframe, "1s")
        # Defaults preservados
        self.assertTrue(s.mms_active)
        self.assertEqual(s.mms_periodos, [20])


class TestIndicadorSinal(unittest.TestCase):
    def test_typed_dict_aceita_valores_validos(self):
        ind: IndicadorSinal = {"nome": "MMS", "sinal": 1}
        self.assertEqual(ind["nome"], "MMS")
        self.assertEqual(ind["sinal"], 1)

    def test_typed_dict_aceita_sinais_negativos_e_zero(self):
        for sinal in (-1, 0, 1):
            ind: IndicadorSinal = {"nome": "RSI", "sinal": sinal}
            self.assertEqual(ind["sinal"], sinal)


class TestFormatarMarketCapIntegracao(unittest.TestCase):
    """Testa que formatar_market_cap retorna MarketCapInfo
    e que o consumer (cards.py) continua funcionando via __getitem__."""

    def test_retorna_market_cap_info(self):
        from core.config import formatar_market_cap

        mc = formatar_market_cap(500e9)  # Blue Chip
        self.assertIsInstance(mc, MarketCapInfo)
        self.assertEqual(mc.categoria, "Blue Chip")
        self.assertIn("B", mc.texto)

    def test_none_retorna_nd(self):
        from core.config import formatar_market_cap

        mc = formatar_market_cap(None)
        self.assertEqual(mc.texto, "N/D")
        self.assertEqual(mc.categoria, "")

    def test_categorias(self):
        from core.config import formatar_market_cap

        # Blue Chip: >= 10 bi
        self.assertEqual(formatar_market_cap(10e9).categoria, "Blue Chip")
        # Mid Cap: >= 2 bi
        self.assertEqual(formatar_market_cap(2e9).categoria, "Mid Cap")
        # Small Cap: >= 500 mi
        self.assertEqual(formatar_market_cap(500e6).categoria, "Small Cap")
        # Micro Cap: < 500 mi
        self.assertEqual(formatar_market_cap(100e6).categoria, "Micro Cap")

    def test_acesso_dict_compativel_com_cards(self):
        """Simula exatamente como cards.py acessa mc_data."""
        from core.config import formatar_market_cap

        mc_data = formatar_market_cap(5e9)
        # Como cards.py acessa (linhas 47, 268, 272, 274, 277)
        self.assertEqual(mc_data["texto"], "R$ 5.00B")
        self.assertEqual(mc_data["categoria"], "Mid Cap")
        # color e bg devem ser acessiveis (nao testamos valor exato - depende de flet)
        _ = mc_data["color"]
        _ = mc_data["bg"]
        # Truthy check como em cards.py:268 (if mc_data["categoria"])
        self.assertTrue(mc_data["categoria"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
