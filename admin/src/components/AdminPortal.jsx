import { BarChart3, Database, Home, Moon, Scale, Search, ShieldCheck, Sun, TerminalSquare } from "lucide-react";
import { useEffect, useState } from "react";
import DataDashboard from "./DataDashboard";
import ResearchPage from "./ResearchPage";
import ReportsDashboard from "./ReportsDashboard";
import OpsConsole from "./OpsConsole";
import BrandMark from "./BrandMark";
import TrustDashboard from "./TrustDashboard";

function adminSection() {
  const path = window.location.pathname;
  if (path.startsWith("/admin/crawl") || path.startsWith("/research")) return "crawl";
  if (path.startsWith("/admin/ops")) return "ops";
  if (path.startsWith("/admin/reports")) return "reports";
  if (path.startsWith("/admin/trust")) return "trust";
  return "data";
}

function NavLink({ href, active, icon: Icon, title, subtitle, onNavigate }) {
  return (
    <a
      href={href}
      onClick={(event) => {
        event.preventDefault();
        onNavigate(href);
      }}
      className={`group flex items-center gap-3 rounded-xl border px-3 py-2.5 transition ${active ? "border-emerald-200 bg-emerald-50 text-emerald-950 shadow-sm" : "border-transparent text-slate-500 hover:bg-slate-50 hover:text-slate-800"
        }`}
    >
      <div className={`flex h-9 w-9 items-center justify-center rounded-xl ${active ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-500 group-hover:bg-white"}`}>
        <Icon className="h-5 w-5" strokeWidth={2.5} />
      </div>
      <div className="min-w-0">
        <p className="text-sm font-bold leading-5">{title}</p>
        {subtitle && <p className="truncate text-xs font-medium opacity-70">{subtitle}</p>}
      </div>
    </a>
  );
}

function AdminHome({ apiBase }) {
  return <DataDashboard apiBase={apiBase} mode="admin" />;
}

