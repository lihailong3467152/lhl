import os
import time
import random
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ====================== 终极配置 ======================
# 直接写绝对路径！再也不会找不到！
COMPANY_FILE = r"D:\Python\list.xlsx"
SAVE_FOLDER = r"D:\Python\预决算文件"
YEAR = "2025"
KEYWORDS = ["预算公开", "决算公开", "财政预决算", "部门预算", "部门决算"]

os.makedirs(SAVE_FOLDER, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
# ======================================================

def get_pdf_link(company):
    search_words = f"{company} {YEAR} 预决算公开"
    url = f"https://www.baidu.com/s?wd={search_words}"

    try:
        time.sleep(random.uniform(1.5, 3))
        res = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")

        for a in soup.find_all("a", href=True):
            link = urljoin(url, a["href"])
            title = a.get_text().strip()

            if any(kw in title for kw in KEYWORDS) and link.endswith(".pdf"):
                return link

    except Exception as e:
        print(f"搜索失败：{company}")
    return None

def download(company, url):
    # 文件名格式：公司名+预决算.pdf
    filename = f"{company}+预决算.pdf"
    save_path = os.path.join(SAVE_FOLDER, filename)

    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        with open(save_path, "wb") as f:
            f.write(r.content)
        print(f"✅ 下载成功：{filename}")
        return True
    except:
        print(f"❌ 下载失败：{filename}")
        return False

# ====================== 主程序 ======================
if __name__ == "__main__":
    print("正在读取公司名单...")
    
    # 强制绝对路径 → 永远不报错
    df = pd.read_excel(COMPANY_FILE)
    
    result = []

    for i, row in df.iterrows():
        company = str(row["公司名称"]).strip()
        print(f"\n===== {i+1}/{len(df)} | {company} =====")

        link = get_pdf_link(company)
        if not link:
            print("未找到预决算PDF")
            result.append([company, "", "未找到"])
            continue

        success = download(company, link)
        result.append([company, link, "已下载" if success else "下载失败"])

    pd.DataFrame(result, columns=["公司名称", "PDF链接", "状态"]).to_excel(r"D:\Python\下载结果.xlsx", index=False)
    print("\n🎉 全部完成！")