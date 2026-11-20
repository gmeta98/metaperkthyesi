import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from streamlit.testing.v1 import AppTest


class LanguageTests(unittest.TestCase):
    def test_login_defaults_to_albanian_and_switches_to_english(self):
        with patch.dict(os.environ, {"APP_PASSWORD": "test-password"}):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.radio(key="ui_language").value, "sq")
            self.assertEqual(app.text_input[0].label, "Fjalëkalimi")
            app.radio(key="ui_language").set_value("en").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.text_input[0].label, "Site password")
            app.text_input[0].set_value("test-password")
            next(b for b in app.button if b.label == "Open LayoutLens").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.get("file_uploader")), 1)
            next(b for b in app.button if b.label == "Sign out").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.radio(key="ui_language").value, "en")
            self.assertEqual(len(app.get("file_uploader")), 0)

    def test_ui_switch_preserves_translation_values_and_results(self):
        app = AppTest.from_string('''
import streamlit as st
from interface import language_switch
from translator import translation_settings
language_switch()
options = translation_settings()
st.session_state["test_options"] = options
st.session_state.setdefault("downloads", [("result", "test.docx", b"test")])
''').run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="_translation_target_choice").label, "Gjuha e përkthimit")
        original = dict(app.session_state["test_options"])
        self.assertTrue(app.text_area(key="_translation_style_instruction").value.startswith("Përkthim formal"))
        app.radio(key="ui_language").set_value("en").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["test_options"], original)
        self.assertEqual(app.session_state["downloads"][0][2], b"test")
        app.selectbox(key="_translation_target_choice").set_value("Romanian").run()
        app.radio(key="ui_language").set_value("sq").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.selectbox(key="_translation_target_choice").value, "Romanian")
        self.assertEqual(app.session_state["test_options"]["target_language"], "Romanian")

    def test_conversion_choices_survive_language_change(self):
        app = AppTest.from_string('''
from interface import control, language_switch
language_switch()
control("radio", "Workflow", ["Convert only", "Convert & Translate"])
control("checkbox", "Automatically download completed Word files", value=True)
''').run()
        app.radio(key="_conversion_Workflow").set_value("Convert & Translate").run()
        app.checkbox[0].uncheck().run()
        app.radio(key="ui_language").set_value("en").run()
        self.assertFalse(app.exception)
        self.assertEqual(app.radio(key="_conversion_Workflow").value, "Convert & Translate")
        self.assertFalse(app.checkbox[0].value)


if __name__ == "__main__":
    unittest.main()
