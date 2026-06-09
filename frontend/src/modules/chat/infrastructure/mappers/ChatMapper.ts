import { ChatSource } from "../../domain/models/Message";
import { ChatSendResult } from "../../domain/repositories/ChatApiRepository";
import { ChatResponseDTO, ChatSourceDTO, TranscribeResponseDTO } from "../dto/ChatResponseDTO";

function isSourceObject(raw: unknown): raw is ChatSourceDTO {
  return typeof raw === "object" && raw !== null;
}

function toChatSource(raw: string | ChatSourceDTO): ChatSource {
  if (typeof raw === "string") {
    return { title: raw, url: null, reliabilityLevel: null };
  }
  if (isSourceObject(raw)) {
    return {
      title: raw.title || raw.file_name || raw.url || "Nguồn RAG",
      url: raw.url ?? null,
      reliabilityLevel: raw.reliability_level ?? null,
    };
  }
  return { title: "Nguồn RAG", url: null, reliabilityLevel: null };
}

export class ChatMapper {
  static toDomainChatResponse(dto: ChatResponseDTO): ChatSendResult {
    const sources = (dto.sources || []).map(toChatSource);
    return {
      reply: dto.answer,
      sources,
      sessionId: dto.session_id,
    };
  }

  static toDomainTranscribeResponse(dto: TranscribeResponseDTO): string {
    return dto.text;
  }
}
