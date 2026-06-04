export interface DiagnosticsResponseDTO {
  image_quality: {
    passed: boolean;
    issues: string[];
  };
  prediction: {
    disease_label: string;
    confidence: number;
    observed_symptoms: string[];
  };
  rag_advice: {
    status: string;
    summary: string;
    explanation: string;
    recommendations: string[];
    sources: Array<{
      title?: string;
      url?: string;
      file_name?: string;
      reliability_level?: string;
    }>;
    safety_disclaimer?: string;
  };
}
