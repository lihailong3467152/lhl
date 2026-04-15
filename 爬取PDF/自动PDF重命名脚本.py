import os
import re
from PyPDF2 import PdfReader

# 清理非法文件名字符
def clean_filename(name):
    illegal_chars = r'[\\/*?:"<>|]'
    return re.sub(illegal_chars, "", name).strip()

# 从 PDF 里提取真正的标题
def get_pdf_real_title(pdf_path):
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            
            # 方案1：优先读取 PDF 元数据标题
            meta_title = reader.metadata.title if reader.metadata else None
            if meta_title and len(meta_title) > 4:
                return clean_filename(meta_title)

            # 方案2：元数据没有 → 读取第一页文本找最像标题的行
            first_page = reader.pages[0]
            text = first_page.extract_text()
            if not text:
                return None

            # 按行拆分，找最长、最像标题的行
            lines = [line.strip() for line in text.splitlines() if line.strip() and len(line) > 4]
            if lines:
                # 取最可能是标题的第一行
                best_line = lines[0]
                return clean_filename(best_line)

    except Exception as e:
        return None

# 批量重命名：标题.pdf
def rename_pdfs_to_title(folder):
    if not os.path.isdir(folder):
        print(f"目录不存在: {folder}")
        return

    for filename in os.listdir(folder):
        if filename.lower().endswith(".pdf"):
            old_path = os.path.join(folder, filename)

            # 获取标题
            title = get_pdf_real_title(old_path)
            if not title:
                print(f"❌ 无法提取标题: {filename}")
                continue

            # 新文件名 = 标题.pdf
            new_name = f"{title}.pdf"
            new_path = os.path.join(folder, new_name)

            # 重名自动加编号
            index = 1
            while os.path.exists(new_path):
                new_name = f"{title}_{index}.pdf"
                new_path = os.path.join(folder, new_name)
                index += 1

            # 执行重命名
            os.rename(old_path, new_path)
            print(f"✅ 成功: {filename} → {new_name}")

if __name__ == "__main__":
    # 你要处理的目录
    target_folder = r"D:\下载"
    rename_pdfs_to_title(target_folder)
    print("\n=== 全部处理完成 ===")