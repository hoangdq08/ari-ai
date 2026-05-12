import { Article } from "../../domain/models/Article";
import { ArticleDTO } from "../dto/HandbookResponseDTO";

export class HandbookMapper {
  static toDomainArticle(dto: ArticleDTO): Article {
    return {
      id: dto.id,
      title: dto.title,
      description: dto.content,
      category: dto.category,
    };
  }
}
