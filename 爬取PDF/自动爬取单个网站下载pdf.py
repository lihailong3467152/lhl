import os
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# ====================== 只需改这里的网址 ======================
TARGET_URL = "https://www.hangzhou.gov.cn/art/2025/7/2/art_1229063412_4367328.html"
SAVE_DIR = r"D:\脚本下载"
# ==============================================================

def download_pdfs():
    # 创建保存目录（修复了错误）
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }


    # 获取网页
    try:
        resp = requests.get(TARGET_URL, headers=headers, timeout=20)
    except:
        print("网页访问失败")
        return

    # 解析所有PDF链接
    soup = BeautifulSoup(resp.text, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        link_text = a.get_text(strip=True)  # 网页上显示的标题

        # 只处理PDF
        if not href.lower().endswith(".pdf"):
            continue

        # 跳过包含“汇总”的
        if "汇总" in href or "汇总" in link_text:
            print(f"跳过汇总文件：{link_text}")
            continue

        # 拼接完整PDF地址
        full_url = urljoin(TARGET_URL, href)

        # 文件名 = 网页标题 + .pdf
        filename = link_text + ".pdf"
        
        # 清理文件名非法字符（Windows不允许的字符）
        invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            filename = filename.replace(char, "")
        
        save_path = os.path.join(SAVE_DIR, filename)

        # 跳过已下载的文件
        if os.path.exists(save_path):
            print(f"已存在，跳过：{filename}")
            continue

        # 开始下载
        print(f"正在下载：{filename}")
        try:
            pdf_resp = requests.get(full_url, headers=headers, stream=True, timeout=30)
            # 下载完成后直接保存为标题命名
            with open(save_path, "wb") as f:
                f.write(pdf_resp.content)

            print(f"✅ 下载并命名完成：{filename}\n")

        except Exception as e:
            print(f"❌ 下载失败：{filename} | 错误：{e}\n")

    print("🎉 所有PDF下载完成！")

if __name__ == "__main__":
    download_pdfs()