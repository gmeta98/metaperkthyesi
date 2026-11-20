# Metapërkthyesi

One Streamlit app with one login and two pages, combining the existing OCR and Word translation apps.

The interface opens in Albanian. Use **Gjuha e faqes / Interface language → Shqip / English** in the sidebar to switch languages, including before login. This changes labels and instructions only: document languages, translation settings, file contents, and completed results stay unchanged. The language choice lasts for the browser session. Technical translation settings are collapsed by default. Streamlit's built-in upload buttons may still appear in English; Albanian instructions explain how to use them.

- **PDF → Word:** choose Convert only or Convert & Translate. For the combined workflow, select editable Word and configure translation in the sidebar. Translation starts immediately after each PDF conversion, without a review step.
- **Translate Word:** upload existing DOCX files for standalone translation. Existing translation settings and document handling are retained.
- **Automatic downloads:** enabled by default on both pages. In the combined workflow, the converted, translated, and optional exact-look Word files download when that document finishes. Manual buttons and the batch ZIP remain available. Browsers may require permission for multiple downloads.
- A translation failure retains the converted outputs and offers **Retry failed translations**, using the stored Word file without running OCR again.
- Standalone translation saves each completed result immediately, continues after individual failures, and offers downloads for the successful files and a ZIP. Retry processes failed files only.
- Completed outputs appear in separate saved-results sections with their original filenames and translation languages. Changing uploads, settings, or pages does not remove them. Use the page's **Clear saved results** button or sign out to remove them.
- Interrupted translations remain retryable, including documents still waiting in a batch. **Continue conversion** resumes an interrupted PDF batch, skipping PDFs already converted. A partly converted PDF starts conversion again; a translated document that was interrupted is translated again from its retained Word source.
- Translation responses must contain exactly one non-empty translation for every expected text item. Missing, duplicate, unknown, blank, and malformed entries trigger the existing repair attempt; if that also fails, no translated Word file is marked ready.
- A configured API key and model are required for translation. Missing credentials never produce simulated translations.
- Translation settings are shared between the two pages for the current browser session. Signing out clears session data.
- Progress distinguishes conversion, translation, and ready files. **OCR usage** excludes translation usage and cost.
- The original language order is preserved: Albanian, Italian, English, French, German, Spanish, Portuguese, and Greek. Additional choices are Romanian, Turkish, Serbian, Croatian, Bosnian, Macedonian, Montenegrin, Bulgarian, Dutch, Polish, Ukrainian, Russian, and Arabic. Custom languages remain available.

## Run locally

Use Python 3.12 or newer. Install requirements and start the app:

```sh
python3 -m pip install -r requirements.txt
python3 -m streamlit run app.py
```

Configure APP_PASSWORD, OPENAI_API_KEY, and OPENAI_MODEL in a local .env or Streamlit Secrets. The model is the translation model; OCR retains its existing model selector. No credentials were copied from the original projects.

For Streamlit Community Cloud, use app.py as the entrypoint and add the same three settings in Secrets.

Conversion and translation use the original processing code. The integration adds shared navigation/login, the automatic handoff, and translation downloads. Original source folders are unchanged.

## Local checks

```sh
python3 -m unittest discover -s tests -v
```

These checks use simulated API responses; live translation quality and actual browser download permissions must be checked in the deployed app. Saved results and recovery data are kept in the current Streamlit session, not permanent storage. A server restart or browser refresh that starts a new session can remove them; download completed files before leaving.
