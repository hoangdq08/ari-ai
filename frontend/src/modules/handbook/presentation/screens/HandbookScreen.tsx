"use client";

import { Search, Loader2 } from "lucide-react";
import { KnowledgeCard } from "../components/KnowledgeCard";
import { useHandbookStore } from "../stores/useHandbookStore";
import { useArticles } from "../hooks/useArticles";
import { CATEGORIES } from "../../domain/models/Article";

export function HandbookScreen() {
  const { searchQuery, activeCategory, setSearchQuery, setActiveCategory } = useHandbookStore();
  const { data: articles, isLoading } = useArticles();

  return (
    <div className="flex flex-col min-h-full pb-24">
      {/* Sticky Wrapper: Header + Search + Categories */}
      <div className="sticky top-16 z-30 bg-white/95 backdrop-blur-md pb-2 pt-6 px-4 shadow-[0_4px_20px_-10px_rgba(0,0,0,0.05)] border-b border-slate-100/80 transition-all">
        <h1 className="font-extrabold text-[32px] text-slate-900 mb-4 tracking-tight">Cẩm nang</h1>

        <div className="relative mb-4">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Tìm kiếm sâu bệnh, cây trồng..."
            className="w-full bg-slate-50/50 border-2 border-slate-200/80 text-[17px] text-slate-900 rounded-2xl pl-12 pr-4 py-4 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all shadow-sm placeholder:text-slate-500 font-medium"
          />
          <Search className="absolute left-4 top-4 w-6 h-6 text-slate-500" strokeWidth={2.5} />
        </div>

        {/* Categories / Tags */}
        <div className="flex overflow-x-auto gap-2.5 pb-2 -mx-4 px-4 [&::-webkit-scrollbar]:hidden">
          {CATEGORIES.map((tag) => {
            const isActive = tag === activeCategory;
            return (
              <button
                key={tag}
                onClick={() => setActiveCategory(tag)}
                className={`flex-shrink-0 px-5 py-2.5 rounded-full text-[16px] font-bold transition-colors shadow-sm ${isActive
                  ? "bg-emerald-500 text-white border border-emerald-500 shadow-[0_4px_10px_rgba(16,185,129,0.2)]"
                  : "bg-white border-2 border-slate-200 text-slate-700 hover:bg-slate-50 active:bg-slate-100"
                  }`}
              >
                {tag}
              </button>
            );
          })}
        </div>
      </div>

      {/* Article List */}
      <div className="px-4 space-y-4 pt-5">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-10 text-slate-400">
            <Loader2 className="w-8 h-8 animate-spin mb-4 text-emerald-500" />
            <p>Đang tải cẩm nang...</p>
          </div>
        ) : articles?.length === 0 ? (
          <div className="text-center py-10 text-slate-500">
            Không tìm thấy bài viết nào phù hợp.
          </div>
        ) : (
          articles?.map((article) => (
            <KnowledgeCard
              key={article.id}
              title={article.title}
              description={article.description}
              category={article.category}
            />
          ))
        )}
      </div>
    </div>
  );
}
