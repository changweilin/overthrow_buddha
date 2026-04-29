(function () {
  const DATA_BASE = "../data/intel_archive/";
  const state = {
    articles: [],
    filtered: [],
    selectedId: "",
    view: "card",
  };

  const el = {
    articleCount: document.getElementById("article-count"),
    generatedAt: document.getElementById("generated-at"),
    resultCount: document.getElementById("result-count"),
    list: document.getElementById("article-list"),
    empty: document.getElementById("empty-state"),
    search: document.getElementById("search-input"),
    sort: document.getElementById("sort-select"),
    source: document.getElementById("source-filter"),
    status: document.getElementById("status-filter"),
    clear: document.getElementById("clear-filters"),
    cardView: document.getElementById("card-view"),
    listView: document.getElementById("list-view"),
    fileLoader: document.getElementById("file-loader"),
    previewEmpty: document.getElementById("preview-empty"),
    previewCard: document.getElementById("preview-card"),
    previewImage: document.getElementById("preview-image"),
    previewImageFallback: document.getElementById("preview-image-fallback"),
    previewSource: document.getElementById("preview-source"),
    previewStatus: document.getElementById("preview-status"),
    previewTitle: document.getElementById("preview-title"),
    previewSummary: document.getElementById("preview-summary"),
    previewUpdated: document.getElementById("preview-updated"),
    previewCollected: document.getElementById("preview-collected"),
    previewId: document.getElementById("preview-id"),
    openUrl: document.getElementById("open-url"),
    translateFull: document.getElementById("translate-full"),
    openSummary: document.getElementById("open-summary"),
    openOriginal: document.getElementById("open-original"),
  };

  const dateTime = new Intl.DateTimeFormat("zh-TW", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });

  function text(value, fallback = "未提供") {
    return String(value || "").trim() || fallback;
  }

  function summaryText(article) {
    const summary = text(article.summary_excerpt, "");
    if (!summary && article.summary_status !== "current") {
      return "摘要尚未產生；可先查看標題、來源與原文連結。";
    }
    return summary || "尚無摘要內容。";
  }

  function formatDate(value) {
    if (!value) return "未知";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return dateTime.format(date);
  }

  function normalize(value) {
    return String(value || "").toLocaleLowerCase("zh-TW");
  }

  function pathFor(relativePath) {
    return relativePath ? DATA_BASE + relativePath : "";
  }

  function translateUrl(url) {
    if (!url) return "#";
    return `https://translate.google.com/translate?sl=auto&tl=zh-TW&u=${encodeURIComponent(url)}`;
  }

  function compareDate(a, b, key, direction) {
    const left = new Date(a[key] || 0).getTime();
    const right = new Date(b[key] || 0).getTime();
    return direction === "asc" ? left - right : right - left;
  }

  function compareText(a, b, key, direction) {
    const left = normalize(a[key]);
    const right = normalize(b[key]);
    const result = left.localeCompare(right, "zh-TW");
    return direction === "desc" ? -result : result;
  }

  function sortArticles(items) {
    const sort = el.sort.value;
    return [...items].sort((a, b) => {
      if (sort === "updated_asc") return compareDate(a, b, "updated_at", "asc");
      if (sort === "collected_desc") return compareDate(a, b, "collected_at", "desc");
      if (sort === "title_asc") return compareText(a, b, "title", "asc");
      if (sort === "title_desc") return compareText(a, b, "title", "desc");
      if (sort === "source_asc") return compareText(a, b, "source", "asc");
      if (sort === "status_asc") return compareText(a, b, "summary_status", "asc");
      return compareDate(a, b, "updated_at", "desc");
    });
  }

  function buildOptions(select, values, allLabel) {
    const current = select.value;
    select.textContent = "";
    select.append(new Option(allLabel, "all"));
    values.forEach((value) => select.append(new Option(value, value)));
    select.value = values.includes(current) ? current : "all";
  }

  function hydrateFilters() {
    const sources = [...new Set(state.articles.map((item) => text(item.source, "未知來源")))].sort();
    const statuses = [...new Set(state.articles.map((item) => text(item.summary_status, "unknown")))].sort();
    buildOptions(el.source, sources, "全部來源");
    buildOptions(el.status, statuses, "全部狀態");
  }

  function applyFilters() {
    const query = normalize(el.search.value);
    const source = el.source.value;
    const status = el.status.value;
    const filtered = state.articles.filter((article) => {
      const haystack = normalize([
        article.id,
        article.title,
        article.source,
        article.summary_status,
        article.summary_excerpt,
      ].join(" "));
      const matchesQuery = !query || haystack.includes(query);
      const matchesSource = source === "all" || text(article.source, "未知來源") === source;
      const matchesStatus = status === "all" || text(article.summary_status, "unknown") === status;
      return matchesQuery && matchesSource && matchesStatus;
    });
    state.filtered = sortArticles(filtered);
    renderList();
    if (!state.filtered.some((article) => article.id === state.selectedId)) {
      selectArticle(state.filtered[0] || null);
    }
  }

  function renderList() {
    el.list.textContent = "";
    el.list.classList.toggle("list-mode", state.view === "list");
    el.resultCount.textContent = String(state.filtered.length);
    el.empty.hidden = state.filtered.length > 0;

    const fragment = document.createDocumentFragment();
    state.filtered.forEach((article) => {
      const card = document.createElement("article");
      card.className = "article-card";
      if (article.id === state.selectedId) card.classList.add("active");
      card.tabIndex = 0;
      card.setAttribute("role", "button");
      card.setAttribute("aria-label", `預覽 ${text(article.title)}`);

      const thumb = document.createElement("div");
      thumb.className = "thumb";
      if (article.image) {
        const img = document.createElement("img");
        img.src = pathFor(article.image);
        img.alt = "";
        img.loading = "lazy";
        img.onerror = () => {
          thumb.textContent = "";
          const fallback = document.createElement("div");
          fallback.className = "thumb-placeholder";
          fallback.textContent = "無預覽圖";
          thumb.append(fallback);
        };
        thumb.append(img);
      } else {
        const fallback = document.createElement("div");
        fallback.className = "thumb-placeholder";
        fallback.textContent = "無預覽圖";
        thumb.append(fallback);
      }

      const body = document.createElement("div");
      body.className = "article-body";
      const title = document.createElement("h3");
      title.textContent = text(article.title, "未命名文章");
      const summary = document.createElement("p");
      summary.className = "article-summary";
      summary.textContent = summaryText(article);
      const foot = document.createElement("div");
      foot.className = "article-foot";
      const source = document.createElement("span");
      source.className = "badge";
      source.textContent = text(article.source, "未知來源");
      const date = document.createElement("span");
      date.textContent = formatDate(article.updated_at);
      foot.append(source, date);
      body.append(title, summary, foot);
      card.append(thumb, body);

      card.addEventListener("click", () => selectArticle(article));
      card.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectArticle(article);
        }
      });
      fragment.append(card);
    });
    el.list.append(fragment);
  }

  function selectArticle(article) {
    state.selectedId = article ? article.id : "";
    document.querySelectorAll(".article-card.active").forEach((node) => node.classList.remove("active"));
    document.querySelectorAll(".article-card").forEach((node, index) => {
      if (state.filtered[index] && state.filtered[index].id === state.selectedId) {
        node.classList.add("active");
      }
    });

    if (!article) {
      el.previewEmpty.hidden = false;
      el.previewCard.hidden = true;
      return;
    }

    el.previewEmpty.hidden = true;
    el.previewCard.hidden = false;
    el.previewTitle.textContent = text(article.title, "未命名文章");
    el.previewSummary.textContent = summaryText(article);
    el.previewSource.textContent = text(article.source, "未知來源");
    el.previewStatus.textContent = text(article.summary_status, "unknown");
    el.previewUpdated.textContent = formatDate(article.updated_at);
    el.previewCollected.textContent = formatDate(article.collected_at);
    el.previewId.textContent = text(article.id);
    el.openUrl.href = article.url || "#";
    el.translateFull.href = translateUrl(article.url);
    el.openSummary.href = pathFor(article.summary_zh_md);
    el.openOriginal.href = pathFor(article.original_md);

    if (article.image) {
      el.previewImage.hidden = false;
      el.previewImageFallback.hidden = true;
      el.previewImage.src = pathFor(article.image);
      el.previewImage.alt = `${text(article.title, "文章")} 預覽圖`;
      el.previewImage.onerror = () => {
        el.previewImage.hidden = true;
        el.previewImageFallback.hidden = false;
      };
    } else {
      el.previewImage.removeAttribute("src");
      el.previewImage.hidden = true;
      el.previewImageFallback.hidden = false;
    }
  }

  function setView(view) {
    state.view = view;
    el.cardView.classList.toggle("active", view === "card");
    el.listView.classList.toggle("active", view === "list");
    el.cardView.setAttribute("aria-pressed", String(view === "card"));
    el.listView.setAttribute("aria-pressed", String(view === "list"));
    renderList();
  }

  function loadIndex(index) {
    state.articles = Array.isArray(index.articles) ? index.articles : [];
    state.selectedId = "";
    el.articleCount.textContent = `${index.article_count || state.articles.length} 篇`;
    el.generatedAt.textContent = `索引時間 ${formatDate(index.generated_at)}`;
    hydrateFilters();
    applyFilters();
  }

  async function boot() {
    if (window.ARCHIVE_INDEX) {
      loadIndex(window.ARCHIVE_INDEX);
      return;
    }
    try {
      const response = await fetch(DATA_BASE + "index.json", { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      loadIndex(await response.json());
    } catch (error) {
      el.generatedAt.textContent = "請載入 index.json";
      el.empty.hidden = false;
      el.empty.querySelector("strong").textContent = "尚未載入資料";
      el.empty.querySelector("span").textContent = "按左側「載入 index.json」選擇資料索引檔。";
    }
  }

  [el.search, el.sort, el.source, el.status].forEach((input) => {
    input.addEventListener("input", applyFilters);
    input.addEventListener("change", applyFilters);
  });

  el.clear.addEventListener("click", () => {
    el.search.value = "";
    el.sort.value = "updated_desc";
    el.source.value = "all";
    el.status.value = "all";
    applyFilters();
  });

  el.cardView.addEventListener("click", () => setView("card"));
  el.listView.addEventListener("click", () => setView("list"));
  el.fileLoader.addEventListener("change", async (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    const index = JSON.parse(await file.text());
    loadIndex(index);
  });

  boot();
}());
