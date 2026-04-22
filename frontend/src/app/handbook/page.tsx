import { Search } from "lucide-react";
import { KnowledgeCard } from "@/components/features/KnowledgeCard";

export default function HandbookPage() {
  const articles = [
    {
      title: "Phòng trừ bệnh đạo ôn hại lúa vụ Đông Xuân",
      description: "Hướng dẫn nhận biết sớm vết bệnh hình mắt én trên lá và cách sử dụng thuốc đặc trị an toàn.",
      category: "Lúa Gạo",
    },
    {
      title: "Kỹ thuật ủ phân hữu cơ vi sinh từ phụ phẩm",
      description: "Tận dụng rơm rạ, vỏ sầu riêng để ủ phân bón giúp tiết kiệm chi phí và cải tạo đất.",
      category: "Kỹ thuật",
    },
    {
      title: "Dấu hiệu nhận biết rầy nâu và cách phòng tránh",
      description: "Các chu kỳ sinh trưởng của rầy nâu và phương pháp '3 giảm 3 tăng' hiệu quả cho bà con.",
      category: "Côn trùng",
    },
    {
      title: "Lịch gieo sạ lúa vùng Đồng bằng sông Cửu Long",
      description: "Cập nhật lịch thời vụ mới nhất từ Bộ NN&PTNT để né rầy và ngập mặn.",
      category: "Thời vụ",
    }
  ];

  return (
    <div className="flex flex-col min-h-full pb-24">
      {/* Sticky Wrapper: Header + Search + Categories */}
      <div className="sticky top-16 z-30 bg-white/95 backdrop-blur-md pb-2 pt-6 px-4 shadow-[0_4px_20px_-10px_rgba(0,0,0,0.05)] border-b border-slate-100/80 transition-all">
        <h1 className="font-extrabold text-[32px] text-slate-900 mb-4 tracking-tight">Cẩm nang</h1>

        <div className="relative mb-4">
          <input
            type="text"
            placeholder="Tìm kiếm sâu bệnh, cây trồng..."
            className="w-full bg-slate-50/50 border-2 border-slate-200/80 text-[17px] text-slate-900 rounded-2xl pl-12 pr-4 py-4 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all shadow-sm placeholder:text-slate-500 font-medium"
          />
          <Search className="absolute left-4 top-4 w-6 h-6 text-slate-500" strokeWidth={2.5} />
        </div>

        {/* Categories / Tags */}
        <div className="flex overflow-x-auto gap-2.5 pb-2 -mx-4 px-4 [&::-webkit-scrollbar]:hidden">
          {["Tất cả", "Lúa Gạo", "Cây ăn quả", "Sâu bệnh", "Kỹ thuật"].map((tag, idx) => (
            <button
              key={tag}
              className={`flex-shrink-0 px-5 py-2.5 rounded-full text-[16px] font-bold transition-colors shadow-sm ${idx === 0
                ? "bg-emerald-500 text-white border border-emerald-500 shadow-[0_4px_10px_rgba(16,185,129,0.2)]"
                : "bg-white border-2 border-slate-200 text-slate-700 hover:bg-slate-50 active:bg-slate-100"
                }`}
            >
              {tag}
            </button>
          ))}
        </div>
      </div>

      {/* Article List */}
      <div className="px-4 space-y-4 pt-5">
        {articles.map((article, idx) => (
          <KnowledgeCard
            key={idx}
            title={article.title}
            description={article.description}
            category={article.category}
          />
        ))}
      </div>
    </div>
  );
}
