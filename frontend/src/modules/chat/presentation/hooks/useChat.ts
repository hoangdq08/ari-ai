"use client";

import { useChatStore } from "../stores/useChatStore";
import { useDI } from "@/shared/hooks/useDI";

export const useChat = () => {
  const { chatApiRepository } = useDI();
  const { addMessage, setTyping, clearChat, messages, isTyping } = useChatStore(state => state);

  const submitMessage = async (text: string) => {
    const userMessageId = Date.now().toString();
    addMessage({
      id: userMessageId,
      role: "user",
      content: text,
    });
    
    setTyping(true);
    
    try {
      const response = await chatApiRepository.sendMessage(text);

      const primarySource = response.sources[0];
      addMessage({
        id: (Date.now() + 1).toString(),
        role: "ai",
        content: response.reply,
        citation: primarySource
          ? primarySource.url
            ? `${primarySource.title} (${primarySource.url})`
            : primarySource.title
          : undefined,
        sources: response.sources,
      });
    } catch (error) {
      console.error("Lỗi khi gửi tin nhắn:", error);
      addMessage({
        id: (Date.now() + 1).toString(),
        role: "ai",
        content: "Xin lỗi bà con, hệ thống đang gặp sự cố kết nối. Vui lòng thử lại sau.",
      });
    } finally {
      setTyping(false);
    }
  };

  const submitAudio = async (file: Blob) => {
    setTyping(true);
    try {
      const transcribedText = await chatApiRepository.transcribeAudio(file);
      setTyping(false);
      await submitMessage(transcribedText);
    } catch (error) {
      console.error("Lỗi khi nhận diện giọng nói:", error);
      setTyping(false);
      addMessage({
        id: (Date.now() + 1).toString(),
        role: "ai",
        content: "Xin lỗi bà con, tôi không thể phân tích đoạn ghi âm vừa rồi. Vui lòng thử lại.",
      });
    }
  };

  return {
    messages,
    isTyping,
    submitMessage,
    submitAudio,
    clearChat,
    addMessage,
    setTyping,
  };
};
