export interface ChatApiRepository {
  sendMessage(message: string, sessionId?: string): Promise<{ reply: string; sources: string[] }>;
  transcribeAudio(file: Blob): Promise<string>;
}
