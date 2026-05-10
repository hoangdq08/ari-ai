"use client";

import { Send, Image as ImageIcon, Mic } from "lucide-react";
import { useRef, useState } from "react";
import { useChatStore } from "../../application/useChatStore";
import { useDiagnoseImage } from "@/modules/diagnostics/application/useDiagnoseImage";

export function ChatInput() {
  const [text, setText] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const addMessage = useChatStore((state) => state.addMessage);
  
  const diagnoseMutation = useDiagnoseImage();

  const handleSendText = () => {
    if (!text.trim()) return;
    addMessage({
      id: Date.now().toString(),
      role: "user",
      content: text,
    });
    setText("");
  };

  const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const imageUrl = URL.createObjectURL(file);

    // 1. Thêm tin nhắn user chứa ảnh
    addMessage({
      id: Date.now().toString(),
      role: "user",
      content: "Tôi vừa gửi một hình ảnh, nhờ chuyên gia xem giúp.",
      imageUrl: imageUrl,
    });

    // 2. Gọi mock API chẩn đoán
    diagnoseMutation.mutate(file, {
      onSuccess: (result) => {
        addMessage({
          id: Date.now().toString(),
          role: "ai",
          content: result.advice,
          citation: result.citation,
        });
      },
      onError: () => {
        addMessage({
          id: Date.now().toString(),
          role: "ai",
          content: "Xin lỗi bà con, hệ thống đang gặp lỗi. Vui lòng thử lại sau.",
        });
      }
    });

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-full max-w-[448px] px-4 z-40 pointer-events-none safe-area-pb">
      <div className="mx-auto bg-white/95 backdrop-blur-xl border-2 border-emerald-100 p-2 rounded-[32px] shadow-[0_15px_40px_-10px_rgba(16,185,129,0.3)] pointer-events-auto transition-all flex items-center gap-1.5">
        <input 
          type="file" 
          accept="image/*" 
          className="hidden" 
          ref={fileInputRef}
          onChange={handleImageUpload}
        />
        <button 
          onClick={() => fileInputRef.current?.click()}
          className="p-2.5 text-slate-500 hover:text-emerald-600 transition-colors bg-slate-100/80 hover:bg-emerald-50 rounded-full active:scale-95 flex-shrink-0"
        >
          <ImageIcon className="w-[22px] h-[22px]" />
        </button>
        <button className="p-2.5 text-slate-500 hover:text-emerald-600 transition-colors bg-slate-100/80 hover:bg-emerald-50 rounded-full active:scale-95 flex-shrink-0">
          <Mic className="w-[22px] h-[22px]" />
        </button>
        
        <div className="flex-1 relative flex items-center">
          <input 
            type="text" 
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSendText()}
            placeholder="Hỏi chuyên gia AI..." 
            className="w-full bg-slate-100/80 border-none text-[16px] text-slate-900 rounded-full pl-5 pr-12 py-3.5 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all placeholder:text-slate-500 font-medium"
          />
          <button 
            onClick={handleSendText}
            className="absolute right-1.5 p-2 bg-emerald-500 text-white rounded-full hover:bg-emerald-600 transition-colors shadow-md active:scale-95"
          >
            <Send className="w-[20px] h-[20px] ml-0.5" strokeWidth={2.5} />
          </button>
        </div>
      </div>
    </div>
  );
}
