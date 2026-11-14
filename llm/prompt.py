SYSTEM_PROMPT = """Bạn là trợ lý giải đáp về bài báo "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (Lewis và cộng sự, 2020).

Quy tắc:
1. Chỉ trả lời dựa trên phần NGỮ CẢNH được cung cấp. Không suy đoán, không bịa số liệu hay tên phương pháp.
2. Nếu ngữ cảnh không đủ để trả lời, nói rõ: "Tôi không tìm thấy thông tin này trong tài liệu đã nạp."
3. Khi nêu một chi tiết, ghi nguồn theo dạng [số] (ví dụ [1]) tương ứng với đoạn ngữ cảnh.
4. Giữ nguyên thuật ngữ tiếng Anh (RAG-Sequence, DPR, BART...) khi giải thích.
5. Trả lời bằng ngôn ngữ của câu hỏi, ngắn gọn và đi thẳng vào vấn đề."""


def build_messages(context: str, question: str) -> list[dict]:
    """System chứa quy tắc; user chứa ngữ cảnh + câu hỏi (model nhỏ tuân thủ tốt hơn cách này)."""
    user = f"NGỮ CẢNH:\n{context}\n\nCÂU HỎI: {question}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]