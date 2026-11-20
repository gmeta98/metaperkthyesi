"""Interface translations only; document languages and prompts stay unchanged."""
import streamlit as st

SQ = {
    "Interrupted": "U ndërpre",
    "Processing was interrupted. You can retry this document.": "Përpunimi u ndërpre. Klikoni «Riprovo» për ta vazhduar këtë dokument.",
    "This document is waiting. Use Retry to continue.": "Ky dokument është në pritje. Klikoni «Riprovo» për të vazhduar.",
    "Saved translations": "Përkthimet e ruajtura",
    "Saved PDF results": "Rezultatet e ruajtura të PDF-ve",
    "Clear saved translations": "Pastro përkthimet e ruajtura",
    "Clear saved PDF results": "Pastro rezultatet e ruajtura të PDF-ve",
    "These results belong to the documents and languages shown below, even if you change the upload or settings.": "Këto rezultate u përkasin dokumenteve dhe gjuhëve të shënuara më poshtë. Ato ruhen edhe nëse ndryshoni dokumentet e ngarkuara ose cilësimet.",
    "Completed files stay available in this session until you clear them or sign out.": "Dokumentet e përfunduara ruhen gjatë kësaj seance, derisa t’i pastroni ose të dilni nga llogaria.",
    "Conversion was interrupted. {0} document(s) remain. Completed files will not be converted again.": "Kthimi në Word u ndërpre. Mbeten {0} dokumente. Dokumentet e përfunduara nuk do të kthehen nga e para.",
    "Continue conversion": "Vazhdo kthimin në Word",
    "Labels replace signature/stamp crops. Their transcribed wording stays editable. Photographs and maps remain images.": "Firmat shënohen me tekst; teksti i vulave mund të redaktohet. Fotografitë dhe hartat mbeten figura.",
    '<div class="eyebrow">GPT-5.6 document vision</div>': '<div class="eyebrow">Kthim dhe përkthim dokumentesh</div>',
    '<h1 class="hero-title">PDF to Word, without losing the page</h1>': '<h1 class="hero-title">Kthe PDF-në në Word</h1>',
    '<div class="eyebrow">Private access</div>': '<div class="eyebrow">Hyrje me fjalëkalim</div>',
    '<div class="empty-hint">Drop one or more scanned forms, certificates, reports, or mixed-layout PDFs here.</div>': '<div class="empty-hint">Ngarkoni formularë, certifikata, raporte ose dokumente të tjera PDF.</div>',
    '<div class="file-card"><span>{0}</span><span>{1} page{2} · {3:.1f} MB</span></div>': '<div class="file-card"><span>{0}</span><span>{1} faqe · {3:.1f} MB</span></div>',
    '<div class="privacy">When Translation-ready Word or JSON is selected, page images and optional embedded PDF text are sent to the OpenAI API for OCR. Exact-look-only conversions stay local.</div>': '<div class="privacy">Për të krijuar Word të redaktueshëm, përmbajtja e PDF-së dërgohet te OpenAI për lexim. Kopja me pamjen e origjinalit krijohet pa këtë dërgim.</div>',
    '\n        <div class="feature-row">\n          <div><strong>Text + tables</strong><span>Editable Word elements</span></div>\n          <div><strong>Natural reflow</strong><span>Built for translation</span></div>\n          <div><strong>Visual fallback</strong><span>Pixel-faithful reference</span></div>\n        </div>\n        ': '<div class="feature-row"><div><strong>Tekst dhe tabela</strong><span>Të redaktueshme në Word</span></div><div><strong>Gati për përkthim</strong><span>Përkthimi mund të nisë automatikisht</span></div><div><strong>Pamja e origjinalit</strong><span>Kopje për krahasim</span></div></div>',
    'Model(s): {0} · Metered responses: {1:,} · Cached input: {2:,} · Cache-written input: {3:,} · Reasoning: {4:,} (already included in output) · Total tokens: {5:,}. Cost is estimated in USD at default-tier standard API rates; your billing dashboard is authoritative.{6}': 'Modeli: {0} · Përgjigje të matura: {1:,} · Njësi të ripërdorura: {2:,} · Njësi të ruajtura: {3:,} · Njësi arsyetimi: {4:,} (përfshihen te njësitë e krijuara) · Njësi gjithsej: {5:,}. Kosto e përafërt në dollarë amerikanë. Shuma përfundimtare shfaqet te llogaria e faturimit.{6}',
    'App password is not configured. Add APP_PASSWORD to your local .env file or to Streamlit Cloud Secrets.': 'Administratori duhet të vendosë fjalëkalimin APP_PASSWORD te Secrets.',
    "PDF → Word": "Kthim në Word", "Translate Word": "Përkthim dokumentesh",
    "Workflow": "Çfarë dëshironi të bëni?", "Convert only": "Vetëm kthim në Word",
    "Convert & Translate": "Kthe në Word dhe përkthe", "Convert to Word": "Kthe në Word",
    "Convert {0} PDFs to Word": "Kthe {0} PDF në Word",
    "Document Translation Office": "Përkthim dokumentesh",
    "Translation": "Përkthimi", "Source language": "Gjuha e dokumentit",
    "Target language": "Gjuha e përkthimit", "Custom source language": "Shkruani gjuhën e dokumentit",
    "Custom target language": "Shkruani gjuhën e përkthimit",
    "Professional Settings": "Udhëzime për përkthimin", "Document type": "Lloji i dokumentit",
    "Style requirements": "Si dëshironi të jetë përkthimi?", "Document context": "Çfarë duhet të dijë përkthyesi?",
    "Required terminology": "Terma që duhen përdorur", "API": "Cilësime teknike",
    "OpenAI model": "Modeli i përkthimit", "API key configured": "Çelësi i shërbimit është vendosur",
    "Technical settings": "Cilësime teknike", "Leave these settings unchanged unless your administrator asks you to change them.": "Lërini këto cilësime siç janë, përveçse kur ju udhëzon administratori.",
    "Word output": "Dokumentet që dëshironi të merrni", "Translation-ready Word": "Word i redaktueshëm",
    "Exact-look reference": "Kopje Word me pamjen e origjinalit", "Editable Word style": "Pamja e dokumentit Word",
    "Compact translation": "Format i thjeshtë për përkthim", "Source typography": "Shkrimi i origjinalit",
    "Signatures and stamps": "Firmat dhe vulat", "Keep cropped images": "Ruaji si figura",
    "Editable text and signature labels": "Kthe tekstin e vulave në shkrim; shëno firmat",
    "Skip pages with no detected content": "Hiq faqet ku nuk u gjet përmbajtje",
    "Quality": "Cilësia", "Balanced": "Standarde", "Maximum": "Maksimale",
    "OCR model": "Modeli për leximin e PDF-së", "High Reasoning": "Më i fuqishëm — Sol",
    "Medium Reasoning": "I balancuar — Terra", "Low Reasoning": "Më ekonomik — Luna",
    "Use embedded PDF text as an OCR aid": "Përdor edhe tekstin që gjendet brenda PDF-së",
    "Automatically download completed Word files": "Shkarko automatikisht dokumentet e përfunduara",
    "Advanced downloads": "Skedarë shtesë për ndihmë teknike", "Include diagnostic JSON files": "Përfshi skedarët teknikë JSON",
    "First page": "Nga faqja", "Last page": "Deri te faqja", "Your files": "Dokumentet tuaja",
    "Translate document": "Përkthe dokumentet", "Retry failed translations": "Riprovo përkthimet e papërfunduara",
    "Download all completed translations (ZIP)": "Shkarko të gjitha përkthimet e përfunduara (ZIP)",
    "Download all results (ZIP)": "Shkarko të gjitha dokumentet (ZIP)",
    "Download {0}": "Shkarko {0}", "Download {0} — translated Word": "Shkarko {0} — Word i përkthyer",
    "Download {0} — {1}": "Shkarko {0} — {1}", "translation-ready Word": "Word i redaktueshëm",
    "exact-look Word": "Word me pamjen e origjinalit", "OCR layout data (JSON)": "Të dhënat teknike të PDF-së (JSON)",
    "API usage report (JSON)": "Raporti teknik i përdorimit (JSON)",
    "Download combined API usage report (JSON)": "Shkarko raportin e përbashkët të përdorimit (JSON)",
    "Sign out": "Dil", "Site password": "Fjalëkalimi", "Password": "Fjalëkalimi",
    "Enter password": "Shkruani fjalëkalimin", "Open LayoutLens": "Hyr", "Sign in": "Hyr",
    "Enter the site password to open conversion and translation.": "Shkruani fjalëkalimin për të hapur kthimin në Word dhe përkthimin.",
    "Incorrect password.": "Fjalëkalimi nuk është i saktë.",
    "Too many incorrect attempts. Try again in 30 seconds.": "Fjalëkalimi u shkrua gabim disa herë. Provoni sërish pas 30 sekondash.",
    "Too many incorrect attempts. Try again in {0} seconds.": "Fjalëkalimi u shkrua gabim disa herë. Provoni sërish pas {0} sekondash.",
    "This site is locked, but its password has not been configured.": "Faqja nuk është ende gati. Administratori duhet të vendosë fjalëkalimin.",
    'Add APP_PASSWORD = "your password" to the Streamlit Secrets box, then reboot the app.': "Për administratorin: vendosni APP_PASSWORD te Secrets dhe rinisni aplikacionin.",
    "Upload one or more PDFs and get editable Word reconstructions, exact-look copies, or both.": "Ngarkoni dokumentet PDF për t’i kthyer në Word. Mund t’i përktheni menjëherë pas kthimit.",
    "Upload one or more .docx files to begin.": "Ngarkoni një ose disa dokumente Word (.docx) për të filluar.",
    "Choose your files using Browse files, or drag them into the box below.": "Klikoni «Browse files» për të zgjedhur dokumentet, ose tërhiqini brenda kutisë më poshtë.",
    "Translation starts automatically after each PDF is converted.": "Përkthimi fillon vetë sapo secili PDF të jetë kthyer në Word.",
    "Convert & Translate requires editable Word output.": "Për të përkthyer, zgjidhni edhe «Word i redaktueshëm».",
    "Choose at least one Word output.": "Zgjidhni të paktën një lloj dokumenti Word.",
    "Select editable Word and enter both languages and a translation model to continue.": "Zgjidhni Word të redaktueshëm, gjuhën e dokumentit, gjuhën e përkthimit dhe modelin.",
    "The first page must come before the last page.": "Numri i faqes së parë nuk mund të jetë më i madh se ai i faqes së fundit.",
    "This batch is larger than 500 MB. Split it into two smaller batches.": "Dokumentet së bashku kalojnë 500 MB. Ngarkojini në grupe më të vogla.",
    "Choose at most {0} PDFs in one batch.": "Ngarkoni deri në {0} dokumente PDF njëherësh.",
    "{0} is larger than 100 MB. Split or compress it, then try again.": "{0} kalon 100 MB. Ndajeni në pjesë ose zvogëloni madhësinë dhe provoni sërish.",
    "Batch mode will process every page in all {0} PDFs ({1} pages total). Upload one PDF by itself to choose a page range.": "Do të përpunohen të gjitha faqet e {0} PDF-ve ({1} faqe gjithsej). Për të zgjedhur vetëm disa faqe, ngarkoni një PDF të vetëm.",
    "A batch can contain at most {0} pages total. This selection contains {1}; split it into smaller batches.": "Mund të përpunoni deri në {0} faqe njëherësh. Keni zgjedhur {1}; ndajini dokumentet në grupe më të vogla.",
    "Document": "Dokumenti", "Translation Job": "Përkthimi", "Text items": "Pjesë teksti",
    "Unique text": "Pjesë pa përsëritje", "Batches": "Grupe për përkthim", "Extracted text preview": "Teksti i dokumentit",
    "Repeated table headers": "Tituj tabelash që përsëriten", "No repeated first-row table header patterns found.": "Nuk u gjetën tituj tabelash që përsëriten.",
    "Review translated text": "Shiko tekstin e përkthyer", "Translated item {0}": "Pjesa e përkthyer {0}",
    "{0} repeated text items will reuse an exact-match translation.": "Për {0} pjesë teksti të përsëritura do të përdoret i njëjti përkthim.",
    "Showing analysis for {0}. {1} files are queued.": "Po shfaqet {0}. Janë zgjedhur {1} dokumente.",
    "Cannot preview {0}: {1}. Other files can still be processed.": "Nuk mund të shfaqet {0}: {1}. Dokumentet e tjera mund të përpunohen.",
    "Layout, tables, paragraphs, runs, and existing text formatting are preserved; only text node contents are replaced.": "Ruhet struktura dhe formatimi i dokumentit. Përkthehet vetëm teksti.",
    "Preparing document": "Duke përgatitur dokumentin", "Applying translations to the Word file": "Duke vendosur përkthimin në Word",
    "Translating batch {0} of {1}": "Duke përkthyer grupin {0} nga {1}",
    "Translated {0} of {1} unique text items": "U përkthyen {0} nga {1} pjesë teksti",
    "Pending": "Në pritje", "Translating": "Duke përkthyer", "Ready": "Gati", "Failed": "I papërfunduar",
    "{0}/{1}: {2} — Translating": "{0}/{1}: {2} — Duke përkthyer",
    "{0} — Translating": "{0} — Duke përkthyer", "{0} — Ready": "{0} — Gati",
    "{0} — Ready (converted and translated)": "{0} — Gati (u kthye në Word dhe u përkthye)",
    "{0} — Translation failed: {1}": "{0} — Përkthimi nuk u përfundua: {1}",
    "File {0}/{1}: {2} — Converting: {3}": "Dokumenti {0}/{1}: {2} — Duke kthyer në Word: {3}",
    "File {0}/{1}: {2} — Translating": "Dokumenti {0}/{1}: {2} — Duke përkthyer",
    "Finished {0} {1}.": "U përfunduan {0} dokumente PDF.",
    "Conversion stopped: {0}": "Kthimi në Word u ndërpre: {0}",
    "Batch finished: {0} of {1} PDFs produced a Word file.": "Përpunimi përfundoi: {0} nga {1} PDF u kthyen në Word.",
    "Some processing could not finish, but the available Word output is ready below.": "Një pjesë e punës nuk u përfundua. Dokumentet Word që u krijuan mund t’i shkarkoni më poshtë.",
    "Conversion stopped before a requested Word file was ready.": "Kthimi u ndërpre përpara se të krijohej dokumenti Word.",
    "{0} is ready. Use its download button below.": "{0} është gati. Klikoni butonin e shkarkimit më poshtë.",
    "{0} translation(s) can be retried using the converted Word files. OCR will not run again.": "Mund të riprovoni {0} përkthime duke përdorur dokumentet Word të krijuara. PDF-të nuk do të lexohen nga e para.",
    "OCR usage": "Përdorimi për kthimin në Word", "These figures cover PDF conversion only. Translation usage and cost are not included.": "Këto të dhëna janë vetëm për kthimin e PDF-së në Word. Përkthimi nuk përfshihet.",
    "API calls": "Kërkesa te shërbimi", "Input tokens": "Njësi të lexuara", "Output tokens": "Njësi të krijuara", "Estimated cost": "Kosto e përafërt",
    "Translation unavailable: add OPENAI_API_KEY to Streamlit Secrets or your local .env.": "Përkthimi nuk është ende gati. Kërkojini administratorit të vendosë çelësin OPENAI_API_KEY.",
    "Add OPENAI_API_KEY to Streamlit Secrets or your local .env before translating.": "Përpara përkthimit, administratori duhet të vendosë çelësin OPENAI_API_KEY te Secrets.",
    "The OpenAI package is missing. Install the app requirements.": "Mungon një pjesë e programit. Kërkojini administratorit të instalojë kërkesat e aplikacionit.",
    "Enter a translation model.": "Zgjidhni modelin e përkthimit te cilësimet teknike.",
    "Enter both source and target languages.": "Zgjidhni gjuhën e dokumentit dhe gjuhën e përkthimit.",
    "Natural paragraphs, headings, lists, tables, headers, and footers that reflow while you translate.": "Tekst, tituj dhe tabela që mund t’i redaktoni dhe përktheni në Word.",
    "Optional image-based Word copy for visual comparison. It stays local and is not editable.": "Kopje me figura që ruan pamjen e PDF-së. Shërben për krahasim; teksti i saj nuk mund të redaktohet.",
    "Compact uses Times New Roman 12 pt, modest headings and single-spaced paragraphs for translation.": "Përdor Times New Roman 12, tituj të thjeshtë dhe hapësirë të vogël mes rreshtave.",
    "Labels replace signature/stamp crops. Their transcribed wording stays editable. Photographs, maps and barcodes remain images.": "Firmat shënohen me tekst; teksti i vulave mund të redaktohet. Fotografitë, hartat dhe barkodet mbeten figura.",
    "Applies only to editable Word. Pages with images, marks or text are retained; exact-look output keeps every selected page.": "Faqet me tekst ose figura ruhen. Kopja me pamjen e origjinalit ruan çdo faqe të zgjedhur.",
    "Maximum uses a higher-resolution scan and a second OCR verification pass. It is slower and uses more API tokens.": "Cilësia maksimale e lexon PDF-në më hollësisht dhe e kontrollon përsëri. Kërkon më shumë kohë dhe kushton më shumë.",
    "High Reasoning uses GPT-5.6 Sol for the hardest pages; Medium Reasoning uses GPT-5.6 Terra for a quality/cost balance; Low Reasoning uses GPT-5.6 Luna for the lowest cost.": "Sol për faqe të vështira; Terra për balancë mes cilësisë dhe kostos; Luna për kosto më të ulët.",
    "Improves born-digital PDFs. Turn it off if the PDF contains an incorrect hidden OCR layer.": "Ndihmon kur PDF-ja ka tekst të lexueshëm. Çaktivizojeni nëse teksti i saj i brendshëm ka gabime.",
    "Downloads each Word file as soon as its PDF finishes. Your browser may ask to allow multiple downloads. Download buttons stay available below.": "Dokumentet shkarkohen sapo të përfundojnë. Shfletuesi mund t’ju kërkojë leje për disa shkarkime. Butonat mbeten të disponueshëm më poshtë.",
    "Optional OCR layout and API usage files for troubleshooting. Leave off for Word-only downloads. Requesting layout data for an exact-look-only conversion also runs OCR.": "Skedarë për ndihmë teknike. Lëreni të çaktivizuar nëse ju duhen vetëm dokumentet Word. Aktivizimi mund të sjellë lexim shtesë të PDF-së dhe kosto.",
    "Albanian": "Shqip", "Italian": "Italisht", "English": "Anglisht", "French": "Frëngjisht", "German": "Gjermanisht",
    "Spanish": "Spanjisht", "Portuguese": "Portugalisht", "Greek": "Greqisht", "Romanian": "Rumanisht", "Turkish": "Turqisht",
    "Serbian": "Serbisht", "Croatian": "Kroatisht", "Bosnian": "Boshnjakisht", "Macedonian": "Maqedonisht",
    "Montenegrin": "Malazezisht", "Bulgarian": "Bullgarisht", "Dutch": "Holandisht", "Polish": "Polonisht",
    "Ukrainian": "Ukrainisht", "Russian": "Rusisht", "Arabic": "Arabisht", "Custom": "Gjuhë tjetër",
    "Legal / judicial file": "Dosje ligjore / gjyqësore", "Police / investigative file": "Dosje policore / hetimore",
    "Financial police / Guardia di Finanza file": "Dosje e policisë financiare / Guardia di Finanza",
    "Court / prosecution document": "Dokument gjykate / prokurorie", "Business document": "Dokument biznesi",
    "Medical document": "Dokument mjekësor", "Academic document": "Dokument akademik", "Immigration document": "Dokument emigracioni",
    "Technical document": "Dokument teknik", "General professional document": "Dokument i përgjithshëm profesional",
    "Rendering PDF pages": "Duke përgatitur faqet", "PDF pages rendered": "Faqet u përgatitën",
    "Building exact-look Word document": "Duke krijuar kopjen me pamjen e origjinalit",
    "Exact-look Word document ready": "Kopja me pamjen e origjinalit është gati",
    "Building translation-ready Word document": "Duke krijuar Word-in e redaktueshëm",
    "Translation-ready Word document ready": "Word-i i redaktueshëm është gati",
    "Reading page layout with GPT-5.6 vision": "Duke lexuar përmbajtjen e faqeve",
}


def tr(text, *values):
    translated = SQ.get(text, text) if st.session_state.get("ui_language", "sq") == "sq" else text
    return translated.format(*values) if values else translated


def language_switch():
    st.sidebar.radio("Gjuha e faqes / Interface language", ["sq", "en"],
                     format_func=lambda code: "Shqip" if code == "sq" else "English",
                     key="ui_language", horizontal=True)


def control(method, label, *args, **kwargs):
    """Keep conversion choices stable when translated labels change."""
    saved = st.session_state.setdefault("conversion_preferences", {})
    key = "_conversion_" + label
    kwargs.pop("key", None)
    if label in saved:
        st.session_state[key] = saved[label]

    def changed():
        saved[label] = st.session_state[key]

    if method in ("radio", "selectbox", "segmented_control"):
        options = kwargs.get("options", args[0] if args else [])
        labels = {option: tr(option) for option in options}
        kwargs["format_func"] = labels.__getitem__
    if "help" in kwargs:
        kwargs["help"] = tr(kwargs["help"])
    result = getattr(st, method)(tr(label), *args, key=key, on_change=changed, **kwargs)
    saved[label] = result
    return result
