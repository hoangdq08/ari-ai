import { CheckCircle2, ChevronDown, Database, ExternalLink, FileText, Globe2, Layers3, Loader2, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const CRAWL_GROUPS = [
  {
    key: "dieu_kien",
    label: "Điều kiện",
    topic: "điều kiện sản xuất cà phê đất nước khí hậu địa hình vùng trồng",
    terms: ["đất", "nước", "khí hậu", "địa hình", "vùng trồng", "thổ nhưỡng"]
  },
  {
    key: "thiet_lap_vuon",
    label: "Thiết lập vườn",
    topic: "thiết lập vườn trồng cà phê vườn ươm làm đất mật độ cây che bóng",
    terms: ["vườn ươm", "làm đất", "mật độ", "trồng mới", "che bóng", "khoảng cách"]
  },
  {
    key: "cham_soc",
    label: "Chăm sóc",
    topic: "chăm sóc dinh dưỡng cà phê tưới bón phân tỉa cành tạo tán quản lý cỏ",
    terms: [
      "dinh dưỡng",
      "bón phân",
      "phân bón",
      "tưới",
      "tỉa cành",
      "tạo tán",
      "thiếu kali",
      "thiếu lân",
      "thiếu đạm",
      "thiếu canxi",
      "canxi",
      "magie",
      "bo",
      "kẽm",
      "vi lượng",
      "cải tạo đất",
      "vàng lá do thiếu"
    ]
  },
  {
    key: "bao_ve",
    label: "Bảo vệ",
    topic: "bảo vệ cây cà phê sâu bệnh nấm tuyến trùng rệp mọt vàng lá phòng ngừa",
    terms: ["bệnh", "sâu", "nấm", "tuyến trùng", "rệp", "mọt", "vàng lá", "phòng ngừa"]
  },
  {
    key: "giong",
    label: "Giống",
    topic: "chọn giống cà phê cây giống TR4 TRS1 ghép cải tạo tái canh vườn già",
    terms: ["giống", "cây giống", "tr4", "trs1", "ghép", "tái canh", "vườn già"]
  },
  {
    key: "thu_hoach",
    label: "Thu hoạch",
    topic: "thu hoạch cà phê tỷ lệ trái chín sơ chế phơi sấy bảo quản phân loại lỗi hạt",
    terms: ["thu hoạch", "trái chín", "sơ chế", "phơi", "sấy", "bảo quản", "lỗi hạt"]
  },
  {
    key: "quan_tri",
    label: "Quản trị",
    topic: "quản trị sản xuất cà phê chi phí năng suất tiêu chuẩn VietGAP 4C bao tiêu xuất khẩu",
    terms: ["chi phí", "kinh tế", "tối ưu", "giảm chi phí", "năng suất", "tiêu chuẩn", "vietgap", "4c", "bao tiêu", "xuất khẩu"]
  },
  {
    key: "khac",
    label: "Khác",
    topic: "vấn đề khác liên quan đến sản xuất cà phê kinh nghiệm tổng quan rủi ro khuyến nghị",
    terms: ["khác", "vấn đề khác", "tổng quan", "kinh nghiệm", "rủi ro", "khuyến nghị", "tư vấn"]
  },
  {
    key: "giao_tiep",
    label: "Giao tiếp",
    topic: "hướng dẫn người dùng đặt câu hỏi về cây cà phê và dữ liệu nông nghiệp",
    terms: ["chào", "cảm ơn", "hướng dẫn", "hỗ trợ", "ngoài phạm vi", "bạn là ai"]
  }
];

const QUERY_PRESETS = CRAWL_GROUPS.map((group) => ({ label: group.label, query: group.topic }));
const DEFAULT_GROUP_KEYS = CRAWL_GROUPS.map((group) => group.key);

const BATCH_TARGET_PER_TOPIC = 6;

function badgeClass(level) {
  if (level === "official") return "bg-emerald-50 text-emerald-700 border-emerald-200";
  if (level === "semi_official") return "bg-amber-50 text-amber-700 border-amber-200";
  return "bg-slate-50 text-slate-700 border-slate-200";
}

function typeIcon(type) {
  return type === "pdf" || type === "docx" || type === "txt" ? FileText : Globe2;
}

function friendlyError(err, fallback) {
  const message = err?.message || "";
  try {
    const payload = JSON.parse(message);
    const detail = payload.detail;
    if (typeof detail === "string") return detail;
  } catch {
    // Keep fallback below.
  }
  return message.length > 220 ? fallback : message || fallback;
}

function normalizeText(value = "") {
  return value
    .toString()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/\s+/g, " ")
    .trim();
}

function inferGroupsForQuery(query, enabledKeys = DEFAULT_GROUP_KEYS) {
  const enabled = CRAWL_GROUPS.filter((group) => enabledKeys.includes(group.key));
  const normalized = normalizeText(query);
  const scored = enabled.map((group) => {
    const matchedTerms = group.terms.filter((term) => normalized.includes(normalizeText(term)));
    return { group, score: matchedTerms.length, matchedTerms };
  });
  const matched = scored.filter((item) => item.score > 0).sort((a, b) => b.score - a.score);
  if (matched.length) return matched;
  return [{ group: enabled[0] || CRAWL_GROUPS[0], score: 0, matchedTerms: [] }];
}

