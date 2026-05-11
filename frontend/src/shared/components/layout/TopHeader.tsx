"use client";

import React from 'react';
import { Leaf, ChevronLeft, Eraser } from 'lucide-react';
import { usePathname, useRouter } from 'next/navigation';

export function TopHeader() {
  const pathname = usePathname();
  const router = useRouter();
  
  const isChat = pathname === '/chat';

  const handleClearChat = () => {
    if (window.confirm("Bạn có chắc chắn muốn xóa toàn bộ lịch sử trò chuyện không?")) {
      // Dynamic import to avoid importing zustand store in layout if not needed
      import('@/modules/chat/application/useChatStore').then((module) => {
        module.useChatStore.getState().clearChat();
      });
    }
  };

  return (
    <header className="sticky top-0 z-50 w-full h-[64px] bg-white/60 backdrop-blur-xl border-b border-slate-100/50 shadow-[0_4px_30px_rgba(0,0,0,0.02)] transition-all">
      <div className="flex h-full items-center px-4 gap-3 max-w-md mx-auto">
        {isChat ? (
          <button 
            onClick={() => router.back()}
            className="p-2 -ml-2 text-slate-600 hover:text-emerald-600 hover:bg-emerald-50 rounded-full transition-colors active:scale-95"
          >
            <ChevronLeft className="w-7 h-7" strokeWidth={2.5} />
          </button>
        ) : (
          <div className="bg-gradient-to-br from-emerald-400 to-teal-600 p-2 rounded-xl shadow-sm ml-1">
            <Leaf className="h-5 w-5 text-white" />
          </div>
        )}
        <div className="flex-1 flex items-center gap-2">
          <span className="font-bold text-[22px] bg-clip-text text-transparent bg-gradient-to-r from-emerald-800 to-teal-700 tracking-tight">
            {isChat ? 'Trợ lý Nông nghiệp' : 'Nông Trí AI'}
          </span>
        </div>
        
        {isChat && (
          <button 
            onClick={handleClearChat}
            className="p-2 -mr-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-full transition-colors"
            title="Xóa lịch sử trò chuyện"
          >
            <Eraser className="w-5 h-5" />
          </button>
        )}
      </div>
    </header>
  );
}
