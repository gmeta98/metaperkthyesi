from __future__ import annotations

from interface import tr, control

import hmac
import os
import json
import zipfile
from collections import Counter
from dataclasses import dataclass
from io import BytesIO
from typing import Iterable

import streamlit as st
from docx import Document
from docx.document import Document as DocumentObject
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn
from dotenv import load_dotenv

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled in the UI
    OpenAI = None


load_dotenv(override=False)

LANGUAGES = [
    "Albanian",
    "Italian",
    "English",
    "French",
    "German",
    "Spanish",
    "Portuguese",
    "Greek",
    "Romanian",
    "Turkish",
    "Serbian",
    "Croatian",
    "Bosnian",
    "Macedonian",
    "Montenegrin",
    "Bulgarian",
    "Dutch",
    "Polish",
    "Ukrainian",
    "Russian",
    "Arabic",
    "Custom",
]

DOCUMENT_TYPE_CONTEXTS = {
    "Legal / judicial file": (
        "Formal legal or judicial file. Preserve legal force, procedural meaning, "
        "institutional names, dates, protocol numbers, article references, party roles, "
        "official titles, and document hierarchy."
    ),
    "Police / investigative file": (
        "Police or investigative file. Preserve investigative terminology, speaker roles, "
        "surveillance or transcript context, dates, times, locations, identifying details, "
        "and concise official register."
    ),
    "Financial police / Guardia di Finanza file": (
        "Italian Guardia di Finanza or financial-police material. Preserve authority names, "
        "tax/financial/legal terminology, protocol references, offices, ranks, investigative "
        "acts, and formal administrative style."
    ),
    "Court / prosecution document": (
        "Court, prosecution, or criminal-procedure document. Preserve procedural terms, "
        "charges, article references, names, roles, chronology, exhibits, and formal legal register."
    ),
    "Business document": (
        "Business or administrative document. Preserve commercial terms, company names, "
        "dates, amounts, obligations, references, and professional tone."
    ),
    "Medical document": (
        "Medical document. Preserve clinical terminology, measurements, dates, diagnoses, "
        "medications, and professional tone."
    ),
    "Academic document": (
        "Academic document. Preserve terminology, citations, titles, names, references, and formal tone."
    ),
    "Immigration document": (
        "Immigration or civil-status document. Preserve authority names, personal data, dates, "
        "case references, legal status terms, and official register."
    ),
    "Technical document": (
        "Technical document. Preserve technical terminology, measurements, labels, references, "
        "and concise professional tone."
    ),
    "General professional document": (
        "General professional document. Preserve meaning, names, dates, references, and professional tone."
    ),
}

DOCUMENT_TYPE_PROMPT_LABELS = {
    "Legal / judicial file": "legal/judicial",
    "Police / investigative file": "police/investigative",
    "Financial police / Guardia di Finanza file": "financial-police/Guardia di Finanza",
    "Court / prosecution document": "court/prosecution",
    "Business document": "business/administrative",
    "Medical document": "medical",
    "Academic document": "academic",
    "Immigration document": "immigration/civil-status",
    "Technical document": "technical",
    "General professional document": "general professional",
}

DEFAULT_SYSTEM_PROMPT = """You are a professional legal and business document translator.
Translate faithfully from {source_language} to {target_language}.
Preserve meaning, names, numbers, dates, addresses, references, section numbering, and punctuation intent.
Use natural, professional {target_language} as used by native speakers in official translation practice.
Prefer the meaning required by the local context over literal word-for-word cognates.
Avoid unnatural borrowed terms when a standard, idiomatic {target_language} term fits the sentence better.
For legal, judicial, police, financial-police, prosecution, or administrative documents, preserve legal effect and procedural nuance. Use standard official/legal terminology in {target_language}; do not simplify, soften, intensify, or paraphrase legal meaning.
For transcripts, police/legal notes, speaker descriptions, and conversational summaries, translate the practical meaning in context.
If a text item is a table-cell fragment rather than a full sentence, infer its role from nearby items and translate it as a natural fragment.
Do not summarize, explain, add commentary, or omit content.
Return only the requested translation output."""

