import logging
import os

import requests

from .cache import get_cache_dir, read_cache_json, write_cache_json

logger = logging.getLogger(__name__)


def _get_paper_from_cache(data):
    """Return the selected paper dict from the unified cache data."""
    if isinstance(data, dict) and data.get("selected"):
        return data["selected"]
    raise KeyError(
        "No selected paper found in cache; run the 'select' step first."
    )


def _download_pdf(pdf_url, pdf_cache_path):
    """Download *pdf_url* to *pdf_cache_path*, retrying once on failure."""
    logger.info(f"Downloading PDF from arXiv: {pdf_url}")
    for attempt in range(2):
        try:
            resp = requests.get(pdf_url, timeout=60)
            resp.raise_for_status()
            with open(pdf_cache_path, "wb") as pf:
                pf.write(resp.content)
            logger.info(f"Saved PDF to {pdf_cache_path}")
            return
        except Exception as e:
            if attempt == 1:
                logger.exception(
                    "Failed to download PDF after 2 attempts: %s", e
                )
                raise
            logger.warning(
                f"PDF download failed (attempt 1/2): {e}. Retrying..."
            )


def _extract_pages(pdf_cache_path):
    """Extract per-page text from *pdf_cache_path* using pypdf."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(pdf_cache_path)
        pages = []
        for p in reader.pages:
            try:
                text = p.extract_text() or ""
            except Exception:
                text = ""
            pages.append(text)
        logger.info(f"Extracted {len(pages)} pages from PDF")
        return pages
    except Exception as e:
        logger.exception("PDF text extraction failed: %s", e)
        raise


def step_pdf(config):
    data = read_cache_json(config)

    # Return early if pages are already cached.
    paper = _get_paper_from_cache(data)
    if paper.get("pages_text"):
        logger.info("Loading paper detail from cache.")
        return paper

    id_url = paper.get("id", "")
    if not id_url:
        raise ValueError(
            "Paper has no 'id' field. Cannot construct PDF URL."
        )
    arxiv_id = id_url.rstrip("/").split("/")[-1]
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    cache_dir = get_cache_dir(config)
    pdf_cache_path = os.path.join(cache_dir, f"{arxiv_id}.pdf")

    if os.path.exists(pdf_cache_path):
        logger.info(f"Using cached PDF at {pdf_cache_path}")
    else:
        _download_pdf(pdf_url, pdf_cache_path)

    pages = _extract_pages(pdf_cache_path)

    paper_detail = dict(paper)
    paper_detail["pdf_url"] = pdf_url
    paper_detail["pdf_cache_path"] = pdf_cache_path
    paper_detail["pages_text"] = pages

    data["selected"] = paper_detail
    write_cache_json(data, config)
    logger.info("Paper detail persisted to paper.json")
    return paper_detail
