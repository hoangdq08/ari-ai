import { HttpClientRepository } from "@/core/domain/repositories/HttpClientRepository";
import { Article } from "../../domain/models/Article";
import { HandbookApiRepository } from "../../domain/repositories/HandbookApiRepository";
import { HandbookResponseDTO } from "../dto/HandbookResponseDTO";
import { HandbookMapper } from "../mappers/HandbookMapper";

export class HandbookApiRepositoryImpl implements HandbookApiRepository {
  constructor(private httpClient: HttpClientRepository) { }
  async fetchArticles(category: string, search: string): Promise<Article[]> {
    const response = await this.httpClient.get<HandbookResponseDTO>('/handbook/search', {
      params: {
        q: search.trim(),
        category: category,
        limit: 10
      }
    });

    const results = response.data.results || [];
    return results.map(HandbookMapper.toDomainArticle);
  }
}