BATCH_MAX_ITEMS = 40
BATCH_MAX_CHARS = 6000
ROLLING_CONTEXT_PAIRS = 12
DOCUMENT_CONTEXT_ITEMS = 80
DOCUMENT_CONTEXT_CHARS = 5000
MAX_TRANSLATION_ATTEMPTS = 2
XML_SPACE = qn("xml:space")


@dataclass(frozen=True)
class TextUnit:
    location: str
    text: str
    target_index: int


@dataclass(frozen=True)
class DocumentAnalysis:
    text_items: int
    unique_text_items: int
    repeated_text_items: int
    estimated_batches: int
    repeated_header_rows: list[tuple[tuple[str, ...], int]]


def iter_text_targets(document: DocumentObject) -> Iterable[tuple[str, Paragraph]]:
    seen_paragraphs: set[str] = set()

    for location, paragraph in iter_raw_text_targets(document):
        paragraph_id = f"{paragraph.part.partname}:{paragraph._p.getroottree().getpath(paragraph._p)}"
        if paragraph_id in seen_paragraphs:
            continue
        seen_paragraphs.add(paragraph_id)
        yield location, paragraph


def iter_raw_text_targets(document: DocumentObject) -> Iterable[tuple[str, Paragraph]]:
    yield from iter_block_paragraphs(document.element.body, document, "Body")

    for part_index, (part_type, part) in enumerate(iter_existing_header_footer_parts(document), start=1):
        yield from iter_block_paragraphs(part.element, part, f"{part_type} {part_index}")


def iter_existing_header_footer_parts(document: DocumentObject) -> Iterable[tuple[str, object]]:
    seen_parts: set[str] = set()
    for relationship in document.part.rels.values():
        if relationship.reltype not in (RT.HEADER, RT.FOOTER):
            continue

        part = relationship.target_part
        part_name = str(part.partname)
        if part_name in seen_parts:
            continue

        seen_parts.add(part_name)
        part_type = "Header" if relationship.reltype == RT.HEADER else "Footer"
        yield part_type, part


def iter_block_paragraphs(container, parent, prefix: str) -> Iterable[tuple[str, Paragraph]]:
    paragraph_index = 0
    table_index = 0

    for child in container.iterchildren():
        if child.tag == qn("w:p"):
            paragraph_index += 1
            yield f"{prefix} paragraph {paragraph_index}", Paragraph(child, parent)
        elif child.tag == qn("w:tbl"):
            table_index += 1
            yield from iter_table_paragraphs(Table(child, parent), f"{prefix} table {table_index}")


def iter_table_paragraphs(table: Table, prefix: str) -> Iterable[tuple[str, Paragraph]]:
    for row_index, row in enumerate(table.rows, start=1):
        for cell_index, cell in enumerate(row.cells, start=1):
            yield from iter_cell_paragraphs(cell, f"{prefix}, row {row_index}, cell {cell_index}")


def iter_cell_paragraphs(cell: _Cell, prefix: str) -> Iterable[tuple[str, Paragraph]]:
    for paragraph_index, paragraph in enumerate(cell.paragraphs, start=1):
        yield f"{prefix}, paragraph {paragraph_index}", paragraph
    for table_index, nested_table in enumerate(cell.tables, start=1):
        yield from iter_table_paragraphs(nested_table, f"{prefix}, nested table {table_index}")


def collect_text_units(document: DocumentObject) -> list[TextUnit]:
    units: list[TextUnit] = []

    for text_target_index, (location, paragraph) in enumerate(iter_text_targets(document)):
        text = paragraph.text.strip()
        if text:
            units.append(TextUnit(location, text, text_target_index))

    return units


def collect_table_header_rows(document: DocumentObject) -> list[tuple[str, ...]]:
    rows: list[tuple[str, ...]] = []

    for table in document.tables:
        if not table.rows:
            continue

        seen_paragraphs: set[str] = set()
        row_text: list[str] = []
        for cell in table.rows[0].cells:
            cell_parts: list[str] = []
            for paragraph in cell.paragraphs:
                paragraph_id = paragraph._p.getroottree().getpath(paragraph._p)
                if paragraph_id in seen_paragraphs:
                    continue
                seen_paragraphs.add(paragraph_id)
                text = paragraph.text.strip()
                if text:
                    cell_parts.append(text)

            cell_text = " / ".join(cell_parts).strip()
            if cell_text:
                row_text.append(cell_text)

        if row_text:
            rows.append(tuple(row_text))

    return rows


