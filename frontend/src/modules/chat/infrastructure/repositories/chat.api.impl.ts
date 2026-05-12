import { HttpClientRepository } from '@/core/domain/repositories/HttpClientRepository';
import { ChatApiRepository } from '../../domain/repositories/ChatApiRepository';
import { ChatMessageRequestDTO } from '../dto/ChatRequestDTO';
import { ChatResponseDTO, TranscribeResponseDTO } from '../dto/ChatResponseDTO';
import { ChatMapper } from '../mappers/ChatMapper';

export class ChatApiRepositoryImpl implements ChatApiRepository {
  constructor(private httpClient: HttpClientRepository) { }
  async sendMessage(message: string, sessionId?: string): Promise<{ reply: string; sources: string[] }> {
    const payload: ChatMessageRequestDTO = { message, session_id: sessionId };
    const response = await this.httpClient.post<ChatResponseDTO>('/chat/message', payload);
    return ChatMapper.toDomainChatResponse(response.data);
  }

  async transcribeAudio(file: Blob): Promise<string> {
    const formData = new FormData();
    // Đặt tên file là audio.webm để backend dễ xử lý
    formData.append('file', file, 'audio.webm');

    const response = await this.httpClient.post<TranscribeResponseDTO>('/chat/transcribe', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return ChatMapper.toDomainTranscribeResponse(response.data);
  }
}
