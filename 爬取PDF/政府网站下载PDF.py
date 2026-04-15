import os
import re
import time
import urllib.parse
from urllib.parse import urljoin, urlparse, unquote
import requests
from bs4 import BeautifulSoup
import hashlib

# ==================== 配置区域 ====================
# 请在此处填入要下载的政府网站URL（最多两个）
WEBSITE_URLS = [
    "https://jxf.jiangxi.gov.cn/jxsczt/2025nsjbmysgk/index.html",  # 替换为第一个政府网站URL
    #"https://example2.gov.cn",  # 替换为第二个政府网站URL（如只有一个可删除此行）
]

# 下载保存路径
DOWNLOAD_PATH = r"D:\单站深度下载\PDF"

# 请求配置
REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

# 请求超时时间（秒）
REQUEST_TIMEOUT = 30

# 请求间隔时间（秒），避免对服务器造成压力
REQUEST_DELAY = 1

# 最大重试次数
MAX_RETRIES = 3

# 已下载文件的URL记录，避免重复下载
downloaded_urls = set()
# ==================== 配置区域结束 ====================


def create_session():
    """创建并配置requests会话"""
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    # 禁用SSL证书验证（部分政府网站证书可能有问题）
    session.verify = False
    return session


def decode_filename(filename):
    """
    解码文件名中的URL编码和特殊字符
    支持多种编码格式的解码
    """
    if not filename:
        return filename
    
    # 尝试多次URL解码（处理多重编码情况）
    decoded = filename
    for _ in range(5):  # 最多解码5次
        try:
            new_decoded = unquote(decoded)
            if new_decoded == decoded:
                break
            decoded = new_decoded
        except:
            break
    
    # 尝试处理GBK编码的URL
    try:
        # 检查是否包含百分号编码
        if '%' in filename:
            # 尝试GBK解码
            gbk_decoded = unquote(filename.encode('latin-1').decode('gbk'))
            if gbk_decoded and not gbk_decoded.startswith('%'):
                decoded = gbk_decoded
    except:
        pass
    
    # 清理文件名中的非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    decoded = re.sub(illegal_chars, '_', decoded)
    
    # 去除首尾空格和点
    decoded = decoded.strip('. ')
    
    return decoded


def get_filename_from_url(url, response=None):
    """
    从URL或响应头中提取并解码文件名
    优先级：Content-Disposition > URL路径 > 默认名称
    """
    filename = None
    
    # 1. 尝试从Content-Disposition头获取文件名
    if response and 'Content-Disposition' in response.headers:
        content_disp = response.headers['Content-Disposition']
        
        # 尝试匹配 filename*=UTF-8''格式
        match = re.search(r"filename\*=UTF-8''(.+?)(?:;|$)", content_disp, re.IGNORECASE)
        if match:
            filename = unquote(match.group(1))
        
        # 尝试匹配 filename="..." 或 filename=...
        if not filename:
            match = re.search(r'filename[*]?=["\']?([^"\';\s]+)["\']?', content_disp, re.IGNORECASE)
            if match:
                filename = match.group(1)
                # 尝试解码可能的编码文件名
                try:
                    # 检查是否是UTF-8编码的字节序列
                    if filename.startswith('='):
                        # 可能是 =?UTF-8?B?...?= 格式
                        import email.header
                        decoded_parts = email.header.decode_header(filename)
                        filename = ''.join(
                            part.decode(enc or 'utf-8') if isinstance(part, bytes) else part
                            for part, enc in decoded_parts
                        )
                except:
                    pass
    
    # 2. 从URL路径获取文件名
    if not filename:
        parsed_url = urlparse(url)
        path = unquote(parsed_url.path)
        filename = os.path.basename(path)
    
    # 3. 解码文件名
    filename = decode_filename(filename)
    
    # 4. 如果没有扩展名，添加.pdf
    if filename and not filename.lower().endswith('.pdf'):
        filename += '.pdf'
    
    # 5. 如果文件名为空，使用URL哈希作为文件名
    if not filename or filename == '.pdf':
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        filename = f"document_{url_hash}.pdf"
    
    return filename


def is_valid_pdf_url(url):
    """检查URL是否指向PDF文件"""
    if not url:
        return False
    
    # 检查URL扩展名
    parsed = urlparse(url)
    path = unquote(parsed.path.lower())
    
    # 直接PDF链接
    if path.endswith('.pdf'):
        return True
    
    # 某些政府网站使用动态链接，参数中包含pdf
    query = parsed.query.lower()
    if 'pdf' in query or 'file' in query or 'download' in query or 'attach' in query:
        return True
    
    return False


