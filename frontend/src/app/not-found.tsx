import Link from 'next/link';
import { AlertCircle } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6 text-center animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="w-24 h-24 mb-6 rounded-full bg-emerald-100 flex items-center justify-center">
        <AlertCircle className="w-12 h-12 text-emerald-500" />
      </div>
      <h1 className="text-3xl font-bold text-slate-800 mb-2">404 - Lạc đường</h1>
      <p className="text-slate-500 mb-8 max-w-[280px]">
        Xin lỗi, tính năng hoặc trang bạn đang tìm kiếm không tồn tại trên hệ thống Nông Trí AI.
      </p>
      <Link 
        href="/" 
        className="px-6 py-3 bg-emerald-600 text-white font-medium rounded-xl shadow-lg shadow-emerald-200 hover:bg-emerald-700 active:scale-95 transition-all"
      >
        Trở về Trang chủ
      </Link>
    </div>
  );
}