def analyze_document(document: DocumentObject) -> DocumentAnalysis:
    units = collect_text_units(document)
    unique_units = list({unit.text: unit for unit in units}.values())
    header_counts = Counter(collect_table_header_rows(document))
    repeated_headers = [
        (row, count)
        for row, count in header_counts.most_common()
        if count > 1
    ]

    return DocumentAnalysis(
        text_items=len(units),
        unique_text_items=len(unique_units),
        repeated_text_items=len(units) - len(unique_units),
        estimated_batches=len(build_batches(unique_units)),
        repeated_header_rows=repeated_headers,
    )


def set_paragraph_text(paragraph: Paragraph, text: str) -> None:
    text_nodes = paragraph._element.xpath(".//w:t")
    if not text_nodes:
        return

    replacement = " ".join(text.splitlines()).strip()
    original_lengths = [len(node.text or "") for node in text_nodes]
    chunks = split_text_for_existing_nodes(replacement, original_lengths)

    for node, chunk in zip(text_nodes, chunks):
        set_text_node_text(node, chunk)


def set_text_node_text(node, text: str) -> None:
    node.text = text
    if text:
        node.set(XML_SPACE, "preserve")
    elif XML_SPACE in node.attrib:
        del node.attrib[XML_SPACE]


def split_text_for_existing_nodes(text: str, original_lengths: list[int]) -> list[str]:
    if len(original_lengths) == 1:
        return [text]

    total_original = sum(original_lengths)
    if total_original <= 0:
        return [text] + [""] * (len(original_lengths) - 1)

    chunks: list[str] = []
    cursor = 0
    text_length = len(text)

    for index, original_length in enumerate(original_lengths):
        if index == len(original_lengths) - 1:
            chunks.append(text[cursor:])
            break

        target_length = round(text_length * (original_length / total_original))
        remaining_nodes = len(original_lengths) - index - 1
        max_cursor = max(cursor, text_length - remaining_nodes)
        next_cursor = min(cursor + target_length, max_cursor)

        if cursor < next_cursor < text_length and not text[next_cursor].isspace():
            left_space = text.rfind(" ", cursor, next_cursor)
            right_space = text.find(" ", next_cursor)
            if left_space > cursor and next_cursor - left_space <= 12:
                next_cursor = left_space
            elif right_space != -1 and right_space - next_cursor <= 12:
                next_cursor = right_space

        chunks.append(text[cursor:next_cursor])
        cursor = next_cursor

    return chunks


def replace_text_unit(document: DocumentObject, unit: TextUnit, translated_text: str) -> None:
    text_targets = [paragraph for _, paragraph in iter_text_targets(document)]
    set_paragraph_text(text_targets[unit.target_index], translated_text)


def build_preview(units: list[TextUnit], max_items: int = 12) -> str:
    preview_lines = []
    for unit in units[:max_items]:
        preview_lines.append(f"{unit.location}\n{unit.text}")
    return "\n\n".join(preview_lines)


def format_header_row(row: tuple[str, ...]) -> str:
    return " | ".join(row)


def get_config_value(name: str) -> str:
    environment_value = os.getenv(name, "").strip()
    if environment_value:
        return environment_value

    try:
        secret_value = st.secrets[name]
    except (FileNotFoundError, KeyError):
        return ""

    return str(secret_value).strip()


