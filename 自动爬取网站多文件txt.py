import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import os
import datetime
import re

# ====================== 【核心配置】批量添加网站 ======================
# 支持添加1个/多个网站，直接在列表里追加网址即可
TARGET_URLS = [
    "https://www.gov.cn/",  # 网站1
    #"https://www.xxx2.com",  # 网站2
    # "https://www.xxx3.com", # 网站3（需要就取消注释）
]
# 基础保存根目录
BASE_SAVE_DIR = r"D:\多网站脚本下载\爬取"
# =====================================================================

# 反爬请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def clean_filename(name):
    """
    清理Windows非法文件/文件夹名字符
    替换 \ / : * ? " < > | 为下划线，避免创建失败
    """
    illegal_chars = r'[\\/:*?"<>|]'
    return re.sub(illegal_chars, '_', name.strip())

def get_web_title(url):
    """获取目标网站的HTML标题（用于创建文件夹名称）"""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title else "未命名网站"
        return clean_filename(title)
    except:
        return "未命名网站"

def get_valid_links(main_url):
    """过滤顶部/底部/导航无用链接，仅提取正文文章链接"""
    try:
        response = requests.get(main_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        # 关键：删除头部、底部、导航栏，彻底过滤无用链接
        for tag in soup(['header', 'footer', 'nav']):
            tag.decompose()

        a_tags = soup.find_all("a")
        valid_links = []
        for a in a_tags:
            link_name = a.get_text(strip=True)
            link_href = a.get("href")
            if not link_name or not link_href:
                continue
            if link_href.startswith(("javascript:", "#", "mailto:", "tel:")):
                continue
            full_url = urljoin(main_url, link_href)
            valid_links.append({"name": link_name, "url": full_url})
        return valid_links
    except Exception as e:
        print(f"❌ 获取链接失败：{str(e)}")
        return []

def get_article_content(article_url):
    """爬取单篇文章标题+正文"""
    try:
        time.sleep(1)
        response = requests.get(article_url, headers=HEADERS, timeout=10)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 文章标题
        article_title = soup.title.string.strip() if soup.title else "无标题文章"
        article_title = clean_filename(article_title)
        # 文章正文
        paragraphs = soup.find_all("p")
        content = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        return article_title, content
    except Exception as e:
        return "爬取失败", f"爬取异常：{str(e)}"

def save_single_article(folder_path, link_name, content):
    """
    保存单个文章为独立TXT
    规则：已存在文件 → 直接跳过
    命名：超链接标题_时间.txt
    """
    # 生成时间戳
    now_time = datetime.datetime.now().strftime("%Y-%m-%d-%H.%M")
    # 文件名：超链接标题_时间.txt
    file_name = f"{link_name}_{now_time}.txt"
    file_path = os.path.join(folder_path, file_name)

    # ✅ 核心：文件已存在 → 跳过爬取
    if os.path.exists(file_path):
        print(f"⏭️  文件已存在，跳过：{file_name}")
        return

    # 保存文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ 保存成功：{file_name}")

def main():
    # 自动创建根目录
    os.makedirs(BASE_SAVE_DIR, exist_ok=True)
    print("🚀 多网站爬虫启动，开始批量爬取...\n")

    # 遍历所有目标网站
    for index, main_url in enumerate(TARGET_URLS, 1):
        print(f"{'='*60}")
        print(f"正在处理第 {index} 个网站：{main_url}")
        print(f"{'='*60}")

        # 1. 获取网站标题，创建对应文件夹
        web_title = get_web_title(main_url)
        web_folder = os.path.join(BASE_SAVE_DIR, web_title)
        os.makedirs(web_folder, exist_ok=True)
        print(f"📂 网站文件夹：{web_folder}")

        # 2. 获取有效文章链接
        links = get_valid_links(main_url)
        if not links:
            print("❌ 该网站无有效文章链接，跳过\n")
            continue
        print(f"🔗 共提取到 {len(links)} 个有效文章链接")

        # 3. 遍历所有链接，逐个爬取+保存（重复跳过）
        for link_idx, item in enumerate(links, 1):
            link_url = item["url"]
            link_name = clean_filename(item["name"])
            print(f"\n📝 正在爬取第 {link_idx} 篇：{link_name}")
            
            # 爬取内容
            article_title, content = get_article_content(link_url)
            # 拼接完整内容
            full_content = f"【文章来源】{link_url}\n【文章标题】{article_title}\n\n【正文】\n{content}"
            # 保存（自动去重）
            save_single_article(web_folder, link_name, full_content)

        print(f"\n🎉 第 {index} 个网站爬取完成！\n")

    print("🏁 所有网站爬取任务全部完成！")

if __name__ == "__main__":
    main()