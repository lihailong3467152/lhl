import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import os
from datetime import datetime

# ====================== 【必填】修改这里 ======================
TARGET_URL = "https://www.gov.cn/"  # 你要爬取的目标网页
SAVE_FILE = "爬取结果.txt"          # 结果保存的文件名（基础名，会附加时间）
SAVE_DIR = r"D:\多网站脚本下载\爬取"  # 保存目录
# =============================================================

# 反爬请求头（必须加，否则大部分网站会拒绝访问）
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def get_valid_links(main_url):
    """
    功能：爬取目标网页的所有【中文名称 + 超链接】
    返回：列表 [{"name": 中文名称, "url": 完整链接}, ...]
    """
    try:
        # 发送请求
        response = requests.get(main_url, headers=HEADERS, timeout=10)
        response.raise_for_status()  # 报错404/500等异常
        response.encoding = response.apparent_encoding  # 自动识别中文编码

        # 解析HTML
        soup = BeautifulSoup(response.text, "html.parser")
        a_tags = soup.find_all("a")  # 提取所有带超链接的标签

        # 忽略导航/页脚等无关区域的关键词
        IGNORED_KEYWORDS = [
            "nav", "menu", "header", "footer", "top", "bottom", "sidebar",
            "side", "breadcrumb", "friend", "友情链接", "link", "links", "navs"
        ]

        def is_in_ignored_section(tag):
            """如果 a 标签位于 nav/header/footer/aside 或其祖先的 id/class 含有关键词，则视为无关链接。"""
            for parent in tag.parents:
                if parent.name in ("nav", "header", "footer", "aside"):
                    return True
                # 检查 id/class/其它属性中是否包含关键词
                if parent.attrs:
                    combined = " ".join([str(v) for v in parent.attrs.values()])
                    lower = combined.lower()
                    for kw in IGNORED_KEYWORDS:
                        if kw in lower:
                            return True
            return False

        valid_links = []
        for a in a_tags:
            # 跳过在导航/页脚等区域的链接
            if is_in_ignored_section(a):
                continue
            link_name = a.get_text(strip=True)  # 提取中文名称（去除空格）
            link_href = a.get("href")  # 提取超链接

            # 过滤：空名称、空链接、无效链接（javascript/锚点）
            if not link_name or not link_href:
                continue
            if link_href.startswith(("javascript:", "#", "mailto:")):
                continue

            # 关键：相对链接 → 绝对链接（比如 /article/123 → 完整网址）
            full_url = urljoin(main_url, link_href)
            valid_links.append({"name": link_name, "url": full_url})

        print(f"✅ 共提取到 {len(valid_links)} 个有效超链接")
        return valid_links

    except Exception as e:
        print(f"❌ 获取链接失败：{str(e)}")
        return []

def get_article_content(article_url):
    """
    功能：爬取单个超链接对应的文章内容
    返回：文章标题 + 正文
    """
    try:
        time.sleep(1)  # 延迟1秒，防封IP
        response = requests.get(article_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, "html.parser")

        # 提取标题（通用适配大部分网站）
        title = soup.title.string if soup.title else "无标题"
        # 提取正文（抓取所有p标签文字，适配绝大多数文章页）
        paragraphs = soup.find_all("p")
        content = "\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

        return f"【文章标题】{title}\n【文章正文】\n{content}\n"

    except Exception as e:
        return f"❌ 爬取失败：{str(e)}\n"

def main():
    """主函数：自动爬取所有链接+文章"""
    print("开始爬取...")
    # 1. 获取所有超链接
    links = get_valid_links(TARGET_URL)
    if not links:
        print("无有效链接，程序结束")
        return
    # 2. 批量爬取文章并保存
    # 确保保存目录存在，并以 名称+时间 格式命名，例如: 爬取结果2026-03-26-13.40.txt
    os.makedirs(SAVE_DIR, exist_ok=True)
    base, ext = os.path.splitext(SAVE_FILE)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H.%M")
    final_save_file = os.path.join(SAVE_DIR, f"{base}{timestamp}{ext}")
    print(f"将结果保存到：{final_save_file}")

    with open(final_save_file, "w", encoding="utf-8") as f:
        for idx, item in enumerate(links, 1):
            name = item["name"]
            url = item["url"]
            print(f"正在爬取第 {idx} 个：{name} | {url}")

            # 写入名称+链接
            f.write(f"{'='*50}\n第{idx}篇 | 名称：{name} | 链接：{url}\n{'='*50}\n")
            # 写入文章内容
            f.write(get_article_content(url))
            f.write("\n\n")

    print(f"\n🎉 爬取完成！结果已保存到：{final_save_file}")

if __name__ == "__main__":
    main()