def get_configured_client() -> OpenAI | None:
    api_key = get_config_value("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return None
    return OpenAI(api_key=api_key)


def build_batches(
    items: list[TextUnit],
    *,
    max_items: int = BATCH_MAX_ITEMS,
    max_chars: int = BATCH_MAX_CHARS,
) -> list[list[TextUnit]]:
    batches: list[list[TextUnit]] = []
    current: list[TextUnit] = []
    current_chars = 0

    for item in items:
        item_chars = len(item.text)
        would_exceed_items = len(current) >= max_items
        would_exceed_chars = current and current_chars + item_chars > max_chars
        if would_exceed_items or would_exceed_chars:
            batches.append(current)
            current = []
            current_chars = 0

        current.append(item)
        current_chars += item_chars

    if current:
        batches.append(current)

    return batches


def build_document_context(units: list[TextUnit], user_context: str) -> str:
    sampled_text = "\n".join(
        f"- {unit.text}"
        for unit in units[:DOCUMENT_CONTEXT_ITEMS]
        if len(unit.text) > 2
    )
    if len(sampled_text) > DOCUMENT_CONTEXT_CHARS:
        sampled_text = sampled_text[:DOCUMENT_CONTEXT_CHARS].rsplit("\n", 1)[0]

    return f"""User document context:
{user_context or "No extra context provided."}

Early document text for context:
{sampled_text or "No preview text available."}"""


def build_profile_context(subject_matter: str) -> str:
    return DOCUMENT_TYPE_CONTEXTS.get(
        subject_matter,
        DOCUMENT_TYPE_CONTEXTS["General professional document"],
    )


def build_recent_context(pairs: list[tuple[TextUnit, str]]) -> str:
    if not pairs:
        return "No previous translations in this job yet."

    recent_pairs = pairs[-ROLLING_CONTEXT_PAIRS:]
    return "\n".join(
        f"- Source: {unit.text}\n  Translation: {translated_text}"
        for unit, translated_text in recent_pairs
    )


def parse_translation_response(response_text: str, units: list[TextUnit]) -> list[str]:
    response_text = response_text.strip()
    if response_text.startswith("```") and response_text.endswith("```"):
        lines = response_text.splitlines()
        if lines[0].lower() not in {"```", "```json"}:
            raise ValueError("The translation response was not valid JSON.")
        response_text = "\n".join(lines[1:-1])
    payload = json.loads(response_text)
    if not isinstance(payload, dict):
        raise ValueError("The translation response was not a JSON object.")
    translations = payload.get("translations")
    if not isinstance(translations, list):
        raise ValueError("The translation response did not include a translations list.")

    expected_ids = {unit.target_index for unit in units}
    by_id: dict[int, str] = {}
    for item in translations:
        if not isinstance(item, dict):
            raise ValueError("The translation response contained an invalid text item.")
        item_id = item.get("id")
        translated_text = item.get("text")
        if type(item_id) is not int or item_id not in expected_ids:
            raise ValueError("The translation response contained an unknown text item.")
        if item_id in by_id:
            raise ValueError("The translation response repeated a text item.")
        if not isinstance(translated_text, str) or not translated_text.strip():
            raise ValueError("The translation response contained empty or invalid text.")
        by_id[item_id] = translated_text.strip()

    missing = [unit.target_index for unit in units if unit.target_index not in by_id]
    if missing:
        raise ValueError(f"The translation response missed {len(missing)} text items.")

    return [by_id[unit.target_index] for unit in units]


def translate_units(
    units: list[TextUnit],
    *,
    source_language: str,
    target_language: str,
    subject_matter: str,
    style_instruction: str,
    glossary: str,
    document_context: str,
    recent_context: str,
    model: str,
) -> list[str]:
    client = get_configured_client()
    if client is None:
        raise RuntimeError("Translation requires OPENAI_API_KEY and the OpenAI package. Configure them before starting.")

    system_prompt = DEFAULT_SYSTEM_PROMPT.format(
        source_language=source_language,
        target_language=target_language,
    )

    items_json = json.dumps(
        [{"id": unit.target_index, "text": unit.text} for unit in units],
        ensure_ascii=False,
        indent=2,
    )
    user_prompt = f"""Subject matter: {subject_matter or "General professional document"}
Document profile:
{build_profile_context(subject_matter)}

Style requirements: {style_instruction or "Professional, accurate, and natural"}
Glossary and required terminology:
{glossary or "None provided"}

Document-wide context:
{document_context}

Recent translation choices from this same job:
{recent_context}

Translate each JSON item from {source_language} to {target_language}.
Use nearby items in this batch as context for terminology and tone, but translate each item separately.
Choose context-appropriate local wording, not literal cognates, when the source term has several possible meanings.
Do not preserve source-language syntax when it would sound unnatural in {target_language}.
Keep terminology, register, speaker labels, and recurring phrases consistent with the document-wide context and recent translation choices.
For legal prose, translate sentence-by-sentence with exact legal meaning; preserve obligations, negations, conditions, procedural terms, and references.
For names of public bodies, offices, laws, articles, forms, exhibits, protocol numbers, addresses, emails, phone numbers, codes, and file references, preserve the identifying content exactly unless a standard translated institution name is clearly appropriate.
Keep the same id values. Do not merge, split, remove, renumber, or reorder items.
Return only valid JSON in this exact shape:
{{"translations":[{{"id":0,"text":"translated text"}}]}}

Text items:
{items_json}"""

    last_error: Exception | None = None
    for attempt in range(1, MAX_TRANSLATION_ATTEMPTS + 1):
        repair_instruction = ""
        if attempt > 1:
            repair_instruction = (
                "\nThe previous response could not be parsed. Return only valid JSON, "
                "with every original id present exactly once, no extra ids, "
                "and a complete non-empty translation for every text item."
            )

        response = client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt + repair_instruction},
            ],
        )
        try:
            return parse_translation_response(response.output_text.strip(), units)
        except ValueError as exc:
            last_error = exc

    raise ValueError(f"Could not parse translation response after retry: {last_error}")


