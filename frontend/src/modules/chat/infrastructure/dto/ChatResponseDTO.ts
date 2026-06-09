export interface ChatSourceDTO {
  title?: string | null;
  url?: string | null;
  file_name?: string | null;
  page?: number | string | null;
  source_type?: string | null;
  reliability_level?: string | null;
}

export interface ChatResponseDTO {
  answer: string;
  sources: Array<string | ChatSourceDTO>;
  confidence_level?: string;
  safety_disclaimer?: string;
  session_id?: string;
}

export interface TranscribeResponseDTO {
  text: string;
}
