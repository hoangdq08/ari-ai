import { Article } from "../entities/Article";

export interface IHandbookApi {
  fetchArticles(category: string, search: string): Promise<Article[]>;
}
