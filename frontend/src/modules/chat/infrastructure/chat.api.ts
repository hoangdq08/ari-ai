import { apiClient } from '@/core/http/apiClient';
import { IChatApi, ChatResponse, TranscribeResponse } from '../domain/interfaces/IChatApi';

export interface ChatMessageRequest {
  message: string;
  session_id?: string;
}

class ChatApiImpl implements IChatApi {
  sendMessage = async (data: { message: string; session_id?: string }): Promise<ChatResponse> => {
    const response = await apiClient.post<ChatResponse>('/chat/message', data);
    return response.data;
  };

  transcribeAudio = async (file: File | Blob): Promise<TranscribeResponse> => {
    const formData = new FormData();
    // Đặt tên file là audio.webm để backend dễ xử lý
    formData.append('file', file, 'audio.webm');
    
    const response = await apiClient.post<TranscribeResponse>('/chat/transcribe', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  };
}

export const chatApi = new ChatApiImpl();
