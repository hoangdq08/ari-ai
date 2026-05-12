import { ChatResponseDTO, TranscribeResponseDTO } from "../dto/ChatResponseDTO";

export class ChatMapper {
  static toDomainChatResponse(dto: ChatResponseDTO) {
    return {
      reply: dto.reply,
      sources: dto.sources,
    };
  }

  static toDomainTranscribeResponse(dto: TranscribeResponseDTO): string {
    return dto.text;
  }
}
