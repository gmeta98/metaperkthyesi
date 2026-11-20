import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import translator
import translation_jobs as jobs
from ocr_reader import ui

OPTIONS = dict(source_language="Italian", target_language="Albanian", subject_matter="Legal / judicial file",
               style_instruction="", glossary="", user_context="", model="gpt-5.6-sol")


class ReliabilityTests(unittest.TestCase):
    def test_partial_batch_survives_and_retry_only_runs_failure(self):
        batch = [jobs.new_job(f"{i}.docx", bytes([i]), OPTIONS) for i in range(3)]
        with patch.object(jobs, "st", MagicMock()), patch.object(jobs, "deliver") as delivery, \
             patch.object(translator, "translate_document", side_effect=[(b"one", []), RuntimeError("failed"), (b"three", [])]):
            jobs.run_pending(batch, True)
            self.assertEqual([j["status"] for j in batch], ["Ready", "Failed", "Ready"])
            self.assertEqual(delivery.call_count, 2)
        with patch.object(jobs, "st", MagicMock()), patch.object(jobs, "deliver") as delivery, \
             patch.object(translator, "translate_document", return_value=(b"two", [])) as translate:
            jobs.run_pending(batch, True)
            self.assertEqual(translate.call_count, 1)
            self.assertEqual(delivery.call_count, 1)
            self.assertEqual([j["output"] for j in batch], [b"one", b"two", b"three"])

    def test_pdf_retry_uses_stored_word_and_never_converts(self):
        job = jobs.new_job("sample.pdf", b"converted word", OPTIONS)
        job["status"] = "Failed"
        fake = MagicMock()
        fake.session_state = {"pdf_translation_jobs": [job], "downloads": [("Word", "sample.docx", b"converted word")]}
        fake.button.return_value = True
        with patch.object(ui, "st", fake), patch.object(ui, "convert_pdf") as convert, \
             patch.object(translator, "translate_document", return_value=(b"translated", [])) as translate:
            ui._retry_pdf_translations(False)
            convert.assert_not_called()
            translate.assert_called_once_with(b"converted word", **OPTIONS)
            self.assertIn(b"translated", [data for _, _, data in fake.session_state["downloads"]])

    def test_no_api_key_never_creates_preview_translation(self):
        with patch.object(translator, "get_configured_client", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
                translator.translate_units([], **{k: v for k, v in OPTIONS.items() if k != "user_context"},
                                           document_context="", recent_context="")

    def test_upload_and_settings_changes_have_distinct_result_identity(self):
        original = jobs.fingerprint([("one.docx", b"one")], OPTIONS)
        self.assertNotEqual(original, jobs.fingerprint([("two.docx", b"one")], OPTIONS))
        self.assertNotEqual(original, jobs.fingerprint([("one.docx", b"two")], OPTIONS))
        self.assertNotEqual(original, jobs.fingerprint([("one.docx", b"one")], dict(OPTIONS, target_language="English")))

    def test_existing_languages_remain_first(self):
        self.assertEqual(translator.LANGUAGES[:8], ["Albanian", "Italian", "English", "French", "German", "Spanish", "Portuguese", "Greek"])
        self.assertEqual(translator.LANGUAGES[-1], "Custom")

    def test_browser_download_failure_preserves_result(self):
        job = jobs.new_job("one.docx", b"one", OPTIONS)
        job.update(status="Ready", output=b"translated")
        with patch("ocr_reader.downloads.auto_download_word", side_effect=RuntimeError("browser")), patch.object(jobs, "st", MagicMock()):
            jobs.deliver(job)
        self.assertEqual(job["output"], b"translated")


if __name__ == "__main__":
    unittest.main()
