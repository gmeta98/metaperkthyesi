import streamlit as st
from interface import language_switch, tr
from ocr_reader.config import load_environment
from ocr_reader.ui import _password_gate, run
from translator import main

st.set_page_config(page_title="Metapërkthyesi", page_icon="📄", layout="wide")
load_environment()
language_switch()
if _password_gate():
    page = st.navigation([
        st.Page(run, title=tr("PDF → Word"), url_path="convert", default=True),
        st.Page(main, title=tr("Translate Word"), url_path="translate"),
    ])
    page.run()
