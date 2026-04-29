# 爬蟲子專案

此子專案負責收集公開 OSINT 來源中的現代戰爭無人機相關資料。爬取方式採單執行緒、慢速、尊重 `robots.txt`，不進行登入繞過、CAPTCHA 繞過、反爬規避或高頻率請求。

## 功能

- 從 `config/sources.yaml` 讀取來源設定。
- 支援 RSS 與一般 HTML 來源探索。
- 使用 `ETag` / `Last-Modified` 條件請求判斷是否更新。
- 若來源未提供更新標頭，使用正文 hash 判斷內容是否變更。
- 已爬過且未更新的文章只更新 `last_seen`，不重寫 Markdown、不重抓圖片。
- 圖片預設下載到文章資料夾的 `media/`。
- 影片預設只保存外部連結，不下載原檔。
- 每次執行會輸出 log 到 `crawler_project/logs/`。

## 常用命令

```powershell
python crawler_project\run_crawler.py --dry-run
python crawler_project\run_crawler.py --limit 5
python crawler_project\run_crawler.py --source "Defense News Unmanned"
```

參數說明：

- `--dry-run`：只檢查來源與候選文章，不寫入 archive。
- `--limit`：覆蓋來源設定中的文章數量上限。
- `--source`：只執行指定來源名稱。
- `--no-delay`：跳過慢速等待，主要用於本機驗證。

## 來源設定

來源設定放在：

```text
crawler_project/config/sources.yaml
```

每個來源可設定名稱、URL、允許網域、候選文章篩選字串、媒體策略與延遲範圍。初版已包含 Defense News 無人系統 RSS。

## 每日排程

註冊每日任務：

```powershell
powershell -ExecutionPolicy Bypass -File crawler_project\scripts\register_daily_task.ps1 -DailyTime "06:30"
```

如果系統找不到 Python：

```powershell
powershell -ExecutionPolicy Bypass -File crawler_project\scripts\register_daily_task.ps1 -DailyTime "06:30" -PythonPath "C:\Path\To\python.exe"
```

排程會執行：

1. `crawler_project\run_crawler.py`
2. `analysis_project\generate_summaries.py`
3. `analysis_project\build_index.py`

## 安全邊界

爬蟲只處理公開來源中的高層次 OSINT 內容，例如新聞、政策、研究、裝備趨勢與戰場觀察。若文章疑似包含武器製作、改裝、攻擊流程、目標選擇或其他可操作細節，系統會標記 `restricted_detail`，並避免在本地 Markdown 中重述操作性內容。

