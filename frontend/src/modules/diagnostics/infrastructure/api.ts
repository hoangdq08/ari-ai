import { DiseaseResult } from "../domain/DiseaseResult";

export async function mockDiagnoseImage(_imageFile: File): Promise<DiseaseResult> {
  // Simulate network delay
  void _imageFile;
  await new Promise(resolve => setTimeout(resolve, 2000));
  
  return {
    diseaseName: "Đạo ôn cổ bông",
    confidence: 0.92,
    advice: "Dạ, ảnh bà con tải lên cho thấy triệu chứng bệnh đạo ôn cổ bông khá rõ. Cần phun ngay thuốc đặc trị (như Tricyclazole) và ngừng bón đạm.",
    citation: "Cẩm nang Bệnh học Lúa Gạo - Tr.45"
  };
}
