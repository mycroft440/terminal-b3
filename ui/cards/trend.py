"""Computa estilo visual derivado da tendencia do ativo."""
from dataclasses import dataclass
import flet as ft


@dataclass
class TrendStyle:
    """Estilo visual derivado da tendencia do ativo.

    Atributos sao usados por _build_variation_col para colorir a coluna
    direita do card (variacao %, status, gradient).
    """
    cor_gradiente: str
    cor_texto: str
    icone_seta: str
    texto_status: str


def compute_trend_style(dado: dict) -> TrendStyle:
    """Calcula estilo visual baseado na tendencia do ativo.

    Args:
        dado: dict do ativo avaliado com chaves:
            - isAlta (bool): se tendencia atual e de alta
            - semDados (bool): se ativo nao tem dados de mercado
            - tendencia (str): 'alta', 'baixa' ou 'neutra'
            - semConfluencia (bool): se indicadores divergem

    Returns:
        TrendStyle com cor_gradiente, cor_texto, icone_seta, texto_status
    """
    is_neutro = dado.get("semDados") or dado.get("tendencia") == "neutra"
    is_sem_sinal = dado.get("semConfluencia") and not is_neutro
    is_alta = dado["isAlta"] and not is_neutro

    if is_neutro:
        return TrendStyle(
            cor_gradiente=ft.Colors.BLUE_GREY_800,
            cor_texto=ft.Colors.BLUE_GREY_400,
            icone_seta="•",
            texto_status="SEM DADOS",
        )
    if is_sem_sinal:
        return TrendStyle(
            cor_gradiente=ft.Colors.BLUE_GREY_800,
            cor_texto=ft.Colors.GREEN_400 if is_alta else ft.Colors.RED_400,
            icone_seta="▲" if is_alta else "▼",
            texto_status="DIÁRIO",
        )
    # Tendencia confirmada
    return TrendStyle(
        cor_gradiente=ft.Colors.GREEN_900 if is_alta else ft.Colors.RED_900,
        cor_texto=ft.Colors.GREEN_400 if is_alta else ft.Colors.RED_400,
        icone_seta="▲" if is_alta else "▼",
        texto_status="TEND ALTA" if is_alta else "TEND BAIXA",
    )
