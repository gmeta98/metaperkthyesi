from __future__ import annotations

from interface import tr, control

import hashlib
import hmac
import io
import json
import shutil
import time
import uuid
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path

import streamlit as st

from .config import (
    DEFAULT_MODEL_PRESET,
    MODEL_PRESETS,
    PROJECT_ROOT,
    Settings,
    apply_quality_preset,
    load_environment,
)
from .pdf import inspect_pdf_bytes
from .pipeline import PartialConversionError, convert_pdf
from .export_options import ExportOptions
from .downloads import auto_download_word


JOBS_DIR = PROJECT_ROOT / ".ocr_jobs"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_BATCH_BYTES = 500 * 1024 * 1024
MAX_FILES_PER_BATCH = 20
MAX_PAGES_PER_CONVERSION = 150
JOB_RETENTION_SECONDS = 24 * 60 * 60


@dataclass(frozen=True, slots=True)
class UploadDocument:
    name: str
    data: bytes
    page_count: int
    page_numbers: tuple[int, ...]


def run() -> None:
    _conversion_page()
    _saved_pdf_results()


def _conversion_page() -> None:
    _styles()
    load_environment()
    if not st.session_state.get("job_cleanup_done"):
        _cleanup_stale_jobs()
        st.session_state["job_cleanup_done"] = True

    st.markdown(tr('<div class="eyebrow">GPT-5.6 document vision</div>'), unsafe_allow_html=True)
    st.markdown(
        tr('<h1 class="hero-title">PDF to Word, without losing the page</h1>'),
        unsafe_allow_html=True,
    )
    st.caption(
        tr('Upload one or more PDFs and get editable Word reconstructions, exact-look copies, or both.')
    )
    _feature_row()

    st.caption(tr("Choose your files using Browse files, or drag them into the box below."))
    uploaded_files = st.file_uploader(
        "PDF",
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if not uploaded_files:
        st.markdown(
            tr('<div class="empty-hint">Drop one or more scanned forms, certificates, reports, or mixed-layout PDFs here.</div>'),
            unsafe_allow_html=True,
        )
        _privacy_note()
        return

    if len(uploaded_files) > MAX_FILES_PER_BATCH:
        st.error(tr('Choose at most {0} PDFs in one batch.', MAX_FILES_PER_BATCH))
        return

    digest = hashlib.sha256()
    documents: list[UploadDocument] = []
    total_bytes = 0
    for uploaded in uploaded_files:
        data = uploaded.getvalue()
        total_bytes += len(data)
        digest.update(uploaded.name.encode("utf-8", errors="replace"))
        digest.update(b"\0")
        digest.update(data)
        if len(data) > MAX_UPLOAD_BYTES:
            st.error(
                tr('{0} is larger than 100 MB. Split or compress it, then try again.', uploaded.name)
            )
            return
        try:
            info = inspect_pdf_bytes(data)
        except Exception as exc:
            st.error(tr('{0}: {1}', uploaded.name, exc))
            return
        documents.append(
            UploadDocument(
                name=uploaded.name,
                data=data,
                page_count=info.page_count,
                page_numbers=tuple(range(1, info.page_count + 1)),
            )
        )

    if total_bytes > MAX_BATCH_BYTES:
        st.error(tr('This batch is larger than 500 MB. Split it into two smaller batches.'))
        return

    upload_digest = digest.hexdigest()
    if st.session_state.get("upload_digest") != upload_digest:
        st.session_state["upload_digest"] = upload_digest
        for field in ("First page", "Last page"):
            st.session_state.get("conversion_preferences", {}).pop(field, None)
            st.session_state.pop("_conversion_" + field, None)

    for document in documents:
        st.markdown(
            tr('<div class="file-card"><span>{0}</span><span>{1} page{2} · {3:.1f} MB</span></div>', _escape(document.name), document.page_count, 's' if document.page_count != 1 else '', len(document.data) / 1024 / 1024),
            unsafe_allow_html=True,
        )

    if len(documents) == 1:
        document = documents[0]
        left, right = st.columns(2)
        with left:
            first_page = control('number_input', 'First page', 1, document.page_count, 1)
        with right:
            last_page = control(
                'number_input', 'Last page',
                1,
                document.page_count,
                document.page_count,
            )
        if first_page > last_page:
            st.warning(tr('The first page must come before the last page.'))
            return
        documents[0] = replace(
            document,
            page_numbers=tuple(range(int(first_page), int(last_page) + 1)),
        )
    else:
        total_pages = sum(document.page_count for document in documents)
        st.info(
            tr('Batch mode will process every page in all {0} PDFs ({1} pages total). Upload one PDF by itself to choose a page range.', len(documents), total_pages)
        )

    workflow = control('radio', 'Workflow', ["Convert only", "Convert & Translate"], horizontal=True)
    translation_options = None
    if workflow == "Convert & Translate":
        from translator import translation_settings
        translation_options = translation_settings()
        st.caption(tr('Translation starts automatically after each PDF is converted.'))

    st.subheader(tr('Word output'))
    editable = control(
        'checkbox', 'Translation-ready Word',
        value=True,
        help="Natural paragraphs, headings, lists, tables, headers, and footers that reflow while you translate.",
    )
    faithful = control(
        'checkbox', 'Exact-look reference',
        value=False,
        help="Optional image-based Word copy for visual comparison. It stays local and is not editable.",
    )
    if translation_options is not None and not editable:
        st.info(tr('Convert & Translate requires editable Word output.'))
    if not editable and not faithful:
        st.info(tr('Choose at least one Word output.'))

    word_style = control(
        'selectbox', 'Editable Word style', ["Compact translation", "Source typography"],
        disabled=not editable,
        help="Compact uses Times New Roman 12 pt, modest headings and single-spaced paragraphs for translation.",
    )
    mark_style = control(
        'selectbox', 'Signatures and stamps', ["Keep cropped images", "Editable text and signature labels"],
        disabled=not editable,
        help="Labels replace signature/stamp crops. Their transcribed wording stays editable. Photographs and maps remain images.",
    )
    skip_blank_pages = control(
        'checkbox', 'Skip pages with no detected content', value=True, disabled=not editable,
        help="Applies only to editable Word. Pages with images, marks or text are retained; exact-look output keeps every selected page.",
    )
    export_options = ExportOptions(
        style="compact" if word_style == "Compact translation" else "source",
        marks="editable" if mark_style == "Editable text and signature labels" else "images",
        skip_blank_pages=skip_blank_pages,
    )

    quality = control(
        'segmented_control', 'Quality',
        options=["Balanced", "Maximum"],
        default="Balanced",
        help="Maximum uses a higher-resolution scan and a second OCR verification pass. It is slower and uses more API tokens.",
    )
    reasoning_level = control(
        'segmented_control', 'OCR model',
        options=list(MODEL_PRESETS),
        default=DEFAULT_MODEL_PRESET,
        help=(
            "High Reasoning uses GPT-5.6 Sol for the hardest pages; Medium Reasoning "
            "uses GPT-5.6 Terra for a quality/cost balance; Low Reasoning uses "
            "GPT-5.6 Luna for the lowest cost."
        ),
    )
    include_native_text = control(
        'checkbox', 'Use embedded PDF text as an OCR aid',
        value=True,
        help="Improves born-digital PDFs. Turn it off if the PDF contains an incorrect hidden OCR layer.",
    )
    auto_download = control(
        'checkbox', 'Automatically download completed Word files', value=True,
        help="Downloads each Word file as soon as its PDF finishes. Your browser may ask to allow multiple downloads. Download buttons stay available below.",
    )
    with st.expander(tr('Advanced downloads')):
        include_json = control(
            'checkbox', 'Include diagnostic JSON files', value=False, key="include_diagnostic_json",
            help="Optional OCR layout and API usage files for troubleshooting. Leave off for Word-only downloads. Requesting layout data for an exact-look-only conversion also runs OCR.",
        )
    option_fingerprint = (
        upload_digest,
        tuple((document.name, document.page_numbers) for document in documents),
        editable,
        faithful,
        quality or "Balanced",
        reasoning_level or DEFAULT_MODEL_PRESET,
        include_native_text,
        include_json,
        export_options,
        tuple(sorted(translation_options.items())) if translation_options else None,
    )
    if st.session_state.get("conversion_options") != option_fingerprint:
        st.session_state["conversion_options"] = option_fingerprint
    _privacy_note()

    selected_page_count = sum(len(document.page_numbers) for document in documents)
    too_many_pages = selected_page_count > MAX_PAGES_PER_CONVERSION
    if too_many_pages:
        st.warning(
            tr('A batch can contain at most {0} pages total. This selection contains {1}; split it into smaller batches.', MAX_PAGES_PER_CONVERSION, selected_page_count)
        )

    button_label = (
        "Convert to Word"
        if len(documents) == 1
        else tr("Convert {0} PDFs to Word", len(documents))
    )
    if translation_options is not None:
        button_label = "Convert & Translate"
    from translator import translation_configuration_error
    translation_error = translation_configuration_error(translation_options) if translation_options else ""
    if translation_error:
        st.warning(tr(translation_error))
    translation_invalid = bool(translation_error) or translation_options is not None and (
        not editable or not all(translation_options[k].strip() for k in ("model", "source_language", "target_language"))
    )
    if translation_invalid:
        st.info(tr('Select editable Word and enter both languages and a translation model to continue.'))
    if st.button(
        tr(button_label),
        type="primary",
        use_container_width=True,
        disabled=not (editable or faithful) or too_many_pages or translation_invalid or bool(st.session_state.get("pdf_conversion_queue")),
    ):
        _run_batch_conversion(
            documents=documents,
            editable=editable,
            faithful=faithful,
            quality=quality or "Balanced",
            reasoning_level=reasoning_level or DEFAULT_MODEL_PRESET,
            include_native_text=include_native_text,
            include_json=include_json,
            export_options=export_options,
            auto_download=auto_download,
            translation_options=translation_options,
        )



def _password_gate() -> bool:
    expected_password = _site_password()
    if not expected_password:
        st.error(tr('This site is locked, but its password has not been configured.'))
        st.caption(
            tr('Add APP_PASSWORD = "your password" to the Streamlit Secrets box, then reboot the app.')
        )
        return False

    if st.session_state.get("layoutlens_authenticated"):
        _, sign_out_column = st.columns([5, 1])
        with sign_out_column:
            if st.button(tr('Sign out'), use_container_width=True):
                for key in list(st.session_state):
                    if key != "ui_language":
                        del st.session_state[key]
                st.rerun()
        return True

    st.markdown(tr('<div class="eyebrow">Private access</div>'), unsafe_allow_html=True)
    st.markdown(
        tr('<h1 class="hero-title">Metapërkthyesi</h1>'),
        unsafe_allow_html=True,
    )
    st.caption(tr('Enter the site password to open conversion and translation.'))

    locked_until = float(st.session_state.get("layoutlens_locked_until", 0.0))
    remaining = max(0, int(locked_until - time.time()))
    if remaining:
        st.error(tr('Too many incorrect attempts. Try again in {0} seconds.', remaining + 1))
        return False

    with st.form("layoutlens_password_form", clear_on_submit=True):
        entered_password = st.text_input(
            tr('Site password'),
            type="password",
            placeholder=tr('Enter password'),
        )
        submitted = st.form_submit_button(
            tr('Open LayoutLens'),
            type="primary",
            use_container_width=True,
        )

    if submitted:
        entered_digest = hashlib.sha256(entered_password.encode("utf-8")).digest()
        expected_digest = hashlib.sha256(expected_password.encode("utf-8")).digest()
        if hmac.compare_digest(entered_digest, expected_digest):
            st.session_state["layoutlens_authenticated"] = True
            st.session_state.pop("layoutlens_failed_logins", None)
            st.session_state.pop("layoutlens_locked_until", None)
            st.rerun()

        failures = int(st.session_state.get("layoutlens_failed_logins", 0)) + 1
        st.session_state["layoutlens_failed_logins"] = failures
        if failures >= 5:
            st.session_state["layoutlens_failed_logins"] = 0
            st.session_state["layoutlens_locked_until"] = time.time() + 30
            st.error(tr('Too many incorrect attempts. Try again in 30 seconds.'))
        else:
            st.error(tr('Incorrect password.'))
    return False


def _site_password() -> str:
    try:
        from .config import _get_setting

        return (_get_setting("APP_PASSWORD", "") or "").strip()
    except Exception:
        return ""


def _run_batch_conversion(
    *,
    documents: list[UploadDocument],
    editable: bool,
    faithful: bool,
    quality: str,
    reasoning_level: str,
    include_native_text: bool,
    include_json: bool,
    export_options: ExportOptions | None = None,
    auto_download: bool = True,
    translation_options: dict | None = None,
    _resume: bool = False,
) -> None:
    if not _resume:
        st.session_state["pdf_conversion_queue"] = dict(
            id=uuid.uuid4().hex, next_index=0, documents=documents, usage_reports=[],
            options=dict(editable=editable, faithful=faithful, quality=quality,
                         reasoning_level=reasoning_level, include_native_text=include_native_text,
                         include_json=include_json, export_options=export_options,
                         translation_options=translation_options),
        )
    queue = st.session_state["pdf_conversion_queue"]
    job_id = queue["id"]
    job_dir = JOBS_DIR / job_id
    JOBS_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    JOBS_DIR.chmod(0o700)
    job_dir.mkdir(exist_ok=True, mode=0o700)
    progress_bar = st.progress(0.0)
    status = st.empty()

    try:
        mode = "both" if editable and faithful else "editable" if editable else "faithful"
        needs_ocr = editable or include_json
        settings = Settings.from_environment(require_api_key=needs_ocr)
        preset = MODEL_PRESETS.get(
            reasoning_level,
            MODEL_PRESETS[DEFAULT_MODEL_PRESET],
        )
        settings = replace(
            settings,
            model=preset.model,
            reasoning_effort=preset.reasoning_effort,
            include_native_text=include_native_text,
        )
        settings = apply_quality_preset(settings, quality)
        displayed_progress = 0.0
        downloads = [entry for entry in st.session_state.get("downloads", []) if not entry[1].endswith(".zip")]
        usage_reports = queue["usage_reports"]
        failures: list[tuple[str, str]] = []
        files_with_word_output = 0
        file_count = len(documents)

        for index, document in enumerate(documents[queue["next_index"]:], start=queue["next_index"] + 1):
            document_dir = job_dir / f"document-{index:03d}"
            output_dir = document_dir / "output"
            document_dir.mkdir(exist_ok=True, mode=0o700)
            source_path = document_dir / _safe_filename(document.name)
            source_path.write_bytes(document.data)
            source_path.chmod(0o600)

            def progress(message: str, current: int, total: int) -> None:
                nonlocal displayed_progress
                status.text(tr('File {0}/{1}: {2} — Converting: {3}', index, file_count, document.name, tr(message)))
                phase_value = _phase_progress(message, current, total)
                if translation_options is not None:
                    phase_value *= 0.5
                overall_value = ((index - 1) + phase_value) / file_count
                displayed_progress = max(displayed_progress, overall_value)
                progress_bar.progress(displayed_progress)

            try:
                result = convert_pdf(
                    source_path,
                    output_dir,
                    page_numbers=list(document.page_numbers),
                    settings=settings,
                    mode=mode,
                    include_layout_json=include_json,
                    export_options=export_options,
                    progress=progress,
                )
            except PartialConversionError as exc:
                result = exc.result
                failures.append(
                    (
                        document.name,
                        _friendly_error(exc.__cause__ or exc),
                    )
                )
            except Exception as exc:
                failures.append((document.name, _friendly_error(exc)))
                queue["next_index"] = index
                displayed_progress = max(displayed_progress, index / file_count)
                progress_bar.progress(displayed_progress)
                continue

            if result.editable_docx or result.faithful_docx:
                files_with_word_output += 1
            is_batch = file_count > 1
            ready_downloads = _load_downloads(
                result,
                source_name=document.name if is_batch else None,
                filename_prefix=f"{index:02d}-" if is_batch else "",
                include_json=include_json,
            )
            # Retain results and advance the queue before translation or any UI
            # yield: an interrupted translation must not repeat completed OCR.
            st.session_state["downloads"] = downloads + ready_downloads
            queue["next_index"] = index
            usage = _load_usage_report(result)
            if usage is not None:
                usage_reports.append((document.name, usage))
                st.session_state["api_usage_report"] = _combine_usage_reports(usage_reports)
            if translation_options is not None and result.editable_docx:
                from translation_jobs import new_job, execute
                language = _safe_filename(translation_options["target_language"])
                prefix = f"{index:02d}-" if is_batch else ""
                name = f"{prefix}{result.editable_docx.stem}_{language}.docx"
                job = new_job(document.name, result.editable_docx.read_bytes(), translation_options, name)
                st.session_state.setdefault("pdf_translation_jobs", []).append(job)
                status.text(tr('File {0}/{1}: {2} — Translating', index, file_count, document.name))
                if execute(job):
                    ready_downloads.append((f"Download {document.name} — translated Word", name, job["output"]))
                    st.success(tr('{0} — Ready (converted and translated)', document.name))
                else:
                    failures.append((document.name, f'Translation failed: {job["error"]}. Converted files remain available.'))
            elif translation_options is None:
                st.success(tr('{0} — Ready', document.name))
            downloads.extend(ready_downloads)
            # Retain the manual fallback before attempting browser delivery.
            st.session_state["downloads"] = downloads.copy()
            if auto_download:
                for _, filename, data in ready_downloads:
                    if filename.endswith(".docx"):
                        try:
                            auto_download_word(filename, data, f"{job_id}:{index}:{filename}")
                        except Exception:
                            st.info(tr('{0} is ready. Use its download button below.', filename))
            displayed_progress = max(displayed_progress, index / file_count)
            progress_bar.progress(displayed_progress)

        combined_usage = _combine_usage_reports(usage_reports)
        if combined_usage is not None:
            st.session_state["api_usage_report"] = combined_usage
            if file_count > 1 and include_json:
                downloads.append(
                    (
                        "Download combined API usage report (JSON)",
                        "layoutlens-batch-api-usage.json",
                        json.dumps(
                            combined_usage,
                            ensure_ascii=False,
                            indent=2,
                        ).encode("utf-8"),
                    )
                )
        else:
            st.session_state.pop("api_usage_report", None)

        if file_count > 1 and downloads:
            downloads.insert(
                0,
                (
                    "Download all results (ZIP)",
                    "layoutlens-batch-results.zip",
                    _build_download_zip(downloads),
                ),
            )
        if downloads:
            st.session_state["downloads"] = downloads
        else:
            st.session_state.pop("pdf_translation_jobs", None)
            st.session_state.pop("downloads", None)

        progress_bar.progress(1.0)
        if failures:
            if file_count == 1:
                if files_with_word_output:
                    status.warning(
                        tr('Some processing could not finish, but the available Word output is ready below.')
                    )
                else:
                    status.error(
                        tr('Conversion stopped before a requested Word file was ready.')
                    )
            else:
                status.warning(
                    tr('Batch finished: {0} of {1} PDFs produced a Word file.', files_with_word_output, file_count)
                )
            for name, detail in failures:
                st.warning(tr('{0}: {1}', name, detail))
        else:
            noun = "PDF" if file_count == 1 else "PDFs"
            status.success(tr('Finished {0} {1}.', file_count, noun))
    except Exception as exc:
        st.session_state.pop("api_usage_report", None)
        st.error(tr('Conversion stopped: {0}', _friendly_error(exc)))
    finally:
        if queue["next_index"] >= len(documents):
            st.session_state.pop("pdf_conversion_queue", None)
        shutil.rmtree(job_dir, ignore_errors=True)


def _retry_pdf_translations(auto_download: bool, *, disabled: bool = False) -> None:
    from translation_jobs import execute, deliver, unfinished
    jobs = st.session_state.get("pdf_translation_jobs", [])
    failed = [job for job in jobs if unfinished(job)]
    if not failed:
        return
    from translator import translation_configuration_error
    error = next((translation_configuration_error(job["options"]) for job in failed
                  if translation_configuration_error(job["options"])), "")
    if error:
        st.warning(tr(error))
    disabled = disabled or bool(error)
    st.info(tr('{0} translation(s) can be retried using the converted Word files. OCR will not run again.', len(failed)))
    if not st.button(tr('Retry failed translations'), key="retry_pdf_translation", disabled=disabled):
        return
    downloads = [entry for entry in st.session_state.get("downloads", []) if not entry[1].endswith(".zip")]
    for job in failed:
        status = st.empty()
        status.info(tr('{0} — Translating', job['name']))
        if execute(job):
            downloads.append((f'Download {job["name"]} — translated Word', job["output_name"], job["output"]))
            st.session_state["downloads"] = downloads.copy()
            status.success(tr('{0} — Ready (converted and translated)', job['name']))
            if auto_download:
                deliver(job)
        else:
            status.warning(tr('{0} — Translation failed: {1}', job['name'], job['error']))
    if len(downloads) > 1:
        downloads.insert(0, ("Download all results (ZIP)", "layoutlens-batch-results.zip", _build_download_zip(downloads)))
    st.session_state["downloads"] = downloads


def _load_downloads(
    result,
    *,
    source_name: str | None = None,
    filename_prefix: str = "",
    include_json: bool = False,
) -> list[tuple[str, str, bytes]]:
    downloads: list[tuple[str, str, bytes]] = []

    def add(label: str, path: Path) -> None:
        path.chmod(0o600)
        button_label = (
            f"Download {source_name} — {label}"
            if source_name
            else f"Download {label}"
        )
        downloads.append(
            (
                button_label,
                f"{filename_prefix}{path.name}",
                path.read_bytes(),
            )
        )

    if result.editable_docx:
        add("translation-ready Word", result.editable_docx)
    if result.faithful_docx:
        add("exact-look Word", result.faithful_docx)
    if include_json and result.layout_json:
        add("OCR layout data (JSON)", result.layout_json)
    if include_json and result.usage_json:
        add("API usage report (JSON)", result.usage_json)
    return downloads


def _load_usage_report(result) -> dict | None:
    if not result.usage_json:
        return None
    try:
        return json.loads(result.usage_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _combine_usage_reports(
    reports: list[tuple[str, dict]],
) -> dict | None:
    if not reports:
        return None

    integer_fields = (
        "api_calls",
        "metered_responses",
        "unmetered_attempts",
        "input_tokens",
        "cached_input_tokens",
        "cache_write_input_tokens",
        "output_tokens",
        "reasoning_tokens",
        "total_tokens",
    )
    summaries = [report.get("summary", {}) for _, report in reports]
    summary = {
        field: sum(int(item.get(field, 0) or 0) for item in summaries)
        for field in integer_fields
    }
    costs = [item.get("estimated_cost_usd") for item in summaries]
    summary["estimated_cost_usd"] = (
        None
        if any(cost is None for cost in costs)
        else round(sum(float(cost) for cost in costs), 6)
    )
    summary["known_minimum_cost_usd"] = round(
        sum(float(item.get("known_minimum_cost_usd", 0) or 0) for item in summaries),
        6,
    )

    model_totals: dict[str, dict] = {}
    for _, report in reports:
        for entry in report.get("by_model", []):
            model = str(entry.get("model", ""))
            if not model:
                continue
            total = model_totals.setdefault(
                model,
                {
                    "model": model,
                    "api_calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "reasoning_tokens": 0,
                    "estimated_cost_usd": 0.0,
                    "_cost_unknown": False,
                },
            )
            for field in (
                "api_calls",
                "input_tokens",
                "output_tokens",
                "reasoning_tokens",
            ):
                total[field] += int(entry.get(field, 0) or 0)
            entry_cost = entry.get("estimated_cost_usd")
            if entry_cost is None:
                total["_cost_unknown"] = True
            else:
                total["estimated_cost_usd"] += float(entry_cost)

    by_model = []
    for model in sorted(model_totals):
        entry = model_totals[model]
        unknown = entry.pop("_cost_unknown")
        entry["estimated_cost_usd"] = (
            None
            if unknown
            else round(float(entry["estimated_cost_usd"]), 6)
        )
        by_model.append(entry)

    calls = []
    for document_name, report in reports:
        calls.extend(
            {"document": document_name, **call}
            for call in report.get("calls", [])
        )

    return {
        "pricing": reports[0][1].get("pricing", {}),
        "documents": [name for name, _ in reports],
        "summary": summary,
        "by_model": by_model,
        "calls": calls,
    }


def _build_download_zip(downloads: list[tuple[str, str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        used = set()
        for index, (_, filename, data) in enumerate(downloads, 1):
            candidate = filename
            while candidate in used:
                candidate = f"{index:02d}-" + candidate
            used.add(candidate)
            archive.writestr(candidate, data)
    return buffer.getvalue()


def _usage_summary() -> None:
    report = st.session_state.get("api_usage_report")
    if not report:
        return
    summary = report.get("summary", {})
    cost = summary.get("estimated_cost_usd")
    if cost is None:
        cost_label = "Unknown"
    elif cost < 0.01:
        cost_label = f"${cost:,.4f}"
    else:
        cost_label = f"${cost:,.2f}"

    st.subheader(tr('OCR usage'))
    st.caption(tr('These figures cover PDF conversion only. Translation usage and cost are not included.'))
    calls, input_tokens, output_tokens, estimated_cost = st.columns(4)
    calls.metric(tr('API calls'), f"{summary.get('api_calls', 0):,}")
    input_tokens.metric(tr('Input tokens'), f"{summary.get('input_tokens', 0):,}")
    output_tokens.metric(tr('Output tokens'), f"{summary.get('output_tokens', 0):,}")
    estimated_cost.metric(tr('Estimated cost'), cost_label)
    model_names = ", ".join(
        entry.get("model", "") for entry in report.get("by_model", []) if entry.get("model")
    ) or "No metered response"
    unmetered = summary.get("unmetered_attempts", 0)
    unknown_note = ""
    if unmetered:
        minimum = summary.get("known_minimum_cost_usd", 0)
        unknown_note = (
            f" {unmetered:,} request attempt(s) returned no token data, so the exact "
            f"cost is unknown; the metered minimum is ${minimum:,.4f}."
        )
    st.caption(
        tr('Model(s): {0} · Metered responses: {1:,} · Cached input: {2:,} · Cache-written input: {3:,} · Reasoning: {4:,} (already included in output) · Total tokens: {5:,}. Cost is estimated in USD at default-tier standard API rates; your billing dashboard is authoritative.{6}', model_names, summary.get('metered_responses', 0), summary.get('cached_input_tokens', 0), summary.get('cache_write_input_tokens', 0), summary.get('reasoning_tokens', 0), summary.get('total_tokens', 0), unknown_note)
    )


def _downloads() -> None:
    downloads = st.session_state.get("downloads", [])
    if not downloads:
        return
    st.subheader(tr('Your files'))
    for index, (label, filename, data) in enumerate(downloads):
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if filename.endswith(".json"):
            mime = "application/json"
        elif filename.endswith(".zip"):
            mime = "application/zip"
        st.caption(filename)
        st.download_button(_download_label(label), key=f"pdf-download-{index}", data=data, file_name=filename, mime=mime, use_container_width=True)


def _feature_row() -> None:
    st.markdown(
        tr('\n        <div class="feature-row">\n          <div><strong>Text + tables</strong><span>Editable Word elements</span></div>\n          <div><strong>Natural reflow</strong><span>Built for translation</span></div>\n          <div><strong>Visual fallback</strong><span>Pixel-faithful reference</span></div>\n        </div>\n        '),
        unsafe_allow_html=True,
    )


def _privacy_note() -> None:
    st.markdown(
        tr('<div class="privacy">When Translation-ready Word or JSON is selected, page images and optional embedded PDF text are sent to the OpenAI API for OCR. Exact-look-only conversions stay local.</div>'),
        unsafe_allow_html=True,
    )


def _styles() -> None:
    st.markdown(
        """
        <style>
        /* Streamlit owns foreground/background pairs for the active theme.
           Do not force a light canvas underneath dark-mode widget colors. */
        .block-container { max-width: 780px; padding-top: 4.2rem; padding-bottom: 5rem; }
        .hero-title { font-size: clamp(2.4rem, 6vw, 4.5rem) !important; letter-spacing: -0.055em !important; line-height: .98 !important; max-width: 720px; }
        .eyebrow { color: inherit; font-size: .78rem; font-weight: 760; letter-spacing: .14em; text-transform: uppercase; margin-bottom: .8rem; }
        [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p,
        [data-testid="stText"] { color: inherit; }
        [data-testid="stCaptionContainer"] { opacity: 1; }
        [data-testid="stFileUploader"] small { color: inherit; opacity: 1; }
        [data-testid="stCaptionContainer"] p { font-size: 1.08rem; max-width: 650px; }
        .feature-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 1.8rem 0 1.4rem; }
        .feature-row div { border: 1px solid currentColor; border-color: color-mix(in srgb, currentColor 35%, transparent); border-radius: 14px; padding: 14px 15px; }
        .feature-row strong, .feature-row span { display: block; }
        .feature-row strong { font-size: .92rem; }
        .feature-row span { font-size: .78rem; margin-top: 3px; }
        [data-testid="stFileUploaderDropzone"] { border-radius: 18px; min-height: 150px; }
        .empty-hint, .privacy { color: inherit; font-size: .82rem; margin-top: .8rem; }
        .privacy { border-left: 3px solid currentColor; padding-left: 10px; }
        .file-card { display: flex; justify-content: space-between; gap: 16px; align-items: center; padding: 14px 16px; margin: 1rem 0; border: 1px solid currentColor; border-color: color-mix(in srgb, currentColor 35%, transparent); border-radius: 12px; color: inherit; font-weight: 650; }
        .file-card span:last-child { font-size: .82rem; font-weight: 500; white-space: nowrap; }
        .stButton > button[kind="primary"] { border-radius: 12px; min-height: 50px; font-weight: 720; }
        /* Keep the brand button as a complete, high-contrast color pair. */
        button[data-testid="stBaseButton-primary"]:not(:disabled),
        button[kind="segmented_controlActive"]:not(:disabled),
        button[data-variant="segmented_control"][data-selected]:not([data-disabled]) { background-color: #126149; border-color: #126149; color: #ffffff; }
        button[data-testid="stBaseButton-primary"]:not(:disabled):hover,
        button[kind="segmented_controlActive"]:not(:disabled):hover,
        button[data-variant="segmented_control"][data-selected]:not([data-disabled]):hover { background-color: #0b4b38; border-color: #0b4b38; color: #ffffff; }
        .stDownloadButton > button { border-radius: 12px; min-height: 46px; }
        [data-testid="stMetric"] { border: 1px solid currentColor; border-color: color-mix(in srgb, currentColor 35%, transparent); border-radius: 12px; padding: 10px; }
        @media (max-width: 650px) { .feature-row { grid-template-columns: 1fr; } .file-card { align-items: flex-start; flex-direction: column; } }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _safe_filename(value: str) -> str:
    name = Path(value).name
    cleaned = "".join(char if char.isalnum() or char in {"-", "_", "."} else "-" for char in name)
    return cleaned or "document.pdf"


def _escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _phase_progress(message: str, current: int, total: int) -> float:
    ratio = min(1.0, current / total) if total else 0.0
    lowered = message.lower()
    if "render" in lowered:
        return 0.02 + 0.13 * ratio
    if "exact-look" in lowered:
        return 0.15 + 0.08 * ratio
    if "read" in lowered or "vision" in lowered:
        return 0.23 + 0.57 * ratio
    if "translation-ready" in lowered:
        return 0.80 + 0.16 * ratio
    return 0.96 * ratio


def _cleanup_stale_jobs() -> None:
    if not JOBS_DIR.is_dir():
        return
    cutoff = time.time() - JOB_RETENTION_SECONDS
    for candidate in JOBS_DIR.iterdir():
        try:
            if candidate.is_dir() and candidate.stat().st_mtime < cutoff:
                shutil.rmtree(candidate, ignore_errors=True)
        except OSError:
            continue


def _friendly_error(error: Exception) -> str:
    message = str(error).strip()
    if "OPENAI_API_KEY" in message:
        return message
    if "401" in message or "authentication" in message.lower():
        return "The OpenAI API key was rejected. Check the key in your environment file."
    if "rate" in message.lower() and "limit" in message.lower():
        return "The OpenAI API is temporarily rate-limited. Wait a moment, then retry."
    return message or "An unexpected conversion error occurred."


def _download_label(label):
    if label.startswith("Download ") and " — " in label:
        name, description = label[9:].rsplit(" — ", 1)
        if description == "translated Word":
            return tr("Download {0} — translated Word", name)
        return tr("Download {0} — {1}", name, tr(description))
    if label.startswith("Download ") and label not in ("Download all results (ZIP)", "Download combined API usage report (JSON)"):
        return tr("Download {0}", tr(label[9:]))
    return tr(label)


def _saved_pdf_results():
    auto_download = st.session_state.get("conversion_preferences", {}).get("Automatically download completed Word files", True)
    queue = st.session_state.get("pdf_conversion_queue")
    if not (queue or st.session_state.get("downloads") or st.session_state.get("pdf_translation_jobs")):
        return
    st.subheader(tr("Saved PDF results"))
    st.caption(tr("Completed files stay available in this session until you clear them or sign out."))
    if st.button(tr("Clear saved PDF results"), key="clear_pdf_results"):
        for key in ("downloads", "pdf_translation_jobs", "pdf_conversion_queue", "api_usage_report"):
            st.session_state.pop(key, None)
        return
    if queue:
        remaining = len(queue["documents"]) - queue["next_index"]
        st.info(tr("Conversion was interrupted. {0} document(s) remain. Completed files will not be converted again.", remaining))
        if st.button(tr("Continue conversion"), key="resume_pdf_conversion"):
            _run_batch_conversion(documents=queue["documents"], auto_download=auto_download,
                                  _resume=True, **queue["options"])
    # A rerun can arrive immediately after translation completes but before
    # its download was added. Reconcile the retained result without API work.
    downloads = st.session_state.get("downloads", [])
    for job in st.session_state.get("pdf_translation_jobs", []):
        if job["status"] == "Ready" and not any(name == job["output_name"] and data == job["output"] for _, name, data in downloads):
            downloads = [entry for entry in downloads if not entry[1].endswith(".zip")]
            downloads.append((f'Download {job["name"]} — translated Word', job["output_name"], job["output"]))
            st.session_state["downloads"] = downloads
    _retry_pdf_translations(auto_download)
    _usage_summary()
    _downloads()
