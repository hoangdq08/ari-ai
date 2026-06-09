import { ChatSource } from "../models/Message";

export interface ChatSendResult {
  reply: string;
  sources: ChatSource[];
  sessionId?: string;
}

export interface ChatApiRepository {
  sendMessage(message: string, sessionId?: string): Promise<ChatSendResult>;
  transcribeAudio(file: Blob): Promise<string>;
}
