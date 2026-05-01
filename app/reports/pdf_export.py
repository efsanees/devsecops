"""
PDF rapor üretici.

Önce WeasyPrint ile PDF üretmeyi dener.
WeasyPrint başarısız olursa (Windows'ta GTK eksik olabilir)
HTML döndürür — browser'dan Ctrl+P → PDF Olarak Kaydet ile kullanılabilir.

render_pdf() → (bytes, is_pdf: bool)
  is_pdf=True  → application/pdf olarak sun
  is_pdf=False → text/html olarak sun
"""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from app.reports.markdown_export import _build_context

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _render_html(job_result: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    # HTML şablonunda dsomm.categories.get() kullanıyoruz — dict metoduna izin ver
    env.policies["json.dumps_kwargs"] = {"ensure_ascii": False}
    template = env.get_template("report.html.j2")
    ctx = _build_context(job_result)
    return template.render(**ctx)


def render_pdf(job_result: dict) -> tuple[bytes, bool]:
    """
    Returns:
        (content_bytes, is_pdf)
        is_pdf=True  → PDF üretildi, application/pdf ile sun
        is_pdf=False → HTML üretildi, text/html ile sun
    """
    html = _render_html(job_result)

    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html).write_pdf()
        logger.info("PDF üretildi: %d bayt", len(pdf_bytes))
        return pdf_bytes, True
    except Exception as exc:
        # WeasyPrint kurulu değil veya GTK eksik — HTML fallback
        logger.warning("WeasyPrint başarısız (%s), HTML döndürülüyor", exc)
        return html.encode("utf-8"), False
