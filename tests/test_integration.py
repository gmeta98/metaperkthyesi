import io
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from docx import Document
from ocr_reader import ui
from ocr_reader.config import Settings
import translator


class IntegrationTests(unittest.TestCase):
    def run_batch(self, *, translate=True, failure=False, auto=True, count=1):
        events = []
        fake_st = MagicMock()
        fake_st.session_state = {}
        options = dict(source_language="Italian", target_language="English",
                       subject_matter="Legal / judicial file", style_instruction="",
                       glossary="", user_context="", model="test-model")

        def convert(source, output, **kwargs):
            events.append("convert")
            output.mkdir(parents=True)
            path = output / "source-word.docx"
            path.write_bytes(b"converted")
            return SimpleNamespace(editable_docx=path, faithful_docx=None,
                                   layout_json=None, usage_json=None)

        def translate_file(data, **kwargs):
            events.append("translate")
            self.assertEqual(data, b"converted")
            self.assertEqual(kwargs, options)
            if failure:
                raise RuntimeError("test translation failure")
            return b"translated", []

        with tempfile.TemporaryDirectory() as temp, \
             patch.object(ui, "st", fake_st), \
             patch.object(ui, "JOBS_DIR", Path(temp)), \
             patch.object(ui.Settings, "from_environment", return_value=Settings(api_key="test")), \
             patch.object(ui, "convert_pdf", side_effect=convert), \
             patch.object(translator, "translate_document", side_effect=translate_file), \
             patch.object(ui, "auto_download_word", side_effect=lambda *a: events.append("download")) as download:
            ui._run_batch_conversion(
                documents=[ui.UploadDocument(f"file-{i}.pdf", b"pdf", 1, (1,)) for i in range(count)],
                editable=True, faithful=False, quality="Balanced", reasoning_level="Medium Reasoning",
                include_native_text=True, include_json=False, auto_download=auto,
                translation_options=options if translate else None,
            )
            fake_st.error.assert_not_called()
            self.assertEqual(list(Path(temp).iterdir()), [])
            return events, fake_st.session_state["downloads"], download.call_count, fake_st

    def test_combined_order_and_outputs(self):
        events, files, downloads, _ = self.run_batch()
        self.assertEqual(events, ["convert", "translate", "download", "download"])
        self.assertEqual([data for _, _, data in files], [b"converted", b"translated"])
        self.assertEqual(downloads, 2)

    def test_conversion_only_does_not_translate(self):
        events, files, _, _ = self.run_batch(translate=False)
        self.assertEqual(events, ["convert", "download"])
        self.assertEqual(len(files), 1)

    def test_manual_downloads(self):
        events, files, downloads, _ = self.run_batch(auto=False)
        self.assertEqual(downloads, 0)
        self.assertEqual(len(files), 2)

    def test_translation_failure_preserves_conversion(self):
        _, files, _, fake_st = self.run_batch(failure=True)
        self.assertEqual([data for _, _, data in files], [b"converted"])
        self.assertIn("Translation failed", str(fake_st.warning.call_args))

    def test_batch_zip_contains_both_outputs_with_unique_names(self):
        _, files, downloads, _ = self.run_batch(count=2)
        with zipfile.ZipFile(io.BytesIO(files[0][2])) as archive:
            self.assertEqual(len(archive.namelist()), 4)
            self.assertEqual(len(set(archive.namelist())), 4)
        self.assertEqual(downloads, 4)

    def test_standalone_translation_preserves_document(self):
        document = Document()
        document.add_paragraph("Buongiorno")
        document.add_table(rows=1, cols=1).cell(0, 0).text = "Buongiorno"
        source = io.BytesIO()
        document.save(source)
        with patch.object(translator, "st", MagicMock()), \
             patch.object(translator, "translate_units", side_effect=lambda units, **kw: ["Good morning"] * len(units)):
            output, _ = translator.translate_document(source.getvalue(), source_language="Italian",
                target_language="English", subject_matter="General", style_instruction="",
                glossary="", user_context="", model="test")
        result = Document(io.BytesIO(output))
        self.assertEqual(result.paragraphs[0].text, "Good morning")
        self.assertEqual(result.tables[0].cell(0, 0).text, "Good morning")


if __name__ == "__main__":
    unittest.main()