function inferGroupForQuery(query, enabledKeys = DEFAULT_GROUP_KEYS) {
  return inferGroupsForQuery(query, enabledKeys)[0]?.group || CRAWL_GROUPS[0];
}

function batchQueryVariants(topic, group) {
  const cleaned = topic.trim();
  const lower = cleaned.toLowerCase();
  const hasCoffee = lower.includes("cà phê") || lower.includes("ca phe") || lower.includes("coffee");
  const coffeeTopic = hasCoffee ? cleaned : `${cleaned} cà phê`;
  const groupContext = group?.topic || "";
  return [
    coffeeTopic,
    `${coffeeTopic} ${groupContext}`,
    `${coffeeTopic} khuyến nông tài liệu kỹ thuật`,
    `${coffeeTopic} viện nghiên cứu PDF`,
    `${coffeeTopic} quy trình kỹ thuật canh tác`,
  ];
}

function mergeCandidates(current, incoming, topic, searchedQuery, group) {
  const merged = new Map(current.map((candidate) => [candidate.url, candidate]));
  for (const candidate of incoming) {
    if (Number(candidate.relevance_score || 0) <= 0) continue;
    const enriched = { ...candidate, batch_topic: topic, batch_group: group?.label, batch_group_key: group?.key, searched_query: searchedQuery };
    const previous = merged.get(candidate.url);
    if (!previous || Number(enriched.relevance_score || 0) > Number(previous.relevance_score || 0)) {
      merged.set(candidate.url, enriched);
    }
  }
  return Array.from(merged.values()).sort((a, b) => Number(b.relevance_score || 0) - Number(a.relevance_score || 0));
}

function urlsFromGroups(groups, topics) {
  const topicSet = new Set(topics);
  const unique = new Map();
  for (const group of groups) {
    if (!topicSet.has(group.topic)) continue;
    for (const candidate of group.candidates || []) {
      const current = unique.get(candidate.url);
      if (!current || Number(candidate.relevance_score || 0) > Number(current.relevance_score || 0)) {
        unique.set(candidate.url, candidate);
      }
    }
  }
  return Array.from(unique.values())
    .sort((a, b) => Number(b.relevance_score || 0) - Number(a.relevance_score || 0))
    .map((candidate) => candidate.url);
}

function uniqueUrls(candidates) {
  return Array.from(new Set((candidates || []).map((candidate) => candidate.url).filter(Boolean)));
}

function eventsSince(events, startedAt) {
  if (!startedAt) return [];
  const startTime = Date.parse(startedAt);
  return (events || []).filter((event) => {
    const eventTime = Date.parse(event.logged_at || "");
    return Number.isFinite(eventTime) && eventTime >= startTime;
  });
}

function progressTone(status) {
  if (status === "running") return "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (status === "done") return "border-emerald-100 bg-white text-slate-700";
  if (status === "empty") return "batch-progress-empty border-slate-200 bg-white text-slate-700";
  return "border-slate-100 bg-slate-50 text-slate-500";
}

function progressStatus(status, candidateCount) {
  if (status === "running") {
    return { label: "Đang tìm", className: "bg-emerald-50 text-emerald-700" };
  }
  if (status === "done" && candidateCount > 0) {
    return { label: "Có nguồn", className: "bg-emerald-50 text-emerald-700" };
  }
  if (status === "empty") {
    return { label: "Thiếu nguồn", className: "bg-amber-50 text-amber-700" };
  }
  return { label: "Chờ tìm", className: "bg-slate-100 text-slate-600" };
}

