import { Activity, CheckCircle2, Database, EyeOff, Image, Loader2, PauseCircle, PlayCircle, RefreshCw, Terminal, Trash2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

function classNames(...items) {
  return items.filter(Boolean).join(" ");
}

function streamClass(stream) {
  if (stream === "chat") return "text-sky-300";
  if (stream === "feedback") return "text-amber-300";
  if (stream === "crawl") return "text-emerald-300";
  if (stream === "chunking") return "text-violet-300";
  if (stream === "image") return "text-pink-300";
  if (stream === "research") return "text-cyan-300";
  return "text-slate-300";
}

function statusClass(status) {
  if (status === "done") return "bg-emerald-50 text-emerald-700";
  if (status === "review") return "bg-amber-50 text-amber-700";
  if (status === "placeholder") return "bg-blue-50 text-blue-700";
  return "bg-slate-50 text-slate-500";
}

function statusLabel(status) {
  const labels = {
    done: "xong",
    review: "cần duyệt",
    placeholder: "mô phỏng",
    waiting: "chờ"
  };
  return labels[status] || status || "chờ";
}

function streamLabel(stream) {
  const labels = {
    all: "Tất cả",
    chat: "Chat",
    feedback: "Phản hồi",
    crawl: "Crawl",
    chunking: "Chunking",
    image: "Ảnh",
    research: "Research"
  };
  return labels[stream] || stream;
}

function PipelineCard({ title, icon: Icon, rows = [] }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-50 text-slate-600">
          <Icon className="h-4 w-4" />
        </div>
        <h2 className="text-sm font-semibold text-slate-950">{title}</h2>
      </div>
      <div className="divide-y divide-slate-100">
        {rows.map((row) => (
          <div key={row.step} className="flex items-center justify-between gap-3 px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-slate-800">{row.label}</p>
              <p className="text-xs font-medium text-slate-500">{row.step}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-semibold text-slate-950">{row.count}</span>
              <span className={classNames("rounded-md px-2 py-1 text-[11px] font-bold", statusClass(row.status))}>{statusLabel(row.status)}</span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function TerminalLine({ event }) {
  const time = new Date(event.logged_at).toLocaleTimeString();
  return (
    <div className="grid gap-2 border-b border-slate-800/80 px-4 py-2 font-mono text-xs md:grid-cols-[86px_92px_132px_minmax(0,1fr)]">
      <span className="text-slate-500">{time}</span>
      <span className={classNames("font-semibold", streamClass(event.stream))}>[{event.stream}]</span>
      <span className="text-slate-400">{event.event}</span>
      <span className="min-w-0 text-slate-200">
        {event.message}
        {Object.keys(event.payload || {}).length > 0 && (
          <span className="ml-2 text-slate-500">{JSON.stringify(event.payload)}</span>
        )}
      </span>
    </div>
  );
}

export default function OpsConsole({ apiBase }) {
  const [events, setEvents] = useState([]);
  const [hiddenBefore, setHiddenBefore] = useState("");
  const [pipelines, setPipelines] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showPipelines, setShowPipelines] = useState(() => window.localStorage.getItem("nongtri_ops_show_pipelines") !== "false");
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");

  async function loadOps(showLoading = false) {
    if (showLoading) setLoading(true);
    setError("");
    try {
      const response = await fetch(`${apiBase}/admin/ops-events?limit=300`);
      if (!response.ok) throw new Error(await response.text());
      const payload = await response.json();
      setEvents(payload.events || []);
      setPipelines(payload.pipelines || null);
    } catch (err) {
      setError(err.message || "Không tải được ops console.");
    } finally {
      if (showLoading) setLoading(false);
    }
  }

  useEffect(() => {
    void loadOps(true);
  }, []);

  useEffect(() => {
    if (!autoRefresh) return undefined;
    const timer = window.setInterval(() => void loadOps(false), 2500);
    return () => window.clearInterval(timer);
  }, [autoRefresh]);

  function togglePipelines() {
    setShowPipelines((current) => {
      const next = !current;
      window.localStorage.setItem("nongtri_ops_show_pipelines", String(next));
      return next;
    });
  }

  function clearVisibleEvents() {
    setHiddenBefore(new Date().toISOString());
  }

  const streams = useMemo(() => ["all", ...Array.from(new Set(events.map((event) => event.stream))).sort()], [events]);
  const visibleEvents = useMemo(() => {
    const freshEvents = hiddenBefore ? events.filter((event) => event.logged_at > hiddenBefore) : events;
    const rows = filter === "all" ? freshEvents : freshEvents.filter((event) => event.stream === filter);
    return rows.slice().reverse();
  }, [events, filter, hiddenBefore]);

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="flex items-center gap-3 rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-600 shadow-sm">
          <Loader2 className="h-5 w-5 animate-spin text-emerald-600" />
          Đang tải nhật ký vận hành
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-950 text-emerald-300">
              <Terminal className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-slate-950">Nhật ký vận hành</h1>
              <p className="text-sm font-medium text-slate-500">Theo dõi chat, phản hồi, crawl, chunking và luồng huấn luyện dữ liệu.</p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={togglePipelines}
              className={classNames(
                "inline-flex h-9 items-center gap-2 rounded-lg border px-3 text-xs font-semibold",
                showPipelines ? "border-slate-200 bg-white text-slate-600" : "border-slate-800 bg-slate-950 text-white"
              )}
            >
              <EyeOff className="h-4 w-4" />
              {showPipelines ? "Ẩn luồng" : "Hiện luồng"}
            </button>
            <select
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 outline-none"
            >
              {streams.map((stream) => (
                <option key={stream} value={stream}>
                  {streamLabel(stream)}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => setAutoRefresh((value) => !value)}
              className={classNames(
                "inline-flex h-9 items-center gap-2 rounded-lg border px-3 text-xs font-semibold",
                autoRefresh ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-white text-slate-600"
              )}
            >
              {autoRefresh ? <PauseCircle className="h-4 w-4" /> : <PlayCircle className="h-4 w-4" />}
              Tự động {autoRefresh ? "bật" : "tắt"}
            </button>
            <button
              type="button"
              onClick={() => void loadOps(true)}
              className="inline-flex h-9 items-center gap-2 rounded-lg bg-slate-950 px-3 text-xs font-semibold text-white"
            >
              <RefreshCw className="h-4 w-4" />
              Làm mới
            </button>
          </div>
        </div>
        {error && <div className="border-b border-red-100 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{error}</div>}
        {showPipelines && (
          <div className="grid gap-4 p-4 xl:grid-cols-2">
            <PipelineCard title="Luồng chunking RAG" icon={Database} rows={pipelines?.rag_chunking || []} />
            <PipelineCard title="Luồng dữ liệu huấn luyện ảnh" icon={Image} rows={pipelines?.vision_training || []} />
          </div>
        )}
      </section>

      <section className="overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-4 py-3">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-emerald-300" />
            <h2 className="text-sm font-semibold text-slate-100">Nhật ký realtime</h2>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={clearVisibleEvents}
              disabled={!visibleEvents.length}
              className="inline-flex h-8 items-center gap-2 rounded-lg border border-slate-800 px-3 text-xs font-semibold text-slate-300 disabled:opacity-40"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Xóa
            </button>
            <span className="rounded-md bg-slate-900 px-2 py-1 text-xs font-semibold text-slate-400">{visibleEvents.length} dòng</span>
          </div>
        </div>
        <div className="max-h-[560px] overflow-auto">
          {visibleEvents.length ? (
            visibleEvents.map((event, index) => <TerminalLine key={`${event.logged_at}-${index}`} event={event} />)
          ) : (
            <div className="px-4 py-12 text-center font-mono text-sm text-slate-500">
              <CheckCircle2 className="mx-auto mb-3 h-6 w-6 text-slate-600" />
              Chưa có hoạt động trong phiên backend hiện tại.
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
