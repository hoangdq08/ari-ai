import { DiseaseResult } from "../../domain/models/DiseaseResult";
import { DiagnosticsResponseDTO } from "../dto/DiagnosticsResponseDTO";

export class DiagnosticsMapper {
  static toDomainDiseaseResult(dto: DiagnosticsResponseDTO): DiseaseResult {
    return {
      diseaseName: dto.disease_name,
      confidence: dto.confidence,
      advice: `${dto.treatment} ${dto.preventive_measures}`.trim(),
      citation: "Nông Trí AI - Chẩn đoán bằng hình ảnh"
    };
  }
}