def translate_document(
    source_bytes: bytes,
    *,
    source_language: str,
    target_language: str,
    subject_matter: str,
    style_instruction: str,
    glossary: str,
    user_context: str,
    model: str,
) -> tuple[bytes, list[tuple[TextUnit, str]]]:
    document = Document(BytesIO(source_bytes))
    units = collect_text_units(document)
    if not units:
        raise ValueError("This Word document contains no editable text to translate.")
    translated_pairs: list[tuple[TextUnit, str]] = []
    text_targets = [paragraph for _, paragraph in iter_text_targets(document)]
    document_context = build_document_context(units, user_context)
    translation_cache: dict[str, str] = {}
    recent_pairs: list[tuple[TextUnit, str]] = []

    progress = st.progress(0, text=tr('Preparing document'))
    translated_count = 0
    unique_units: list[TextUnit] = []
    seen_texts: set[str] = set()
    for unit in units:
        if unit.text in seen_texts:
            continue
        seen_texts.add(unit.text)
        unique_units.append(unit)

    batches = build_batches(unique_units)
    for batch_index, batch in enumerate(batches, start=1):
        progress.progress(
            translated_count / max(len(unique_units), 1),
            text=tr('Translating batch {0} of {1}', batch_index, len(batches)),
        )
        translated_texts = translate_units(
            batch,
            source_language=source_language,
            target_language=target_language,
            subject_matter=subject_matter,
            style_instruction=style_instruction,
            glossary=glossary,
            document_context=document_context,
            recent_context=build_recent_context(recent_pairs),
            model=model,
        )
        for unit, translated_text in zip(batch, translated_texts):
            translation_cache[unit.text] = translated_text
            recent_pairs.append((unit, translated_text))
            translated_count += 1

        progress.progress(
            translated_count / max(len(unique_units), 1),
            text=tr('Translated {0} of {1} unique text items', translated_count, len(unique_units)),
        )

    progress.progress(1.0, text=tr('Applying translations to the Word file'))
    for unit in units:
        translated_text = translation_cache[unit.text]
        set_paragraph_text(text_targets[unit.target_index], translated_text)
        translated_pairs.append((unit, translated_text))

    progress.empty()
    output = BytesIO()
    from ocr_reader.wordflow import finalize_editable_layout
    finalize_editable_layout(document)
    document.save(output)
    return output.getvalue(), translated_pairs


def resolve_language(choice: str, custom: str) -> str:
    return custom.strip() if choice == "Custom" else choice


def document_type_prompt_label(subject_matter: str) -> str:
    return DOCUMENT_TYPE_PROMPT_LABELS.get(subject_matter, "general professional")


