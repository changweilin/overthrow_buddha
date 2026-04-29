# Analysis Project

Tools for Traditional Chinese summaries, archive indexing, and follow-up media downloads.

## Commands

```powershell
python analysis_project\generate_summaries.py
python analysis_project\build_index.py
python analysis_project\download_pending_media.py --dry-run
```

`generate_summaries.py` uses `GEMINI_API_KEY` from `.env` when the Gemini Python SDK is available. Without it, each article receives a pending Chinese summary file and metadata is marked `pending_model`.

`download_pending_media.py` downloads only media explicitly marked `pending_download`. Videos are skipped unless `--include-videos` is passed, and each item is capped by `--max-mb`.

