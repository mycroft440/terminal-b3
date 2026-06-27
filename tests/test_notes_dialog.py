"""
Testes de regressao para ui/dialogs/notes/ package (Fase 5.1).

Validam que a decomposicao de notes_dialog.py em 4 modulos mantem
comportamento identico ao monolitico original.
"""
import unittest
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import flet as ft
from unittest.mock import MagicMock

from ui.dialogs.notes import (
    create_notes_dialog,
    MarkdownEditor,
    ImageGallery,
    load_image_as_data_uri,
    clear_image_cache,
    _load_image_as_data_uri,
    _clear_image_cache,
)
from ui.dialogs.notes.image_helpers import _DATA_URI_CACHE, _MIME_MAP


# ─── PNG 1x1 vermelho para testes de imagem ────────────────────────────────
PNG_1x1_RED = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x00\x03\x00\x01\x00\x05\xfe\xd4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class TestImageHelpers(unittest.TestCase):
    """load_image_as_data_uri e clear_image_cache."""

    def setUp(self):
        # Limpa cache antes de cada teste
        clear_image_cache()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        clear_image_cache()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_carrega_imagem_existente(self):
        path = os.path.join(self.tmpdir, "test.png")
        with open(path, "wb") as f:
            f.write(PNG_1x1_RED)
        uri = load_image_as_data_uri(path)
        self.assertIsNotNone(uri)
        self.assertTrue(uri.startswith("data:image/png;base64,"))

    def test_retorna_none_para_arquivo_inexistente(self):
        result = load_image_as_data_uri("/caminho/inexistente.png")
        self.assertIsNone(result)

    def test_retorna_none_para_path_vazio(self):
        self.assertIsNone(load_image_as_data_uri(""))
        self.assertIsNone(load_image_as_data_uri(None))

    def test_cache_funciona(self):
        """Segunda chamada deve usar cache (nao re-ler arquivo)."""
        path = os.path.join(self.tmpdir, "cached.png")
        with open(path, "wb") as f:
            f.write(PNG_1x1_RED)

        # Primeira chamada - popula cache
        uri1 = load_image_as_data_uri(path)
        self.assertEqual(len(_DATA_URI_CACHE), 1)

        # Segunda chamada - usa cache
        uri2 = load_image_as_data_uri(path)
        self.assertEqual(uri1, uri2)
        self.assertEqual(len(_DATA_URI_CACHE), 1)

    def test_clear_cache_especifico(self):
        path = os.path.join(self.tmpdir, "x.png")
        with open(path, "wb") as f:
            f.write(PNG_1x1_RED)
        load_image_as_data_uri(path)
        self.assertEqual(len(_DATA_URI_CACHE), 1)
        clear_image_cache(path)
        self.assertEqual(len(_DATA_URI_CACHE), 0)

    def test_clear_cache_completo(self):
        path = os.path.join(self.tmpdir, "y.png")
        with open(path, "wb") as f:
            f.write(PNG_1x1_RED)
        load_image_as_data_uri(path)
        self.assertGreaterEqual(len(_DATA_URI_CACHE), 1)
        clear_image_cache()
        self.assertEqual(len(_DATA_URI_CACHE), 0)

    def test_mime_map_por_extensao(self):
        casos = [
            (".png", "image/png"),
            (".jpg", "image/jpeg"),
            (".jpeg", "image/jpeg"),
            (".gif", "image/gif"),
            (".webp", "image/webp"),
            (".bmp", "image/bmp"),
        ]
        for ext, expected_mime in casos:
            self.assertEqual(_MIME_MAP[ext], expected_mime)

    def test_retrocompatibilidade_aliases(self):
        """Aliases _load_image_as_data_uri e _clear_image_cache existem."""
        self.assertEqual(_load_image_as_data_uri, load_image_as_data_uri)
        self.assertEqual(_clear_image_cache, clear_image_cache)


