import {
  AlertTriangle,
  CheckCircle2,
  Database,
  FileSearch,
  Layers3,
  Loader2,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const STRATEGIC_CATEGORIES = [
  ["Dinh dưỡng & chi phí", ["dinh dưỡng", "phân bón", "chi phí", "kinh tế"]],
  ["Tạo tán & chất lượng", ["tạo tán", "tỉa cành", "tăng năng suất", "chất lượng hạt"]],
  ["Nước tưới & chống hạn", ["tưới", "nước", "hạn", "chống hạn"]],
  ["Sâu bệnh & dư lượng", ["sâu bệnh", "dư lượng", "bảo vệ thực vật", "xuất khẩu"]],
  ["Giống & cải tạo", ["giống", "ghép", "cải tạo", "vườn già"]],
  ["Tiêu chuẩn & bao tiêu", ["tiêu chuẩn", "vietgap", "4c", "bao tiêu", "nâng giá trị"]],
  ["Khác liên quan", ["khác", "tổng quan", "kinh nghiệm", "rủi ro", "khuyến nghị", "tư vấn"]],
  ["Giao tiếp", ["chào", "cảm ơn", "hướng dẫn", "hỗ trợ", "ngoài phạm vi", "bạn là ai"]]
];

function cx(...items) {
  return items.filter(Boolean).join(" ");
}

function toneClass(tone) {
  const map = {
    emerald: "bg-emerald-50 text-emerald-700 border-emerald-100",
    blue: "bg-blue-50 text-blue-700 border-blue-100",
    amber: "bg-amber-50 text-amber-700 border-amber-100",
    red: "bg-red-50 text-red-700 border-red-100",
    slate: "bg-slate-50 text-slate-700 border-slate-100"
  };
  return map[tone] || map.slate;
}

function reliabilityClass(level) {
  if (level === "official") return "bg-emerald-50 text-emerald-700 border-emerald-100";
  if (level === "semi_official") return "bg-amber-50 text-amber-700 border-amber-100";
  if (level === "manual") return "bg-blue-50 text-blue-700 border-blue-100";
  return "bg-slate-50 text-slate-600 border-slate-100";
}

function reliabilityLabel(level) {
  const labels = {
    official: "Chính thống",
    semi_official: "Bán chính thống",
    manual: "Thủ công",
    internet: "Internet"
  };
  return labels[level] || "Chưa rõ";
}

function reviewClass(status) {
  if (status === "approved" || status === "indexed") return "bg-emerald-50 text-emerald-700 border-emerald-100";
  if (status === "rejected" || status === "blocked") return "bg-red-50 text-red-700 border-red-100";
  return "bg-amber-50 text-amber-700 border-amber-100";
}

function reviewLabel(status) {
  const labels = {
    approved: "Đã duyệt",
    needs_review: "Cần review",
    rejected: "Loại",
    indexed: "Đã index",
    held_for_review: "Giữ lại",
    blocked: "Chặn"
  };
  return labels[status] || "Chưa duyệt";
}

function sourceTypeLabel(type) {
  const labels = {
    web: "Trang web",
    pdf: "PDF",
    file: "Tệp",
    html: "HTML",
    manual: "Thủ công"
  };
  return labels[type] || "Chưa rõ";
}

function Metric({ icon: Icon, label, value, note, tone = "slate" }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">{label}</p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-slate-950">{value}</p>
          {note && <p className="mt-1 text-xs font-medium text-slate-500">{note}</p>}
        </div>
        <div className={cx("flex h-10 w-10 items-center justify-center rounded-xl border", toneClass(tone))}>
          <Icon className="h-5 w-5" strokeWidth={2.4} />
        </div>
      </div>
    </div>
  );
}