function PipelineTimeline({ running, completed, sourceCount, events = [] }) {
  const eventCounts = events.reduce(
    (acc, event) => {
      const name = event.event || event.status;
      const key = event.url || event.source_id || `${name}-${event.logged_at}`;
      if (name === "fetching") acc.fetching.add(key);
      if (name === "ingested") acc.ingested.add(key);
      if (name === "failed") acc.failed.add(key);
      if (name === "chunked") acc.chunked.add(event.source_id || key);
      // Duplicate / duplicate_skipped events fire when the URL has been
      // crawled previously. Without tracking them the dashboard reports
      // "Đã thử tải 1 · Đã nạp 0 · Lỗi 0" and 0% progress, which looks
      // like a silent failure even though everything worked - the source
      // was just already on disk.
      if (name === "duplicate" || name === "duplicate_skipped") acc.duplicate.add(key);
      return acc;
    },
    { fetching: new Set(), ingested: new Set(), failed: new Set(), chunked: new Set(), duplicate: new Set() }
  );
  const count = {
    fetching: eventCounts.fetching.size,
    ingested: eventCounts.ingested.size,
    failed: eventCounts.failed.size,
    chunked: eventCounts.chunked.size,
    duplicate: eventCounts.duplicate.size,
  };
  // Duplicates count as "processed" - they were attempted, found existing,
  // and skipped on purpose. Otherwise progress stays at 0% when the user
  // re-runs the same URL set.
  const processedCount = Math.min(sourceCount, count.ingested + count.failed + count.duplicate);
  const progressPercent = sourceCount ? Math.min(100, Math.round((processedCount / sourceCount) * 100)) : 0;
  const latestEvent = events[events.length - 1];
  const stageLabel = completed
    ? "Hoàn tất lượt nạp"
    : latestEvent?.event === "fetching"
      ? "Đang tải nguồn"
      : latestEvent?.event === "ingested"
        ? "Đã bóc text nguồn"
        : latestEvent?.event === "chunked"
          ? "Đang chunk và lập chỉ mục"
          : latestEvent?.event === "failed"
            ? "Ghi nhận nguồn lỗi"
            : latestEvent?.event === "duplicate" || latestEvent?.event === "duplicate_skipped"
              ? "Nguồn đã tồn tại, bỏ qua"
              : "Chờ sự kiện crawl";

  return (
    <section className="mt-4 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="px-4 py-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h2 className="text-base font-extrabold text-slate-950">Pipeline thu thập dữ liệu</h2>
            <p className="text-xs font-semibold text-slate-500">Tải nguồn / bóc text / làm sạch / chunk / lập chỉ mục RAG</p>
          </div>
          <span className={`w-fit rounded-lg px-3 py-2 text-xs font-extrabold ${completed ? "bg-emerald-50 text-emerald-700" : "bg-slate-950 text-white"}`}>
            {completed ? "Xong" : "Đang chạy"}
          </span>
        </div>
        <div className="mt-4">
          <div className="flex items-center justify-between gap-3 text-xs font-black text-slate-500">
            <span>{stageLabel}</span>
            <span>{processedCount}/{sourceCount} nguồn · {progressPercent}%</span>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200/80">
            <div
              className={`h-full rounded-full bg-emerald-500 transition-all duration-500 ${running ? "research-progress-active" : ""}`}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
          <p className="mt-2 text-xs font-semibold text-slate-500">
            Đã thử tải {count.fetching} · Đã nạp {count.ingested} · Đã chunk {count.chunked} · Đã có sẵn {count.duplicate} · Lỗi {count.failed}
          </p>
        </div>
      </div>
    </section>
  );
}

