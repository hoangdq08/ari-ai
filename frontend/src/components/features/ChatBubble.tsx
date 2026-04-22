import { User, Bot, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";

interface ChatBubbleProps {
  role: "user" | "ai";
  content: string;
  citation?: string;
}

export function ChatBubble({ role, content, citation }: ChatBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={cn("flex w-full mt-4 space-x-3 px-4", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center border border-emerald-200">
          <Bot className="w-5 h-5 text-emerald-600" />
        </div>
      )}
      
      <div className={cn("flex flex-col gap-1 max-w-[82%]", isUser ? "items-end" : "items-start")}>
        <div 
          className={cn(
            "p-4 rounded-[20px] text-[16px] leading-relaxed font-medium", 
            isUser 
              ? "bg-gradient-to-br from-emerald-500 to-teal-500 text-white rounded-br-sm shadow-[0_4px_15px_rgba(16,185,129,0.2)]" 
              : "bg-white border-2 border-slate-200 text-slate-900 rounded-bl-sm shadow-sm"
          )}
        >
          {content}
        </div>
        
        {/* Hộp trích dẫn hiển thị minh bạch nguồn gốc (Reliability) */}
        {!isUser && citation && (
          <div className="mt-1.5 flex items-start gap-2 bg-amber-50/80 border-2 border-amber-200 rounded-xl p-3 text-[13px] text-amber-900 shadow-sm max-w-full">
            <BookOpen className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-600" strokeWidth={2.5} />
            <span className="font-semibold leading-snug">
              Trích xuất: <span className="font-bold text-amber-950">{citation}</span>
            </span>
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center border border-slate-300">
          <User className="w-5 h-5 text-slate-600" />
        </div>
      )}
    </div>
  );
}
