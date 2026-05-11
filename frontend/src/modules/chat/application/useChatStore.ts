import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { Message } from "../domain/entities/Message";
import { IChatApi } from "../domain/interfaces/IChatApi";
import { chatStorageAdapter } from "../infrastructure/chat.storage";

interface ChatState {
  messages: Message[];
  isTyping: boolean;
  addMessage: (message: Message) => void;
  setTyping: (status: boolean) => void;
  submitMessage: (text: string, api: IChatApi) => Promise<void>;
  submitAudio: (file: Blob, api: IChatApi) => Promise<void>;
  clearChat: () => void;
}

const defaultMessages: Message[] = [
  {
    id: "1",
    role: "ai",
    content: "Chào bà con! Hôm nay ruộng đồng nhà mình có gặp vấn đề gì không ạ?"
  }
];

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: defaultMessages,
      isTyping: false,
  
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  
  setTyping: (status) => set({ isTyping: status }),

  clearChat: () => set({ messages: defaultMessages, isTyping: false }),
  
  submitMessage: async (text: string, api: IChatApi) => {
    const userMessageId = Date.now().toString();
    // Thêm tin nhắn user vào giao diện
    get().addMessage({
      id: userMessageId,
      role: "user",
      content: text,
    });
    
    get().setTyping(true);
    
    try {
      // Gọi API qua Interface được tiêm (Dependency Injection)
      const response = await api.sendMessage({ message: text });
      
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

  submitAudio: async (file: Blob, api: IChatApi) => {
    get().setTyping(true);
    try {
      // Gọi API STT Backend
      const transcribeRes = await api.transcribeAudio(file);
      const transcribedText = transcribeRes.text;
      
      get().setTyping(false);
      
      // Gửi text vừa nhận diện được như một tin nhắn bình thường
      await get().submitMessage(transcribedText, api);
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
    }),
    {
      name: 'nong-tri-chat-storage',
      storage: createJSONStorage(() => chatStorageAdapter),
      partialize: (state) => ({ messages: state.messages }),
    }
  )
);
