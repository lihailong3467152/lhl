#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新余市消费运行监测数据爬取脚本
支持爬取多个公开数据源的消费相关数据
输出格式：Excel (.xlsx) 和 CSV (.csv)
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import os
from datetime import datetime
import re
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils.dataframe import dataframe_to_rows

# 创建输出目录
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crawled_data')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
}

def save_to_excel(data_list, filename, sheet_name='数据'):
    """保存数据到Excel文件"""
    if not data_list:
        print(f"⚠️ 无数据可保存: {filename}")
        return None
    
    df = pd.DataFrame(data_list)
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # 保存Excel
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # 调整列宽
        worksheet = writer.sheets[sheet_name]
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    # 同时保存CSV
    csv_filepath = filepath.replace('.xlsx', '.csv')
    df.to_csv(csv_filepath, index=False, encoding='utf-8-sig')
    
    print(f"✅ 数据已保存: {filepath}")
    print(f"✅ CSV已保存: {csv_filepath}")
    return filepath

def crawl_statistical_bulletin():
    """
    爬取新余市国民经济和社会发展统计公报
    数据源：红黑统计公报库
    """
    print("\n" + "="*60)
    print("📊 爬取新余市统计公报数据")
    print("="*60)
    
    results = []
    
    # 红黑统计公报库 - 新余市2024年统计公报
    urls = [
        {
            'url': 'https://tjgb.hongheiku.com/djs/59957.html',
            'year': '2024',
            'name': '新余市2024年国民经济和社会发展统计公报'
        },
        {
            'url': 'https://tjgb.hongheiku.com/djs/48142.html',
            'year': '2023',
            'name': '新余市2023年国民经济和社会发展统计公报'
        },
        {
           'url': 'https://tjgb.hongheiku.com/djs/72589.html',
        'year': '2025',
        'name': '新余市2025年国民经济和社会发展统计公报'
    }
    ]
    
    for url_info in urls:
        try:
            print(f"正在爬取: {url_info['name']}")
            response = requests.get(url_info['url'], headers=HEADERS, timeout=30)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找正文内容
            content_div = soup.find('div', class_='content') or soup.find('div', class_='article-content') or soup.find('article')
            
            if content_div:
                text = content_div.get_text()
                
                # 提取关键数据
                data_items = []
                
                # 社会消费品零售总额
                retail_match = re.search(r'社会消费品零售总额(\d+\.?\d*)亿元', text)
                if retail_match:
                    data_items.append({
                        '指标名称': '社会消费品零售总额',
                        '数值': retail_match.group(1),
                        '单位': '亿元',
                        '年份': url_info['year'],
                        '数据来源': url_info['name'],
                        '发布部门': '新余市统计局'
                    })
                
                # 城镇消费品零售额
                town_match = re.search(r'城镇消费品零售额(\d+\.?\d*)亿元', text)
                if town_match:
                    data_items.append({
                        '指标名称': '城镇消费品零售额',
                        '数值': town_match.group(1),
                        '单位': '亿元',
                        '年份': url_info['year'],
                        '数据来源': url_info['name'],
                        '发布部门': '新余市统计局'
                    })
                
                # 乡村消费品零售额
                rural_match = re.search(r'乡村消费品零售额(\d+\.?\d*)亿元', text)
                if rural_match:
                    data_items.append({
                        '指标名称': '乡村消费品零售额',
                        '数值': rural_match.group(1),
                        '单位': '亿元',
                        '年份': url_info['year'],
                        '数据来源': url_info['name'],
                        '发布部门': '新余市统计局'
                    })
                
                # 限额以上单位零售额
                limit_match = re.search(r'限额以上.*?零售额(\d+\.?\d*)亿元', text)
                if limit_match:
                    data_items.append({
                        '指标名称': '限额以上单位零售额',
                        '数值': limit_match.group(1),
                        '单位': '亿元',
                        '年份': url_info['year'],
                        '数据来源': url_info['name'],
                        '发布部门': '新余市统计局'
                    })
                
                # 城镇居民人均可支配收入
                income_town = re.search(r'城镇居民人均可支配收入(\d+)元', text)
                if income_town:
                    data_items.append({
                        '指标名称': '城镇居民人均可支配收入',
                        '数值': income_town.group(1),
                        '单位': '元',
                        '年份': url_info['year'],
                        '数据来源': url_info['name'],
                        '发布部门': '新余市统计局'
                    })
                
                # 农村居民人均可支配收入
                income_rural = re.search(r'农村居民人均可支配收入(\d+)元', text)
                if income_rural:
                    data_items.append({
                        '指标名称': '农村居民人均可支配收入',
                        '数值': income_rural.group(1),
                        '单位': '元',
                        '年份': url_info['year'],
                        '数据来源': url_info['name'],
                        '发布部门': '新余市统计局'
                    })
                
                # 城镇居民人均消费支出
                spend_town = re.search(r'城镇居民人均消费支出(\d+)元', text)
                if spend_town:
                    data_items.append({
                        '指标名称': '城镇居民人均消费支出',
                        '数值': spend_town.group(1),
                        '单位': '元',
                        '年份': url_info['year'],
                        '数据来源': url_info['name'],
                        '发布部门': '新余市统计局'
                    })
                
                # 农村居民人均消费支出
                spend_rural = re.search(r'农村居民人均消费支出(\d+)元', text)
                if spend_rural:
                    data_items.append({
                        '指标名称': '农村居民人均消费支出',
                        '数值': spend_rural.group(1),
                        '单位': '元',
                        '年份': url_info['year'],
                        '数据来源': url_info['name'],
                        '发布部门': '新余市统计局'
                    })
                
                # CPI
                cpi_match = re.search(r'居民消费价格.*?上涨(\d+\.?\d*)%', text)
                if cpi_match:
                    data_items.append({
                        '指标名称': '居民消费价格指数(CPI)涨幅',
                        '数值': cpi_match.group(1),
                        '单位': '%',
                        '年份': url_info['year'],
                        '数据来源': url_info['name'],
                        '发布部门': '国家统计局新余调查队'
                    })
                
                # GDP
                gdp_match = re.search(r'地区生产总值(\d+\.?\d*)亿元', text)
                if gdp_match:
                    data_items.append({
                        '指标名称': '地区生产总值(GDP)',
                        '数值': gdp_match.group(1),
                        '单位': '亿元',
                        '年份': url_info['year'],
                        '数据来源': url_info['name'],
                        '发布部门': '新余市统计局'
                    })
                
                # 网络零售额
                online_match = re.search(r'网络零售额.*?(\d+\.?\d*)亿元', text)
                if online_match:
                    data_items.append({
                        '指标名称': '网络零售额',
                        '数值': online_match.group(1),
                        '单位': '亿元',
                        '年份': url_info['year'],
                        '数据来源': url_info['name'],
                        '发布部门': '新余市商务局'
                    })
                
                results.extend(data_items)
                print(f"  ✅ 提取到 {len(data_items)} 条数据")
            
            time.sleep(1)  # 避免请求过快
            
        except Exception as e:
            print(f"  ❌ 爬取失败: {e}")
    
    # 保存结果
    if results:
        save_to_excel(results, '新余市统计公报消费数据.xlsx', '统计公报数据')
    
    return results

