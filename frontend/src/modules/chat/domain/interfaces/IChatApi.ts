export interface ChatResponse {
  reply: string;
  sources: string[];
}

export interface TranscribeResponse {
  text: string;
}

export interface IChatApi {
  sendMessage(payload: { message: string; session_id?: string }): Promise<ChatResponse>;
  transcribeAudio(file: Blob): Promise<TranscribeResponse>;
}
