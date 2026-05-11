"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Eraser } from "lucide-react";
import { ChatBubble } from "../components/ChatBubble";
import { ChatInput } from "../components/ChatInput";
import { useChatStore } from "../../application/useChatStore";

export function ChatScreen() {
  const messages = useChatStore((state) => state.messages);
  const isTyping = useChatStore((state) => state.isTyping);
  const clearChat = useChatStore((state) => state.clearChat);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [headerActionsNode, setHeaderActionsNode] = useState<HTMLElement | null>(null);

  useEffect(() => {
    setHeaderActionsNode(document.getElementById('header-actions'));
  }, []);

  const handleClearChat = () => {
    if (window.confirm("Bạn có chắc chắn muốn xóa toàn bộ lịch sử trò chuyện không?")) {
      clearChat();
    }
  };

  // Auto scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

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
            imageUrl={msg.imageUrl}
          />
        ))}

        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex w-full items-start gap-2.5 px-4 mb-4 mt-2">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-emerald-100 flex items-center justify-center border border-emerald-200">
              <span className="text-emerald-700 text-xs font-bold">AI</span>
            </div>
            <div className="flex flex-col gap-1 max-w-[85%]">
              <div className="px-4 py-3 bg-white border-2 border-slate-200 text-slate-900 rounded-2xl rounded-tl-sm shadow-sm inline-flex">
                <div className="flex space-x-1.5 items-center h-4">
                  <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Chat Input Bar */}
      <ChatInput />

      {/* Clear Chat Button (Portal into Header) */}
      {headerActionsNode && createPortal(
        <button 
          onClick={handleClearChat}
          className="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-full transition-colors active:scale-95"
          title="Xóa lịch sử trò chuyện"
        >
          <Eraser className="w-[22px] h-[22px]" strokeWidth={2.5} />
        </button>,
        headerActionsNode
      )}
    </div>
  );
}
