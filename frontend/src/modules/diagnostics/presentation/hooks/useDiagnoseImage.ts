import { useMutation } from "@tanstack/react-query";
import { DiseaseResult } from "../../domain/models/DiseaseResult";
import { useDI } from "@/shared/hooks/useDI";

export function useDiagnoseImage() {
  const { diagnosticsApiRepository } = useDI();

  return useMutation<DiseaseResult, Error, File | Blob>({
    mutationFn: (file: File | Blob) => diagnosticsApiRepository.diagnoseImage(file),
  });
}
