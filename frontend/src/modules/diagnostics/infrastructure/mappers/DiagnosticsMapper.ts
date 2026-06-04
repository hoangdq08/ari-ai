import { DiseaseResult } from "../../domain/models/DiseaseResult";
import { DiagnosticsResponseDTO } from "../dto/DiagnosticsResponseDTO";

export class DiagnosticsMapper {
  static toDomainDiseaseResult(dto: DiagnosticsResponseDTO): DiseaseResult {
    const advice = [
      dto.rag_advice.summary,
      dto.rag_advice.explanation,
      ...(dto.rag_advice.recommendations || []).map((item) => `- ${item}`),
    ].filter(Boolean).join("\n\n");
    const firstSource = dto.rag_advice.sources?.[0];

    return {
      diseaseName: dto.prediction.disease_label,
      confidence: dto.prediction.confidence,
      advice,
      citation: firstSource?.title || firstSource?.file_name || firstSource?.url || "Nông Trí AI - Chẩn đoán bằng hình ảnh"
    };
  }
}
