import { useMutation } from "@tanstack/react-query";
import { mockDiagnoseImage } from "../infrastructure/api";
import { DiseaseResult } from "../domain/DiseaseResult";

export function useDiagnoseImage() {
  return useMutation<DiseaseResult, Error, File>({
    mutationFn: (file: File) => mockDiagnoseImage(file),
  });
}
