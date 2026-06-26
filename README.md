<p align="center">
  <img src="assets/album_art.png" alt="Podcast-AI" width="180"/>
</p>

<h1 align="center">🎙️ Podcast-AI</h1>
<p align="center">
  <em>Automated arXiv research paper → conversational podcast pipeline</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-≥3.13-blue?logo=python" alt="Python 3.13+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/status-active-brightgreen" alt="Status: Active">
</p>

---

## 📖 Overview

Podcast-AI is a lightweight automated pipeline that transforms a selected arXiv research paper into a short conversational podcast episode. From paper discovery through RSS distribution (and optionally YouTube upload), every step is driven by a single command or run incrementally step by step.

<p align="center">
  <b>Fetch → Select → PDF → Chunk Summary → Final Summary → Script → Audio → Video → Release → RSS → Upload</b>
</p>

---

## ✨ Features

- **📄 Paper Discovery** – Fetches latest papers from arXiv by category
- **🤖 Multi-Provider LLM** – Supports OpenRouter, Ollama, GitHub, LM Studio, and Ollama Cloud
- **📝 Smart Summarization** – Chunked PDF summarization + final synthesis
- **🎤 Natural TTS** – Conversational script generation with `edge-tts`
- **🎬 Video Assembly** – Combines album art + audio into a shareable video
- **📡 RSS & Releases** – Generates a podcast RSS feed and GitHub Releases
- **☁️ YouTube Upload** – Optional automated upload to YouTube
- **🔁 CI/CD Ready** – Ships with a GitHub Actions workflow for fully automated runs

---

## 🧱 Pipeline Architecture

| Step | Description |
|------|-------------|
| `fetch` | Pull recent papers from arXiv based on configured category |
| `select` | Choose the best paper via LLM scoring |
| `pdf` | Download and extract text from the paper PDF |
| `chunk_summary` | Summarise each chunk of the PDF independently |
| `final_summary` | Synthesise chunk summaries into a coherent overview |
| `script` | Generate a conversational podcast script from the summary |
| `audio` | Produce TTS audio (MP3) for each host using `edge-tts` |
| `video` | Assemble video from album art + generated audio |
| `release` | Prepare release artifacts and update episode history |
| `rss` | Generate an RSS feed (`feed.xml`) |
| `upload` | Upload episode to YouTube (requires credentials) |
| `clear` | Remove all cached data |

Run the **full pipeline** with a single command, or execute any step in isolation via `--step`.

---

## 📋 Prerequisites