def default_style_requirements(subject_matter: str) -> str:
    document_label = document_type_prompt_label(subject_matter)
    return (
        "Formal, accurate, natural, and suitable for certified translation review. "
        f"Preserve {document_label} meaning, official tone, names, dates, article references, "
        "protocol numbers, and institutional terminology."
    )


def default_document_context(source_language: str, subject_matter: str) -> str:
    document_label = document_type_prompt_label(subject_matter)
    language_label = source_language if source_language != "Custom" else "Source-language"
    return (
        f"{language_label} {document_label} file. Some documents are prose-heavy "
        f"{document_label} records; others contain tables, transcript summaries, speaker "
        "descriptions, dates, names, offices, protocol numbers, and conversational notes."
    )


def refresh_defaults_for_document_type() -> None:
    subject_matter = st.session_state.get("subject_matter", "Legal / judicial file")
    source_language = resolve_language(
        st.session_state.get("source_choice", "Italian"),
        st.session_state.get("source_custom", ""),
    )
    st.session_state["style_instruction"] = default_style_requirements(subject_matter)
    st.session_state["user_context"] = default_document_context(source_language, subject_matter)


def refresh_document_context_for_source() -> None:
    subject_matter = st.session_state.get("subject_matter", "Legal / judicial file")
    source_language = resolve_language(
        st.session_state.get("source_choice", "Italian"),
        st.session_state.get("source_custom", ""),
    )
    st.session_state["user_context"] = default_document_context(source_language, subject_matter)


def log_out() -> None:
    for key in (
        "authenticated",
        "login_error",
        "login_password",
        "uploaded_files",
        "translated_docx",
        "translated_zip",
        "translated_pairs",
        "download_name",
    ):
        st.session_state.pop(key, None)


def check_password() -> None:
    configured_password = get_config_value("APP_PASSWORD")
    submitted_password = st.session_state.get("login_password", "")
    password_matches = bool(configured_password) and hmac.compare_digest(
        submitted_password,
        configured_password,
    )

    st.session_state["authenticated"] = password_matches
    st.session_state["login_error"] = not password_matches
    st.session_state.pop("login_password", None)


def require_password() -> None:
    configured_password = get_config_value("APP_PASSWORD")
    if not configured_password:
        st.error(
            tr('App password is not configured. Add APP_PASSWORD to your local .env file or to Streamlit Cloud Secrets.')
        )
        st.stop()

    if st.session_state.get("authenticated"):
        return

    st.title(tr('Document Translation Office'))
    st.subheader(tr('Sign in'))

    with st.form("login_form"):
        st.text_input(tr('Password'), type="password", key="login_password")
        st.form_submit_button(
            tr('Sign in'),
            type="primary",
            on_click=check_password,
            use_container_width=True,
        )

    if st.session_state.get("login_error"):
        st.error(tr('Incorrect password.'))

    st.stop()


