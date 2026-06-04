export interface ChatMessageRequestDTO {
  question: string;
  top_k?: number;
  session_id?: string;
}
