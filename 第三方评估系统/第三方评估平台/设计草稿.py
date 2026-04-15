import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import os
import re

# ================= 配置区域 =================
# 1. 替换为你想要爬取的主网页地址
MAIN_URL = 'https://www.runoob.com/fastapi/fastapi-request-response.html'

# 2. 设置请求头，伪装成浏览器（防止被服务器直接拒绝）
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 3. 创建一个文件夹用来保存下载的文章
SAVE_DIR = './downloaded_articles'
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)
# ============================================

def clean_filename(filename):
    """
    清理文件名中的非法字符，防止保存文件时报错
    Windows文件名不能包含: \ / : * ? " < > |
    """
    return re.sub(r'[\\/:*?"<>|]', '_', filename).strip()

def get_article_links(main_url):
    """
    第一步：爬取主网页，提取所有文章的标题和链接
    """
    try:
        response = requests.get(main_url, headers=HEADERS, timeout=10)
        response.raise_for_status() # 检查请求是否成功
        response.encoding = response.apparent_encoding # 自动识别并设置正确的编码，防止中文乱码
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        # 提取所有的 <a> 标签
        # 注意：有时候网页里有很多无关链接（比如导航栏），你可以在这里缩小范围
        # 例如如果文章列表都在 <div class="list"> 里，可以写 soup.find('div', class_='list').find_all('a')
        for a_tag in soup.find_all('a'):
            title = a_tag.text.strip()
            link = a_tag.get('href')
            
            # 过滤掉空的、没有文字的、或者 JavaScript 动作链接
            if title and link and not link.startswith('javascript:'):
                # 将可能存在的相对路径（如 /post/123.html）转换为完整的绝对路径
                full_link = urllib.parse.urljoin(main_url, link)
                articles.append({'title': title, 'url': full_link})
                
        return articles
    except Exception as e:
        print(f"获取文章列表失败: {e}")
        return []

def download_article(article_info):
    """
    第二步：根据链接进入文章详情页，抓取正文并保存
    """
    title = clean_filename(article_info['title'])
    url = article_info['url']
    
    # 避免保存空标题的文件
    if not title:
        return

    print(f"正在爬取: {title} ({url})")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ================= 核心修改点 =================
        # 这里的提取规则必须根据目标网站修改！
        # 假设文章正文包裹在 <div class="article-content"> 中：
        # content_div = soup.find('div', class_='article-content')
        
        # 如果你不知道怎么写，最粗暴的方法是提取整个 body 的纯文本，但这会包含很多无关内容(如侧边栏、底部信息)
        content_div = soup.find('body') 
        # ============================================
        
        if content_div:
            # 获取纯文本内容
            text_content = content_div.get_text(separator='\n', strip=True)
            
            # 保存到本地txt文件
            file_path = os.path.join(SAVE_DIR, f"{title}.txt")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text_content)
            print(f"✅ 保存成功: {title}.txt")
        else:
            print(f"❌ 未找到文章正文内容: {title}")
            
    except Exception as e:
        print(f"❌ 爬取文章失败 {title}: {e}")

if __name__ == '__main__':
    # 1. 获取所有链接和中文名称
    print("开始获取文章列表...")
    article_list = get_article_links(MAIN_URL)
    print(f"共找到 {len(article_list)} 个可能的文章链接。\n")
    
    # 2. 遍历下载每一篇文章
    for article in article_list:
        download_article(article)
        # 加上延时，非常重要！防止请求过快被服务器封禁IP
        time.sleep(2) 
        
    print("\n所有任务执行完毕！")