def translation_settings() -> dict:
    from interface import SQ
    # Keep durable values separate from widgets, which Streamlit cleans up
    # when their page is no longer rendered.
    saved = st.session_state.setdefault("translation_preferences", dict(
        source_choice="Italian", source_custom="", target_choice="Albanian", target_custom="",
        subject_matter="Legal / judicial file", glossary="",
        model=get_config_value("OPENAI_MODEL") or "gpt-5.6-sol",
    ))
    saved.setdefault("style_instruction", default_style_requirements(saved["subject_matter"]))
    saved.setdefault("user_context", default_document_context(
        resolve_language(saved["source_choice"], saved["source_custom"]), saved["subject_matter"]))

    # Translate only built-in instructions for display, keeping the original
    # values used for processing and leaving user-written instructions intact.
    displays = {}
    for subject in DOCUMENT_TYPE_CONTEXTS:
        displays[default_style_requirements(subject)] = (
            "Përkthim formal, i saktë dhe i natyrshëm, i përshtatshëm për shqyrtim profesional. "
            "Ruani kuptimin, tonin zyrtar, emrat, datat, nenet, numrat e protokollit dhe termat institucionalë. "
            "Lloji i dokumentit: " + SQ.get(subject, subject) + "."
        )
        source_language = resolve_language(saved["source_choice"], saved["source_custom"])
        displays[default_document_context(source_language, subject)] = (
            "Dokument në gjuhën " + SQ.get(source_language, source_language) + ". "
            "Lloji: " + SQ.get(subject, subject) + ". "
            "Mund të përmbajë tekst, tabela, përmbledhje transkriptesh, emra, data, orare, adresa, "
            "numra protokolli dhe shënime zyrtare."
        )
    reverse_displays = {value: key for key, value in displays.items()}

    def underlying(field, value):
        return reverse_displays.get(value, value) if field in ("style_instruction", "user_context") else value

    def changed(field):
        saved[field] = underlying(field, st.session_state["_translation_" + field])
        if field == "subject_matter":
            saved["style_instruction"] = default_style_requirements(saved[field])
        if field in ("source_choice", "source_custom", "subject_matter"):
            saved["user_context"] = default_document_context(
                resolve_language(saved["source_choice"], saved["source_custom"]), saved["subject_matter"])

    def widget(field, label, kind="text", **kwargs):
        key = "_translation_" + field
        display = saved[field]
        if st.session_state.get("ui_language", "sq") == "sq" and field in ("style_instruction", "user_context"):
            display = displays.get(display, display)
        st.session_state[key] = display
        method = {"text": st.text_input, "area": st.text_area, "select": st.selectbox}[kind]
        if kind == "select":
            labels = {option: tr(option) for option in kwargs["options"]}
            kwargs["format_func"] = labels.__getitem__
        value = method(tr(label), key=key, on_change=changed, args=(field,), **kwargs)
        saved[field] = underlying(field, value)
        return saved[field]

    with st.sidebar:
        st.header(tr('Translation'))
        source = widget("source_choice", "Source language", "select", options=LANGUAGES)
        source_custom = widget("source_custom", "Custom source language", disabled=source != "Custom")
        target = widget("target_choice", "Target language", "select", options=LANGUAGES)
        target_custom = widget("target_custom", "Custom target language", disabled=target != "Custom")
        st.header(tr('Professional Settings'))
        subject = widget("subject_matter", "Document type", "select", options=list(DOCUMENT_TYPE_CONTEXTS))
        style = widget("style_instruction", "Style requirements", "area", height=110)
        context = widget("user_context", "Document context", "area", height=110)
        glossary = widget("glossary", "Required terminology", "area", height=130)
        with st.expander(tr("Technical settings")):
            st.caption(tr("Leave these settings unchanged unless your administrator asks you to change them."))
            model = widget("model", "OpenAI model")
        if not get_config_value("OPENAI_API_KEY"):
            st.warning(tr('Translation unavailable: add OPENAI_API_KEY to Streamlit Secrets or your local .env.'))
        else:
            st.caption(tr('API key configured'))
    return dict(source_language=resolve_language(source, source_custom),
                target_language=resolve_language(target, target_custom),
                subject_matter=subject, style_instruction=style, user_context=context,
                glossary=glossary, model=model)


def translation_configuration_error(options):
    if not get_config_value("OPENAI_API_KEY"):
        return "Add OPENAI_API_KEY to Streamlit Secrets or your local .env before translating."
    if OpenAI is None:
        return "The OpenAI package is missing. Install the app requirements."
    if not options["model"].strip():
        return "Enter a translation model."
    if not options["source_language"].strip() or not options["target_language"].strip():
        return "Enter both source and target languages."
    return ""


