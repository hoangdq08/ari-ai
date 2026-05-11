import { useMutation } from "@tanstack/react-query";
import { diagnoseImage } from "../infrastructure/api";
import { DiseaseResult } from "../domain/DiseaseResult";

export function useDiagnoseImage() {
  return useMutation<DiseaseResult, Error, File>({
    mutationFn: (file: File) => diagnoseImage(file),
  });
}
