import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from streamlit.runtime.scriptrunner import RerunException, StopException
from streamlit.runtime.scriptrunner_utils.script_requests import RerunData
from streamlit.testing.v1 import AppTest
import translator
import translation_jobs as jobs
from ocr_reader import ui
from ocr_reader.config import Settings

OPTIONS = dict(source_language="Italian", target_language="Albanian", subject_matter="Legal / judicial file",
               style_instruction="", glossary="", user_context="", model="test-model")


class ResponseValidationTests(unittest.TestCase):
    def setUp(self):
        self.units = [translator.TextUnit("body", "Source text", 0)]

    def test_rejects_empty_duplicate_missing_unknown_and_invalid_entries(self):
        invalid = [[], [{"id": 0, "text": ""}], [{"id": 0, "text": " \n\t "}],
                   [{"id": 0, "text": None}], [{"id": False, "text": "text"}],
                   [{"id": "0", "text": "text"}], [{"id": 2, "text": "text"}],
                   [{"id": 0, "text": "one"}, {"id": 0, "text": "two"}],
                   [{"id": 0, "text": "one"}, {"id": 8, "text": "extra"}],
                   [None], ["text"]]
        for entries in invalid:
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                translator.parse_translation_response(json.dumps({"translations": entries}), self.units)
        for payload in ('[]', 'null', '1', '{}', '{"translations":{}}', 'not JSON'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                translator.parse_translation_response(payload, self.units)

    def test_accepts_complete_response_and_restores_original_item_order(self):
        units = self.units + [translator.TextUnit("table", "Other", 4)]
        response = '```json\n{"translations":[{"id":4,"text":"Second"},{"id":0,"text":"First"}]}\n```'
        self.assertEqual(translator.parse_translation_response(response, units), ["First", "Second"])

    def test_invalid_response_is_retried_before_text_is_applied(self):
        client = MagicMock()
        client.responses.create.side_effect = [
            SimpleNamespace(output_text='{"translations":[{"id":0,"text":""}]}'),
            SimpleNamespace(output_text='{"translations":[{"id":0,"text":"Përkthimi"}]}')]
        with patch.object(translator, "get_configured_client", return_value=client):
            result = translator.translate_units(self.units,
                **{k: v for k, v in OPTIONS.items() if k != "user_context"},
                document_context="", recent_context="")
        self.assertEqual(result, ["Përkthimi"])
        self.assertEqual(client.responses.create.call_count, 2)

    def test_repeated_invalid_response_does_not_create_download(self):
        client = MagicMock()
        client.responses.create.return_value = SimpleNamespace(output_text='{"translations":[{"id":0,"text":""}]}')
        with patch.object(translator, "get_configured_client", return_value=client), self.assertRaises(ValueError):
            translator.translate_units(self.units, **{k: v for k, v in OPTIONS.items() if k != "user_context"},
                document_context="", recent_context="")
        self.assertEqual(client.responses.create.call_count, translator.MAX_TRANSLATION_ATTEMPTS)


class RecoveryTests(unittest.TestCase):
    def test_rerun_and_stop_keep_source_and_make_translation_retryable(self):
        for signal in (RerunException(RerunData()), StopException()):
            job = jobs.new_job("one.docx", b"source", OPTIONS)
            with patch.object(translator, "translate_document", side_effect=signal), self.assertRaises(type(signal)):
                jobs.execute(job)
            self.assertEqual(job["status"], "Interrupted")
            self.assertEqual(job["source"], b"source")
            self.assertTrue(jobs.unfinished(job))
            with patch.object(translator, "translate_document", return_value=(b"translated", [])):
                self.assertTrue(jobs.execute(job))

    def test_pdf_resume_skips_completed_conversion(self):
        fake = MagicMock()
        fake.session_state = {}
        converted = []
        interrupted = False

        def convert(source, output, **kwargs):
            nonlocal interrupted
            converted.append(source.name)
            if source.name == "second.pdf" and not interrupted:
                interrupted = True
                raise RerunException(RerunData())
            output.mkdir(parents=True)
            word = output / (source.stem + ".docx")
            word.write_bytes(source.stem.encode())
            return SimpleNamespace(editable_docx=word, faithful_docx=None, layout_json=None, usage_json=None)

        with tempfile.TemporaryDirectory() as folder, patch.object(ui, "st", fake), \
             patch.object(ui, "JOBS_DIR", Path(folder)), patch.object(ui, "convert_pdf", side_effect=convert), \
             patch.object(ui.Settings, "from_environment", return_value=Settings(api_key="test")):
            documents = [ui.UploadDocument(name, b"pdf", 1, (1,)) for name in ("first.pdf", "second.pdf")]
            with self.assertRaises(RerunException):
                ui._run_batch_conversion(documents=documents, editable=True, faithful=False, quality="Balanced",
                    reasoning_level="Medium Reasoning", include_native_text=True, include_json=False, auto_download=False)
            self.assertEqual(fake.session_state["pdf_conversion_queue"]["next_index"], 1)
            self.assertEqual(fake.session_state["downloads"][0][2], b"first")
            queue = fake.session_state["pdf_conversion_queue"]
            ui._run_batch_conversion(documents=queue["documents"], auto_download=False, _resume=True, **queue["options"])
            self.assertNotIn("pdf_conversion_queue", fake.session_state)
            self.assertEqual(converted, ["first.pdf", "second.pdf", "second.pdf"])
            with zipfile.ZipFile(io.BytesIO(fake.session_state["downloads"][0][2])) as archive:
                self.assertEqual(set(archive.namelist()), {"01-first.docx", "02-second.docx"})

    def test_interrupted_pdf_translation_retries_without_conversion(self):
        fake = MagicMock()
        fake.session_state = {}
        fake.button.return_value = True

        def convert(source, output, **kwargs):
            output.mkdir(parents=True)
            word = output / "converted.docx"
            word.write_bytes(b"converted")
            return SimpleNamespace(editable_docx=word, faithful_docx=None, layout_json=None, usage_json=None)

        with tempfile.TemporaryDirectory() as folder, patch.object(ui, "st", fake), \
             patch.object(ui, "JOBS_DIR", Path(folder)), patch.object(ui, "convert_pdf", side_effect=convert) as conversion, \
             patch.object(ui.Settings, "from_environment", return_value=Settings(api_key="test")), \
             patch.object(translator, "translation_configuration_error", return_value=""):
            with patch.object(translator, "translate_document", side_effect=RerunException(RerunData())), self.assertRaises(RerunException):
                ui._run_batch_conversion(documents=[ui.UploadDocument("source.pdf", b"pdf", 1, (1,))],
                    editable=True, faithful=False, quality="Balanced", reasoning_level="Medium Reasoning",
                    include_native_text=True, include_json=False, auto_download=False, translation_options=OPTIONS)
            self.assertNotIn("pdf_conversion_queue", fake.session_state)
            self.assertEqual(fake.session_state["pdf_translation_jobs"][0]["status"], "Interrupted")
            with patch.object(translator, "translate_document", return_value=(b"translated", [])):
                ui._retry_pdf_translations(False)
            self.assertEqual(conversion.call_count, 1)
            self.assertTrue(any(data == b"translated" for _, _, data in fake.session_state["downloads"]))

    def test_zip_preserves_results_with_duplicate_filenames(self):
        data = ui._build_download_zip([("a", "same.docx", b"a"), ("b", "same.docx", b"b")])
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertEqual(len(set(archive.namelist())), 2)
            self.assertEqual({archive.read(name) for name in archive.namelist()}, {b"a", b"b"})


class SavedResultsTests(unittest.TestCase):
    def test_both_pages_keep_results_without_uploads_until_explicitly_cleared(self):
        app = AppTest.from_string('''
import streamlit as st
from unittest.mock import patch
from translator import main
from ocr_reader.ui import run
from translation_jobs import new_job
st.session_state["ui_language"] = "en"
if "seeded" not in st.session_state:
    job = new_job("old.docx", b"source", dict(source_language="Italian", target_language="Albanian", model="test"))
    job.update(status="Ready", output=b"translation", pairs=[])
    st.session_state["translation_jobs"] = [job]
    st.session_state["downloads"] = [("Download Word", "old.docx", b"conversion")]
    st.session_state["seeded"] = True
page = st.radio("Test page", ["Word", "PDF"])
with patch("streamlit.file_uploader", return_value=[]):
    main() if page == "Word" else run()
''').run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("download_button")), 1)
        app.radio[0].set_value("PDF").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("download_button")), 1)
        app.radio[0].set_value("Word").run()
        self.assertEqual(len(app.get("download_button")), 1)
        app.button(key="clear_translation_results").click().run()
        self.assertEqual(len(app.get("download_button")), 0)
        app.radio[0].set_value("PDF").run()
        self.assertEqual(len(app.get("download_button")), 1)
        app.button(key="clear_pdf_results").click().run()
        self.assertEqual(len(app.get("download_button")), 0)
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