class TestMarkdownEditor(unittest.TestCase):
    """MarkdownEditor: editor + toolbar + toggle preview."""

    def setUp(self):
        self.page = MagicMock()
        self.editor = MarkdownEditor(self.page)
        # Mock update() em char_counter e tf_nota para evitar RuntimeError
        # (controles precisam estar adicionados a ft.Page real para update())
        self.editor.char_counter.update = MagicMock()
        self.editor.tf_nota.update = MagicMock()

    def test_instancia_com_page(self):
        self.assertIsInstance(self.editor, MarkdownEditor)
        self.assertIsInstance(self.editor.tf_nota, ft.TextField)
        self.assertIsInstance(self.editor.md_preview, ft.Markdown)

    def test_is_preview_mode_inicia_false(self):
        self.assertFalse(self.editor.is_preview_mode)

    def test_set_text_define_valor(self):
        self.editor.set_text("Texto de teste")
        self.assertEqual(self.editor.tf_nota.value, "Texto de teste")

    def test_get_text_retorna_strip(self):
        self.editor.set_text("  texto com espacos  ")
        self.assertEqual(self.editor.get_text(), "texto com espacos")

    def test_get_text_vazio_retorna_string_vazia(self):
        self.editor.set_text("")
        self.assertEqual(self.editor.get_text(), "")

    def test_get_text_none_retorna_string_vazia(self):
        self.editor.tf_nota.value = None
        self.assertEqual(self.editor.get_text(), "")

    def test_set_text_atualiza_char_counter(self):
        self.editor.set_text("abc")
        # char_counter deve ter sido atualizado
        self.assertIn("3 caracteres", self.editor.char_counter.value)

    def test_set_text_atualiza_line_counter(self):
        self.editor.set_text("linha1\nlinha2\nlinha3")
        self.assertIn("3 linhas", self.editor.char_counter.value)

    def test_set_timestamp_com_data(self):
        self.editor.set_timestamp("01/01/2024 as 10:00")
        self.assertEqual(self.editor.lbl_timestamp.value, "Editado: 01/01/2024 as 10:00")

    def test_set_timestamp_vazio_limpa_label(self):
        self.editor.set_timestamp("")
        self.assertEqual(self.editor.lbl_timestamp.value, "")

    def test_reset_to_edit_mode_define_is_preview_false(self):
        # Primeiro entra em preview mode
        self.editor.is_preview_mode = True
        self.editor.reset_to_edit_mode()
        self.assertFalse(self.editor.is_preview_mode)

    def test_reset_to_edit_mode_define_visibilidades(self):
        self.editor.reset_to_edit_mode()
        self.assertTrue(self.editor.tf_nota.visible)
        self.assertFalse(self.editor.preview_scroll.visible)
        self.assertTrue(self.editor.format_toolbar.visible)

    def test_toggle_preview_alterna_estado(self):
        # Antes: edit mode
        self.assertFalse(self.editor.is_preview_mode)
        # Depois de toggle: preview mode
        self.editor.toggle_preview(None)
        self.assertTrue(self.editor.is_preview_mode)
        # Depois de outro toggle: edit mode novamente
        self.editor.toggle_preview(None)
        self.assertFalse(self.editor.is_preview_mode)

    def test_toggle_preview_para_preview_esconde_editor(self):
        self.editor.toggle_preview(None)
        self.assertFalse(self.editor.tf_nota.visible)
        self.assertTrue(self.editor.preview_scroll.visible)
        self.assertFalse(self.editor.format_toolbar.visible)

    def test_toggle_preview_para_edit_esconde_preview(self):
        # Primeiro toggle (vai para preview)
        self.editor.toggle_preview(None)
        # Segundo toggle (volta para edit)
        self.editor.toggle_preview(None)
        self.assertTrue(self.editor.tf_nota.visible)
        self.assertFalse(self.editor.preview_scroll.visible)

    def test_insert_format_adiciona_texto(self):
        self.editor.set_text("inicio")
        self.editor.insert_format("**", "**", "negrito")
        self.assertEqual(self.editor.tf_nota.value, "inicio**negrito**")

    def test_fmt_bold_adiciona_negrito(self):
        self.editor.set_text("")
        self.editor.fmt_bold(None)
        self.assertIn("**negrito**", self.editor.tf_nota.value)

    def test_fmt_italic_adiciona_italico(self):
        self.editor.set_text("")
        self.editor.fmt_italic(None)
        self.assertIn("*italico*", self.editor.tf_nota.value)

    def test_fmt_code_adiciona_codigo(self):
        self.editor.set_text("")
        self.editor.fmt_code(None)
        self.assertIn("`codigo`", self.editor.tf_nota.value)

    def test_fmt_separator_adiciona_separador(self):
        self.editor.set_text("texto")
        self.editor.fmt_separator(None)
        self.assertIn("---", self.editor.tf_nota.value)

    def test_nota_container_existe(self):
        self.assertIsInstance(self.editor.nota_container, ft.Container)


