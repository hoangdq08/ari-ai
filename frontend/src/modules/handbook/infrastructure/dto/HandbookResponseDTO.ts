export interface MlAgriSourceDTO {
  source_id: string;
  title: string | null;
  source_type: string | null;
  url: string | null;
  file_name: string | null;
  reliability_level: string | null;
  crawled_at: string | null;
  category: string | null;
  category_label: string | null;
}

export interface HandbookResponseDTO {
  sources: MlAgriSourceDTO[];
}
