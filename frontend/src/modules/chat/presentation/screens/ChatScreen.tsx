"use client";

import { ChatBubble } from "../components/ChatBubble";
import { ChatInput } from "../components/ChatInput";
import { useChatStore } from "../../application/useChatStore";

export function ChatScreen() {
  const messages = useChatStore((state) => state.messages);

  return (
    <div className="flex flex-col min-h-full pb-24 pt-2 relative">
      {/* Intro Header */}
      <div className="px-4 py-4 mb-2 flex flex-col items-center justify-center text-center">
        <div className="w-14 h-14 bg-emerald-100 rounded-full flex items-center justify-center mb-3 border border-emerald-200 shadow-sm">
          <span className="text-3xl">👨‍🌾</span>
        </div>
        <h1 className="font-bold text-lg text-slate-800">Chuyên Gia Nông Nghiệp AI</h1>
        <p className="text-sm text-slate-500 mt-1 max-w-[280px]">Sẵn sàng giải đáp thắc mắc và chẩn đoán sâu bệnh cho bà con dựa trên cẩm nang khuyến nông.</p>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 space-y-1 pb-48 w-full max-w-md mx-auto">
        {messages.map((msg) => (
          <ChatBubble 
            key={msg.id}
            role={msg.role} 
            content={msg.content} 
            citation={msg.citation}
          />
        ))}
      </div>

      {/* Chat Input Bar */}
      <ChatInput />
    </div>
  );
}
