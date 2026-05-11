import { create } from "zustand";
import { Message } from "../domain/Message";
import { chatApi } from "../infrastructure/chat.api";

interface ChatState {
  messages: Message[];
  isTyping: boolean;
  addMessage: (message: Message) => void;
  setTyping: (status: boolean) => void;
  submitMessage: (text: string) => Promise<void>;
  submitAudio: (file: Blob) => Promise<void>;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [
    {
      id: "1",
      role: "ai",
      content: "Chào bà con! Hôm nay ruộng đồng nhà mình có gặp vấn đề gì không ạ?"
    }
  ],
  isTyping: false,
  
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  
  setTyping: (status) => set({ isTyping: status }),
  
  submitMessage: async (text: string) => {
    const userMessageId = Date.now().toString();
    // Thêm tin nhắn user vào giao diện
    get().addMessage({
      id: userMessageId,
      role: "user",
      content: text,
    });
    
    get().setTyping(true);
    
    try {
      // Gọi API Backend thực tế
      const response = await chatApi.sendMessage({ message: text });
      
      // Thêm phản hồi của AI vào giao diện
      get().addMessage({
        id: (Date.now() + 1).toString(),
        role: "ai",
        content: response.reply,
        citation: response.sources.length > 0 ? response.sources[0] : undefined
      });
    } catch (error) {
      console.error("Lỗi khi gửi tin nhắn:", error);
      get().addMessage({
        id: (Date.now() + 1).toString(),
        role: "ai",
        content: "Xin lỗi bà con, hệ thống đang gặp sự cố kết nối. Vui lòng thử lại sau.",
      });
    } finally {
      get().setTyping(false);
    }
  },

  submitAudio: async (file: Blob) => {
    get().setTyping(true);
    try {
      // Gọi API STT Backend
      const transcribeRes = await chatApi.transcribeAudio(file);
      const transcribedText = transcribeRes.text;
      
      get().setTyping(false);
      
      // Gửi text vừa nhận diện được như một tin nhắn bình thường
      await get().submitMessage(transcribedText);
    } catch (error) {
      console.error("Lỗi khi nhận diện giọng nói:", error);
      get().setTyping(false);
      get().addMessage({
        id: (Date.now() + 1).toString(),
        role: "ai",
        content: "Xin lỗi bà con, tôi không thể phân tích đoạn ghi âm vừa rồi. Vui lòng thử lại.",
      });
    }
  }
}));
