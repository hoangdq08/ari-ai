import {
  AlertTriangle,
  BadgeCheck,
  BookOpenCheck,
  BrainCircuit,
  CheckCircle2,
  CircleAlert,
  DatabaseZap,
  FileCheck2,
  Gauge,
  GitBranch,
  Globe2,
  Layers3,
  Loader2,
  RefreshCw,
  Scale,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

function cx(...items) {
  return items.filter(Boolean).join(" ");
}

function percent(value) {
  if (value == null) return "—";
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function statusTone(status) {
  if (status === "ready" || status === "controlled" || status === "active") return "emerald";
  if (status === "review" || status === "policy") return "amber";
  return "red";
}

function toneClass(tone) {
  const tones = {
    emerald: "border-emerald-100 bg-emerald-50 text-emerald-700",
    amber: "border-amber-100 bg-amber-50 text-amber-700",
    red: "border-red-100 bg-red-50 text-red-700",
    blue: "border-blue-100 bg-blue-50 text-blue-700",
    slate: "border-slate-100 bg-slate-50 text-slate-600",
  };
  return tones[tone] || tones.slate;
}

function Metric({ icon: Icon, label, value, note, tone = "slate" }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400">{label}</p>
          <p className="mt-2 text-3xl font-black tracking-tight text-slate-950">{value}</p>
          {note && <p className="mt-1 text-xs font-semibold leading-5 text-slate-500">{note}</p>}
        </div>
        <div className={cx("flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg border", toneClass(tone))}>
          <Icon className="h-5 w-5" strokeWidth={2.35} />
        </div>
      </div>
    </div>
  );
}

function Panel({ title, subtitle, action, children, className = "" }) {
  return (
    <section className={cx("rounded-xl border border-slate-200 bg-white shadow-sm", className)}>
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

function RiskBadge({ status }) {
  const tone = status === "needs_action" ? "red" : "emerald";
  return (
    <span className={cx("rounded-lg border px-2 py-1 text-[11px] font-black uppercase tracking-wide", toneClass(tone))}>
      {status === "needs_action" ? "cần xử lý" : "đã kiểm soát"}
    </span>
  );
}

function ProgressLine({ label, value, note, tone = "emerald" }) {
  const width = Math.max(0, Math.min(100, Math.round(Number(value || 0) * 100)));
  const bar = tone === "red" ? "bg-red-500" : tone === "amber" ? "bg-amber-500" : "bg-emerald-500";
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-black text-slate-800">{label}</p>
          {note && <p className="mt-1 truncate text-xs font-semibold text-slate-500">{note}</p>}
        </div>
        <span className="text-sm font-black text-slate-950">{width}%</span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-white">
        <div className={cx("h-full rounded-full", bar)} style={{ width: `${width}%` }} />
      </div>
    </div>
  );
}

function buildTheoryCases(summary, activeRisks) {
  return [
    {
      key: "bias",
      icon: BrainCircuit,
      title: "Bias không phải lỗi ngẫu nhiên",
      theory: "AI học từ dữ liệu lịch sử, nên sai lệch trong nguồn dữ liệu sẽ được mã hóa thành sai lệch có hệ thống trong khuyến nghị.",
      project: `Trong dự án này, bias xuất hiện khi nguồn internet/thương mại chiếm ${percent(summary.internet_source_share)} và nguồn đã tin cậy chỉ chiếm ${percent(summary.reviewed_source_share)}.`,
      evidence: `Trust report đo tỷ lệ nguồn, cảnh báo thương mại và gate review. ${summary.needs_review_source_count || 0} nguồn đang bị giữ để review.`,
      tone: summary.internet_source_share > 0.75 ? "red" : "amber",
    },
    {
      key: "fairness",
      icon: Scale,
      title: "Fairness là công bằng theo điều kiện",
      theory: "Không có một định nghĩa fairness tối ưu cho mọi nhóm; hệ thống phải chọn mục tiêu công bằng phù hợp bối cảnh.",
      project: "Với nông nghiệp, fairness là không áp một khuyến nghị chung cho mọi vùng, quy mô nông hộ, mùa vụ và điều kiện đất nước khác nhau.",
      evidence: `Dashboard đo coverage theo vùng và chủ đề. Độ phủ chủ đề hiện là ${percent(summary.topic_coverage_rate)}.`,
      tone: summary.topic_coverage_rate >= 0.85 ? "emerald" : "red",
    },
    {
      key: "robustness",
      icon: ShieldCheck,
      title: "Robustness chống học nhầm tương quan",
      theory: "Mô hình dễ học các tín hiệu giả như nguồn thương mại, text nhiễu, ảnh mờ, hoặc context thiếu thay vì bản chất nông học.",
      project: "Chat/RAG phải hạ độ tin cậy khi thiếu vùng, tuổi cây, mùa vụ, triệu chứng hoặc khi nguồn có nhiều cảnh báo chất lượng.",
      evidence: `${summary.high_risk_warning_total || 0} cảnh báo rủi ro cao đang được đưa vào risk register.`,
      tone: summary.high_risk_warning_total > 0 ? "amber" : "emerald",
    },
    {
      key: "explainability",
      icon: BookOpenCheck,
      title: "Explainability phải giúp người dùng hành động",
      theory: "Giải thích tốt không chỉ nói mô hình dự đoán gì, mà nói vì sao, dựa vào nguồn nào, và cần thay đổi thông tin gì để kết quả tốt hơn.",
      project: "System card yêu cầu câu trả lời nêu nguồn, mức tin cậy, giả định vùng/mùa vụ và thông tin còn thiếu theo hướng phản thực tế.",
      evidence: "Pattern: nếu bổ sung vùng trồng, tuổi cây, triệu chứng rõ hơn thì khuyến nghị có thể cụ thể và đáng tin hơn.",
      tone: "blue",
    },
    {
      key: "leakage",
      icon: GitBranch,
      title: "Data leakage làm điểm đánh giá ảo",
      theory: "Nếu dữ liệu tương lai, cùng URL, cùng chunk hoặc cùng ảnh lọt vào cả train và test, mô hình trông có vẻ giỏi nhưng thất bại ngoài thực tế.",
      project: "Dữ liệu RAG cần dedupe theo nội dung và khi đánh giá phải split theo nguồn/thời gian thay vì split ngẫu nhiên theo chunk.",
      evidence: "Backend hiện chặn nạp trùng bằng content_hash và risk register có control chống leakage.",
      tone: "emerald",
    },
    {
      key: "feedback",
      icon: DatabaseZap,
      title: "Feedback loop có thể khuếch đại bias",
      theory: "Khi dự đoán của hệ thống tạo ra dữ liệu huấn luyện tương lai, hệ thống có thể tự củng cố lựa chọn sai.",
      project: "Click/feedback của người dùng không được đi thẳng vào training data; cần review trước khi thành nhãn huấn luyện.",
      evidence: activeRisks.some((risk) => risk.key === "feedback_loop") ? "Feedback loop đang cần xử lý." : "Risk register đánh dấu feedback loop đang được kiểm soát bằng policy review.",
      tone: "emerald",
    },
  ];
}

function TheoryCard({ item }) {
  const Icon = item.icon;
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start gap-3">
        <div className={cx("flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg border", toneClass(item.tone))}>
          <Icon className="h-5 w-5" strokeWidth={2.35} />
        </div>
        <div className="min-w-0">
          <h3 className="text-sm font-black text-slate-950">{item.title}</h3>
          <div className="mt-3 space-y-2">
            <p className="rounded-lg bg-slate-50 px-3 py-2 text-xs font-bold leading-5 text-slate-600">
              <span className="text-slate-950">Lý thuyết: </span>
              {item.theory}
            </p>
            <p className="rounded-lg bg-emerald-50 px-3 py-2 text-xs font-bold leading-5 text-emerald-800">
              <span className="text-emerald-950">Trong dự án: </span>
              {item.project}
            </p>
            <p className="rounded-lg bg-white px-3 py-2 text-xs font-bold leading-5 text-slate-500 ring-1 ring-slate-100">
              <span className="text-slate-900">Minh chứng/kiểm soát: </span>
              {item.evidence}
            </p>
          </div>
        </div>
      </div>
    </article>
  );
}

export default function TrustDashboard({ apiBase }) {
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadTrust() {
    setError("");
    try {
      const response = await fetch(`${apiBase}/trust-report`);
      if (!response.ok) throw new Error(await response.text());
      setPayload(await response.json());
    } catch (err) {
      setError(err.message || "Không tải được trust report.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadTrust();
  }, []);

  const summary = payload?.summary || {};
  const risks = payload?.risk_register || [];
  const activeRisks = useMemo(() => risks.filter((item) => item.status === "needs_action"), [risks]);
  const theoryCases = useMemo(() => buildTheoryCases(summary, activeRisks), [summary, activeRisks]);
  const scoreTone = summary.status === "ready" ? "emerald" : summary.status === "review" ? "amber" : "red";

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="flex items-center gap-3 rounded-full bg-white px-5 py-3 text-sm font-bold text-slate-600 shadow-sm">
          <Loader2 className="h-5 w-5 animate-spin text-emerald-600" />
          Đang tải AI Trust Dashboard
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="grid gap-0 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="p-5">
            <div className="flex flex-wrap items-center gap-2">
              <span className={cx("rounded-lg border px-3 py-1 text-xs font-black", toneClass(scoreTone))}>
                {summary.status === "ready" ? "Sẵn sàng" : summary.status === "review" ? "Cần review" : "Rủi ro cao"}
              </span>
              <span className="rounded-lg bg-slate-100 px-3 py-1 text-xs font-bold text-slate-500">
                {summary.source_count || 0} nguồn đánh giá
              </span>
            </div>
            <h1 className="mt-4 text-3xl font-black tracking-tight text-slate-950">AI Trust & Governance</h1>
            <p className="mt-2 max-w-3xl text-sm font-semibold leading-6 text-slate-500">
              Theo dõi thiên lệch nguồn, độ phủ tri thức, rủi ro dữ liệu, leakage và feedback loop trước khi dùng AI làm khuyến nghị.
            </p>
            {error && <div className="mt-4 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-sm font-bold text-red-700">{error}</div>}
          </div>
          <div className="border-t border-slate-100 bg-slate-50 p-5 xl:border-l xl:border-t-0">
            <div className="rounded-xl bg-white p-4">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-black uppercase tracking-widest text-slate-400">Trust Score</p>
                  <p className="mt-2 text-5xl font-black tracking-tight text-slate-950">{summary.trust_score ?? "—"}</p>
                </div>
                <div className={cx("flex h-14 w-14 items-center justify-center rounded-xl border", toneClass(scoreTone))}>
                  <Gauge className="h-7 w-7" />
                </div>
              </div>
              <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
                <div className={cx("h-full rounded-full", scoreTone === "red" ? "bg-red-500" : scoreTone === "amber" ? "bg-amber-500" : "bg-emerald-500")} style={{ width: `${summary.trust_score || 0}%` }} />
              </div>
            </div>
            <button
              type="button"
              onClick={() => void loadTrust()}
              className="mt-3 inline-flex h-10 w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-bold text-white"
            >
              <RefreshCw className="h-4 w-4" />
              Làm mới
            </button>
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Metric icon={Scale} label="Nguồn đã tin cậy" value={percent(summary.reviewed_source_share)} note="official + semi-official" tone="emerald" />
        <Metric icon={Globe2} label="Nguồn internet" value={percent(summary.internet_source_share)} note="rủi ro bias thương mại" tone={summary.internet_source_share > 0.75 ? "red" : "amber"} />
        <Metric icon={Layers3} label="Nguồn được index" value={summary.indexed_source_count ?? 0} note={`${summary.held_source_count || 0} giữ review · ${summary.blocked_source_count || 0} chặn`} tone={(summary.held_source_count || summary.blocked_source_count) ? "amber" : "blue"} />
        <Metric icon={ShieldAlert} label="Rủi ro mở" value={activeRisks.length} note={`${summary.high_risk_warning_total || 0} cảnh báo rủi ro cao`} tone={activeRisks.length ? "red" : "emerald"} />
      </section>

      <Panel
        title="Khung lý thuyết Tư duy TTNT"
        subtitle="Mỗi khái niệm được nối với rủi ro thật trong dữ liệu nông nghiệp và cơ chế kiểm soát đang có trong hệ thống."
      >
        <div className="grid gap-3 xl:grid-cols-2">
          {theoryCases.map((item) => (
            <TheoryCard key={item.key} item={item} />
          ))}
        </div>
      </Panel>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <Panel title="Risk Register" subtitle="Các rủi ro cần kiểm soát trước khi dùng dữ liệu cho tư vấn hoặc huấn luyện.">
          <div className="space-y-3">
            {risks.map((risk) => (
              <article key={risk.key} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex min-w-0 gap-3">
                    <div className={cx("mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg border", toneClass(risk.status === "needs_action" ? "red" : "emerald"))}>
                      {risk.status === "needs_action" ? <CircleAlert className="h-5 w-5" /> : <CheckCircle2 className="h-5 w-5" />}
                    </div>
                    <div className="min-w-0">
                      <h3 className="text-sm font-black text-slate-950">{risk.title}</h3>
                      <p className="mt-1 text-xs font-semibold leading-5 text-slate-500">{risk.evidence}</p>
                    </div>
                  </div>
                  <RiskBadge status={risk.status} />
                </div>
                <p className="mt-3 rounded-lg bg-white px-3 py-2 text-xs font-bold leading-5 text-slate-600">{risk.mitigation}</p>
              </article>
            ))}
          </div>
        </Panel>

        <Panel title="Governance Controls" subtitle="Các chốt kiểm soát đang áp dụng cho hệ thống.">
          <div className="space-y-3">
            {(payload?.controls || []).map((control) => {
              const tone = statusTone(control.status);
              return (
                <div key={control.name} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                  <div className="flex items-start gap-3">
                    <div className={cx("flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg border", toneClass(tone))}>
                      {tone === "emerald" ? <BadgeCheck className="h-5 w-5" /> : <AlertTriangle className="h-5 w-5" />}
                    </div>
                    <div>
                      <p className="text-sm font-black text-slate-900">{control.name}</p>
                      <p className="mt-1 text-xs font-semibold leading-5 text-slate-500">{control.detail}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <Panel title="Độ phủ chủ đề" subtitle="Phát hiện under-representation theo nhóm kiến thức nông nghiệp.">
          <div className="grid gap-3 md:grid-cols-2">
            {(payload?.coverage || []).map((item) => (
              <ProgressLine
                key={item.key}
                label={item.label}
                value={item.count > 0 ? Math.min(1, item.count / 20) : 0}
                note={`${item.count} nguồn, ${item.official_count} chính thống`}
                tone={item.count ? "emerald" : "red"}
              />
            ))}
          </div>
        </Panel>

        <Panel title="Vùng canh tác & domain" subtitle="Theo dõi bias vùng miền và tập trung nguồn.">
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-3">
              {(payload?.region_coverage || []).map((item) => (
                <div key={item.label} className="flex items-center justify-between gap-3 rounded-xl border border-slate-100 bg-slate-50 px-3 py-2">
                  <div>
                    <p className="text-sm font-black text-slate-900">{item.label}</p>
                    <p className="text-xs font-semibold text-slate-500">{item.official_count} nguồn chính thống</p>
                  </div>
                  <span className={cx("rounded-lg border px-2 py-1 text-xs font-black", toneClass(item.count ? "emerald" : "red"))}>{item.count}</span>
                </div>
              ))}
            </div>
            <div className="space-y-2">
              {(payload?.domain_concentration || []).slice(0, 6).map((item) => (
                <div key={item.domain} className="rounded-xl border border-slate-100 bg-slate-50 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="truncate text-xs font-black text-slate-800">{item.domain}</p>
                    <p className="text-xs font-black text-slate-500">{percent(item.share)}</p>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white">
                    <div className="h-full rounded-full bg-slate-500" style={{ width: `${Math.round(item.share * 100)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </section>

      <Panel title="System Card" subtitle="Mục đích sử dụng, giới hạn và cách giải thích cho người dùng.">
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
            <div className="flex items-center gap-2 text-sm font-black text-slate-900">
              <FileCheck2 className="h-4 w-4 text-emerald-600" />
              {payload?.model_card?.system_name || "Nông Trí AI"}
            </div>
            <p className="mt-3 text-sm font-semibold leading-6 text-slate-600">{payload?.model_card?.intended_use}</p>
            <p className="mt-3 text-sm font-semibold leading-6 text-slate-500">{payload?.model_card?.not_intended_use}</p>
          </div>
          <div className="rounded-xl border border-slate-100 bg-slate-50 p-4">
            <div className="flex items-center gap-2 text-sm font-black text-slate-900">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              Giải thích phản thực tế
            </div>
            <p className="mt-3 text-sm font-semibold leading-6 text-slate-600">{payload?.model_card?.user_explanation_pattern}</p>
            <div className="mt-3 rounded-lg bg-white px-3 py-2 text-xs font-bold leading-5 text-slate-500">
              Ví dụ: nếu người dùng cung cấp vùng trồng, tuổi cây và triệu chứng rõ hơn, hệ thống có thể tăng độ tin cậy hoặc chuyển từ khuyến nghị tổng quát sang khuyến nghị theo điều kiện cụ thể.
            </div>
          </div>
        </div>
      </Panel>
    </div>
  );
}
