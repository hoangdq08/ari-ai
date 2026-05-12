import { ChatApiRepository } from "@/modules/chat/domain/repositories/ChatApiRepository";
import { ChatStorageRepository } from "@/modules/chat/domain/repositories/ChatStorageRepository";
import { ChatApiRepositoryImpl } from "@/modules/chat/infrastructure/repositories/chat.api.impl";
import { ChatStorageRepositoryImpl } from "@/modules/chat/infrastructure/repositories/chat.storage.impl";
import { DiagnosticsApiRepository } from "@/modules/diagnostics/domain/repositories/DiagnosticsApiRepository";
import { DiagnosticsApiRepositoryImpl } from "@/modules/diagnostics/infrastructure/repositories/diagnostics.api.impl";
import { HandbookApiRepository } from "@/modules/handbook/domain/repositories/HandbookApiRepository";
import { HandbookApiRepositoryImpl } from "@/modules/handbook/infrastructure/repositories/handbook.api.impl";
import { HttpClientRepositoryImpl } from "../infrastructure/repositories/http.client.impl";
import { HttpClientRepository } from "@/core/domain/repositories/HttpClientRepository";

export interface AppDependencies {
  httpClientRepository: HttpClientRepository;
  chatApiRepository: ChatApiRepository;
  chatStorageRepository: ChatStorageRepository;
  diagnosticsApiRepository: DiagnosticsApiRepository;
  handbookApiRepository: HandbookApiRepository;
}

const httpClientRepository = new HttpClientRepositoryImpl();

export const appDependencies: AppDependencies = {
  httpClientRepository,
  chatApiRepository: new ChatApiRepositoryImpl(httpClientRepository),
  chatStorageRepository: new ChatStorageRepositoryImpl(),
  diagnosticsApiRepository: new DiagnosticsApiRepositoryImpl(httpClientRepository),
  handbookApiRepository: new HandbookApiRepositoryImpl(httpClientRepository),
};
