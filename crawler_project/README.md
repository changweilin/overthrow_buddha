# Crawler Project

Public OSINT crawler for modern drone warfare reporting and research. It is intentionally slow, single-threaded, and bounded to public sources.

## Commands

```powershell
python crawler_project\run_crawler.py --dry-run
python crawler_project\run_crawler.py --limit 5
python crawler_project\run_crawler.py --source "Defense News Unmanned"
```

If `python` is not on PATH, replace it with a full `python.exe` path.

## Daily Schedule

Register a Windows Task Scheduler job:

```powershell
powershell -ExecutionPolicy Bypass -File crawler_project\scripts\register_daily_task.ps1 -DailyTime "06:30"
```

If Python is not discoverable:

```powershell
powershell -ExecutionPolicy Bypass -File crawler_project\scripts\register_daily_task.ps1 -DailyTime "06:30" -PythonPath "C:\Path\To\python.exe"
```

The scheduled job runs:

1. `crawler_project\run_crawler.py`
2. `analysis_project\generate_summaries.py`
3. `analysis_project\build_index.py`

Logs are written to `crawler_project\logs`.

## Safety Boundary

The crawler is for high-level public OSINT: news, policy, research, and trend analysis. It does not bypass login, CAPTCHA, robots.txt, or rate limits. If a source appears to include operational attack or weaponization detail, the archive marks it as `restricted_detail` and stores only high-level context in `original.md`.