function Panel({ title, subtitle, action, children, className = "" }) {
  return (
    <section className={cx("rounded-xl border border-slate-200 bg-white shadow-sm", className)}>
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-4 py-3">
        <div>
          <h2 className="text-sm font-bold text-slate-950">{title}</h2>
          {subtitle && <p className="mt-1 text-xs font-medium leading-5 text-slate-500">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function QualityLine({ label, value, active }) {
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-2">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-extrabold text-slate-600">{label}</span>
        <span className={cx("rounded-full px-2.5 py-1 text-[11px] font-black", active ? "bg-emerald-100 text-emerald-700" : "bg-white text-slate-500")}>
          {value}
        </span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white">
        <div className={cx("h-full rounded-full", active ? "bg-emerald-500" : "bg-slate-300")} style={{ width: active ? "100%" : "8%" }} />
      </div>
    </div>
  );
}

export default function DataDashboard({ apiBase }) {
  const [health, setHealth] = useState(null);
  const [quality, setQuality] = useState(null);
  const [sources, setSources] = useState([]);
  const [evalResult, setEvalResult] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");

  async function loadAll() {
    setBusy("load");
    setError("");
    try {
      const [healthResponse, qualityResponse, sourcesResponse] = await Promise.all([
        fetch(`${apiBase}/health`),
        fetch(`${apiBase}/data-quality`),
        fetch(`${apiBase}/sources`)
      ]);
      if (!healthResponse.ok || !qualityResponse.ok || !sourcesResponse.ok) {
        throw new Error("Không tải được trạng thái dữ liệu.");
      }
      setHealth(await healthResponse.json());
      setQuality(await qualityResponse.json());
      setSources((await sourcesResponse.json()).sources || []);
    } catch (err) {
      setError(err.message || "Không tải được dashboard dữ liệu.");
    } finally {
      setBusy("");
    }
  }

  async function runEval() {
    setBusy("eval");
    setError("");
    try {
      const response = await fetch(`${apiBase}/rag-evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ top_k: 5 })
      });
      if (!response.ok) throw new Error(await response.text());
      setEvalResult(await response.json());
    } catch (err) {
      setError(err.message || "Không chạy được RAG eval.");
    } finally {
      setBusy("");
    }
  }

  async function rebuildIndex() {
    setBusy("rebuild");
    setError("");
    try {
      const response = await fetch(`${apiBase}/rag-rebuild-index`, { method: "POST" });
      if (!response.ok) throw new Error(await response.text());
      await response.json();
      await loadAll();
    } catch (err) {
      setError(err.message || "Không tạo lại được chỉ mục.");
    } finally {
      setBusy("");
    }
  }

  useEffect(() => {
    void loadAll();
  }, []);

  const summary = quality?.summary || {};
  const sourceList = quality?.sources || [];
  const avgQuality = summary.source_count ? Math.round((summary.avg_quality_score || 0) * 100) : null;
  const warningTotal = Object.values(summary.warning_counts || {}).reduce((sum, value) => sum + Number(value || 0), 0);
  // Backend now exposes `real_index_drift` = abs(chunks_indexable - vector_chunks),
  // i.e. only the gap that the source review policy did NOT intend to leave.
  // Earlier this dashboard subtracted total chunks from vector chunks and
  // surfaced "Lệch N chunk" for chunks that were correctly held/blocked by
  // the quality gate, which made everything look broken on day-1 demos.
  // Falling back to the abs() formula keeps older API clients working.
  const indexGap = summary.real_index_drift ?? Math.abs((summary.vector_chunk_count || 0) - (summary.chunks_indexable || summary.chunk_count || 0));
  const approvedCount = summary.review_status_counts?.approved || 0;
  const heldCount = summary.indexing_status_counts?.held_for_review || 0;
  const blockedCount = summary.indexing_status_counts?.blocked || 0;
  const filteredSources = useMemo(() => {
    if (filter === "all") return sourceList.slice(0, 18);
    if (filter === "warnings") return sourceList.filter((item) => item.warnings?.length).slice(0, 18);
    if (filter === "needs_review") return sourceList.filter((item) => item.review_status === "needs_review").slice(0, 18);
    if (filter === "approved") return sourceList.filter((item) => item.review_status === "approved").slice(0, 18);
    if (filter === "rejected") return sourceList.filter((item) => item.review_status === "rejected").slice(0, 18);
    return sourceList.filter((item) => item.reliability_level === filter).slice(0, 18);
  }, [sourceList, filter]);

  const coverage = useMemo(() => {
    return STRATEGIC_CATEGORIES.map(([label, terms]) => {
      const count = sourceList.filter((source) => {
        const text = `${source.title || ""} ${source.url || ""} ${source.file_name || ""}`.toLowerCase();
        return terms.some((term) => text.includes(term));
      }).length;
      return { label, count };
    });
  }, [sourceList]);

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_340px]">
          <div className="p-5">
            <div className="flex items-center gap-2">
              <span className="rounded-lg bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">Dữ liệu RAG</span>
              <span className="rounded-lg bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-500">
                {health?.status === "ok" ? "API hoạt động" : "Đang kiểm tra"}
              </span>
            </div>
            <h1 className="mt-4 text-3xl font-bold tracking-tight text-slate-950">Tổng quan dữ liệu</h1>
            <p className="mt-2 max-w-3xl text-sm font-medium leading-6 text-slate-500">Nguồn, chunk, chỉ mục và độ phủ theo nhóm dữ liệu.</p>
            {error && (
              <div className="mt-4 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-sm font-semibold text-red-700">{error}</div>
            )}
          </div>
          <div className="border-t border-slate-100 bg-slate-50 p-5 lg:border-l lg:border-t-0">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={loadAll}
                disabled={busy === "load"}
                className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-semibold text-white disabled:bg-slate-300"
              >
                {busy === "load" ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                Làm mới
              </button>
              <button
                type="button"
                onClick={rebuildIndex}
                disabled={busy === "rebuild"}
                className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 disabled:opacity-50"
              >
                {busy === "rebuild" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Layers3 className="h-4 w-4" />}
                Tạo chỉ mục
              </button>
            </div>
            <div className="mt-4 rounded-xl bg-white p-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">Chất lượng</p>
                <p className="text-lg font-bold text-slate-950">{avgQuality == null ? "—" : `${avgQuality}%`}</p>
              </div>
              <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-emerald-500" style={{ width: `${avgQuality || 0}%` }} />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Metric icon={Database} label="Nguồn RAG" value={summary.source_count ?? "..."} note={`${sources.length || 0} từ API nguồn`} tone="emerald" />
        <Metric icon={FileSearch} label="Nguồn đã duyệt" value={approvedCount} note={`${heldCount} giữ review · ${blockedCount} chặn`} tone={heldCount || blockedCount ? "amber" : "emerald"} />
        <Metric icon={Layers3} label="Chỉ mục vector" value={summary.vector_chunk_count ?? "..."} note={indexGap ? `Lệch ${indexGap} chunk so với đã duyệt` : "Đồng bộ với chunk đã duyệt"} tone={indexGap > 10 ? "amber" : "slate"} />
        <Metric icon={ShieldCheck} label="Nguồn chính thống" value={summary.reliability_counts?.official ?? 0} note={`${warningTotal} cảnh báo dữ liệu`} tone="amber" />
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Panel title="Đồng bộ pipeline dữ liệu" subtitle="Quan sát luồng từ nguồn thô đến chỉ mục RAG.">
          <div className="grid gap-3 md:grid-cols-4">
            <QualityLine label="Tài liệu thô" value={summary.source_count ?? 0} active={Boolean(summary.source_count)} />
            <QualityLine label="Text sạch" value={sourceList.filter((item) => (item.cleaned_char_count || 0) > 0).length} active={sourceList.some((item) => (item.cleaned_char_count || 0) > 0)} />
            <QualityLine label="Chunk tổng" value={summary.chunk_count ?? 0} active={Boolean(summary.chunk_count)} />
            <QualityLine label="Chunk đã duyệt" value={summary.chunks_indexable ?? summary.indexing_status_counts?.indexed ?? 0} active={Boolean(summary.chunks_indexable)} />
          </div>
          {(summary.chunks_held_for_review || summary.chunks_blocked) ? (
            <p className="mt-3 text-xs font-semibold text-slate-500">
              Quality gate: {summary.chunks_held_for_review || 0} chunk chờ review · {summary.chunks_blocked || 0} chunk bị chặn.
            </p>
          ) : null}
          {indexGap > 10 && (
            <div className="mt-4 flex gap-2 rounded-xl border border-amber-100 bg-amber-50 p-3 text-sm font-bold text-amber-800">
              <AlertTriangle className="h-5 w-5 flex-shrink-0" />
              Chunk đã duyệt nhưng chưa nằm trong chỉ mục vector. Tạo lại chỉ mục để đồng bộ.
            </div>
          )}
        </Panel>

        <Panel
          title="Kiểm thử RAG"
          subtitle="Chạy bộ câu hỏi kiểm thử để đánh giá truy xuất nguồn."
          action={
            <button
              type="button"
              onClick={runEval}
              disabled={busy === "eval"}
              className="inline-flex h-9 items-center gap-2 rounded-xl bg-emerald-600 px-3 text-xs font-black text-white disabled:bg-slate-300"
            >
              {busy === "eval" ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
              Kiểm thử
            </button>
          }
        >
          {evalResult ? (
            <div className="space-y-3">
              <div className="rounded-xl bg-emerald-50 p-3 text-sm font-black text-emerald-800">
                Đạt {evalResult.summary.passed}/{evalResult.summary.case_count} · {Math.round(evalResult.summary.pass_rate * 100)}%
              </div>
              {evalResult.results.slice(0, 4).map((item) => (
                <div key={item.id} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                  <p className="line-clamp-2 text-xs font-bold text-slate-700">{item.question}</p>
                  <p className="mt-1 text-[11px] font-semibold text-slate-500">{item.top_sources?.[0]?.title || "Không có nguồn"}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-200 p-5 text-center text-sm font-semibold text-slate-500">
              Chưa chạy kiểm thử trong phiên này.
            </div>
          )}
        </Panel>
      </section>

      <section className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
        <Panel title="Độ phủ nhóm dữ liệu" subtitle="Dựa trên tiêu đề, URL và tên file của nguồn đã nạp.">
          <div className="space-y-2">
            {coverage.map((item) => (
              <div key={item.label} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2">
                <span className="text-sm font-extrabold text-slate-700">{item.label}</span>
                <span className={cx("rounded-full px-3 py-1 text-xs font-black", item.count ? "bg-emerald-100 text-emerald-700" : "bg-white text-slate-400")}>{item.count}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel
          title="Nguồn dữ liệu"
          subtitle="Bảng nguồn đã nạp, lọc theo độ tin cậy và cảnh báo."
          action={
            <select
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
              className="h-9 rounded-xl border border-slate-200 bg-white px-3 text-xs font-black text-slate-700 outline-none"
            >
              <option value="all">Tất cả</option>
              <option value="warnings">Có cảnh báo</option>
              <option value="approved">Đã duyệt</option>
              <option value="needs_review">Cần review</option>
              <option value="rejected">Bị loại</option>
              <option value="official">Chính thống</option>
              <option value="semi_official">Bán chính thống</option>
              <option value="internet">Internet</option>
            </select>
          }
        >
          <div className="overflow-hidden rounded-xl border border-slate-200">
            <div className="max-h-[520px] overflow-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="sticky top-0 bg-slate-50 text-[11px] uppercase tracking-widest text-slate-500">
                  <tr>
                    <th className="px-3 py-3 font-black">Nguồn</th>
                    <th className="px-3 py-3 font-black">Loại</th>
                    <th className="px-3 py-3 font-black">Độ tin cậy</th>
                    <th className="px-3 py-3 font-black">Review</th>
                    <th className="px-3 py-3 font-black">Text sạch</th>
                    <th className="px-3 py-3 font-black">Chunk</th>
                    <th className="px-3 py-3 font-black">Chất lượng</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 bg-white">
                  {filteredSources.map((item) => (
                    <tr key={item.source_id}>
                      <td className="max-w-sm px-3 py-3 align-top">
                        <p className="line-clamp-2 font-bold text-slate-900">{item.title || item.source_id}</p>
                        {item.warnings?.length > 0 && <p className="mt-1 text-xs font-semibold text-amber-600">{item.warnings.join(", ")}</p>}
                      </td>
                      <td className="px-3 py-3 align-top font-semibold text-slate-600">{sourceTypeLabel(item.source_type)}</td>
                      <td className="px-3 py-3 align-top">
                        <span className={cx("rounded-full border px-2.5 py-1 text-[11px] font-black", reliabilityClass(item.reliability_level))}>
                          {reliabilityLabel(item.reliability_level)}
                        </span>
                      </td>
                      <td className="px-3 py-3 align-top">
                        <span className={cx("rounded-full border px-2.5 py-1 text-[11px] font-black", reviewClass(item.review_status))}>
                          {reviewLabel(item.review_status)}
                        </span>
                        <p className="mt-1 text-[11px] font-semibold text-slate-400">{reviewLabel(item.indexing_status)}</p>
                      </td>
                      <td className="px-3 py-3 align-top font-semibold text-slate-700">{item.cleaned_char_count || 0}</td>
                      <td className="px-3 py-3 align-top font-semibold text-slate-700">{item.chunk_count || 0}</td>
                      <td className="px-3 py-3 align-top font-black text-slate-900">{Math.round((item.quality_score || 0) * 100)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Panel>
      </section>
    </div>
  );
}
