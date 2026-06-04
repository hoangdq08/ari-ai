import { ChatResponseDTO, TranscribeResponseDTO } from "../dto/ChatResponseDTO";

export class ChatMapper {
  static toDomainChatResponse(dto: ChatResponseDTO) {
    const sources = (dto.sources || []).map((source) => {
      if (typeof source === "string") return source;
      return source.title || source.file_name || source.url || "Nguồn RAG";
    });

    return {
      reply: dto.answer,
      sources,
    };
  }

  static toDomainTranscribeResponse(dto: TranscribeResponseDTO): string {
    return dto.text;
  }
}
