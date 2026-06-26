"""Fetch recent AI paper metadata from the arXiv Atom API.

Queries the arXiv API for the latest papers in a configured category,
parses the XML response, and persists the results to the shared cache.
"""

import logging
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from .cache import read_cache_json, write_cache_json

logger = logging.getLogger(__name__)


def step_fetch_arxiv(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Fetch the latest papers from arXiv and store them in the cache.

    If papers are already present in the cache they are returned immediately
    without making a network request. Otherwise, the arXiv Atom API is queried
    and the results are parsed and written to the cache before being returned.

    Args:
        config: Runtime configuration dictionary. Relevant keys:
            ``config["paper"]["fetch"]["arxiv_category"]`` — arXiv category
            string (e.g. ``"cs.AI"``).
            ``config["paper"]["fetch"]["num_latest_papers"]`` — maximum number
            of papers to fetch.

    Returns:
        A list of paper dicts, each containing ``title``, ``summary``, ``id``,
        ``published``, and ``authors`` keys.

    Raises:
        RuntimeError: If the arXiv API returns invalid XML.
    """
    data = read_cache_json(config)
    if isinstance(data, dict) and "papers" in data:
        logger.info("Loading papers from cache.")
        return data["papers"]

    category = config["paper"]["fetch"]["arxiv_category"]
    max_results = config["paper"]["fetch"]["num_latest_papers"]
    url = (
        f"https://export.arxiv.org/api/query"
        f"?search_query=cat:{category}"
        f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    )

    logger.info(f"Fetching from arXiv: {url}")
    with urllib.request.urlopen(url, timeout=30) as response:
        xml_data = response.read()

    logger.debug(f"Raw arXiv response snippet: {xml_data[:500]}...")

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as exc:
        preview = xml_data[:200].decode("utf-8", errors="replace")
        raise RuntimeError(
            f"arXiv API returned invalid XML (ParseError: {exc}). "
            f"Response preview: {preview!r}"
        ) from exc
    namespaces = {"atom": "http://www.w3.org/2005/Atom"}
    papers = []
    for entry in root.findall("atom:entry", namespaces):
        title_el = entry.find("atom:title", namespaces)
        summary_el = entry.find("atom:summary", namespaces)
        id_el = entry.find("atom:id", namespaces)
        published_el = entry.find("atom:published", namespaces)
        author_els = entry.findall("atom:author", namespaces)
        authors = []

        if (
            title_el is None or summary_el is None
            or id_el is None or published_el is None
        ):
            logger.warning("Skipping arXiv entry with missing fields")
            continue

        title = title_el.text.strip().replace("\n", " ")
        summary = summary_el.text.strip().replace("\n", " ")
        id_url = id_el.text.strip()
        published = published_el.text.strip()
        for author_el in author_els:
            name_el = author_el.find("atom:name", namespaces)
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())

        papers.append({
            "title": title,
            "summary": summary,
            "id": id_url,
            "published": published,
            "authors": authors,
        })

    data["papers"] = papers
    write_cache_json(data, config)
    logger.info(f"Fetched {len(papers)} papers from arXiv.")
    return papers
