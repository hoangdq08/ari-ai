import { ChatBubble } from "@/components/features/ChatBubble";
import { ChatInput } from "@/components/features/ChatInput";

export default function ChatPage() {
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
        <ChatBubble 
          role="ai" 
          content="Chào bà con! Hôm nay ruộng đồng nhà mình có gặp vấn đề gì không ạ?" 
        />
        <ChatBubble 
          role="user" 
          content="Lúa nhà tôi đang bị đốm xám hình mắt én trên lá, không biết là bệnh gì?" 
        />
        <ChatBubble 
          role="ai" 
          content="Dạ, theo triệu chứng bà con mô tả, đây là biểu hiện đặc trưng của bệnh đạo ôn trên lúa. Bà con cần ngừng bón phân đạm ngay, luôn giữ mực nước trong ruộng và có thể dùng thuốc đặc trị nhé."
          citation="Cẩm nang Lúa Gạo - Cục Trồng trọt (Trang 45, Mục Phòng trừ bệnh đạo ôn)"
        />
      </div>

      {/* Chat Input Bar */}
      <ChatInput />
    </div>
  );
}
