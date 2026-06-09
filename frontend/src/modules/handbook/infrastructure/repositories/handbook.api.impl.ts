import { HttpClientRepository } from "@/core/domain/repositories/HttpClientRepository";
import { Article } from "../../domain/models/Article";
import { HandbookApiRepository } from "../../domain/repositories/HandbookApiRepository";
import { HandbookResponseDTO } from "../dto/HandbookResponseDTO";
import { HandbookMapper } from "../mappers/HandbookMapper";

/**
 * Backed by ML-Agri `/ml-agri/sources` which returns all sources indexed in
 * the RAG vector store. We filter client-side because the endpoint does not
 * yet accept query params; revisit if the catalog grows beyond a few hundred.
 */
export class HandbookApiRepositoryImpl implements HandbookApiRepository {
  constructor(private httpClient: HttpClientRepository) {}

  async fetchArticles(category: string, search: string): Promise<Article[]> {
    const response = await this.httpClient.get<HandbookResponseDTO>("/ml-agri/sources");
    const sources = response.data.sources || [];
    const all = sources.map(HandbookMapper.toDomainArticle);

    const q = search.trim().toLowerCase();
    return all.filter((article) => {
      const matchCategory =
        category === "Tất cả" ||
        article.category === category ||
        article.category.toLowerCase().includes(category.toLowerCase());
      const matchSearch =
        !q ||
        article.title.toLowerCase().includes(q) ||
        article.description.toLowerCase().includes(q);
      return matchCategory && matchSearch;
    });
  }
}
