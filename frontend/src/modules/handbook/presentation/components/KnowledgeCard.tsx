import { ChevronRight, FileText } from "lucide-react";

interface KnowledgeCardProps {
  title: string;
  description: string;
  category: string;
  date?: string;
}

export function KnowledgeCard({
  title,
  description,
  category,
  date = "Mới cập nhật",
}: KnowledgeCardProps) {
  return (
    <div className="w-full bg-white border-2 border-slate-200 rounded-2xl p-4 shadow-sm hover:shadow-md transition-shadow cursor-pointer group active:scale-[0.98]">
      <div className="flex items-center gap-2">
        <span className="inline-flex items-center px-2.5 py-1 rounded-md bg-emerald-50 text-emerald-700 text-[12px] font-extrabold uppercase tracking-widest border border-emerald-200">
          {category}
        </span>
        <span className="text-[13px] text-slate-500 font-bold">{date}</span>
      </div>

      <div className="flex gap-3 items-start mt-3">
        <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600 border border-emerald-100 group-hover:bg-emerald-500 group-hover:text-white transition-colors duration-300">
          <FileText className="w-6 h-6" strokeWidth={2.5} />
        </div>
        <div className="flex-1 min-w-0 pt-0.5">
          <h3 className="text-[18px] font-extrabold text-slate-900 leading-snug group-hover:text-emerald-600 transition-colors line-clamp-2 break-words">
            {title}
          </h3>
          <p className="text-[15px] text-slate-600 mt-2 line-clamp-2 leading-relaxed font-medium break-words">
            {description}
          </p>
        </div>
        <div className="flex items-center justify-center flex-shrink-0 text-slate-300 group-hover:text-emerald-500 transition-colors">
          <ChevronRight className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
}
