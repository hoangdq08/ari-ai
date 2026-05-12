export interface ArticleDTO {
  id: string;
  title: string;
  content: string;
  category: string;
}

export interface HandbookResponseDTO {
  results: ArticleDTO[];
}
