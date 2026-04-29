# 無人機 OSINT 爬蟲與分析專案

此專案將公開來源的現代戰爭無人機相關資料分成兩個子專案管理：

- `crawler_project/`：負責公開 OSINT 來源收集、去重、更新判斷、媒體管理與每日排程。
- `analysis_project/`：負責繁體中文摘要、索引建立與未下載媒體的後續補抓。

資料會輸出到 `data/intel_archive/`。每篇文章以獨立資料夾保存，包含 `original.md`、`summary.zh.md`、`metadata.json` 與 `media/`。

## 安全邊界

此專案只保存公開新聞、研究、政策與高層次戰場趨勢觀察。若來源含武器製作、改裝、攻擊流程、目標選擇、坐標或繞過防護等可操作細節，系統會標記 `restricted_detail`，摘要與歸檔只保留高層次背景，不重述操作性內容。

## 常用命令

```powershell
python crawler_project\run_crawler.py --dry-run
python crawler_project\run_crawler.py --limit 5
python analysis_project\generate_summaries.py
python analysis_project\build_index.py
python analysis_project\download_pending_media.py --dry-run
```

如果 `python` 不在 PATH，請改用完整的 `python.exe` 路徑。

## 每日排程

註冊 Windows Task Scheduler 每日任務：

```powershell
powershell -ExecutionPolicy Bypass -File crawler_project\scripts\register_daily_task.ps1 -DailyTime "06:30"
```

目前預設流程會依序執行：

1. 爬取公開來源
2. 產生或更新中文摘要
3. 重建 `data/intel_archive/index.json`

更多細節請看：

- `crawler_project/README.zh.md`
- `analysis_project/README.zh.md`

