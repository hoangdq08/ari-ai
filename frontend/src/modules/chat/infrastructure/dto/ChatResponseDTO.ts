export interface ChatResponseDTO {
  answer: string;
  sources: Array<string | {
    title?: string;
    url?: string;
    file_name?: string;
    reliability_level?: string;
  }>;
  confidence_level?: string;
  safety_disclaimer?: string;
}

export interface TranscribeResponseDTO {
  text: string;
}
