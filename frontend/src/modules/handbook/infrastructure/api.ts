import { Article } from "../domain/Article";

const MOCK_ARTICLES: Article[] = [
  {
    id: "1",
    title: "Phòng trừ bệnh đạo ôn hại lúa vụ Đông Xuân",
    description: "Hướng dẫn nhận biết sớm vết bệnh hình mắt én trên lá và cách sử dụng thuốc đặc trị an toàn.",
    category: "Lúa Gạo",
  },
  {
    id: "2",
    title: "Kỹ thuật ủ phân hữu cơ vi sinh từ phụ phẩm",
    description: "Tận dụng rơm rạ, vỏ sầu riêng để ủ phân bón giúp tiết kiệm chi phí và cải tạo đất.",
    category: "Kỹ thuật",
  },
  {
    id: "3",
    title: "Dấu hiệu nhận biết rầy nâu và cách phòng tránh",
    description: "Các chu kỳ sinh trưởng của rầy nâu và phương pháp '3 giảm 3 tăng' hiệu quả cho bà con.",
    category: "Côn trùng",
  },
  {
    id: "4",
    title: "Lịch gieo sạ lúa vùng Đồng bằng sông Cửu Long",
    description: "Cập nhật lịch thời vụ mới nhất từ Bộ NN&PTNT để né rầy và ngập mặn.",
    category: "Thời vụ",
  }
];

export async function mockFetchArticles(category: string, search: string): Promise<Article[]> {
  return new Promise((resolve) => {
    setTimeout(() => {
      let filtered = MOCK_ARTICLES;

      if (category !== "Tất cả") {
        filtered = filtered.filter(a => a.category === category);
      }

      if (search.trim() !== "") {
        const lowerSearch = search.toLowerCase();
        filtered = filtered.filter(a => 
          a.title.toLowerCase().includes(lowerSearch) || 
          a.description.toLowerCase().includes(lowerSearch)
        );
      }

      resolve(filtered);
    }, 500); // simulate 500ms network delay
  });
}
