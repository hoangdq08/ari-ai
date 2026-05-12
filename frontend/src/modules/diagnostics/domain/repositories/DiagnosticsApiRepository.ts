import { DiseaseResult } from "../models/DiseaseResult";

export interface DiagnosticsApiRepository {
  diagnoseImage(file: File | Blob): Promise<DiseaseResult>;
}
