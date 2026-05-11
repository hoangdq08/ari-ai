import { apiClient } from '@/core/http/apiClient';

export interface ChatMessageRequest {
  message: string;
  session_id?: string;
}

export interface ChatMessageResponse {
  reply: string;
  sources: string[];
}

export interface TranscribeResponse {
  text: string;
}

export const chatApi = {
  sendMessage: async (data: ChatMessageRequest): Promise<ChatMessageResponse> => {
    const response = await apiClient.post<ChatMessageResponse>('/chat/message', data);
    return response.data;
  },

  transcribeAudio: async (file: File | Blob): Promise<TranscribeResponse> => {
    const formData = new FormData();
    // Đặt tên file là audio.webm để backend dễ xử lý
    formData.append('file', file, 'audio.webm');
    
    const response = await apiClient.post<TranscribeResponse>('/chat/transcribe', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }
};
