"""RSS feed generation.

Creates an RSS 2.0 feed (with iTunes namespace extensions) from the episode
history and configuration, writing it to ``feed.xml``.
"""

import logging
import os
import xml.sax.saxutils as saxutils
from datetime import datetime, timezone
from typing import Any

from .cache import read_cache_json, get_cache_path
from .episodes import load_episodes

logger = logging.getLogger(__name__)


def step_generate_rss(config: dict[str, Any]) -> None:
    """Generate an RSS feed XML file (``feed.xml``) from the episode list.

    In CI mode, the feed is built from the persistent ``episodes.json``;
    otherwise it is built from the single locally-cached paper.

    Args:
        config: Runtime configuration dictionary.  Requires
            ``output.release_base_url`` and ``output.feed_base_url`` keys
            in the configuration.

    Raises:
        ValueError: If ``output.release_base_url`` or
            ``output.feed_base_url`` are not configured.
    """
    rss_file = "feed.xml"
    show_title = config["podcast"]["show_name"]
    show_desc = config["podcast"]["show_description"]
    base_url = config.get("output", {}).get("release_base_url")
    if not base_url:
        raise ValueError("Missing 'output.release_base_url' in config.json")
    feed_base_url = config.get("output", {}).get("feed_base_url")
    if not feed_base_url:
        raise ValueError("Missing 'output.feed_base_url' in config.json")

    if config.get("is_github_run"):
        episodes = load_episodes()
    else:
        data = read_cache_json(config)
        paper = data.get("selected", {}) if isinstance(data, dict) else {}
        if not paper:
            logger.warning("No cached paper found. Generating empty RSS.")
            episodes = []
        else:
            audio_path = get_cache_path(config, "audio")
            size = os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
            episodes = [{
                "title": paper.get("title", "Local Episode"),
                "description": paper.get("selection_reason", ""),
                "pubDate": datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000"),
                "filename": os.path.basename(audio_path) if audio_path else "",
                "tag": "local",
                "guid": paper.get("id", "local"),
                "size": size,
            }]

    items_xml = ""
    for ep in episodes:
        title = saxutils.escape(ep['title'])
        description = saxutils.escape(ep['description'])
        guid = saxutils.escape(ep['guid'])
        tag = saxutils.escape(ep['tag'])
        filename = saxutils.escape(ep['filename'])
        pub_date = saxutils.escape(ep['pubDate'])
        size = ep.get('size', 10485760)

        items_xml += f"""    <item>
      <title>{title}</title>
      <description>{description}</description>
      <pubDate>{pub_date}</pubDate>
      <enclosure url="{base_url}/releases/download/{tag}/{filename}" type="audio/mpeg" length="{size}"/>
      <guid>{guid}</guid>
    </item>
"""

    rss_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>{show_title}</title>
    <description>{show_desc}</description>
    <link>{base_url}/releases</link>
    <language>en-us</language>
    <itunes:author>{config['podcast']['author']}</itunes:author>
    <itunes:image href="{feed_base_url}/{config['output']['album_art_file']}"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:category text="Technology"/>
{items_xml}
  </channel>
</rss>"""
    with open(rss_file, "w") as f:
        f.write(rss_template.strip())
    logger.info(f"RSS Feed XML structured and exported: {rss_file}")
