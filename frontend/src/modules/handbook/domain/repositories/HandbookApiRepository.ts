import { Article } from "../models/Article";

export interface HandbookApiRepository {
  fetchArticles(category: string, search: string): Promise<Article[]>;
}