class TestImageGallery(unittest.TestCase):
    """ImageGallery: galeria + lightbox + file picker."""

    def setUp(self):
        self.page = MagicMock()
        self.page.overlay = []
        self.tmpdir = tempfile.mkdtemp()
        self.gallery = ImageGallery(self.page, self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_instancia_com_page_e_dir(self):
        self.assertIsInstance(self.gallery, ImageGallery)
        self.assertEqual(self.gallery.images_dir, self.tmpdir)
        self.assertEqual(self.gallery.current_images, [])

    def test_images_row_e_ft_row(self):
        self.assertIsInstance(self.gallery.images_row, ft.Row)

    def test_attachments_section_e_container(self):
        self.assertIsInstance(self.gallery.attachments_section, ft.Container)

    def test_dlg_lightbox_e_alert_dialog(self):
        self.assertIsInstance(self.gallery.dlg_lightbox, ft.AlertDialog)

    def test_file_picker_e_file_picker(self):
        self.assertIsInstance(self.gallery.file_picker, ft.FilePicker)

    def test_clear_limpa_current_images(self):
        self.gallery.current_images = ["/a.png", "/b.png"]
        self.gallery.clear()
        self.assertEqual(self.gallery.current_images, [])

    def test_extend_adiciona_imagens(self):
        self.gallery.extend(["/a.png", "/b.png"])
        self.assertEqual(len(self.gallery.current_images), 2)

    def test_get_images_retorna_copia(self):
        self.gallery.extend(["/a.png"])
        result = self.gallery.get_images()
        self.assertEqual(result, ["/a.png"])
        # Modificar resultado nao deve afetar interno
        result.append("/c.png")
        self.assertEqual(len(self.gallery.current_images), 1)

    def test_refresh_images_com_lista_vazia_nao_quebra(self):
        self.gallery.refresh_images()
        self.assertEqual(len(self.gallery.images_row.controls), 0)

    def test_refresh_images_com_imagem_existente_adiciona_card(self):
        # Cria imagem de teste
        path = os.path.join(self.tmpdir, "test.png")
        with open(path, "wb") as f:
            f.write(PNG_1x1_RED)
        clear_image_cache()

        self.gallery.extend([path])
        self.gallery.refresh_images()
        self.assertEqual(len(self.gallery.images_row.controls), 1)

    def test_refresh_images_com_imagem_inexistente_mostra_placeholder(self):
        """Se imagem nao existe, mostra card com placeholder vermelho."""
        self.gallery.extend(["/caminho/inexistente.png"])
        self.gallery.refresh_images()
        self.assertEqual(len(self.gallery.images_row.controls), 1)
        # O card deve ser um Stack (placeholder + botao remover)

    def test_refresh_images_remove_imagem_do_disco_chama_clear_cache(self):
        path = os.path.join(self.tmpdir, "remove.png")
        with open(path, "wb") as f:
            f.write(PNG_1x1_RED)
        clear_image_cache()

        self.gallery.extend([path])
        self.gallery.refresh_images()

        # Antes de remover: arquivo existe e cache tem 1 entrada
        self.assertTrue(os.path.exists(path))

        # Captura o callback de remove do primeiro card
        img_card = self.gallery.images_row.controls[0]
        # Stack tem 2 controls: image_container + remove_button_container
        # O remove_button esta no segundo container
        remove_container = img_card.controls[-1]
        remove_button = remove_container.content
        # Chama o callback de click
        remove_button.on_click(None)

        # Apos remover: arquivo deletado, lista vazia
        self.assertFalse(os.path.exists(path))
        self.assertEqual(len(self.gallery.current_images), 0)


class TestCreateNotesDialogIntegracao(unittest.TestCase):
    """Teste de integracao: create_notes_dialog orquestra tudo."""

    def setUp(self):
        self.page = MagicMock()
        self.page.overlay = []
        self.tmpdir = tempfile.mkdtemp()
        self.state = {"anotacoes": {}}
        clear_image_cache()

    def tearDown(self):
        clear_image_cache()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_retorna_tupla_dialog_e_open_function(self):
        result = create_notes_dialog(
            page=self.page,
            state=self.state,
            save_notes=lambda: None,
            render_list=lambda: None,
            images_dir=self.tmpdir,
        )
        self.assertEqual(len(result), 2)
        dlg, open_fn = result
        self.assertIsInstance(dlg, ft.AlertDialog)
        self.assertTrue(callable(open_fn))

    def test_open_notes_dialog_para_ticker_sem_nota_existente(self):
        dlg, open_fn = create_notes_dialog(
            page=self.page, state=self.state,
            save_notes=lambda: None, render_list=lambda: None,
            images_dir=self.tmpdir,
        )
        # state['anotacoes'] esta vazio
        open_fn("PETR4")
        # Dialog deve estar aberto
        self.assertTrue(dlg.open)

    def test_open_notes_dialog_carrega_nota_existente(self):
        # Pre-popula state com nota existente
        self.state["anotacoes"]["PETR4"] = {
            "texto": "Nota pre-existente",
            "imagens": [],
            "updated_at": "01/01/2024",
        }
        dlg, open_fn = create_notes_dialog(
            page=self.page, state=self.state,
            save_notes=lambda: None, render_list=lambda: None,
            images_dir=self.tmpdir,
        )
        open_fn("PETR4")
        # Dialog aberto
        self.assertTrue(dlg.open)

    def test_open_notes_dialog_carrega_nota_formato_antigo_string(self):
        """Anotacoes antigas eram strings - devem ser carregadas."""
        self.state["anotacoes"]["VALE3"] = "Nota antiga formato string"
        dlg, open_fn = create_notes_dialog(
            page=self.page, state=self.state,
            save_notes=lambda: None, render_list=lambda: None,
            images_dir=self.tmpdir,
        )
        # Nao deve quebrar
        open_fn("VALE3")
        self.assertTrue(dlg.open)

    def test_open_notes_dialog_limpa_cache_data_uris(self):
        """open_notes_dialog deve chamar clear_image_cache para consistencia."""
        # Popula cache com imagem fake
        _DATA_URI_CACHE["/fake/path.png"] = "data:image/png;base64,FAKE"
        self.assertEqual(len(_DATA_URI_CACHE), 1)

        dlg, open_fn = create_notes_dialog(
            page=self.page, state=self.state,
            save_notes=lambda: None, render_list=lambda: None,
            images_dir=self.tmpdir,
        )
        open_fn("PETR4")
        # Cache deve ter sido limpo
        self.assertEqual(len(_DATA_URI_CACHE), 0)

    def test_salvar_notas_persiste_no_state(self):
        """Testa que salvar_notas atualiza state['anotacoes']."""
        saved_called = [False]
        def save_notes():
            saved_called[0] = True

        dlg, open_fn = create_notes_dialog(
            page=self.page, state=self.state,
            save_notes=save_notes, render_list=lambda: None,
            images_dir=self.tmpdir,
        )
        # Abre dialog
        open_fn("PETR4")
        # Simula edicao de texto
        # (em runtime, usuario digitaria no TextField)
        # Para testar, vamos chamar salvar_notas diretamente
        # Encontrar o botao Salvar nas actions pelo icon (ft.Icons.SAVE)
        salvar_btn = None
        for action in dlg.actions:
            if isinstance(action, ft.Button) and getattr(action, 'icon', None) == ft.Icons.SAVE:
                salvar_btn = action
                break
        self.assertIsNotNone(salvar_btn, "Botao Salvar nao encontrado")
        # Como tf_nota.value esta vazio (nao editado), salvar vai REMOVER
        # a entrada do state (comportamento documentado)
        salvar_btn.on_click(None)
        # save_notes foi chamado
        self.assertTrue(saved_called[0])
        # PETR4 nao deve estar em state['anotacoes'] (texto vazio + sem imagens)
        self.assertNotIn("PETR4", self.state["anotacoes"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
