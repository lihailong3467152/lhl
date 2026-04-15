#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政府网站PDF深度下载工具
功能：从主页面获取所有超链接，进入每个链接页面下载所有PDF文件
特性：自动处理中文乱码、智能命名、支持重试机制
"""

import os
import re
import time
import json
import hashlib
import requests
from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# ==================== 配置区域 ====================

# 目标网站列表（请在这里添加你的政府网站URL）
TARGET_URLS = [
    "https://jxf.jiangxi.gov.cn/jxsczt/2025nsjbmysgk/index.html",  # 示例：请替换为实际的政府网站URL
    # "https://another.gov.cn/zwgk/",  # 第二个网站（取消注释并修改）
]

# 下载路径
DOWNLOAD_DIR = r"D:\单站深度下载\PDF"

# 请求配置
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# 超时设置（秒）
TIMEOUT = 30
MAX_RETRIES = 3
DELAY_BETWEEN_REQUESTS = 1  # 请求间隔，避免被封
MAX_WORKERS = 3  # 并发数，政府网站建议不要太高

# PDF链接匹配模式（更全面的匹配）
PDF_PATTERNS = [
    re.compile(r'href="([^"]+\.pdf)"', re.IGNORECASE),
    re.compile(r"href='([^']+\.pdf)'", re.IGNORECASE),
    re.compile(r'url\(["\']?([^"\')]+\.pdf)["\']?\)', re.IGNORECASE),
    re.compile(r'window\.open\(["\']?([^"\')]+\.pdf)["\']?\)', re.IGNORECASE),
    re.compile(r'location\.href=["\']?([^"\']+\.pdf)["\']?', re.IGNORECASE),
]

# 中文乱码解码配置
ENCODING_TESTS = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'big5', 'latin1', 'iso-8859-1']

# ==================== 日志配置 ====================

def setup_logging():
    """配置日志"""
    log_dir = os.path.join(DOWNLOAD_DIR, "logs")
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, f"download_{time.strftime('%Y%m%d_%H%M%S')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = None

# ==================== 工具函数 ====================

class URLCache:
    """URL缓存，避免重复下载"""
    def __init__(self, cache_file):
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.lock = threading.Lock()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except:
                return set()
        return set()

    def save_cache(self):
        with self.lock:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.cache), f, ensure_ascii=False)

    def add(self, url):
        with self.lock:
            self.cache.add(url)

    def exists(self, url):
        with self.lock:
            return url in self.cache

def smart_decode(text):
    """智能解码，处理各种中文乱码情况"""
    if not text:
        return ""

    # 如果已经是正常中文，直接返回
    if is_valid_chinese(text):
        return text

    # 尝试多种编码解码
    for encoding in ENCODING_TESTS:
        try:
            # 尝试解码
            if isinstance(text, bytes):
                decoded = text.decode(encoding, errors='ignore')
            else:
                # 尝试先编码再解码（处理mojibake）
                decoded = text.encode('latin1').decode(encoding, errors='ignore')

            if is_valid_chinese(decoded):
                return decoded
        except:
            continue

    # 特殊处理：URL编码的乱码
    try:
        decoded = unquote(text)
        if decoded != text and is_valid_chinese(decoded):
            return decoded
    except:
        pass

    # 最后尝试：移除非法字符
    return re.sub(r'[\/:*?"<>|]', '_', text)

def is_valid_chinese(text):
    """检查文本是否包含有效中文字符"""
    if not text:
        return False
    # 检查是否包含中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    return chinese_chars > 0 or len(text) < 100  # 短文本也认为是有效的

def extract_filename_from_url(url):
    """从URL中提取文件名"""
    parsed = urlparse(url)
    path = unquote(parsed.path)
    filename = os.path.basename(path)

    # 移除.pdf后缀用于后续处理
    if filename.lower().endswith('.pdf'):
        filename = filename[:-4]

    return filename

def clean_filename(filename, max_length=100):
    """清理文件名，确保合法且有意义"""
    if not filename:
        filename = "未命名文件"

    # 智能解码
    filename = smart_decode(filename)

    # 移除非法字符
    filename = re.sub(r'[\/:*?"<>|]', '_', filename)

    # 移除多余空格和特殊字符
    filename = re.sub(r'\s+', ' ', filename).strip()

    # 限制长度
    if len(filename) > max_length:
        filename = filename[:max_length]

    # 确保不为空
    if not filename or filename in ['_', '-', ' ']:
        filename = "未命名文件"

    return filename

def get_unique_filepath(directory, filename, extension=".pdf"):
    """获取唯一的文件路径，避免覆盖"""
    base_path = os.path.join(directory, f"{filename}{extension}")

    if not os.path.exists(base_path):
        return base_path

    # 如果文件已存在，添加序号
    counter = 1
    while True:
        new_path = os.path.join(directory, f"{filename}_{counter:03d}{extension}")
        if not os.path.exists(new_path):
            return new_path
        counter += 1
        if counter > 999:  # 防止无限循环
            timestamp = int(time.time())
            return os.path.join(directory, f"{filename}_{timestamp}{extension}")

def extract_title_from_html(html_content, pdf_url, page_url):
    """从HTML中提取PDF的标题"""
    soup = BeautifulSoup(html_content, 'html.parser')

    candidates = []

    # 1. 查找页面标题
    title_tag = soup.find('title')
    if title_tag:
        candidates.append(title_tag.get_text(strip=True))

    # 2. 查找h1标题
    h1_tag = soup.find('h1')
    if h1_tag:
        candidates.append(h1_tag.get_text(strip=True))

    # 3. 查找包含PDF链接的a标签文本
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '.pdf' in href.lower():
            # 检查是否是同一个PDF
            full_href = urljoin(page_url, href)
            if pdf_url in full_href or full_href in pdf_url:
                text = a.get_text(strip=True)
                if text and len(text) > 2:
                    candidates.append(text)
                # 检查title属性
                if a.get('title'):
                    candidates.append(a['title'])

    # 4. 查找class或id包含title的元素
    for elem in soup.find_all(class_=re.compile(r'title|headline', re.I)):
        text = elem.get_text(strip=True)
        if text and len(text) > 2:
            candidates.append(text)

    # 5. 查找article或main内容区域
    for elem in soup.find_all(['article', 'main', 'div'], class_=re.compile(r'content|detail|article', re.I)):
        text = elem.get_text(strip=True)[:100]  # 取前100字符
        if text and len(text) > 10:
            candidates.append(text)
            break

    # 选择最佳标题
    for candidate in candidates:
        decoded = smart_decode(candidate)
        if is_valid_chinese(decoded) and len(decoded) > 3:
            return decoded

    # 如果没有找到中文标题，返回URL中的文件名
    return extract_filename_from_url(pdf_url)

def fetch_url(url, retries=MAX_RETRIES):
    """获取URL内容，带重试机制"""
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
            response.raise_for_status()

            # 尝试检测编码
            if response.encoding == 'ISO-8859-1':
                # 可能是中文编码
                response.encoding = response.apparent_encoding

            return response
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                wait_time = (attempt + 1) * 2
                logger.warning(f"请求失败，{wait_time}秒后重试: {url}, 错误: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"请求失败，已达最大重试次数: {url}, 错误: {e}")
                raise
    return None

def find_all_links(url):
    """查找页面中的所有超链接"""
    try:
        response = fetch_url(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # 转换为绝对URL
            full_url = urljoin(url, href)

            # 只保留同域名的链接
            if urlparse(full_url).netloc == urlparse(url).netloc:
                # 排除PDF文件本身、图片、JS等
                if not any(full_url.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.gif', '.js', '.css']):
                    links.add(full_url)

        return list(links)
    except Exception as e:
        logger.error(f"查找链接失败: {url}, 错误: {e}")
        return []

def find_pdf_links(page_url, html_content):
    """在HTML内容中查找所有PDF链接"""
    pdf_links = []

    # 方法1：使用BeautifulSoup解析
    soup = BeautifulSoup(html_content, 'html.parser')
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if '.pdf' in href.lower():
            full_url = urljoin(page_url, href)
            # 获取链接文本作为标题候选
            link_text = a_tag.get_text(strip=True)
            title = a_tag.get('title', '')
            pdf_links.append({
                'url': full_url,
                'link_text': link_text,
                'title_attr': title,
                'source': 'html_parse'
            })

    # 方法2：使用正则表达式（捕获可能被JS动态生成的链接）
    for pattern in PDF_PATTERNS:
        matches = pattern.findall(html_content)
        for match in matches:
            if match and '.pdf' in match.lower():
                full_url = urljoin(page_url, match)
                if not any(p['url'] == full_url for p in pdf_links):
                    pdf_links.append({
                        'url': full_url,
                        'link_text': '',
                        'title_attr': '',
                        'source': 'regex'
                    })

    # 去重
    seen = set()
    unique_links = []
    for link in pdf_links:
        if link['url'] not in seen:
            seen.add(link['url'])
            unique_links.append(link)

    return unique_links

def download_pdf(pdf_info, page_title, page_url, download_dir, url_cache):
    """下载单个PDF文件"""
    pdf_url = pdf_info['url']

    # 检查是否已下载
    if url_cache.exists(pdf_url):
        logger.info(f"跳过已下载: {pdf_url}")
        return True, "已存在"

    try:
        # 获取PDF内容
        logger.info(f"正在下载PDF: {pdf_url}")
        response = fetch_url(pdf_url)

        if not response or 'application/pdf' not in response.headers.get('Content-Type', '').lower():
            # 尝试检查内容是否是PDF
            content = response.content if response else b''
            if not content.startswith(b'%PDF'):
                logger.warning(f"内容不是PDF: {pdf_url}")
                return False, "非PDF内容"

        content = response.content

        # 确定文件名
        # 优先级：1.链接文本 2.title属性 3.页面标题 4.URL文件名
        filename_candidates = [
            pdf_info.get('link_text', ''),
            pdf_info.get('title_attr', ''),
            page_title,
            extract_filename_from_url(pdf_url)
        ]

        best_name = None
        for candidate in filename_candidates:
            decoded = smart_decode(candidate)
            if is_valid_chinese(decoded) and len(decoded) > 2:
                best_name = decoded
                break

        if not best_name:
            best_name = extract_filename_from_url(pdf_url)

        # 清理文件名
        clean_name = clean_filename(best_name)

        # 添加页面标题前缀（如果不同）
        page_title_clean = clean_filename(page_title)
        if page_title_clean and page_title_clean != clean_name and is_valid_chinese(page_title_clean):
            # 如果文件名太短，添加页面标题作为前缀
            if len(clean_name) < 10:
                clean_name = f"{page_title_clean}_{clean_name}"

        # 确保目录存在
        os.makedirs(download_dir, exist_ok=True)

        # 获取唯一文件路径
        filepath = get_unique_filepath(download_dir, clean_name)

        # 保存文件
        with open(filepath, 'wb') as f:
            f.write(content)

        # 记录到缓存
        url_cache.add(pdf_url)

        logger.info(f"✓ 下载成功: {os.path.basename(filepath)} ({len(content)} bytes)")
        return True, os.path.basename(filepath)

    except Exception as e:
        logger.error(f"✗ 下载失败: {pdf_url}, 错误: {e}")
        return False, str(e)

def process_page(page_url, main_domain, download_dir, url_cache):
    """处理单个页面，下载其中的所有PDF"""
    try:
        logger.info(f"\n处理页面: {page_url}")

        # 获取页面内容
        response = fetch_url(page_url)
        html_content = response.text

        # 提取页面标题
        page_title = extract_title_from_html(html_content, "", page_url)
        logger.info(f"页面标题: {page_title}")

        # 查找所有PDF链接
        pdf_links = find_pdf_links(page_url, html_content)
        logger.info(f"找到 {len(pdf_links)} 个PDF链接")

        if not pdf_links:
            return 0, 0

        # 创建子目录（以页面标题命名）
        if is_valid_chinese(page_title):
            subdir_name = clean_filename(page_title, max_length=50)
        else:
            # 使用URL路径作为目录名
            path_parts = urlparse(page_url).path.strip('/').split('/')
            subdir_name = path_parts[-1] if path_parts else '未分类'
            subdir_name = clean_filename(subdir_name, max_length=50)

        page_download_dir = os.path.join(download_dir, subdir_name)
        os.makedirs(page_download_dir, exist_ok=True)

        # 下载所有PDF
        success_count = 0
        fail_count = 0

        for pdf_info in pdf_links:
            success, msg = download_pdf(pdf_info, page_title, page_url, page_download_dir, url_cache)
            if success:
                success_count += 1
            else:
                fail_count += 1

            # 请求间隔
            time.sleep(DELAY_BETWEEN_REQUESTS)

        return success_count, fail_count

    except Exception as e:
        logger.error(f"处理页面失败: {page_url}, 错误: {e}")
        return 0, 0

def process_website(start_url, download_dir):
    """处理整个网站"""
    logger.info(f"\n{'='*60}")
    logger.info(f"开始处理网站: {start_url}")
    logger.info(f"{'='*60}")

    # 创建网站专属目录
    domain = urlparse(start_url).netloc.replace('www.', '')
    site_download_dir = os.path.join(download_dir, clean_filename(domain))
    os.makedirs(site_download_dir, exist_ok=True)

    # 初始化缓存
    cache_file = os.path.join(site_download_dir, "downloaded_cache.json")
    url_cache = URLCache(cache_file)

    # 查找所有一级链接
    logger.info("正在扫描页面链接...")
    links = find_all_links(start_url)
    logger.info(f"找到 {len(links)} 个待处理页面")

    # 统计
    total_success = 0
    total_fail = 0
    processed_pages = 0

    # 处理每个页面
    for i, link in enumerate(links, 1):
        logger.info(f"\n进度: [{i}/{len(links)}]")
        success, fail = process_page(link, domain, site_download_dir, url_cache)
        total_success += success
        total_fail += fail
        if success > 0 or fail > 0:
            processed_pages += 1

        # 定期保存缓存
        if i % 10 == 0:
            url_cache.save_cache()

        # 页面间延迟
        time.sleep(DELAY_BETWEEN_REQUESTS)

    # 最终保存缓存
    url_cache.save_cache()

    # 输出统计
    logger.info(f"\n{'='*60}")
    logger.info(f"网站处理完成: {start_url}")
    logger.info(f"处理页面数: {processed_pages}")
    logger.info(f"成功下载: {total_success}")
    logger.info(f"失败: {total_fail}")
    logger.info(f"{'='*60}\n")

    return total_success, total_fail

def main():
    """主函数"""
    global logger

    # 确保下载目录存在
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # 设置日志
    logger = setup_logging()

    logger.info("="*60)
    logger.info("政府网站PDF深度下载工具启动")
    logger.info(f"下载目录: {DOWNLOAD_DIR}")
    logger.info(f"目标网站数: {len(TARGET_URLS)}")
    logger.info("="*60)

    # 检查依赖
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as e:
        logger.error(f"缺少依赖: {e}")
        logger.error("请安装依赖: pip install requests beautifulsoup4")
        return

    # 检查目标URL
    if not TARGET_URLS or TARGET_URLS[0].startswith("https://example.gov.cn"):
        logger.error("请修改脚本中的TARGET_URLS，添加实际的政府网站URL！")
        logger.error("当前使用的是示例URL，不会实际下载任何内容。")
        input("按回车键退出...")
        return

    # 处理每个网站
    grand_total_success = 0
    grand_total_fail = 0

    for url in TARGET_URLS:
        if not url.strip():
            continue
        success, fail = process_website(url, DOWNLOAD_DIR)
        grand_total_success += success
        grand_total_fail += fail

        # 网站间长延迟
        time.sleep(5)

    # 最终统计
    logger.info("\n" + "="*60)
    logger.info("所有任务处理完成！")
    logger.info(f"总计成功: {grand_total_success}")
    logger.info(f"总计失败: {grand_total_fail}")
    logger.info(f"文件保存位置: {DOWNLOAD_DIR}")
    logger.info("="*60)

    # 保持窗口打开（Windows双击运行时）
    input("\n按回车键退出...")

if __name__ == "__main__":
    main()