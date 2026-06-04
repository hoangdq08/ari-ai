import {
  AlertCircle,
  BarChart3,
  CheckCircle2,
  Clock,
  Database,
  FileText,
  Image,
  Loader2,
  PlayCircle,
  RefreshCw,
  ShieldCheck,
  Trash2
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

function classNames(...items) {
  return items.filter(Boolean).join(" ");
}

function formatPercent(value) {
  if (value == null) return "—";
  return `${Math.round(value * 100)}%`;
}

function totalFromObject(values = {}) {
  return Object.values(values).reduce((sum, value) => sum + Number(value || 0), 0);
}

function normalizeSearchText(value = "") {
  return value
    .toString()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/\s+/g, " ")
    .trim();
}

function sourceSearchText(source) {
  const rawText = `${source.title || ""} ${source.url || ""} ${source.file_name || ""} ${source.source_id || ""}`;
  return `${rawText.toLowerCase()} ${normalizeSearchText(rawText)}`;
}

function matchedTermsForSource(source, terms = []) {
  const text = sourceSearchText(source);
  return terms.filter((term) => text.includes(term.toLowerCase()) || text.includes(normalizeSearchText(term)));
}

function sourcePipelineStatus(source) {
  const steps = [
    { key: "raw", label: "Thô", done: (source.raw_char_count || 0) > 0 },
    { key: "clean", label: "Sạch", done: (source.cleaned_char_count || 0) > 0 },
    { key: "chunk", label: "Chunk", done: (source.chunk_count || 0) > 0 },
    { key: "index", label: "Chỉ mục", done: (source.chunk_count || 0) > 0 }
  ];
  const doneCount = steps.filter((step) => step.done).length;
  return { steps, doneCount, percent: Math.round((doneCount / steps.length) * 100) };
}

function eventLabel(event) {
  const labels = {
    failed: "lỗi",
    chunked: "đã chunk",
    ingested: "đã nạp",
    fetching: "đang tải",
    extracted: "đã bóc text",
    cleaned: "đã làm sạch"
  };
  return labels[event] || event || "hệ thống";
}

function MetricCard({ icon: Icon, label, value, note, tone = "slate" }) {
  const colors = {
    slate: "bg-slate-50 text-slate-600",
    emerald: "bg-emerald-50 text-emerald-700",
    amber: "bg-amber-50 text-amber-700",
    red: "bg-red-50 text-red-700",
    blue: "bg-blue-50 text-blue-700"
  };
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400">{label}</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">{value}</p>
          {note && <p className="mt-1 text-xs font-medium leading-5 text-slate-500">{note}</p>}
        </div>
        <div className={classNames("flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg", colors[tone])}>
          <Icon className="h-[18px] w-[18px]" strokeWidth={2.25} />
        </div>
      </div>
    </div>
  );
}

