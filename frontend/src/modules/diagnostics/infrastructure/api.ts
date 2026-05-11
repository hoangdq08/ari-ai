import { DiseaseResult } from "../domain/DiseaseResult";

import { apiClient } from "../../../core/http/apiClient";

export async function diagnoseImage(imageFile: File): Promise<DiseaseResult> {
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
