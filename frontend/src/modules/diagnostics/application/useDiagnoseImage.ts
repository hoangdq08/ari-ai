import { useMutation } from "@tanstack/react-query";
import { DiseaseResult } from "../domain/entities/DiseaseResult";
import { IDiagnosticsApi } from "../domain/interfaces/IDiagnosticsApi";

export function useDiagnoseImage(api: IDiagnosticsApi) {
  return useMutation<DiseaseResult, Error, File>({
    mutationFn: (file: File) => api.diagnoseImage(file),
  });
}