- **Python ≥ 3.13**
- **FFmpeg** – required for the `video` step ([install guide](https://ffmpeg.org/download.html))
- **API credentials** – for LLM providers and/or YouTube (optional depending on your chosen features)

---

## 🚀 Installation

### Option 1 — pip (classic)

```bash
git clone https://github.com/your-username/Podcast-AI.git
cd Podcast-AI
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Option 2 — uv (fast)

```bash
git clone https://github.com/your-username/Podcast-AI.git
cd Podcast-AI
uv venv
source .venv/bin/activate
uv sync
```

> A `uv.lock` is included — `uv sync` restores the exact dependency tree.

---

## ⚙️ Configuration

### `config.json` (required)

All runtime settings live in `config.json` at the repository root. Key sections:

| Section | Purpose |
|---------|---------|
| `paper` | arXiv category, fetch count, chunk sizes |
| `llm` | Default provider, per-provider base URLs & timeouts, step-specific overrides |
| `script` | Target word count for the generated script |
| `podcast` | Show name, description, host names |
| `voice` | TTS voice names, speaking rate, pitch, timeouts |
| `output` | Paths and base URLs for releases and RSS |
| `cache` | Cache directory and filenames |
| `logging` | Log level (`DEBUG`, `INFO`, etc.) |
| `prompts` | Prompt templates used during selection, summarisation, and script generation |

### Environment variables / `.env`

Create a `.env` file (or export variables) for any API keys your providers require:

| Variable | Required for |
|----------|--------------|
| `OPENROUTER_API_KEY` | OpenRouter provider |
| `GH_API_KEY` | GitHub-hosted models |
| `OLLAMA_API_KEY` | Ollama Cloud provider |
| `YOUTUBE_CLIENT_ID` | YouTube upload |
| `YOUTUBE_CLIENT_SECRET` | YouTube upload |
| `YOUTUBE_REFRESH_TOKEN` | YouTube upload |

---

## 🎯 Usage

### Full pipeline

```bash
python main.py
```

This runs every step in order: `fetch` → `select` → `pdf` → `chunk_summary` → `final_summary` → `script` → `audio` → `video` → `release` → `rss` → `upload`.

### Single step

Run any step in isolation:

```bash
python main.py --step fetch
python main.py --step select
python main.py --step script
python main.py --step clear
```

Available steps: `fetch`, `select`, `pdf`, `chunk_summary`, `final_summary`, `script`, `audio`, `video`, `release`, `rss`, `upload`, `clear`.

### Cache management

Cache files are stored under the directory configured in `cache.directory` (default: `.podcast_cache`). To wipe all cached data:

```bash
python main.py --step clear
```

---

## 🧩 LLM Providers

The project includes a modular LLM layer under `podcast/llm/`. Each provider module implements a common interface:

| Provider | Module | Description |
|----------|--------|-------------|
| OpenRouter | `openrouter.py` | Routes queries through OpenRouter's multi-model API |
| Ollama | `ollama.py` | Local LLM inference via Ollama |
| Ollama Cloud | `ollama_cloud.py` | Managed Ollama endpoint |
| GitHub | `github.py` | GitHub-hosted models (requires `GH_API_KEY`) |
| LM Studio | `lm_studio.py` | Local LM Studio server |

Select and configure your active provider in `config.json` under the `llm` section.

---

## 🤖 CI/CD

The repository includes a GitHub Actions workflow (`.github/workflows/podcast.yml`) that fully automates the pipeline:

1. Installs system dependencies (FFmpeg) and Python
2. Installs Python requirements
3. Runs the full pipeline
4. Commits updated `episodes.json` (if any changes)
5. Creates a GitHub Release containing the generated MP3 and paper JSON
6. Deploys `feed.xml` and assets to GitHub Pages

The release step detects CI mode via the `GITHUB_ACTIONS=true` environment variable (set automatically by GitHub Actions). The release tag is derived from the current UTC date in `YYYYMMDD` format (e.g. `podcast-20250115`).

---

## 📁 Project Structure

```
Podcast-AI/
├── main.py                 # CLI entry point and pipeline orchestration
├── config.json             # All runtime configuration
├── episodes.json           # Episode history (used by RSS generation)
├── requirements.txt        # pip dependencies
├── pyproject.toml          # Project metadata & uv/pip build config
├── uv.lock                 # Locked dependency tree (uv)
├── assets/
│   └── album_art.png       # Podcast cover art
├── podcast/
│   ├── arxiv.py            # arXiv paper fetching
│   ├── audio.py            # TTS audio generation
│   ├── cache.py            # Atomic cache read/write helpers
│   ├── chunk_summary.py    # Per-chunk LLM summarisation
│   ├── config.py           # config.json loading & validation
│   ├── episodes.py         # episodes.json management
│   ├── final_summary.py    # Final synthesis of chunk summaries
│   ├── log.py              # Logging setup
│   ├── pdf.py              # PDF download & text extraction
│   ├── release.py          # Artifact preparation & release management
│   ├── rss.py              # RSS feed generation
│   ├── script.py           # Conversational script generation
│   ├── selection.py        # Best-paper selection via LLM
│   ├── utils.py            # Shared utilities
│   ├── video.py            # Video assembly (album art + audio)
│   ├── youtube.py          # YouTube upload
│   └── llm/                # LLM provider modules
│       ├── _format.py
│       ├── openrouter.py
│       ├── ollama.py
│       ├── ollama_cloud.py
│       ├── github.py
│       └── lm_studio.py
└── .github/workflows/
    └── podcast.yml         # GitHub Actions automation
```

---

## 🔧 Troubleshooting

- **`config.json` not found** – Ensure `config.json` exists at the project root (see `config.json` for a template).
- **TTS / audio step fails** – The `audio` step requires network access to the `edge-tts` endpoint. Check your network and the `voice` settings in `config.json`.
- **FFmpeg not found** – Install FFmpeg via your package manager (`sudo apt install ffmpeg`, `brew install ffmpeg`, or download from [ffmpeg.org](https://ffmpeg.org/download.html)).
- **LLM provider errors** – Verify that the required environment variable (e.g. `OPENROUTER_API_KEY`) is set and that the provider URL is reachable.
- **YouTube upload fails** – Ensure `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, and `YOUTUBE_REFRESH_TOKEN` are all set correctly.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Open an issue to discuss your feature or bugfix
2. Fork the repository and create a branch
3. Make your changes, adding tests where appropriate
4. Open a pull request

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.
