"use client";

import { createStore, useStore } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { Message } from "../../domain/models/Message";
import { ChatStorageRepository } from "../../domain/repositories/ChatStorageRepository";
import { createContext, useContext, useRef, ReactNode } from "react";
import { useDI } from "@/shared/hooks/useDI";

export interface ChatState {
  messages: Message[];
  isTyping: boolean;
  addMessage: (message: Message) => void;
  setTyping: (status: boolean) => void;
  clearChat: () => void;
}

const defaultMessages: Message[] = [
  {
    id: "1",
    role: "ai",
    content: "Chào bà con! Hôm nay ruộng đồng nhà mình có gặp vấn đề gì không ạ?"
  }
];

export const createChatStore = (storageRepo: ChatStorageRepository) => createStore<ChatState>()(
  persist(
    (set) => ({
      messages: defaultMessages,
      isTyping: false,
      addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
      setTyping: (status) => set({ isTyping: status }),
      clearChat: () => set({ messages: defaultMessages, isTyping: false }),
    }),
    {
      name: 'nong-tri-chat-storage',
      storage: createJSONStorage(() => storageRepo),
      partialize: (state) => ({ messages: state.messages }),
    }
  )
);

export type ChatStoreType = ReturnType<typeof createChatStore>;
export const ChatStoreContext = createContext<ChatStoreType | null>(null);

export const ChatStoreProvider = ({ children }: { children: ReactNode }) => {
  const { chatStorageRepository } = useDI();
  const storeRef = useRef<ChatStoreType>(null);
  
  if (!storeRef.current) {
    storeRef.current = createChatStore(chatStorageRepository);
  }

  return (
    <ChatStoreContext.Provider value={storeRef.current}>
      {children}
    </ChatStoreContext.Provider>
  );
};

export const useChatStore = <T,>(selector: (state: ChatState) => T): T => {
  const store = useContext(ChatStoreContext);
  if (!store) {
    throw new Error("useChatStore must be used within a ChatStoreProvider");
  }
  return useStore(store, selector);
};
