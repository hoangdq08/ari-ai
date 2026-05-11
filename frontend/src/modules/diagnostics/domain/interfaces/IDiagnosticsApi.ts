import { DiseaseResult } from "../entities/DiseaseResult";

export interface IDiagnosticsApi {
  diagnoseImage(file: File): Promise<DiseaseResult>;
}