export default function ResearchPage({ apiBase, admin = false }) {
  const [mode, setMode] = useState("single");
  const [query, setQuery] = useState(admin ? "kỹ thuật sản xuất cà phê bền vững khuyến nông PDF" : "");
  const [batchTopics, setBatchTopics] = useState("");
  const [results, setResults] = useState(null);
  const [batchResults, setBatchResults] = useState(null);
  const [batchProgress, setBatchProgress] = useState([]);
  const [activeBatchTopic, setActiveBatchTopic] = useState("all");
  const [selectedUrls, setSelectedUrls] = useState([]);
  const [crawlResult, setCrawlResult] = useState(null);
  const [maxResults, setMaxResults] = useState(50);
  const [collectLinks, setCollectLinks] = useState(false);
  const [expandedTexts, setExpandedTexts] = useState([]);
  const [crawlEvents, setCrawlEvents] = useState([]);
  const [crawlStartedAt, setCrawlStartedAt] = useState(null);
  const [thinkingTick, setThinkingTick] = useState(0);
  const [loading, setLoading] = useState(false);
  const [crawling, setCrawling] = useState(false);
  const [error, setError] = useState("");

  const batchTopicLines = useMemo(
    () =>
      batchTopics
        .split("\n")
        .map((item) => item.trim())
        .filter(Boolean),
    [batchTopics]
  );

  const inferredBatchGroups = useMemo(() => {
    const groups = new Map(CRAWL_GROUPS.map((group) => [group.key, { ...group, topics: [], matchedTerms: new Set() }]));
    for (const topic of batchTopicLines) {
      for (const match of inferGroupsForQuery(topic).slice(0, 2)) {
        const current = groups.get(match.group.key);
        if (!current) continue;
        current.topics.push(topic);
        match.matchedTerms.forEach((term) => current.matchedTerms.add(term));
      }
    }
    return Array.from(groups.values())
      .filter((group) => group.topics.length > 0)
      .map((group) => ({ ...group, matchedTerms: Array.from(group.matchedTerms) }));
  }, [batchTopicLines]);

  useEffect(() => {
    if (!crawling) return undefined;
    let cancelled = false;
    async function loadEvents() {
      try {
        const response = await fetch(`${apiBase}/crawl-events?limit=1000`);
        if (!response.ok || cancelled) return;
        const payload = await response.json();
        setCrawlEvents(eventsSince(payload.events || [], crawlStartedAt));
      } catch {
        // The crawl request itself owns the visible error state.
      }
    }
    loadEvents();
    const timer = window.setInterval(loadEvents, 1200);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [apiBase, crawlStartedAt, crawling]);

  useEffect(() => {
    if (!loading || mode !== "batch") return undefined;
    const timer = window.setInterval(() => {
      setThinkingTick((current) => current + 1);
    }, 700);
    return () => window.clearInterval(timer);
  }, [loading, mode]);

  async function runSearch() {
    if (!query.trim()) return;
    setLoading(true);
    setThinkingTick(0);
    setError("");
    setResults(null);
    setBatchResults(null);
    setBatchProgress([]);
    setActiveBatchTopic("all");
    setSelectedUrls([]);
    setCrawlResult(null);
    setCrawlEvents([]);
    setCrawlStartedAt(null);
    setExpandedTexts([]);
    try {
      const response = await fetch(`${apiBase}/research-search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, max_results: maxResults, auto_crawl: false })
      });
      if (!response.ok) throw new Error(await response.text());
      setResults(await response.json());
    } catch (err) {
      setError(friendlyError(err, "Không tìm kiếm được dữ liệu."));
    } finally {
      setLoading(false);
    }
  }

  async function runBatchSearch() {
    const topics = batchTopicLines;
    if (!topics.length) return;
    setLoading(true);
    setError("");
    setResults(null);
    setBatchResults(null);
    setBatchProgress(
      topics.map((topic) => ({
        topic,
        group: inferGroupForQuery(topic),
        status: "pending",
        searched: 0,
        total: batchQueryVariants(topic, inferGroupForQuery(topic)).length,
        candidates: 0,
        message: "Đang chờ"
      }))
    );
    setActiveBatchTopic("all");
    setSelectedUrls([]);
    setCrawlResult(null);
    setExpandedTexts([]);

    try {
      setBatchProgress((current) =>
        current.map((item) => ({ ...item, status: "running", message: "Backend đang phân nhóm và tìm nguồn" }))
      );
      const response = await fetch(`${apiBase}/research-batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          queries: topics,
          max_results: maxResults,
          target_per_query: Math.min(BATCH_TARGET_PER_TOPIC, maxResults)
        })
      });
      if (!response.ok) throw new Error(await response.text());
      const payload = await response.json();
      const groups = payload.groups || [];
      const candidates = payload.candidates || [];
      setBatchResults({ topics: payload.topics || topics, groups, candidates });
      setBatchProgress(
        groups.map((group) => ({
          topic: group.topic,
          group: group.group,
          status: (group.candidates || []).length ? "done" : "empty",
          searched: (group.searched_queries || []).length,
          total: (group.searched_queries || []).length || 1,
          candidates: (group.candidates || []).length,
          message: (group.candidates || []).length ? "Có nguồn" : "Chưa tìm thấy nguồn phù hợp"
        }))
      );
      const collectableTopics = groups.filter((group) => group.candidates.length > 0).map((group) => group.topic);
      setActiveBatchTopic(collectableTopics[0] || "all");
      setSelectedUrls(payload.selected_urls || urlsFromGroups(groups, collectableTopics));
    } catch (err) {
      setError(friendlyError(err, "Không chạy tìm hàng loạt được."));
    } finally {
      setLoading(false);
    }
  }

  async function crawlSelected() {
    if (!selectedUrls.length) return;
    setCrawling(true);
    setError("");
    setCrawlResult(null);
    setCrawlEvents([]);
    const startedAt = new Date(Date.now() - 500).toISOString();
    setCrawlStartedAt(startedAt);
    try {
      const response = await fetch(`${apiBase}/crawl-urls`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          urls: selectedUrls,
          reliability_level: "internet",
          max_pages: selectedUrls.length,
          collect_links: collectLinks,
          same_domain_only: true
        })
      });
      if (!response.ok) throw new Error(await response.text());
      setCrawlResult(await response.json());
      try {
        const eventsResponse = await fetch(`${apiBase}/crawl-events?limit=1000`);
        if (eventsResponse.ok) {
          const payload = await eventsResponse.json();
          setCrawlEvents(eventsSince(payload.events || [], startedAt));
        }
      } catch {
        // Keep the completed crawl result even if event refresh fails.
      }
      setExpandedTexts([]);
    } catch (err) {
      setError(friendlyError(err, "Không crawl được nguồn đã chọn."));
    } finally {
      setCrawling(false);
    }
  }

  function toggleUrl(url) {
    setSelectedUrls((current) => {
      if (current.includes(url)) return current.filter((item) => item !== url);
      setError("");
      return [...current, url];
    });
  }

  function toggleTopic(topic) {
    if (!batchResults) return;
    const group = batchResults.groups?.find((item) => item.topic === topic);
    const topicUrls = uniqueUrls(group?.candidates || []);
    if (!topicUrls.length) return;

    setSelectedUrls((current) => {
      const currentSet = new Set(current);
      const allSelected = topicUrls.every((url) => currentSet.has(url));
      if (allSelected) {
        return current.filter((url) => !topicUrls.includes(url));
      }
      for (const url of topicUrls) {
        currentSet.add(url);
      }
      return Array.from(currentSet);
    });
  }

  function toggleText(sourceId) {
    setExpandedTexts((current) =>
      current.includes(sourceId) ? current.filter((item) => item !== sourceId) : [...current, sourceId]
    );
  }

  const visibleCandidates = (results?.candidates || []).filter((candidate) => Number(candidate.relevance_score || 0) > 0);
  const batchCandidates = batchResults?.candidates || [];
  const selectedUrlSet = new Set(selectedUrls);
  const activeBatchGroup = batchResults?.groups?.find((group) => group.topic === activeBatchTopic);
  const displayCandidates =
    mode === "batch"
      ? activeBatchTopic === "all"
        ? batchCandidates
        : activeBatchGroup?.candidates || []
      : visibleCandidates;
  const availableUrlCount = mode === "batch" ? uniqueUrls(batchCandidates).length : uniqueUrls(visibleCandidates).length;
  const batchTopicCount = batchResults?.topics?.length || 0;

  return (
    <div className={`flex flex-col ${admin ? "pb-10" : "min-h-[calc(100vh-64px)] pb-28"}`}>
      <div className={`${admin ? "rounded-xl border border-slate-200 bg-white p-4 shadow-sm" : "sticky top-16 z-30 border-b border-slate-100/80 bg-white/95 px-4 pb-2 pt-6 shadow-[0_4px_20px_-10px_rgba(0,0,0,0.05)] backdrop-blur-md"}`}>
        <div className="mb-4 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className={`${admin ? "text-[26px]" : "text-[32px]"} font-bold tracking-tight text-slate-900`}>{admin ? "Thu thập dữ liệu" : "Cẩm nang"}</h1>
            {admin && <p className="mt-1 text-sm font-medium text-slate-500">Tìm kiếm, duyệt nguồn, nạp vào RAG.</p>}
          </div>
          {(results || batchResults) && admin && (
            <span className="mt-2 w-fit rounded-lg bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 sm:mt-0">
              {displayCandidates.length} nguồn phù hợp
            </span>
          )}
        </div>

        {admin && (
          <div className="mb-3 grid grid-cols-2 gap-1.5 rounded-xl bg-slate-100 p-1">
            <button
              type="button"
              onClick={() => {
                setMode("single");
                setBatchResults(null);
                setBatchProgress([]);
                setActiveBatchTopic("all");
                setSelectedUrls([]);
                setCrawlResult(null);
                setCrawlEvents([]);
                setCrawlStartedAt(null);
                setError("");
              }}
              className={`h-9 rounded-lg text-sm font-semibold transition ${
                mode === "single" ? "bg-white text-slate-950 shadow-sm" : "text-slate-500 hover:text-slate-800"
              }`}
            >
              Tìm từng chủ đề
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("batch");
                setResults(null);
                setBatchProgress([]);
                setActiveBatchTopic("all");
                setSelectedUrls([]);
                setCrawlResult(null);
                setCrawlEvents([]);
                setCrawlStartedAt(null);
                setError("");
              }}
              className={`inline-flex h-9 items-center justify-center gap-2 rounded-lg text-sm font-semibold transition ${
                mode === "batch" ? "bg-white text-slate-950 shadow-sm" : "text-slate-500 hover:text-slate-800"
              }`}
            >
              <Layers3 className="h-4 w-4" />
              Tìm hàng loạt
            </button>
          </div>
        )}

        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_132px_240px]">
          {mode === "single" ? (
            <div className="relative">
              <input
                type="text"
                placeholder="Tìm kiếm nguồn cà phê, PDF, khuyến nông..."
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="h-12 w-full rounded-xl border border-slate-200 bg-white pl-11 pr-4 text-base font-medium text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-emerald-500 focus:bg-white focus:ring-3 focus:ring-emerald-100"
              />
              <Search className="absolute left-3.5 top-3 h-6 w-6 text-slate-400" strokeWidth={2.5} />
            </div>
          ) : (
            <div className="relative lg:col-span-3">
              <textarea
                rows={5}
                placeholder={"Mỗi dòng là một câu tìm kiếm thật...\nthiếu kali trên cây cà phê\ncách chọn giống cà phê TR4\nquy trình tưới tiết kiệm cho cà phê"}
                value={batchTopics}
                onChange={(event) => setBatchTopics(event.target.value)}
                className="w-full resize-none rounded-xl border border-slate-200 bg-white py-3 pl-11 pr-4 text-sm font-medium leading-6 text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-emerald-500 focus:bg-white focus:ring-3 focus:ring-emerald-100"
              />
              <Layers3 className="absolute left-3.5 top-4 h-5 w-5 text-slate-400" strokeWidth={2.5} />
            </div>
          )}
          <div className={`relative ${mode === "batch" ? "lg:col-start-1" : ""}`}>
            <select
              value={maxResults}
              onChange={(event) => setMaxResults(Number(event.target.value))}
              className="h-12 w-full appearance-none rounded-xl border border-slate-200 bg-white py-0 pl-4 pr-10 text-sm font-semibold leading-[48px] text-slate-700 outline-none focus:border-emerald-500 focus:ring-3 focus:ring-emerald-100"
            >
              <option value={10}>10 nguồn</option>
              <option value={20}>20 nguồn</option>
              <option value={50}>50 nguồn</option>
              <option value={100}>100 nguồn</option>
              <option value={200}>200 nguồn</option>
              <option value={500}>500 nguồn</option>
            </select>
            <ChevronDown className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" strokeWidth={2.5} />
          </div>
          <button
            type="button"
            onClick={mode === "batch" ? runBatchSearch : runSearch}
            disabled={loading || (mode === "single" ? !query.trim() : !batchTopics.trim())}
            className="inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-700 active:scale-[0.99] disabled:bg-slate-300 lg:min-w-[220px]"
          >
            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : mode === "batch" ? <Layers3 className="h-5 w-5" /> : <Search className="h-5 w-5" />}
            <span className="whitespace-nowrap">{mode === "batch" ? "Tìm hàng loạt" : "Tìm"}</span>
          </button>
        </div>

        {admin && mode === "single" && (
          <div className="mt-3 flex flex-wrap gap-2 border-t border-slate-100 pt-3">
            {QUERY_PRESETS.map((preset) => (
              <button
                key={preset.label}
                type="button"
                onClick={() => setQuery(preset.query)}
                className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 shadow-sm transition hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-700"
              >
                {preset.label}
              </button>
            ))}
          </div>
        )}

        {admin && mode === "batch" && (
          <div className="mt-3 rounded-xl border border-slate-200 bg-white p-3">
            <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Phân nhóm truy vấn</p>
                <p className="mt-1 text-xs font-medium leading-5 text-slate-500">Nhóm dùng để lọc nguồn đề xuất và gắn metadata khi nạp.</p>
              </div>
              <span className="w-fit rounded-lg bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                {batchTopicLines.length} truy vấn
              </span>
            </div>
            {inferredBatchGroups.length ? (
              <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                {inferredBatchGroups.map((group) => (
                  <div key={group.key} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-950">{group.label}</p>
                      <span className="rounded-lg bg-white px-2.5 py-1 text-xs font-semibold text-emerald-700 shadow-sm">
                        {group.topics.length}
                      </span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {group.matchedTerms.slice(0, 4).map((term) => (
                        <span key={term} className="rounded-md bg-white px-2 py-1 text-[11px] font-medium text-slate-500">
                          {term}
                        </span>
                      ))}
                    </div>
                    <ul className="mt-3 space-y-1.5">
                      {group.topics.slice(0, 3).map((topic) => (
                        <li key={topic} className="line-clamp-1 text-xs font-semibold text-slate-600">
                          {topic}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            ) : (
              <div className="mt-3 rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-4 text-center text-xs font-semibold text-slate-500">
                Nhập mỗi dòng một truy vấn thật; hệ thống sẽ tự gom vào nhóm phù hợp trước khi tìm kiếm.
              </div>
            )}
          </div>
        )}

        {admin && (
          <label className="mt-3 flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50/80 px-3 py-2.5">
            <input
              type="checkbox"
              checked={collectLinks}
              onChange={(event) => setCollectLinks(event.target.checked)}
              className="mt-0.5 h-4 w-4 accent-emerald-600"
            />
            <span className="text-xs font-medium leading-5 text-slate-600">Mở rộng cùng domain</span>
          </label>
        )}
        {error && <div className="mt-3 rounded-xl border border-red-100 bg-red-50 px-3 py-2.5 text-sm font-semibold leading-6 text-red-700">{error}</div>}
      </div>

      {mode === "batch" && (batchProgress.length > 0 || batchResults) && (
        <section className="mt-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-950">Tiến trình từng truy vấn</h2>
              <p className="mt-1 text-xs font-medium text-slate-500">Chọn truy vấn, xem nguồn đề xuất, rồi nạp dữ liệu.</p>
            </div>
            <button
              type="button"
              onClick={() => setActiveBatchTopic("all")}
              className={`h-9 rounded-xl px-4 text-xs font-semibold transition ${
                activeBatchTopic === "all" ? "bg-slate-950 text-white" : "border border-slate-200 bg-white text-slate-600"
              }`}
            >
              Xem tất cả
            </button>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {(batchProgress.length ? batchProgress : batchResults?.groups || []).map((item, index) => {
              const group = batchResults?.groups?.find((entry) => entry.topic === item.topic);
              const inferredGroup = group?.group || item.group;
              const candidateCount = group?.candidates?.length ?? item.candidates ?? 0;
              const topicUrls = uniqueUrls(group?.candidates || []);
              const selectedInTopic = topicUrls.filter((url) => selectedUrlSet.has(url)).length;
              const selectedTopic = topicUrls.length > 0 && selectedInTopic === topicUrls.length;
              const partiallySelected = selectedInTopic > 0 && selectedInTopic < topicUrls.length;
              const activeTopic = activeBatchTopic === item.topic;
              const progressTotal = item.total || group?.searched_queries?.length || 1;
              const isSearching = item.status === "running" || (loading && !batchResults);
              const selectionText = selectedTopic
                ? `Đã chọn toàn bộ ${topicUrls.length || candidateCount} nguồn`
                : partiallySelected
                  ? `Đã chọn ${selectedInTopic} trong ${topicUrls.length || candidateCount} nguồn`
                  : `${candidateCount} nguồn sau lọc`;
              const progressValue = item.status === "done" || item.status === "empty"
                ? 100
                : Math.min(95, Math.round(((item.searched || 0) / progressTotal) * 100));
              const animatedProgress = isSearching ? Math.min(92, 16 + ((thinkingTick * 7 + index * 9) % 76)) : progressValue;

              return (
                <article
                  key={item.topic}
                  className={`rounded-xl border p-3 transition ${progressTone(item.status)} ${
                    activeTopic ? "ring-2 ring-emerald-200" : ""
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={selectedTopic}
                      disabled={isSearching || !candidateCount}
                      ref={(node) => {
                        if (node) node.indeterminate = partiallySelected;
                      }}
                      onChange={() => toggleTopic(item.topic)}
                      className="mt-1 h-4 w-4 accent-emerald-600 disabled:opacity-40"
                    />
                    <button type="button" onClick={() => setActiveBatchTopic(item.topic)} className="min-w-0 flex-1 text-left">
                      <div className="flex items-center justify-between gap-3">
                        <p className="line-clamp-1 text-sm font-semibold text-slate-900">{item.topic}</p>
                        <div className="flex flex-shrink-0 items-center gap-2">
                          {partiallySelected && (
                            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-black uppercase tracking-wider text-amber-700">
                              một phần
                            </span>
                          )}
                          {selectedTopic && (
                            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-black uppercase tracking-wider text-emerald-700">
                              chọn hết
                            </span>
                          )}
                          {item.status === "running" ? (
                            <Loader2 className="h-4 w-4 animate-spin text-emerald-600" />
                          ) : item.status === "done" ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                          ) : null}
                        </div>
                      </div>
                      <p className="mt-1 text-xs font-medium text-slate-500">
                        {isSearching
                          ? `${inferredGroup?.label ? `${inferredGroup.label} · ` : ""}Đang tìm và lọc nguồn`
                          : `${inferredGroup?.label ? `${inferredGroup.label} · ` : ""}${selectionText}`}
                      </p>
                      <div className="mt-3 flex items-center gap-3">
                        <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200/80">
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${
                              isSearching ? "research-progress-active bg-emerald-500" : item.status === "empty" ? "bg-amber-400" : "bg-emerald-500"
                            }`}
                            style={{ width: `${animatedProgress}%` }}
                          />
                        </div>
                        <span className={`w-10 text-right text-[11px] font-black ${isSearching ? "text-emerald-600 dark:text-emerald-300" : "text-slate-400"}`}>
                          {animatedProgress}%
                        </span>
                      </div>
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      )}

      {displayCandidates.length > 0 && (
        <div className={`${admin ? "rounded-2xl" : "sticky top-[198px] mx-4 rounded-[28px]"} z-20 mt-4 border border-emerald-100 bg-white/95 p-3 shadow-sm backdrop-blur-xl`}>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-extrabold text-slate-900">
                Đã chọn {selectedUrls.length} nguồn
              </p>
              <p className="hidden text-xs font-semibold text-slate-500 sm:block">
                {mode === "batch"
                ? `${batchTopicCount} truy vấn · ${availableUrlCount} nguồn khả dụng`
                : `${availableUrlCount} nguồn khả dụng`}
              </p>
            </div>
            <button
              type="button"
              onClick={crawlSelected}
              disabled={!selectedUrls.length || crawling}
              className="inline-flex h-10 items-center gap-2 rounded-xl bg-slate-900 px-4 text-sm font-semibold text-white shadow-sm disabled:bg-slate-300"
            >
              {crawling ? <Loader2 className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4" />}
              Nạp dữ liệu
            </button>
          </div>
        </div>
      )}

      {(crawling || crawlResult) && (
        <PipelineTimeline
          running={crawling}
          completed={Boolean(crawlResult)}
          sourceCount={selectedUrls.length}
          events={crawlEvents}
        />
      )}

      {crawlResult && (
        <section className={`${admin ? "" : "mx-4"} mt-4 rounded-xl border border-emerald-100 bg-white p-4 shadow-sm`}>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
            <h2 className="text-lg font-bold text-slate-900">Kết quả nạp dữ liệu</h2>
          </div>
          <div className="mt-4 space-y-3">
            {crawlResult.ingested.map((item) => (
              <article key={item.source_id} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                <p className="text-[17px] font-semibold leading-snug text-slate-900">{item.title || item.source_id}</p>
                <p className="mt-1 text-xs font-bold text-slate-500">
                  thô {item.raw_text_char_count || 0} · sạch {item.cleaned_text_char_count || 0} · chunk {item.chunks_created}
                </p>
                <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap rounded-xl bg-slate-950 p-3 text-xs leading-5 text-slate-100">
                  {expandedTexts.includes(item.source_id)
                    ? item.cleaned_text || item.cleaned_text_preview || item.raw_text_preview || "Không bóc được text."
                    : item.cleaned_text_preview || item.raw_text_preview || "Không có preview text."}
                </pre>
                <button
                  type="button"
                  onClick={() => toggleText(item.source_id)}
                  className="mt-3 rounded-lg border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700"
                >
                  {expandedTexts.includes(item.source_id) ? "Thu gọn text" : "Xem toàn bộ text sạch"}
                </button>
              </article>
            ))}
          </div>
        </section>
      )}

      <div className={`${admin ? "space-y-2.5 pt-4" : "space-y-4 px-4 pt-5"}`}>
        {displayCandidates.map((candidate) => {
          const Icon = typeIcon(candidate.source_type);
          const selected = selectedUrls.includes(candidate.url);
          return (
            <article
              key={candidate.url}
              className={`w-full cursor-pointer rounded-xl border bg-white p-3 shadow-sm transition hover:border-emerald-200 hover:shadow-md active:scale-[0.995] ${
                selected ? "border-emerald-400 ring-2 ring-emerald-100" : "border-slate-200"
              }`}
              onClick={() => toggleUrl(candidate.url)}
            >
              <div className="grid gap-3 sm:grid-cols-[28px_38px_minmax(0,1fr)_118px] sm:items-start">
                <input
                  type="checkbox"
                  checked={selected}
                  onChange={() => toggleUrl(candidate.url)}
                  onClick={(event) => event.stopPropagation()}
                  className="mt-1 h-4 w-4 accent-emerald-600"
                />
                <div className="hidden h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-500 sm:flex">
                  <Icon className="h-5 w-5" strokeWidth={2.5} />
                </div>
                <div className="min-w-0">
                  <div className="mb-1.5 flex flex-wrap items-center gap-2">
                    <span className={`inline-flex rounded-md border px-2 py-0.5 text-[10px] font-black uppercase tracking-widest ${badgeClass(candidate.reliability_level)}`}>
                      {candidate.reliability_level}
                    </span>
                    <span className="text-xs font-bold text-slate-500">{candidate.source_type}</span>
                    {candidate.batch_topic && (
                      <span className="max-w-full truncate rounded-md bg-emerald-50 px-2 py-0.5 text-[10px] font-black uppercase tracking-widest text-emerald-700">
                        {candidate.batch_topic}
                      </span>
                    )}
                    {candidate.searched_query && (
                      <span className="max-w-full truncate rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-500">
                        truy vấn: {candidate.searched_query}
                      </span>
                    )}
                  </div>
                  <h3 className="line-clamp-1 text-base font-semibold leading-snug text-slate-950">{candidate.title}</h3>
                  <p className="mt-1 line-clamp-2 text-sm font-medium leading-6 text-slate-600">{candidate.snippet || "Không có snippet."}</p>
                  <a
                    href={candidate.url}
                    target="_blank"
                    rel="noreferrer"
                    onClick={(event) => event.stopPropagation()}
                    className="mt-2 inline-flex max-w-full items-center gap-1.5 truncate text-xs font-bold text-emerald-700"
                  >
                    <span className="truncate">{candidate.url}</span>
                    <ExternalLink className="h-3.5 w-3.5 flex-shrink-0" />
                  </a>
                </div>
                <div className="flex items-center justify-between gap-2 sm:block sm:text-right">
                  <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">Điểm</p>
                  <p className="text-lg font-bold text-slate-900">{candidate.relevance_score}</p>
                </div>
              </div>
            </article>
          );
        })}
        {((mode === "single" && results && !visibleCandidates.length) || (mode === "batch" && batchResults && !batchCandidates.length)) && (
          <div className="rounded-xl border border-dashed border-slate-200 bg-white p-6 text-center text-sm font-medium text-slate-500">
            Chưa có nguồn phù hợp sau khi lọc độ liên quan. Hãy thử truy vấn cụ thể hơn như “bón phân cà phê khuyến nông PDF”.
          </div>
        )}
        {!results && !batchResults && (
          <div className="rounded-xl border border-dashed border-slate-200 bg-white p-5 text-center text-sm font-medium text-slate-500">
            {mode === "batch" ? "Nhập nhiều truy vấn rồi chạy tìm hàng loạt để tạo danh sách nguồn." : "Nhập chủ đề rồi bấm tìm để tạo danh sách nguồn."}
          </div>
        )}
      </div>
    </div>
  );
}
