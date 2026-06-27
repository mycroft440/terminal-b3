"""
Testes de regressao para indicadores tecnicos (MMS, RSI, Stoch).

Garantem que os calculos matematicos continuam corretos apos
qualquer refatoracao em core/indicators.py ou services/scanner.py.

API atual (a ser preservada):
  calcular_indicadores(df, mms_periodos, rsi_ativo, stoch_ativo) -> df
    Adiciona colunas MMS_X, MMS_X_Above, MMS_X_Below, RSI_14, RSI_MA,
    STOCH_K, STOCH_D ao DataFrame e retorna o df modificado.
    Retorna df original (sem modificar) se len(df) < 20.

  verificar_confluencia(df_row, mms_periodos, rsi_ativo, stoch_ativo, close_price)
    Recebe uma linha (Series) do DataFrame com indicadores ja calculados.
    Retorna (sinal_mms, sinal_rsi, sinal_stoch) onde cada sinal e:
      1  -> indicador de alta
     -1  -> indicador de baixa
      0  -> neutro
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from core.indicators import calcular_indicadores, verificar_confluencia


class TestCalcularIndicadores(unittest.TestCase):
    """Gera DataFrames sinteticos com comportamento conhecido e verifica
    que os indicadores sao calculados corretamente."""

    def _make_df(self, closes, volumes=None, n_min=25):
        n = max(len(closes), n_min)
        closes = list(closes) + [closes[-1]] * (n - len(closes)) if len(closes) < n else closes
        df = pd.DataFrame(
            {
                "Open": closes,
                "High": [c * 1.01 for c in closes],
                "Low": [c * 0.99 for c in closes],
                "Close": closes,
                "Volume": volumes if volumes else [1000] * len(closes),
            },
            index=pd.date_range("2024-01-01", periods=len(closes), freq="D"),
        )
        return df

    def test_retorna_dataframe(self):
        closes = [100 + i for i in range(30)]
        df = self._make_df(closes)
        result = calcular_indicadores(df, mms_periodos=[20], rsi_ativo=True, stoch_ativo=True)
        self.assertIsInstance(result, pd.DataFrame)

    def test_adiciona_coluna_mms(self):
        closes = [100 + i for i in range(30)]
        df = self._make_df(closes)
        result = calcular_indicadores(df, mms_periodos=[20], rsi_ativo=False, stoch_ativo=False)
        self.assertIn("MMS_20", result.columns)
        self.assertIn("MMS_20_Above", result.columns)
        self.assertIn("MMS_20_Below", result.columns)

    def test_adiciona_coluna_rsi(self):
        closes = [100 + i for i in range(30)]
        df = self._make_df(closes)
        result = calcular_indicadores(df, mms_periodos=[], rsi_ativo=True, stoch_ativo=False)
        self.assertIn("RSI_14", result.columns)
        self.assertIn("RSI_MA", result.columns)

    def test_adiciona_coluna_stoch(self):
        closes = [100 + i for i in range(30)]
        df = self._make_df(closes)
        result = calcular_indicadores(df, mms_periodos=[], rsi_ativo=False, stoch_ativo=True)
        self.assertIn("STOCH_K", result.columns)
        self.assertIn("STOCH_D", result.columns)

    def test_dataframe_curto_retorna_inalterado(self):
        """DataFrame com < 20 linhas deve retornar sem modificar."""
        df = self._make_df([100, 101, 102, 103, 104], n_min=5)
        result = calcular_indicadores(df, mms_periodos=[20], rsi_ativo=True, stoch_ativo=True)
        # Nao deve ter colunas de indicadores adicionadas
        self.assertNotIn("MMS_20", result.columns)
        self.assertNotIn("RSI_14", result.columns)

    def test_dataframe_vazio_nao_quebra(self):
        df = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
        # Nao deve levantar excecao
        result = calcular_indicadores(df, mms_periodos=[20], rsi_ativo=True, stoch_ativo=True)
        self.assertIsInstance(result, pd.DataFrame)

    def test_mms_em_tendencia_alta(self):
        """Em tendencia de alta, Close deve estar acima do MMS no final."""
        closes = [100 + i * 0.5 for i in range(30)]
        df = self._make_df(closes)
        result = calcular_indicadores(df, mms_periodos=[20], rsi_ativo=False, stoch_ativo=False)
        ultima_linha = result.iloc[-1]
        self.assertTrue(ultima_linha["MMS_20_Above"], "Close deve estar acima do MMS em tendencia de alta")

    def test_mms_em_tendencia_baixa(self):
        """Em tendencia de baixa, Close deve estar abaixo do MMS no final."""
        closes = [100 - i * 0.5 for i in range(30)]
        df = self._make_df(closes)
        result = calcular_indicadores(df, mms_periodos=[20], rsi_ativo=False, stoch_ativo=False)
        ultima_linha = result.iloc[-1]
        self.assertTrue(ultima_linha["MMS_20_Below"], "Close deve estar abaixo do MMS em tendencia de baixa")


class TestVerificarConfluencia(unittest.TestCase):
    """verificar_confluencia combina indicadores - nao pode quebrar.
    API: recebe uma linha (Series) do df com indicadores calculados,
    mais mms_periodos, rsi_ativo, stoch_ativo, close_price.
    Retorna tupla (sinal_mms, sinal_rsi, sinal_stoch)."""

    def _make_row(self, mms_above=True, rsi=60, rsi_ma=50, stoch_k=80, stoch_d=70, close=110):
        return pd.Series({
            "MMS_20_Above": mms_above,
            "MMS_20_Below": not mms_above,
            "RSI_14": rsi,
            "RSI_MA": rsi_ma,
            "STOCH_K": stoch_k,
            "STOCH_D": stoch_d,
            "Close": close,
        })

    def test_retorna_tupla_tres_sinais(self):
        row = self._make_row()
        result = verificar_confluencia(row, mms_periodos=[20], rsi_ativo=True, stoch_ativo=True, close_price=110)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 3)

    def test_tudo_alinhado_alta(self):
        row = self._make_row(mms_above=True, rsi=70, rsi_ma=50, stoch_k=85, stoch_d=70, close=110)
        sinal_mms, sinal_rsi, sinal_stoch = verificar_confluencia(
            row, mms_periodos=[20], rsi_ativo=True, stoch_ativo=True, close_price=110
        )
        self.assertEqual(sinal_mms, 1)
        self.assertEqual(sinal_rsi, 1)
        self.assertEqual(sinal_stoch, 1)

    def test_tudo_alinhado_baixa(self):
        row = self._make_row(mms_above=False, rsi=30, rsi_ma=50, stoch_k=20, stoch_d=40, close=90)
        sinal_mms, sinal_rsi, sinal_stoch = verificar_confluencia(
            row, mms_periodos=[20], rsi_ativo=True, stoch_ativo=True, close_price=90
        )
        self.assertEqual(sinal_mms, -1)
        self.assertEqual(sinal_rsi, -1)
        self.assertEqual(sinal_stoch, -1)

    def test_sem_indicadores_tudo_zero(self):
        row = self._make_row()
        sinal_mms, sinal_rsi, sinal_stoch = verificar_confluencia(
            row, mms_periodos=[], rsi_ativo=False, stoch_ativo=False, close_price=110
        )
        self.assertEqual(sinal_mms, 0)
        self.assertEqual(sinal_rsi, 0)
        self.assertEqual(sinal_stoch, 0)

    def test_rsi_neutro_quando_igual_ma(self):
        row = self._make_row(rsi=50, rsi_ma=50)
        _, sinal_rsi, _ = verificar_confluencia(
            row, mms_periodos=[], rsi_ativo=True, stoch_ativo=False, close_price=110
        )
        self.assertEqual(sinal_rsi, 0)

    def test_stoch_neutro_quando_igual_d(self):
        row = self._make_row(stoch_k=50, stoch_d=50)
        _, _, sinal_stoch = verificar_confluencia(
            row, mms_periodos=[], rsi_ativo=False, stoch_ativo=True, close_price=110
        )
        self.assertEqual(sinal_stoch, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
