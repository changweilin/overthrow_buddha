# 分析子專案

此子專案負責處理爬蟲收集後的資料，包括繁體中文摘要、archive 索引建立，以及後續補下載尚未下載的媒體。

## 功能

- 對缺少 `summary.zh.md` 或標記為 `needs_update` 的文章產生繁體中文摘要。
- 優先使用 `.env` 中的 `GEMINI_API_KEY` 與 `GEMINI_MODEL`。
- 若 Gemini API key 或 Python SDK 不可用，會建立待處理摘要檔，並在 metadata 中標記 `pending_model`。
- 建立 `data/intel_archive/index.json`，供前端或後續分析使用。
- 補下載 metadata 中標記為 `pending_download` 的媒體。

## 常用命令

```powershell
python analysis_project\generate_summaries.py
python analysis_project\generate_summaries.py --force
python analysis_project\build_index.py
python analysis_project\download_pending_media.py --dry-run
```

媒體補下載：

```powershell
python analysis_project\download_pending_media.py --max-mb 10
python analysis_project\download_pending_media.py --include-videos --max-mb 50
```

影片預設不下載。只有在 metadata 中明確標記為 `pending_download`，且命令加入 `--include-videos` 時，才會嘗試下載影片。

## 輸出資料

每篇文章會存放在：

```text
data/intel_archive/articles/<source>/<article-id>/
```

主要檔案：

- `original.md`：來源文章整理版 Markdown。
- `summary.zh.md`：繁體中文摘要。
- `metadata.json`：URL、標題、來源、hash、更新狀態與媒體狀態。
- `media/`：下載的圖片或後續補抓的媒體。

## 安全摘要規則

摘要只應提供高層次背景、趨勢、技術概念與可信度限制。若原文包含可操作的武器化、攻擊、改裝、坐標、繞過防護或具體步驟，摘要不得重述這些細節，僅標記並保留非操作性背景。

