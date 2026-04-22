import { Send, Image as ImageIcon, Mic } from "lucide-react";

export function ChatInput() {
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-full max-w-[448px] px-4 z-40 pointer-events-none safe-area-pb">
      <div className="mx-auto bg-white/95 backdrop-blur-xl border-2 border-emerald-100 p-2 rounded-[32px] shadow-[0_15px_40px_-10px_rgba(16,185,129,0.3)] pointer-events-auto transition-all flex items-center gap-1.5">
        <button className="p-2.5 text-slate-500 hover:text-emerald-600 transition-colors bg-slate-100/80 hover:bg-emerald-50 rounded-full active:scale-95 flex-shrink-0">
          <ImageIcon className="w-[22px] h-[22px]" />
        </button>
        <button className="p-2.5 text-slate-500 hover:text-emerald-600 transition-colors bg-slate-100/80 hover:bg-emerald-50 rounded-full active:scale-95 flex-shrink-0">
          <Mic className="w-[22px] h-[22px]" />
        </button>
        
        <div className="flex-1 relative flex items-center">
          <input 
            type="text" 
            placeholder="Hỏi chuyên gia AI..." 
            className="w-full bg-slate-100/80 border-none text-[16px] text-slate-900 rounded-full pl-5 pr-12 py-3.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all placeholder:text-slate-500 font-medium"
          />
          <button className="absolute right-1.5 p-2 bg-emerald-500 text-white rounded-full hover:bg-emerald-600 transition-colors shadow-md active:scale-95">
            <Send className="w-[20px] h-[20px] ml-0.5" strokeWidth={2.5} />
          </button>
        </div>
      </div>
    </div>
  );
}