def main() -> None:
    from translation_jobs import new_job, run_pending
    st.title(tr('Document Translation Office'))
    options = translation_settings()
    auto_download = control("checkbox", "Automatically download completed Word files", value=True)
    st.caption(tr("Choose your files using Browse files, or drag them into the box below."))
    uploaded = st.file_uploader("Word (.docx)", type=["docx"], accept_multiple_files=True, key="uploaded_files")
    files = [(file.name, file.getvalue()) for file in uploaded or []]
    if not files:
        st.info(tr('Upload one or more .docx files to begin.'))
        _translation_results(auto_download)
        return

    left, right = st.columns(2)
    with left:
        st.subheader(tr('Document'))
        try:
            document = Document(BytesIO(files[0][1]))
            units = collect_text_units(document)
            analysis = analyze_document(document)
            columns = st.columns(3)
            columns[0].metric(tr('Text items'), analysis.text_items)
            columns[1].metric(tr('Unique text'), analysis.unique_text_items)
            columns[2].metric(tr('Batches'), analysis.estimated_batches)
            if analysis.repeated_text_items:
                st.caption(tr('{0} repeated text items will reuse an exact-match translation.', analysis.repeated_text_items))
            with st.expander(tr('Repeated table headers')):
                for row, count in analysis.repeated_header_rows[:10]:
                    st.write(f"{count} times: {format_header_row(row)}")
                if not analysis.repeated_header_rows:
                    st.write("No repeated first-row table header patterns found.")
            st.text_area(tr('Extracted text preview'), build_preview(units), height=440)
        except Exception as exc:
            st.warning(tr('Cannot preview {0}: {1}. Other files can still be processed.', files[0][0], exc))
        if len(files) > 1:
            st.caption(tr('Showing analysis for {0}. {1} files are queued.', files[0][0], len(files)))

    with right:
        st.subheader(tr('Translation Job'))
        st.write(f'{tr(options["source_language"])} → {tr(options["target_language"])}')
        st.write(tr(options["subject_matter"]))
        st.caption(tr('Layout, tables, paragraphs, runs, and existing text formatting are preserved; only text node contents are replaced.'))
        error = translation_configuration_error(options)
        if error:
            st.warning(tr(error))
        if st.button(tr('Translate document'), type="primary", disabled=bool(error), use_container_width=True):
            jobs = []
            for index, (name, data) in enumerate(files, 1):
                job = new_job(name, data, options)
                if len(files) > 1:
                    job["output_name"] = f'{index:02d}-' + job["output_name"]
                jobs.append(job)
            # Store each job before processing; completed work survives later failures.
            st.session_state.setdefault("translation_jobs", []).extend(jobs)
            run_pending(jobs, auto_download)

    _translation_results(auto_download)


def _translation_results(auto_download):
    from translation_jobs import run_pending, unfinished
    jobs = st.session_state.get("translation_jobs", [])
    if not jobs:
        return
    st.subheader(tr("Saved translations"))
    st.caption(tr("These results belong to the documents and languages shown below, even if you change the upload or settings."))
    if st.button(tr("Clear saved translations"), key="clear_translation_results"):
        st.session_state["translation_jobs"] = []
        return
    retry_jobs = [job for job in jobs if unfinished(job)]
    error = next((translation_configuration_error(job["options"]) for job in retry_jobs
                  if translation_configuration_error(job["options"])), "")
    if error:
        st.warning(tr(error))
    if retry_jobs:
        if st.button(tr('Retry failed translations'), disabled=bool(error)):
            run_pending(jobs, auto_download)
    ready = [job for job in jobs if job["status"] == "Ready"]
    for job in jobs:
        st.write(f'{job["name"]} — {tr(job["status"])}')
        st.caption(f'{tr(job["options"]["source_language"])} → {tr(job["options"]["target_language"])} · {job["options"]["model"]}')
        if unfinished(job):
            st.warning(tr(job["error"]) if job["error"] else tr("This document is waiting. Use Retry to continue."))
        elif job["status"] == "Ready":
            st.download_button(tr("Download {0}", job["output_name"]), job["output"],
                file_name=job["output_name"], key="download-" + job["id"],
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    if len(ready) > 1:
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for index, job in enumerate(ready, 1):
                archive.writestr(f'{index:02d}-{job["output_name"]}', job["output"])
        st.download_button(tr('Download all completed translations (ZIP)'), buffer.getvalue(),
                           file_name="translated-results.zip", mime="application/zip")
    if ready:
        with st.expander(tr('Review translated text')):
            for index, (unit, text) in enumerate(ready[0]["pairs"][:25]):
                st.markdown(tr('**{0}**', unit.location))
                st.text_area(tr('Translated item {0}', index + 1), text, height=120,
                             key=f'review-{ready[0]["id"]}-{index}')

if __name__ == "__main__":
    main()