def crawl_mofcom_price_data():
    """
    爬取商务部生活必需品价格监测数据
    数据源：商务部商务预报平台
    """
    print("\n" + "="*60)
    print("📊 爬取商务部生活必需品价格数据")
    print("="*60)
    
    results = []
    
    # 商务预报平台 - 新余市生活必需品价格
    urls = [
        {
            'url': 'https://cif.mofcom.gov.cn/cif/html//market_scanner/2025/6/1750641566828.html',
            'name': '新余市生活必需品市场价格监测'
        }
    ]
    
    for url_info in urls:
        try:
            print(f"正在爬取: {url_info['name']}")
            response = requests.get(url_info['url'], headers=HEADERS, timeout=30)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找价格表格
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # 跳过表头
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        try:
                            commodity = cols[0].get_text(strip=True)
                            price = cols[1].get_text(strip=True)
                            change = cols[2].get_text(strip=True) if len(cols) > 2 else ''
                            
                            if commodity and price:
                                results.append({
                                    '商品名称': commodity,
                                    '价格': price,
                                    '涨跌幅': change,
                                    '数据来源': '商务部商务预报平台',
                                    '发布部门': '新余市商务局',
                                    '爬取时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                })
                        except:
                            continue
            
            print(f"  ✅ 提取到 {len(results)} 条数据")
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ 爬取失败: {e}")
    
    # 保存结果
    if results:
        save_to_excel(results, '新余市生活必需品价格数据.xlsx', '价格监测')
    
    return results

def crawl_tourism_data():
    """
    爬取新余市旅游消费数据
    数据源：凤凰网江西、大江网等
    """
    print("\n" + "="*60)
    print("📊 爬取新余市旅游消费数据")
    print("="*60)
    
    results = []
    
    urls = [
        {
            'url': 'https://jx.ifeng.com/c/8dZJfi0vqiX',
            'name': '国庆假期新余旅游数据'
        }
    ]
    
    for url_info in urls:
        try:
            print(f"正在爬取: {url_info['name']}")
            response = requests.get(url_info['url'], headers=HEADERS, timeout=30)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取正文
            content_div = soup.find('div', class_='content') or soup.find('article') or soup.find('div', class_='article-content')
            
            if content_div:
                text = content_div.get_text()
                
                # 提取游客人数
                visitor_match = re.search(r'接待游客(\d+\.?\d*)万人次', text)
                if visitor_match:
                    results.append({
                        '指标名称': '接待游客人数',
                        '数值': visitor_match.group(1),
                        '单位': '万人次',
                        '时间段': '国庆假期',
                        '数据来源': '凤凰网江西',
                        '发布部门': '新余市文广旅局'
                    })
                
                # 提取旅游收入
                income_match = re.search(r'旅游收入(\d+\.?\d*)亿元', text)
                if income_match:
                    results.append({
                        '指标名称': '旅游收入',
                        '数值': income_match.group(1),
                        '单位': '亿元',
                        '时间段': '国庆假期',
                        '数据来源': '凤凰网江西',
                        '发布部门': '新余市文广旅局'
                    })
                
                # 同比增长
                growth_match = re.search(r'同比.*?增长(\d+\.?\d*)%', text)
                if growth_match:
                    results.append({
                        '指标名称': '游客同比增长',
                        '数值': growth_match.group(1),
                        '单位': '%',
                        '时间段': '国庆假期',
                        '数据来源': '凤凰网江西',
                        '发布部门': '新余市文广旅局'
                    })
            
            print(f"  ✅ 提取到 {len(results)} 条数据")
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ 爬取失败: {e}")
    
    # 保存结果
    if results:
        save_to_excel(results, '新余市旅游消费数据.xlsx', '旅游数据')
    
    return results

def crawl_ecommerce_data():
    """
    爬取新余市电商/快递数据
    数据源：凤凰网江西、江西省邮政管理局
    """
    print("\n" + "="*60)
    print("📊 爬取新余市电商快递数据")
    print("="*60)
    
    results = []
    
    urls = [
        {
            'url': 'https://jx.ifeng.com/c/8rXiKfanN6b',
            'name': '新余市快递物流数据'
        }
    ]
    
    for url_info in urls:
        try:
            print(f"正在爬取: {url_info['name']}")
            response = requests.get(url_info['url'], headers=HEADERS, timeout=30)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content_div = soup.find('div', class_='content') or soup.find('article') or soup.find('div', class_='article-content')
            
            if content_div:
                text = content_div.get_text()
                
                # 快递业务量
                express_match = re.search(r'快递业务量.*?(\d+\.?\d*)亿件', text)
                if express_match:
                    results.append({
                        '指标名称': '快递业务量',
                        '数值': express_match.group(1),
                        '单位': '亿件',
                        '年份': '2025',
                        '数据来源': '凤凰网江西',
                        '发布部门': '新余市邮政管理局'
                    })
                
                # 邮政行业寄递业务总量
                postal_match = re.search(r'邮政行业寄递业务总量(\d+\.?\d*)亿件', text)
                if postal_match:
                    results.append({
                        '指标名称': '邮政行业寄递业务总量',
                        '数值': postal_match.group(1),
                        '单位': '亿件',
                        '年份': '2025',
                        '数据来源': '凤凰网江西',
                        '发布部门': '新余市邮政管理局'
                    })
                
                # 农产品快递业务量
                agri_match = re.search(r'农产品快递业务量突破(\d+)万件', text)
                if agri_match:
                    results.append({
                        '指标名称': '农产品快递业务量',
                        '数值': agri_match.group(1),
                        '单位': '万件',
                        '年份': '2025',
                        '数据来源': '凤凰网江西',
                        '发布部门': '新余市邮政管理局'
                    })
            
            print(f"  ✅ 提取到 {len(results)} 条数据")
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ 爬取失败: {e}")
    
    # 保存结果
    if results:
        save_to_excel(results, '新余市电商快递数据.xlsx', '电商快递')
    
    return results

def crawl_auto_sales_data():
    """
    爬取新余市汽车消费数据
    数据源：凤凰网江西、大江网
    """
    print("\n" + "="*60)
    print("📊 爬取新余市汽车消费数据")
    print("="*60)
    
    results = []
    
    urls = [
        {
            'url': 'https://jx.ifeng.com/c/8rtksLV2hZh',
            'name': '新余市汽车消费数据'
        }
    ]
    
    for url_info in urls:
        try:
            print(f"正在爬取: {url_info['name']}")
            response = requests.get(url_info['url'], headers=HEADERS, timeout=30)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            content_div = soup.find('div', class_='content') or soup.find('article') or soup.find('div', class_='article-content')
            
            if content_div:
                text = content_div.get_text()
                
                # 汽车年销量
                sales_match = re.search(r'年销量达(\d+\.?\d*)万辆', text)
                if sales_match:
                    results.append({
                        '指标名称': '汽车年销量',
                        '数值': sales_match.group(1),
                        '单位': '万辆',
                        '地点': '仙女湖汽车城',
                        '数据来源': '凤凰网江西',
                        '发布部门': '新余市商务局'
                    })
                
                # 新能源汽车销量
                ev_match = re.search(r'新能源车年销量突破(\d+)辆', text)
                if ev_match:
                    results.append({
                        '指标名称': '新能源汽车年销量',
                        '数值': ev_match.group(1),
                        '单位': '辆',
                        '地点': '仙女湖汽车城',
                        '数据来源': '凤凰网江西',
                        '发布部门': '新余市商务局'
                    })
                
                # 汽车品牌数量
                brand_match = re.search(r'引进汽车品牌(\d+)个', text)
                if brand_match:
                    results.append({
                        '指标名称': '汽车品牌数量',
                        '数值': brand_match.group(1),
                        '单位': '个',
                        '地点': '仙女湖汽车城',
                        '数据来源': '凤凰网江西',
                        '发布部门': '新余市商务局'
                    })
                
                # 新能源品牌数量
                ev_brand_match = re.search(r'新能源品牌近(\d+)个', text)
                if ev_brand_match:
                    results.append({
                        '指标名称': '新能源汽车品牌数量',
                        '数值': ev_brand_match.group(1),
                        '单位': '个',
                        '地点': '仙女湖汽车城',
                        '数据来源': '凤凰网江西',
                        '发布部门': '新余市商务局'
                    })
            
            print(f"  ✅ 提取到 {len(results)} 条数据")
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ 爬取失败: {e}")
    
    # 保存结果
    if results:
        save_to_excel(results, '新余市汽车消费数据.xlsx', '汽车消费')
    
    return results

def crawl_population_data():
    """
    爬取新余市人口数据
    数据源：聚汇数据网
    """
    print("\n" + "="*60)
    print("📊 爬取新余市人口数据")
    print("="*60)
    
    results = []
    
    # 聚汇数据网人口数据
    urls = [
        {
            'url': 'https://population.gotohui.com/pdata-208/2023',
            'name': '新余市人口数据'
        }
    ]
    
    for url_info in urls:
        try:
            print(f"正在爬取: {url_info['name']}")
            response = requests.get(url_info['url'], headers=HEADERS, timeout=30)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找数据表格
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        try:
                            indicator = cols[0].get_text(strip=True)
                            value = cols[1].get_text(strip=True)
                            
                            if indicator and value:
                                results.append({
                                    '指标名称': indicator,
                                    '数值': value,
                                    '年份': '2023',
                                    '数据来源': '聚汇数据网',
                                    '发布部门': '新余市统计局'
                                })
                        except:
                            continue
            
            print(f"  ✅ 提取到 {len(results)} 条数据")
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ 爬取失败: {e}")
    
    # 保存结果
    if results:
        save_to_excel(results, '新余市人口数据.xlsx', '人口数据')
    
    return results

def generate_summary_report(all_data):
    """生成汇总报告"""
    print("\n" + "="*60)
    print("📊 生成数据汇总报告")
    print("="*60)
    
    # 合并所有数据
    summary = []
    
    for category, data_list in all_data.items():
        for item in data_list:
            item['数据类别'] = category
            summary.append(item)
    
    if summary:
        # 保存汇总报告
        df = pd.DataFrame(summary)
        filepath = os.path.join(OUTPUT_DIR, '新余市消费数据汇总报告.xlsx')
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='汇总数据', index=False)
            
            # 调整列宽
            worksheet = writer.sheets['汇总数据']
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        print(f"✅ 汇总报告已保存: {filepath}")
        
        # 同时保存CSV
        csv_filepath = filepath.replace('.xlsx', '.csv')
        df.to_csv(csv_filepath, index=False, encoding='utf-8-sig')
        print(f"✅ CSV汇总已保存: {csv_filepath}")
    
    return summary

def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 新余市消费运行监测数据爬取脚本")
    print("="*60)
    print(f"📅 爬取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 输出目录: {OUTPUT_DIR}")
    print("="*60)
    
    all_data = {}
    
    # 1. 爬取统计公报数据
    all_data['统计公报'] = crawl_statistical_bulletin()
    
    # 2. 爬取生活必需品价格数据
    all_data['价格监测'] = crawl_mofcom_price_data()
    
    # 3. 爬取旅游数据
    all_data['旅游消费'] = crawl_tourism_data()
    
    # 4. 爬取电商快递数据
    all_data['电商快递'] = crawl_ecommerce_data()
    
    # 5. 爬取汽车消费数据
    all_data['汽车消费'] = crawl_auto_sales_data()
    
    # 6. 爬取人口数据
    all_data['人口数据'] = crawl_population_data()
    
    # 生成汇总报告
    summary = generate_summary_report(all_data)
    
    # 打印统计信息
    print("\n" + "="*60)
    print("📊 爬取统计")
    print("="*60)
    total = 0
    for category, data_list in all_data.items():
        count = len(data_list)
        total += count
        print(f"  {category}: {count} 条数据")
    print(f"  总计: {total} 条数据")
    print("="*60)
    print(f"✅ 所有数据已保存到: {OUTPUT_DIR}")
    print("="*60)

if __name__ == "__main__":
    main()