function ThemeButton({ theme, onToggle }) {
  const dark = theme === "dark";
  return (
    <button
      type="button"
      onClick={onToggle}
      className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-emerald-200 hover:text-emerald-700"
      aria-label={dark ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối"}
    >
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      {dark ? "Sáng" : "Tối"}
    </button>
  );
}

export default function AdminPortal({ apiBase, userAppUrl = "/", theme, onToggleTheme }) {
  const [active, setActive] = useState(adminSection);
  const [visited, setVisited] = useState(() => new Set([adminSection()]));

  function navigateAdmin(href) {
    window.history.pushState({}, "", href);
    const next = adminSection();
    setActive(next);
    setVisited((current) => new Set([...current, next]));
  }

  useEffect(() => {
    function handlePopState() {
      const next = adminSection();
      setActive(next);
      setVisited((current) => new Set([...current, next]));
    }
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  return (
    <main className="min-h-screen bg-[#f7faf8] text-slate-950">
      <div className="flex min-h-screen">
        <aside className="fixed inset-y-0 left-0 hidden w-72 border-r border-slate-200 bg-white/96 px-4 py-5 backdrop-blur-xl lg:block">
          <div className="flex items-center gap-3">
            <BrandMark className="h-12 w-12 flex-shrink-0 shadow-sm" />
            <div>
              <p className="text-lg font-bold tracking-tight text-slate-900">Nông Trí Admin</p>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">Vận hành dữ liệu</p>
            </div>
          </div>

          <nav className="mt-8 space-y-1">
            <NavLink href="/admin" active={active === "data"} icon={Database} title="Dữ liệu" subtitle="Độ phủ, chỉ mục" onNavigate={navigateAdmin} />
            <NavLink href="/admin/crawl" active={active === "crawl"} icon={Search} title="Thu thập" subtitle="Tìm kiếm, nạp nguồn" onNavigate={navigateAdmin} />
            <NavLink href="/admin/trust" active={active === "trust"} icon={Scale} title="Tin cậy AI" subtitle="Bias, fairness, risk" onNavigate={navigateAdmin} />
            <NavLink href="/admin/ops" active={active === "ops"} icon={TerminalSquare} title="Nhật ký" subtitle="Log, luồng xử lý" onNavigate={navigateAdmin} />
            <NavLink href="/admin/reports" active={active === "reports"} icon={BarChart3} title="Báo cáo" subtitle="Chất lượng, lịch sử" onNavigate={navigateAdmin} />
          </nav>

          <div className="absolute bottom-4 left-4 right-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="mb-2 flex items-center gap-2 text-sm font-bold text-slate-800">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              Kiểm soát an toàn
            </div>
            <p className="text-xs font-medium leading-5 text-slate-500">Duyệt nguồn trước khi nạp.</p>
          </div>
        </aside>

        <section className="flex min-w-0 flex-1 flex-col lg:pl-72">
          <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur-xl lg:px-8">
            <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-4">
              <div className="flex items-center gap-3 lg:hidden">
                <BrandMark className="h-9 w-9 flex-shrink-0 shadow-sm" />
                <div>
                  <p className="text-base font-bold text-slate-900">Nông Trí Admin</p>
                  <p className="text-xs font-medium text-slate-400">Vận hành dữ liệu</p>
                </div>
              </div>
              <div className="hidden lg:block">
                <h1 className="text-2xl font-bold tracking-tight text-slate-950">
                  {active === "crawl"
                    ? "Thu thập dữ liệu"
                    : active === "trust"
                      ? "Tin cậy AI"
                      : active === "ops"
                        ? "Nhật ký vận hành"
                        : active === "reports"
                          ? "Báo cáo vận hành"
                          : "Tổng quan dữ liệu"}
                </h1>
              </div>
              <div className="flex items-center gap-2">
                <ThemeButton theme={theme} onToggle={onToggleTheme} />
                <a
                  href={userAppUrl}
                  className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-emerald-200 hover:text-emerald-700"
                >
                  <Home className="h-4 w-4" />
                  Ứng dụng
                </a>
              </div>
            </div>
            <nav className="mt-3 grid grid-cols-5 gap-2 lg:hidden">
              <a
                className={`rounded-xl px-3 py-2 text-center text-xs font-semibold ${active === "data" ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-600"}`}
                href="/admin"
                onClick={(event) => {
                  event.preventDefault();
                  navigateAdmin("/admin");
                }}
              >
                Dữ liệu
              </a>
              <a
                className={`rounded-xl px-3 py-2 text-center text-xs font-semibold ${active === "crawl" ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-600"}`}
                href="/admin/crawl"
                onClick={(event) => {
                  event.preventDefault();
                  navigateAdmin("/admin/crawl");
                }}
              >
                Thu thập
              </a>
              <a
                className={`rounded-xl px-3 py-2 text-center text-xs font-semibold ${active === "trust" ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-600"}`}
                href="/admin/trust"
                onClick={(event) => {
                  event.preventDefault();
                  navigateAdmin("/admin/trust");
                }}
              >
                Tin cậy
              </a>
              <a
                className={`rounded-xl px-3 py-2 text-center text-xs font-semibold ${active === "ops" ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-600"}`}
                href="/admin/ops"
                onClick={(event) => {
                  event.preventDefault();
                  navigateAdmin("/admin/ops");
                }}
              >
                Nhật ký
              </a>
              <a
                className={`rounded-xl px-3 py-2 text-center text-xs font-semibold ${active === "reports" ? "bg-emerald-600 text-white" : "bg-slate-100 text-slate-600"}`}
                href="/admin/reports"
                onClick={(event) => {
                  event.preventDefault();
                  navigateAdmin("/admin/reports");
                }}
              >
                Báo cáo
              </a>
            </nav>
          </header>

          <div className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-5 lg:px-8">
            {visited.has("data") && <div className={active === "data" ? "block" : "hidden"}><AdminHome apiBase={apiBase} /></div>}
            {visited.has("crawl") && <div className={active === "crawl" ? "block" : "hidden"}><ResearchPage apiBase={apiBase} admin /></div>}
            {visited.has("trust") && <div className={active === "trust" ? "block" : "hidden"}><TrustDashboard apiBase={apiBase} /></div>}
            {visited.has("ops") && <div className={active === "ops" ? "block" : "hidden"}><OpsConsole apiBase={apiBase} /></div>}
            {visited.has("reports") && <div className={active === "reports" ? "block" : "hidden"}><ReportsDashboard apiBase={apiBase} /></div>}
          </div>
        </section>
      </div>
    </main>
  );
}