function Panel({ title, subtitle, action, children, className = "" }) {
  return (
    <section className={classNames("rounded-xl border border-slate-200 bg-white", className)}>
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 px-4 py-4">
        <div>
          <h2 className="text-base font-black text-slate-950">{title}</h2>
          {subtitle && <p className="mt-1 text-sm font-semibold leading-6 text-slate-500">{subtitle}</p>}
        </div>
        {action}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function PipelineStep({ label, value, note, complete }) {
  return (
    <div className="relative flex gap-3 rounded-lg border border-slate-200 bg-white p-3">
      <div
        className={classNames(
          "mt-0.5 flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-lg",
          complete ? "bg-emerald-500 text-white" : "bg-slate-100 text-slate-400"
        )}
      >
        {complete ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Clock className="h-3.5 w-3.5" />}
      </div>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-slate-900">{label}</p>
        <p className="mt-1 text-2xl font-semibold text-slate-950">{value}</p>
        <p className="text-xs font-medium leading-5 text-slate-500">{note}</p>
      </div>
    </div>
  );
}

function CountList({ title, data }) {
  const rows = Object.entries(data || {});
  return (
    <Panel title={title}>
      <div className="space-y-2">
        {rows.length ? (
          rows.map(([key, value]) => (
            <div key={key} className="flex items-center justify-between gap-3 rounded-xl bg-slate-50 px-3 py-2">
              <span className="truncate text-sm font-extrabold text-slate-700">{key}</span>
              <span className="rounded-full bg-white px-3 py-1 text-sm font-black text-slate-900 shadow-sm">{value}</span>
            </div>
          ))
        ) : (
          <p className="rounded-xl border border-dashed border-slate-200 p-4 text-sm font-semibold text-slate-500">Chưa có dữ liệu.</p>
        )}
      </div>
    </Panel>
  );
}

function Checklist({ summary, coverage }) {
  const missingGroups = coverage.filter((topic) => topic.count === 0).length;
  const indexDiff = Math.abs((summary?.vectorChunks || 0) - (summary?.textChunks || 0));
  const items = [
    {
      label: "Nguồn thật",
      ok: (summary?.rawDocs || 0) > 0,
      note: (summary?.rawDocs || 0) > 0 ? `${summary.rawDocs} nguồn đã nạp` : "Chưa có nguồn crawl/upload thật"
    },
    {
      label: "Độ phủ nhóm",
      ok: missingGroups === 0,
      note: missingGroups === 0 ? "Đủ nhóm chính" : `${missingGroups} nhóm còn trống`
    },
    {
      label: "Chỉ mục RAG",
      ok: (summary?.textChunks || 0) > 0 && indexDiff <= 5,
      note: indexDiff > 5 ? `Lệch ${indexDiff} chunk` : `${summary?.vectorChunks || 0} vector`
    },
    {
      label: "Chất lượng nguồn",
      ok: (summary?.avgQuality || 0) >= 0.65,
      note: `Trung bình ${formatPercent(summary?.avgQuality)}`
    }
  ];
  return (
    <Panel title="Checklist vận hành" subtitle="Các điều kiện tối thiểu trước khi demo hoặc release.">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {items.map((item) => (
          <div key={item.label} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-semibold text-slate-900">{item.label}</p>
              <span className={classNames("rounded-lg px-2 py-1 text-[11px] font-semibold", item.ok ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700")}>
                {item.ok ? "Ổn" : "Cần xử lý"}
              </span>
            </div>
            <p className="mt-2 text-xs font-medium leading-5 text-slate-500">{item.note}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function DataTable({ title, subtitle, rows, columns, emptyText }) {
  return (
    <Panel title={title} subtitle={subtitle}>
      <div className="overflow-hidden rounded-xl border border-slate-200">
        {rows?.length ? (
          <div className="max-h-96 overflow-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="sticky top-0 bg-slate-50 text-[11px] uppercase tracking-widest text-slate-500">
                <tr>
                  {columns.map((column) => (
                    <th key={column.key} className="px-3 py-3 font-black">
                      {column.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {rows.slice(0, 15).map((row, index) => (
                  <tr key={`${title}-${index}`}>
                    {columns.map((column) => (
                      <td key={column.key} className="max-w-xs px-3 py-3 align-top font-semibold text-slate-700">
                        <span className="line-clamp-2 break-words">{column.render ? column.render(row) : row[column.key] || "0"}</span>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="p-5 text-sm font-semibold text-slate-500">{emptyText}</p>
        )}
      </div>
    </Panel>
  );
}

const STRATEGIC_COVERAGE_TOPICS = [
  {
    key: "dinh_duong_chi_phi",
    label: "Dinh dưỡng & chi phí",
    description: "Phân bón, dinh dưỡng, chi phí và tối ưu kinh tế vườn.",
    terms: ["dinh dưỡng", "phân bón", "chi phí", "kinh tế"],
    query: "quản lý dinh dưỡng chi phí phân bón tối ưu kinh tế vườn cà phê"
  },
  {
    key: "tao_tan_chat_luong",
    label: "Tạo tán & chất lượng",
    description: "Tạo tán, tỉa cành, năng suất và chất lượng hạt.",
    terms: ["tạo tán", "tỉa cành", "năng suất", "chất lượng hạt"],
    query: "kỹ thuật tạo tán tỉa cành cà phê tăng năng suất chất lượng hạt"
  },
  {
    key: "nuoc_tuoi_han",
    label: "Nước tưới & chống hạn",
    description: "Hệ thống tưới, mùa khô, chống hạn và tiết kiệm chi phí.",
    terms: ["tưới", "nước", "hạn", "chống hạn"],
    query: "đầu tư hệ thống nước tưới cà phê giải pháp chống hạn tiết kiệm chi phí"
  },
  {
    key: "sau_benh_du_luong",
    label: "Sâu bệnh & dư lượng",
    description: "Sâu bệnh, thuốc BVTV, dư lượng và yêu cầu xuất khẩu.",
    terms: ["sâu bệnh", "dư lượng", "bảo vệ thực vật", "xuất khẩu"],
    query: "quản lý sâu bệnh hại cà phê kiểm soát dư lượng thuốc bảo vệ thực vật xuất khẩu"
  },
  {
    key: "giong_cai_tao",
    label: "Giống & cải tạo",
    description: "Giống mới, ghép cải tạo, tái canh và vườn già cỗi.",
    terms: ["giống", "ghép", "cải tạo", "vườn già", "tái canh"],
    query: "chi phí đầu tư giống cà phê mới ghép cải tạo vườn cà phê già cỗi"
  },
  {
    key: "tieu_chuan_bao_tieu",
    label: "Tiêu chuẩn & bao tiêu",
    description: "VietGAP, 4C, tiêu chuẩn bền vững, bao tiêu và nâng giá trị.",
    terms: ["tiêu chuẩn", "vietgap", "4c", "bao tiêu", "nâng giá trị"],
    query: "áp dụng tiêu chuẩn nông nghiệp tốt cà phê bao tiêu đầu ra nâng giá trị"
  },
  {
    key: "khac_lien_quan",
    label: "Khác liên quan",
    description: "Vấn đề cà phê/nông nghiệp liên quan nhưng chưa vào nhóm chính.",
    terms: ["khác", "tổng quan", "kinh nghiệm", "rủi ro", "khuyến nghị", "tư vấn"],
    query: "các vấn đề khác liên quan đến sản xuất cà phê kinh nghiệm rủi ro khuyến nghị"
  },
  {
    key: "giao_tiep",
    label: "Giao tiếp",
    description: "Lời chào, cảm ơn, hướng dẫn hỏi và chuyển hướng ngoài phạm vi.",
    terms: ["chào", "cảm ơn", "hướng dẫn", "hỗ trợ", "ngoài phạm vi", "bạn là ai"],
    query: "hướng dẫn người dùng đặt câu hỏi về cây cà phê và dữ liệu nông nghiệp"
  }
];

const LIFECYCLE_TOPICS = [
  {
    key: "dieu_kien_san_xuat",
    label: "Điều kiện sản xuất",
    description: "Đất, nước, khí hậu, giống, địa hình.",
    terms: ["đất", "nước", "khí hậu", "địa hình", "giống"],
    query: "điều kiện đất nước khí hậu địa hình giống cây cà phê"
  },
  {
    key: "thiet_lap_vuon",
    label: "Thiết lập vườn trồng",
    description: "Vườn ươm, làm đất, mật độ trồng, cây che bóng, hệ thống tưới.",
    terms: ["vườn ươm", "làm đất", "mật độ", "trồng mới", "che bóng", "hệ thống tưới"],
    query: "thiết lập vườn trồng cà phê vườn ươm làm đất mật độ cây che bóng hệ thống tưới"
  },
  {
    key: "cham_soc_cay",
    label: "Chăm sóc cây",
    description: "Tưới, bón phân, tỉa cành, tạo tán, quản lý cỏ, cải tạo đất.",
    terms: ["tưới", "bón phân", "tỉa cành", "tạo tán", "quản lý cỏ", "cải tạo đất"],
    query: "chăm sóc cây cà phê tưới bón phân tỉa cành tạo tán quản lý cỏ cải tạo đất"
  },
  {
    key: "bao_ve_cay_trong",
    label: "Bảo vệ cây trồng",
    description: "Sâu bệnh, nấm, tuyến trùng, stress hạn/nhiệt, phòng ngừa và xử lý.",
    terms: ["sâu bệnh", "nấm", "tuyến trùng", "stress", "hạn", "phòng ngừa", "xử lý"],
    query: "bảo vệ cây cà phê sâu bệnh nấm tuyến trùng stress hạn nhiệt phòng ngừa xử lý"
  },
  {
    key: "thu_hoach",
    label: "Thu hoạch",
    description: "Thời điểm thu hoạch, tỷ lệ trái chín, nhân công hái, hao hụt.",
    terms: ["thu hoạch", "trái chín", "nhân công", "hao hụt"],
    query: "thu hoạch cà phê thời điểm tỷ lệ trái chín nhân công hái hao hụt"
  },
  {
    key: "sau_thu_hoach",
    label: "Sau thu hoạch",
    description: "Sơ chế, phơi/sấy, bảo quản, phân loại, kiểm soát lỗi hạt.",
    terms: ["sơ chế", "phơi", "sấy", "bảo quản", "phân loại", "lỗi hạt"],
    query: "sau thu hoạch cà phê sơ chế phơi sấy bảo quản phân loại kiểm soát lỗi hạt"
  },
  {
    key: "quan_tri_san_xuat",
    label: "Quản trị sản xuất",
    description: "Nhân lực, thiết bị, SOP, dữ liệu, chi phí, năng suất, chất lượng.",
    terms: ["nhân lực", "thiết bị", "sop", "dữ liệu", "chi phí", "năng suất", "chất lượng"],
    query: "quản trị sản xuất cà phê nhân lực thiết bị SOP dữ liệu chi phí năng suất chất lượng"
  },
  {
    key: "khac_lien_quan",
    label: "Khác",
    description: "Những câu hỏi liên quan đến cà phê nhưng chưa đủ rõ để xếp nhóm.",
    terms: ["khác", "tổng quan", "kinh nghiệm", "rủi ro", "tư vấn"],
    query: "vấn đề khác liên quan đến cây cà phê kinh nghiệm tổng quan rủi ro"
  },
  {
    key: "giao_tiep",
    label: "Giao tiếp",
    description: "Intent hội thoại, hướng dẫn hỏi, phản hồi ngoài phạm vi có EQ.",
    terms: ["chào", "cảm ơn", "hướng dẫn", "hỗ trợ", "ngoài phạm vi"],
    query: "giao tiếp trợ lý nông nghiệp hướng dẫn người dùng hỏi về cây cà phê"
  }
];

function coverageTopics(sources = [], topics = STRATEGIC_COVERAGE_TOPICS) {
  return topics.map((topic) => {
    const matchedSources = sources
      .map((source) => ({ ...source, matched_terms: matchedTermsForSource(source, topic.terms) }))
      .filter((source) => source.matched_terms.length > 0)
      .sort((a, b) => (b.quality_score || 0) - (a.quality_score || 0));
    return { ...topic, count: matchedSources.length, sources: matchedSources };
  });
}

function CoverageCard({ topic, maxCount }) {
  const hasData = topic.count > 0;
  const width = hasData && maxCount ? Math.max(10, Math.min(100, Math.round((topic.count / maxCount) * 100))) : 0;
  return (
    <article className={classNames("rounded-2xl border p-5", hasData ? "border-emerald-100 bg-emerald-50/70" : "border-amber-100 bg-amber-50/60")}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className={classNames("text-lg font-black", hasData ? "text-emerald-900" : "text-amber-900")}>{topic.label}</h3>
          <p className="mt-1 text-sm font-semibold leading-6 text-slate-600">{topic.description}</p>
        </div>
        <span className="flex h-11 min-w-11 items-center justify-center rounded-full bg-white px-3 text-lg font-black text-slate-950 shadow-sm">{topic.count}</span>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {topic.terms.map((term) => (
          <span key={term} className="rounded-full bg-white/80 px-2.5 py-1 text-[11px] font-black text-slate-600 shadow-sm">
            {term}
          </span>
        ))}
      </div>
      <div className="mt-5 h-2 overflow-hidden rounded-full bg-white">
        <div className={classNames("h-full rounded-full", hasData ? "bg-emerald-500" : "bg-amber-300")} style={{ width: `${width}%` }} />
      </div>
      {hasData ? (
        <div className="mt-4 space-y-2">
          {topic.sources.slice(0, 3).map((source) => {
            const pipeline = sourcePipelineStatus(source);
            return (
              <div key={source.source_id} className="rounded-xl border border-white/80 bg-white/80 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="line-clamp-1 text-sm font-black text-slate-900">{source.title || source.file_name || source.source_id}</p>
                    <p className="mt-1 text-[11px] font-bold text-slate-500">
                      Khớp: {source.matched_terms.join(", ")} · Chất lượng {formatPercent(source.quality_score)}
                    </p>
                  </div>
                  <span className="rounded-full bg-slate-950 px-2 py-1 text-[10px] font-black text-white">{pipeline.percent}%</span>
                </div>
                <div className="mt-3 grid grid-cols-4 gap-1.5">
                  {pipeline.steps.map((step) => (
                    <div key={step.key} className={classNames("rounded-md px-2 py-1 text-center text-[10px] font-black", step.done ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-400")}>
                      {step.label}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="mt-4 rounded-xl bg-white/70 p-3 text-xs font-bold leading-5 text-amber-800">
          Chưa có nguồn thật cho nhóm này. Cần tìm kiếm, duyệt nguồn và nạp vào RAG trước khi chatbot dùng ổn định.
        </p>
      )}
      <a href={`/admin/crawl?query=${encodeURIComponent(topic.query)}`} className={classNames("mt-3 inline-flex text-xs font-black", hasData ? "text-emerald-700" : "text-amber-700")}>
        {hasData ? "Crawl bổ sung" : "Cần crawl mục này"}
      </a>
    </article>
  );
}

function FlowExplainer() {
  const steps = [
    ["1", "Tìm nguồn", "Sinh nguồn đề xuất theo nhóm/truy vấn, chưa nạp dữ liệu."],
    ["2", "Chấm điểm", "Lọc theo từ khóa, loại nguồn, domain và độ lệch chủ đề."],
    ["3", "Duyệt", "Người quản trị chọn nguồn phù hợp. Không chọn thì không thu thập."],
    ["4", "Bóc text", "Tải web/PDF/DOCX/TXT và lấy text thô."],
    ["5", "Làm sạch", "Chuẩn hóa Unicode, bỏ nhiễu, ghép dòng, giảm trùng."],
    ["6", "Chia chunk", "Chia đoạn RAG kèm metadata nguồn."],
    ["7", "Lập chỉ mục", "Đẩy chunk vào kho vector/local để chatbot truy xuất."]
  ];
  return (
    <Panel title="Luồng kiểm soát dữ liệu" subtitle="Nguồn chỉ được tính khi đã nạp và khớp rule của nhóm.">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-7">
        {steps.map(([number, label, note]) => (
          <div key={label} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-950 text-xs font-black text-white">{number}</span>
            <p className="mt-3 text-sm font-black text-slate-950">{label}</p>
            <p className="mt-1 text-xs font-semibold leading-5 text-slate-500">{note}</p>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function LifecycleCard({ topic, index, maxCount }) {
  const hasData = topic.count > 0;
  const width = hasData && maxCount ? Math.max(10, Math.min(100, Math.round((topic.count / maxCount) * 100))) : 0;
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4">
      <div className="flex items-start gap-3">
        <div className={classNames("flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl text-sm font-black", hasData ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-500")}>
          {index + 1}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-3">
            <h3 className="text-base font-black text-slate-950">{topic.label}</h3>
            <span className={classNames("rounded-full px-2.5 py-1 text-xs font-black", hasData ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700")}>{topic.count}</span>
          </div>
          <p className="mt-1 text-sm font-semibold leading-6 text-slate-500">{topic.description}</p>
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div className={classNames("h-full rounded-full", hasData ? "bg-emerald-500" : "bg-amber-300")} style={{ width: `${width}%` }} />
          </div>
        </div>
      </div>
    </article>
  );
}

export default function ReportsDashboard({ apiBase }) {
  const [payload, setPayload] = useState(null);
  const [quality, setQuality] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [error, setError] = useState("");

  const summary = useMemo(() => {
    if (!payload) return null;
    const text = payload.text_rag || {};
    const imageCrawl = payload.image_crawl || {};
    const qualitySummary = quality?.summary || {};
    const crawledSourceList = quality?.sources || [];
    return {
      crawledSources: qualitySummary.source_count ?? 0,
      rawDocs: qualitySummary.source_count ?? text.raw_document_count ?? 0,
      cleanedDocs: crawledSourceList.filter((source) => (source.cleaned_char_count || 0) > 0).length,
      textChunks: qualitySummary.chunk_count ?? 0,
      vectorChunks: qualitySummary.vector_chunk_count ?? 0,
      ragSources: text.source_count ?? 0,
      avgQuality: qualitySummary.avg_quality_score ?? 0,
      reliabilityCounts: qualitySummary.reliability_counts || {},
      warningCounts: qualitySummary.warning_counts || {},
      metadataCount: imageCrawl.metadata_count || 0,
      failures: imageCrawl.download_failure_count || 0,
      rawImages: totalFromObject(imageCrawl.raw_count_by_class),
      cleanImages: totalFromObject(imageCrawl.clean_count_by_class)
    };
  }, [payload, quality]);

  const coverage = useMemo(() => coverageTopics(quality?.sources || []), [quality]);
  const lifecycleCoverage = useMemo(() => coverageTopics(quality?.sources || [], LIFECYCLE_TOPICS), [quality]);
  const coverageMax = Math.max(1, ...coverage.map((topic) => topic.count));
  const lifecycleMax = Math.max(1, ...lifecycleCoverage.map((topic) => topic.count));
  const latestEvents = useMemo(() => events.slice().reverse().slice(0, 12), [events]);
  const systemReady = Boolean(summary?.rawDocs);

  async function loadReports(showLoading = !payload) {
    if (showLoading) setLoading(true);
    setError("");
    try {
      const [dashboardResponse, qualityResponse] = await Promise.all([
        fetch(`${apiBase}/crawl-dashboard`),
        fetch(`${apiBase}/data-quality`)
      ]);
      if (!dashboardResponse.ok) throw new Error(await dashboardResponse.text());
      if (!qualityResponse.ok) throw new Error(await qualityResponse.text());
      setPayload(await dashboardResponse.json());
      setQuality(await qualityResponse.json());
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message || "Không tải được báo cáo.");
    } finally {
      if (showLoading) setLoading(false);
    }
  }

  async function loadEvents() {
    try {
      const response = await fetch(`${apiBase}/crawl-events?limit=120`);
      if (response.ok) {
        setEvents((await response.json()).events || []);
      }
    } catch {
      // Realtime report is best-effort.
    }
  }

  async function resetData() {
    const ok = window.confirm("Xóa dữ liệu thô, text sạch, chunk, vector và lịch sử crawl cũ? Hệ thống sẽ không nạp dữ liệu mẫu.");
    if (!ok) return;
    setResetting(true);
    setError("");
    try {
      const response = await fetch(`${apiBase}/admin/reset-rag-data`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seed_knowledge_base: false })
      });
      if (!response.ok) throw new Error(await response.text());
      await loadReports();
      await loadEvents();
    } catch (err) {
      setError(err.message || "Không reset được dữ liệu.");
    } finally {
      setResetting(false);
    }
  }

  useEffect(() => {
    void loadReports(true);
    void loadEvents();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return undefined;
    const timer = window.setInterval(() => {
      void loadReports(false);
      void loadEvents();
    }, 5000);
    return () => window.clearInterval(timer);
  }, [autoRefresh]);

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="flex items-center gap-3 rounded-full bg-white px-5 py-3 text-sm font-black text-slate-600 shadow-sm">
          <Loader2 className="h-5 w-5 animate-spin text-emerald-600" />
          Đang tải báo cáo
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-slate-200 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className={classNames(
                "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold",
                systemReady ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
              )}
            >
              {systemReady ? <CheckCircle2 className="h-3.5 w-3.5" /> : <AlertCircle className="h-3.5 w-3.5" />}
              {systemReady ? "Dữ liệu crawl sẵn sàng" : "Chưa có dữ liệu crawl"}
            </span>
            <span className="rounded-md bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-500">
              {lastUpdated ? `Cập nhật ${lastUpdated.toLocaleTimeString()}` : "Chưa cập nhật"}
            </span>
            <span className="rounded-md bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-500">
              RAG {summary?.ragSources ?? 0} nguồn · {summary?.vectorChunks ?? 0} vector
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setAutoRefresh((value) => !value)}
              className={classNames(
                "inline-flex h-9 items-center justify-center gap-2 rounded-lg border px-3 text-xs font-semibold transition",
                autoRefresh ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-white text-slate-600"
              )}
            >
              <PlayCircle className="h-4 w-4" />
              Tự động {autoRefresh ? "bật" : "tắt"}
            </button>
            <button
              type="button"
              onClick={() => {
                void loadReports(true);
                void loadEvents();
              }}
              className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-slate-950 px-3 text-xs font-semibold text-white"
            >
              <RefreshCw className="h-4 w-4" />
              Làm mới
            </button>
            <button
              type="button"
              onClick={resetData}
              disabled={resetting}
              className="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-red-200 bg-white px-3 text-xs font-semibold text-red-700 disabled:opacity-60"
            >
              {resetting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
              Xóa
            </button>
          </div>
        </div>
        <div className="grid gap-4 px-4 py-4 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">Báo cáo</p>
            <h2 className="mt-1 text-2xl font-bold tracking-tight text-slate-950">Vận hành dữ liệu</h2>
            <p className="mt-2 max-w-3xl text-sm font-medium leading-6 text-slate-500">Độ phủ, chất lượng nguồn và trạng thái chỉ mục.</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">Phạm vi</p>
            <p className="mt-1 text-sm font-medium leading-6 text-slate-600">Chỉ tính nguồn crawl/upload thật.</p>
          </div>
        </div>
        {error && (
          <div className="mx-4 mb-4 flex gap-2 rounded-lg border border-red-100 bg-red-50 p-3 text-sm font-semibold text-red-700">
            <AlertCircle className="h-5 w-5" />
            {error}
          </div>
        )}
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard icon={Database} label="Nguồn đã crawl" value={summary?.crawledSources ?? 0} note="Nguồn thô đã nạp" tone={systemReady ? "emerald" : "amber"} />
        <MetricCard icon={FileText} label="Chunk văn bản" value={summary?.textChunks ?? 0} note="Chunk từ nguồn thật" tone="blue" />
        <MetricCard
          icon={ShieldCheck}
          label="Điểm kiểm định"
          value={summary?.crawledSources ? formatPercent(summary?.avgQuality) : "—"}
          note={`${summary?.warningCounts ? Object.values(summary.warningCounts).reduce((sum, value) => sum + Number(value || 0), 0) : 0} cảnh báo dữ liệu`}
          tone={(summary?.avgQuality ?? 0) >= 0.75 ? "emerald" : (summary?.avgQuality ?? 0) >= 0.55 ? "amber" : "red"}
        />
        <MetricCard icon={Image} label="Metadata ảnh" value={summary?.metadataCount ?? 0} note={`${summary?.failures ?? 0} lỗi tải ảnh`} tone={summary?.failures ? "amber" : "slate"} />
      </section>

      <FlowExplainer />

      <Checklist summary={summary} coverage={coverage} />

      <Panel title="Độ phủ dữ liệu" subtitle="Nguồn thật theo nhóm dữ liệu.">
        <div className="grid gap-4 lg:grid-cols-2">
          {coverage.map((topic) => (
            <CoverageCard key={topic.key} topic={topic} maxCount={coverageMax} />
          ))}
        </div>
      </Panel>

      <Panel
        title="Vòng đời sản xuất"
        subtitle="Điều kiện → Thiết lập → Chăm sóc → Bảo vệ → Thu hoạch → Sau thu hoạch → Quản trị."
      >
        <div className="grid gap-3 lg:grid-cols-2">
          {lifecycleCoverage.map((topic, index) => (
            <LifecycleCard key={topic.key} topic={topic} index={index} maxCount={lifecycleMax} />
          ))}
        </div>
      </Panel>

      <section className="grid gap-5 xl:grid-cols-[1fr_420px]">
        <Panel title="Pipeline RAG" subtitle="Thô → Sạch → Chunk → Chỉ mục.">
          <div className="grid gap-3 md:grid-cols-2">
            <PipelineStep label="Tài liệu thô" value={summary?.rawDocs ?? 0} note="Nguồn crawl/upload gốc" complete={(summary?.rawDocs ?? 0) > 0} />
            <PipelineStep label="Text sạch" value={summary?.cleanedDocs ?? 0} note="Đã bóc text và làm sạch" complete={(summary?.cleanedDocs ?? 0) > 0} />
            <PipelineStep label="Chunk" value={summary?.textChunks ?? 0} note="Chunk thật đưa vào RAG" complete={(summary?.textChunks ?? 0) > 0} />
            <PipelineStep label="Chỉ mục vector" value={summary?.vectorChunks ?? 0} note="Chunk thật đã lập chỉ mục" complete={(summary?.vectorChunks ?? 0) > 0} />
          </div>
        </Panel>

        <Panel
          title="Nhật ký crawl"
          subtitle="Sự kiện mới nhất."
          action={<span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-black text-emerald-700">{events.length} sự kiện</span>}
        >
          <div className="max-h-[352px] space-y-2 overflow-auto pr-1">
            {latestEvents.length ? (
              latestEvents.map((event, index) => (
                <div key={`${event.logged_at}-${index}`} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={classNames(
                        "rounded-full px-2.5 py-1 text-[11px] font-black uppercase",
                        event.event === "failed"
                          ? "bg-red-100 text-red-700"
                          : event.event === "chunked" || event.event === "ingested"
                            ? "bg-emerald-100 text-emerald-700"
                            : event.event === "fetching"
                              ? "bg-blue-100 text-blue-700"
                              : "bg-slate-200 text-slate-700"
                      )}
                    >
                      {eventLabel(event.event)}
                    </span>
                    <span className="text-xs font-bold text-slate-400">{new Date(event.logged_at).toLocaleTimeString()}</span>
                  </div>
                  <p className="mt-2 line-clamp-2 break-all text-sm font-bold text-slate-800">{event.title || event.url || event.source_id || "system"}</p>
                  {(event.chunks_created || event.discovered_link_count || event.error) && (
                    <p className="mt-1 text-xs font-semibold text-slate-500">
                      {event.chunks_created ? `chunk ${event.chunks_created} · thêm ${event.chunks_added || 0}` : ""}
                      {event.discovered_link_count ? ` phát hiện ${event.discovered_link_count}` : ""}
                      {event.error ? ` lỗi: ${event.error}` : ""}
                    </p>
                  )}
                </div>
              ))
            ) : (
              <p className="rounded-xl border border-dashed border-slate-200 p-4 text-sm font-semibold text-slate-500">Chưa có sự kiện crawl trong phiên backend hiện tại.</p>
            )}
          </div>
        </Panel>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <CountList title="Độ tin cậy nguồn" data={summary?.reliabilityCounts} />
        <CountList title="Cảnh báo chất lượng text" data={summary?.warningCounts} />
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <DataTable
          title="Lịch sử crawl gần đây"
          subtitle="Nguồn đã tải, bóc text, làm sạch và nạp."
          rows={payload?.text_rag?.recent_crawl_history || []}
          emptyText="Chưa có lịch sử crawl."
          columns={[
            { key: "status", label: "Trạng thái" },
            { key: "source_type", label: "Loại" },
            { key: "reliability_level", label: "Độ tin cậy" },
            { key: "title", label: "Tiêu đề" },
            { key: "url", label: "URL" }
          ]}
        />
        <DataTable
          title="Nguồn đề xuất gần đây"
          subtitle="Nguồn chờ người quản trị duyệt trước khi crawl."
          rows={payload?.text_rag?.recent_search_candidates || []}
          emptyText="Chưa có nguồn đề xuất."
          columns={[
            { key: "relevance_score", label: "Điểm" },
            { key: "source_type", label: "Loại" },
            { key: "reliability_level", label: "Độ tin cậy" },
            { key: "title", label: "Tiêu đề" },
            { key: "url", label: "URL" }
          ]}
        />
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <DataTable
          title="Tổng quan dữ liệu ảnh"
          subtitle={`Ảnh thô ${summary?.rawImages ?? 0}, ảnh sạch ${summary?.cleanImages ?? 0}.`}
          rows={payload?.reports?.dataset_summary || []}
          emptyText="Chưa có báo cáo dataset_summary.csv."
          columns={[
            { key: "class_label", label: "Lớp" },
            { key: "raw_count", label: "Thô" },
            { key: "clean_count", label: "Sạch" },
            { key: "rejected_count", label: "Loại" }
          ]}
        />
        <DataTable
          title="Tổng quan domain nguồn"
          subtitle="Miền nguồn ảnh và trạng thái giấy phép."
          rows={payload?.reports?.source_domain_summary || []}
          emptyText="Chưa có báo cáo source_domain_summary.csv."
          columns={[
            { key: "source_domain", label: "Domain" },
            { key: "count", label: "Số lượng" },
            { key: "missing_or_unknown_license_count", label: "Chưa rõ giấy phép" }
          ]}
        />
      </section>

    </div>
  );
}
