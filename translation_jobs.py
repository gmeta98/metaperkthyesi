from interface import tr
"""Session-local translation results shared by the two pages."""
import hashlib
import json
import uuid
from pathlib import Path

import streamlit as st


def fingerprint(files, options):
    digest = hashlib.sha256(json.dumps(options, sort_keys=True).encode())
    for name, data in files:
        digest.update(json.dumps([name, len(data)]).encode())
        digest.update(data)
    return digest.hexdigest()


def new_job(name, data, options, output_name=None):
    language = "".join(c if c.isalnum() or c in "-_" else "-" for c in options["target_language"])
    return dict(id=uuid.uuid4().hex, name=name, source=data, options=dict(options),
                output_name=output_name or f"{Path(name).stem}_{language}.docx",
                status="Pending", output=None, pairs=[], error="")


def execute(job):
    from translator import translate_document
    job.update(status="Translating", error="")
    try:
        output, pairs = translate_document(job["source"], **job["options"])
    except Exception as exc:
        job.update(status="Failed", error=str(exc) or "Translation failed.")
        return False
    else:
        job.update(status="Ready", output=output, pairs=pairs)
        # A completed job never needs the source bytes for a retry.
        job["source"] = b""
        return True
    finally:
        # Streamlit rerun/stop signals inherit BaseException. Preserve its
        # control flow while retaining the source and making work retryable.
        if job["status"] == "Translating":
            job.update(status="Interrupted", error="Processing was interrupted. You can retry this document.")


def unfinished(job):
    return job["status"] in {"Pending", "Failed", "Interrupted", "Translating"}


def deliver(job):
    from ocr_reader.downloads import auto_download_word
    try:
        auto_download_word(job["output_name"], job["output"], job["id"])
    except Exception:
        st.info(tr('{0} is ready. Use its download button below.', job['output_name']))


def run_pending(jobs, auto_download):
    for index, job in enumerate(jobs, 1):
        if not unfinished(job):
            continue
        status = st.empty()
        status.info(tr('{0}/{1}: {2} — Translating', index, len(jobs), job['name']))
        if execute(job):
            status.success(tr('{0} — Ready', job['name']))
            if auto_download:
                deliver(job)
        else:
            status.warning(tr('{0} — Translation failed: {1}', job['name'], job['error']))
