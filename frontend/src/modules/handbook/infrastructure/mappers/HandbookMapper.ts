import { Article } from "../../domain/models/Article";
import { MlAgriSourceDTO } from "../dto/HandbookResponseDTO";

/**
 * Map a real ML-Agri RAG source (a crawled document chunk metadata) into
 * the lighter `Article` shape consumed by the handbook UI.
 *
 * We surface `reliability_level` inside `category` so users can see whether a
 * source is `official`, `semi_official`, etc.
 */
export class HandbookMapper {
  static toDomainArticle(dto: MlAgriSourceDTO): Article {
    const title = dto.title || dto.file_name || "Nguồn chưa đặt tên";
    const category = dto.category_label || dto.category || "Khác";
    const reliability = dto.reliability_level ? ` · ${dto.reliability_level}` : "";

    const description = dto.url
      ? `${category}${reliability}\n${dto.url}`
      : `${category}${reliability}`;

    return {
      id: dto.source_id,
      title,
      description,
      category,
    };
  }
}
