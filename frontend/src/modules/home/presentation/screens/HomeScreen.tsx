import { BigActionMenu } from "@/shared/components/features/BigActionMenu";

export function HomeScreen() {
  return (
    <div className="flex flex-col min-h-full pb-8">
      {/* Lời chào mừng */}
      <div className="mt-6 mb-2 px-4 text-center">
        <h1 className="text-2xl font-bold text-slate-800 mb-1">Chào bà con 👋</h1>
        <p className="text-slate-500 text-sm">Hôm nay bà con cần hỗ trợ gì ạ?</p>
      </div>

      {/* Các nút bấm thao tác chính siêu to */}
      <BigActionMenu />
    </div>
  );
}
