import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest


class InterfaceTests(unittest.TestCase):
    def test_settings_survive_hiding_and_switching_context(self):
        app = AppTest.from_string('''
import streamlit as st
st.session_state["ui_language"] = "en"
from translator import translation_settings
page = st.radio("Test page", ["PDF", "No settings", "Word"])
if page != "No settings":
    translation_settings()
''').run()
        self.assertFalse(app.exception)
        app.selectbox(key="_translation_target_choice").set_value("Romanian").run()
        app.text_area(key="_translation_glossary").set_value("Term = translation").run()
        app.text_input(key="_translation_model").set_value("gpt-5.6-sol").run()
        app.radio[0].set_value("No settings").run()
        self.assertFalse(app.exception)
        app.radio[0].set_value("Word").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="_translation_target_choice").value, "Romanian")
        self.assertEqual(app.text_area(key="_translation_glossary").value, "Term = translation")
        self.assertEqual(app.text_input(key="_translation_model").value, "gpt-5.6-sol")

    def test_changed_language_or_upload_keeps_separate_labeled_results(self):
        app = AppTest.from_string('''
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
import streamlit as st
st.session_state["ui_language"] = "en"
from docx import Document
from translator import main
name = st.text_input("Test filename", "one.docx")
doc = Document()
doc.add_paragraph("Buongiorno")
buffer = BytesIO()
doc.save(buffer)
data = buffer.getvalue()
# Stable bytes across reruns, including DOCX timestamps.
data = st.session_state.setdefault("test_document", data)
upload = SimpleNamespace(name=name, getvalue=lambda: data)
with patch("translator.st.file_uploader", return_value=[upload]), patch("translator.get_config_value", return_value="test"), patch("translator.translate_document", return_value=(data, [])), patch("translation_jobs.deliver"):
    main()
''').run()
        self.assertFalse(app.exception)
        next(b for b in app.button if b.label == "Translate document").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("download_button")), 1)
        app.selectbox(key="_translation_target_choice").set_value("English").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("download_button")), 1)
        self.assertTrue(any("Italian → Albanian" in c.value for c in app.caption))
        next(b for b in app.button if b.label == "Translate document").click().run()
        self.assertEqual(len(app.get("download_button")), 3)
        next(x for x in app.text_input if x.label == "Test filename").set_value("two.docx").run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("download_button")), 3)


if __name__ == "__main__":
    unittest.main()
