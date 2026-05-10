import { create } from "zustand";
import { Message } from "../domain/Message";

interface ChatState {
  messages: Message[];
  addMessage: (message: Message) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [
    {
      id: "1",
      role: "ai",
      content: "Chào bà con! Hôm nay ruộng đồng nhà mình có gặp vấn đề gì không ạ?"
    },
    {
      id: "2",
      role: "user",
      content: "Lúa nhà tôi đang bị đốm xám hình mắt én trên lá, không biết là bệnh gì?"
    },
    {
      id: "3",
      role: "ai",
      content: "Dạ, theo triệu chứng bà con mô tả, đây là biểu hiện đặc trưng của bệnh đạo ôn trên lúa. Bà con cần ngừng bón phân đạm ngay, luôn giữ mực nước trong ruộng và có thể dùng thuốc đặc trị nhé.",
      citation: "Cẩm nang Lúa Gạo - Cục Trồng trọt (Trang 45, Mục Phòng trừ bệnh đạo ôn)"
    }
  ],
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
}));