def download_pdf(session, pdf_url, save_dir, source_url):
    """
    下载单个PDF文件
    返回：成功返回文件路径，失败返回None
    """
    if pdf_url in downloaded_urls:
        print(f"  [跳过] 已下载过: {pdf_url}")
        return None
    
    print(f"  [下载] {pdf_url}")
    
    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(pdf_url, timeout=REQUEST_TIMEOUT, stream=True)
            response.raise_for_status()
            
            # 检查是否真的是PDF
            content_type = response.headers.get('Content-Type', '').lower()
            if 'pdf' not in content_type and not is_valid_pdf_url(pdf_url):
                # 可能不是PDF，检查内容
                first_bytes = response.content[:10]
                if b'%PDF' not in first_bytes:
                    print(f"  [警告] 非PDF文件: {pdf_url}")
                    return None
            
            # 获取文件名
            filename = get_filename_from_url(pdf_url, response)
            
            # 确保文件名唯一
            base_name, ext = os.path.splitext(filename)
            counter = 1
            save_path = os.path.join(save_dir, filename)
            while os.path.exists(save_path):
                filename = f"{base_name}_{counter}{ext}"
                save_path = os.path.join(save_dir, filename)
                counter += 1
            
            # 保存文件
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            downloaded_urls.add(pdf_url)
            print(f"  [成功] 保存为: {filename}")
            return save_path
            
        except requests.exceptions.RequestException as e:
            print(f"  [重试 {attempt + 1}/{MAX_RETRIES}] 错误: {e}")
            time.sleep(2)
        except Exception as e:
            print(f"  [失败] 错误: {e}")
            return None
    
    print(f"  [失败] 超过最大重试次数")
    return None


def get_page_content(session, url):
    """获取页面内容"""
    try:
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # 尝试检测编码
        if response.encoding:
            try:
                response.content.decode(response.encoding)
            except:
                response.encoding = response.apparent_encoding or 'utf-8'
        else:
            response.encoding = response.apparent_encoding or 'utf-8'
        
        return response.text
    except Exception as e:
        print(f"[错误] 无法获取页面 {url}: {e}")
        return None


def extract_all_links(session, base_url, html_content):
    """
    从页面中提取所有超链接
    返回：链接列表 [(链接文本, 完整URL), ...]
    """
    links = []
    if not html_content:
        return links
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '').strip()
            if not href:
                continue
            
            # 跳过锚点、JavaScript链接等
            if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            
            # 转换为完整URL
            full_url = urljoin(base_url, href)
            
            # 只处理同域名或相关域名的链接
            parsed_base = urlparse(base_url)
            parsed_url = urlparse(full_url)
            
            # 获取链接文本
            link_text = a_tag.get_text(strip=True) or ''
            
            links.append((link_text, full_url))
        
        # 去重
        seen = set()
        unique_links = []
        for link in links:
            if link[1] not in seen:
                seen.add(link[1])
                unique_links.append(link)
        
        return unique_links
        
    except Exception as e:
        print(f"[错误] 解析页面链接失败: {e}")
        return links


def find_pdfs_in_page(session, page_url, html_content):
    """
    在页面中查找所有PDF链接
    返回：PDF URL列表
    """
    pdf_urls = []
    
    if not html_content:
        return pdf_urls
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. 查找直接指向PDF的链接
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href', '').strip()
            if not href:
                continue
            
            full_url = urljoin(page_url, href)
            
            # 检查是否是PDF链接
            if is_valid_pdf_url(full_url):
                pdf_urls.append(full_url)
        
        # 2. 查找iframe和embed中的PDF
        for tag in soup.find_all(['iframe', 'embed', 'object']):
            src = tag.get('src') or tag.get('data')
            if src:
                full_url = urljoin(page_url, src)
                if is_valid_pdf_url(full_url):
                    pdf_urls.append(full_url)
        
        # 3. 在JavaScript代码中查找PDF链接
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # 匹配常见的PDF URL模式
                patterns = [
                    r'["\']([^"\']*\.pdf[^"\']*)["\']',
                    r'["\']([^"\']*(?:download|file|attach)[^"\']*\.pdf[^"\']*)["\']',
                    r'href\s*=\s*["\']([^"\']*\.pdf[^"\']*)["\']',
                ]
                for pattern in patterns:
                    matches = re.findall(pattern, script.string, re.IGNORECASE)
                    for match in matches:
                        full_url = urljoin(page_url, match)
                        if is_valid_pdf_url(full_url):
                            pdf_urls.append(full_url)
        
        # 去重
        return list(set(pdf_urls))
        
    except Exception as e:
        print(f"  [错误] 查找PDF失败: {e}")
        return pdf_urls


