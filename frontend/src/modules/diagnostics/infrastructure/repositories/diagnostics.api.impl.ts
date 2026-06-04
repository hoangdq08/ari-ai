import { HttpClientRepository } from "@/core/domain/repositories/HttpClientRepository";
import { DiseaseResult } from "../../domain/models/DiseaseResult";
import { DiagnosticsApiRepository } from "../../domain/repositories/DiagnosticsApiRepository";
import { DiagnosticsResponseDTO } from "../dto/DiagnosticsResponseDTO";
import { DiagnosticsMapper } from "../mappers/DiagnosticsMapper";

export class DiagnosticsApiRepositoryImpl implements DiagnosticsApiRepository {
  constructor(private httpClient: HttpClientRepository) { }
  async diagnoseImage(imageFile: File | Blob): Promise<DiseaseResult> {
    const formData = new FormData();
    formData.append("file", imageFile);

    const response = await this.httpClient.post<DiagnosticsResponseDTO>("/ml-agri/diagnose-image", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return DiagnosticsMapper.toDomainDiseaseResult(response.data);
  }
}
