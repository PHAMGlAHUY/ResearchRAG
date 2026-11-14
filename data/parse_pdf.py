from pathlib import Path
from llama_cloud import LlamaCloud

# Khởi tạo client (sẽ tự động lấy API key từ biến môi trường LLAMA_CLOUD_API_KEY)
client = LlamaCloud(api_key='llx-lKq908RSXnZlBBs3ZLuA1dBsRSuprjdZ9pKGHmfS09OmNLqE')

# 1. Tải file PDF lên hệ thống LlamaCloud
pdf_path = Path("./raw/2005.11401v4.pdf")
file_obj = client.files.create(file=pdf_path, purpose="parse")

print(f"Đã tải file lên với ID: {file_obj.id}. Đang tiến hành parse...")

# 2. Gọi API parse (SDK mới tự động xử lý polling đến khi hoàn tất)
result = client.parsing.parse(
    file_id=file_obj.id,
    tier="agentic",       # Chọn "agentic" để xử lý cấu trúc phức tạp, bảng biểu
    version="latest",
    expand=["markdown"],
)

# 3. Lấy nội dung markdown từ các trang thành công và gom lại
markdown_content = "\n\n".join(
    [page.markdown for page in result.markdown.pages if page.success]
)

# 4. Ghi ra file .md
output_path = Path("./raw/2005.11401v4.md")
output_path.write_text(markdown_content, encoding="utf-8")

print(f"Đã chuyển đổi và lưu thành công tại: {output_path}")