def process_website(session, website_url, save_dir):
    """
    处理单个网站：获取首页链接 -> 进入每个链接 -> 下载PDF
    """
    print(f"\n{'='*60}")
    print(f"[开始处理网站] {website_url}")
    print(f"{'='*60}")
    
    # 创建该网站的保存目录
    domain = urlparse(website_url).netloc.replace('www.', '')
    site_dir = os.path.join(save_dir, domain)
    os.makedirs(site_dir, exist_ok=True)
    
    # 1. 获取首页内容
    print(f"\n[步骤1] 获取首页内容...")
    homepage_content = get_page_content(session, website_url)
    if not homepage_content:
        print(f"[错误] 无法获取首页内容，跳过该网站")
        return
    
    # 2. 提取首页所有链接
    print(f"[步骤2] 提取首页所有超链接...")
    links = extract_all_links(session, website_url, homepage_content)
    print(f"[信息] 共找到 {len(links)} 个超链接")
    
    # 3. 首先检查首页是否有直接PDF链接
    print(f"\n[步骤3] 检查首页直接PDF链接...")
    homepage_pdfs = find_pdfs_in_page(session, website_url, homepage_content)
    print(f"[信息] 首页找到 {len(homepage_pdfs)} 个PDF链接")
    
    for pdf_url in homepage_pdfs:
        download_pdf(session, pdf_url, site_dir, website_url)
        time.sleep(REQUEST_DELAY)
    
    # 4. 遍历每个链接，查找PDF
    print(f"\n[步骤4] 深度遍历子页面查找PDF...")
    total_pdfs = len(homepage_pdfs)
    
    for idx, (link_text, link_url) in enumerate(links, 1):
        print(f"\n[{idx}/{len(links)}] 处理链接: {link_text[:30] if link_text else '无标题'}...")
        print(f"  URL: {link_url}")
        
        # 跳过PDF链接（已在首页处理过）
        if is_valid_pdf_url(link_url):
            if link_url not in homepage_pdfs:
                download_pdf(session, link_url, site_dir, website_url)
                total_pdfs += 1
            time.sleep(REQUEST_DELAY)
            continue
        
        # 获取子页面内容
        subpage_content = get_page_content(session, link_url)
        if not subpage_content:
            time.sleep(REQUEST_DELAY)
            continue
        
        # 在子页面中查找PDF
        subpage_pdfs = find_pdfs_in_page(session, link_url, subpage_content)
        
        if subpage_pdfs:
            print(f"  [发现] 找到 {len(subpage_pdfs)} 个PDF链接")
            for pdf_url in subpage_pdfs:
                download_pdf(session, pdf_url, site_dir, link_url)
                total_pdfs += 1
                time.sleep(REQUEST_DELAY)
        
        time.sleep(REQUEST_DELAY)
    
    print(f"\n[完成] 网站 {website_url} 共下载 {total_pdfs} 个PDF文件")


def main():
    """主函数"""
    print("=" * 60)
    print("政府网站PDF深度下载工具")
    print("=" * 60)
    
    # 检查配置
    if not WEBSITE_URLS or WEBSITE_URLS[0] == "https://example1.gov.cn":
        print("\n[错误] 请先在脚本顶部的 WEBSITE_URLS 中配置要下载的网站URL！")
        print("\n使用方法：")
        print("1. 打开脚本文件")
        print("2. 找到 WEBSITE_URLS 配置项")
        print("3. 将示例URL替换为实际的政府网站URL")
        print("4. 保存并重新运行脚本")
        return
    
    # 创建下载目录
    os.makedirs(DOWNLOAD_PATH, exist_ok=True)
    print(f"\n[配置] 下载路径: {DOWNLOAD_PATH}")
    print(f"[配置] 待处理网站数: {len(WEBSITE_URLS)}")
    
    # 创建会话
    session = create_session()
    
    # 禁用SSL警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # 处理每个网站
    start_time = time.time()
    
    for website_url in WEBSITE_URLS:
        if website_url:
            try:
                process_website(session, website_url, DOWNLOAD_PATH)
            except Exception as e:
                print(f"\n[错误] 处理网站 {website_url} 时发生错误: {e}")
    
    # 统计结果
    elapsed_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("下载任务完成！")
    print(f"总耗时: {elapsed_time:.1f} 秒")
    print(f"共下载: {len(downloaded_urls)} 个PDF文件")
    print(f"保存位置: {DOWNLOAD_PATH}")
    print("=" * 60)


if __name__ == "__main__":
    main()