import unicodedata
import re

def normalize_vietnamese(text: str) -> str:
    """Loại bỏ dấu tiếng Việt khỏi chuỗi, đưa về chữ thường."""
    lowered = text.lower().strip()
    decomposed = unicodedata.normalize("NFD", lowered)
    without_marks = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return without_marks.replace("đ", "d")

def needs_accent_restoration(text: str) -> bool:
    """Phát hiện xem câu có cần khôi phục dấu hay không.
    
    Chỉ trả về True nếu câu hoàn toàn không chứa bất kỳ ký tự tiếng Việt có dấu nào.
    """
    if len(text.strip()) < 3:
        return False
    
    # Ký tự tiếng Việt có dấu (bao gồm cả hoa và thường)
    vietnamese_accents = re.compile(r'[áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ]')
    
    if vietnamese_accents.search(text):
        # Có ít nhất 1 ký tự có dấu -> không cần khôi phục, RAG và LLM tự hiểu được.
        return False
        
    return True
