import { HttpClientRepository } from '@/core/domain/repositories/HttpClientRepository';
import { ChatApiRepository } from '../../domain/repositories/ChatApiRepository';
import { ChatMessageRequestDTO } from '../dto/ChatRequestDTO';
import { ChatResponseDTO } from '../dto/ChatResponseDTO';
import { ChatMapper } from '../mappers/ChatMapper';

export class ChatApiRepositoryImpl implements ChatApiRepository {
  constructor(private httpClient: HttpClientRepository) { }
  async sendMessage(message: string, sessionId?: string): Promise<{ reply: string; sources: string[] }> {
    const payload: ChatMessageRequestDTO = { question: message, top_k: 5, session_id: sessionId };
    const response = await this.httpClient.post<ChatResponseDTO>('/ml-agri/chat', payload);
    return ChatMapper.toDomainChatResponse(response.data);
  }

  async transcribeAudio(file: Blob): Promise<string> {
    void file;
    throw new Error("Voice transcription is handled in the browser for this frontend.");
  }
}
