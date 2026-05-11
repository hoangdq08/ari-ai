import { apiClient } from "../../../core/http/apiClient";
import { DiseaseResult } from "../domain/entities/DiseaseResult";
import { IDiagnosticsApi } from "../domain/interfaces/IDiagnosticsApi";

class DiagnosticsApiImpl implements IDiagnosticsApi {
  async diagnoseImage(imageFile: File): Promise<DiseaseResult> {
    const formData = new FormData();
    formData.append("image", imageFile);

    const response = await apiClient.post("/diagnostics/analyze", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    const data = response.data;
    
    return {
      diseaseName: data.disease_name,
      confidence: data.confidence,
      advice: `${data.treatment} ${data.preventive_measures}`.trim(),
      citation: "Nông Trí AI - Chẩn đoán bằng hình ảnh"
    };
  }
}

export const diagnosticsApi = new DiagnosticsApiImpl();
