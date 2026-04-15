#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
新余市消费运行监测数据爬取脚本 V2
基于《新余市消费运行监测指标体系字典（初稿）》
支持爬取2023-2025年数据
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
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'crawled_data_v2')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Connection': 'keep-alive',
}

# 年份配置
YEARS = [2023, 2024, 2025]

# 新余市统计公报URL配置
BULLETIN_URLS = {
    '2023': 'https://tjgb.hongheiku.com/djs/48142.html',
    '2024': 'https://tjgb.hongheiku.com/djs/59957.html',
    '2025': None,  # 2025年公报尚未发布
}

# 指标关键词映射（用于从网页提取数据）
INDICATOR_PATTERNS = {
    # 宏观规模与结构
    '社会消费品零售总额': [r'社会消费品零售总额[^\d]*(\d+\.?\d*)\s*亿元', r'全年社会消费品零售总额[^\d]*(\d+\.?\d*)'],
    '限上单位消费品零售额': [r'限额以上[^零售]*零售额[^\d]*(\d+\.?\d*)\s*亿元', r'限额以上单位[^零售]*零售额[^\d]*(\d+\.?\d*)'],
    '城镇消费品零售额': [r'城镇消费品零售额[^\d]*(\d+\.?\d*)\s*亿元'],
    '乡村消费品零售额': [r'乡村消费品零售额[^\d]*(\d+\.?\d*)\s*亿元'],
    '城镇居民人均可支配收入': [r'城镇居民人均可支配收入[^\d]*(\d+)', r'城镇居民人均可支配收入.*?(\d+)元'],
    '农村居民人均可支配收入': [r'农村居民人均可支配收入[^\d]*(\d+)', r'农村居民人均可支配收入.*?(\d+)元'],
    '城镇居民人均消费支出': [r'城镇居民人均消费支出[^\d]*(\d+)'],
    '农村居民人均消费支出': [r'农村居民人均消费支出[^\d]*(\d+)'],
    '居民消费价格指数': [r'居民消费价格.*?上涨[^\d]*(\d+\.?\d*)%', r'CPI.*?上涨[^\d]*(\d+\.?\d*)%'],
    '地区生产总值': [r'地区生产总值[^\d]*(\d+\.?\d*)\s*亿元', r'GDP[^\d]*(\d+\.?\d*)\s*亿元'],
    '第三产业增加值': [r'第三产业增加值[^\d]*(\d+\.?\d*)\s*亿元'],
    '批发业销售额': [r'批发业[^销]*销售额[^\d]*(\d+\.?\d*)'],
    '零售业销售额': [r'零售业[^销]*销售额[^\d]*(\d+\.?\d*)'],
    '住宿业营业额': [r'住宿业[^营]*营业额[^\d]*(\d+\.?\d*)'],
    '餐饮业营业额': [r'餐饮业[^营]*营业额[^\d]*(\d+\.?\d*)'],
    '常住人口': [r'常住人口[^\d]*(\d+\.?\d*)\s*万人'],
    '城镇化率': [r'城镇化率[^\d]*(\d+\.?\d*)%'],
    
    # 消费活力与趋势
    '接待游客总人数': [r'接待游客[^\d]*(\d+\.?\d*)\s*万人次', r'接待国内外游客[^\d]*(\d+\.?\d*)'],
    '旅游总收入': [r'旅游收入[^\d]*(\d+\.?\d*)\s*亿元', r'实现旅游收入[^\d]*(\d+\.?\d*)'],
    
    # 汽车消费
    '汽车销量': [r'汽车销量[^\d]*(\d+\.?\d*)\s*万辆', r'汽车.*?销量[^\d]*(\d+\.?\d*)'],
    '新能源汽车销量': [r'新能源.*?销量[^\d]*(\d+\.?\d*)', r'新能源汽车.*?(\d+\.?\d*)\s*辆'],
    
    # 网络消费
    '网络零售额': [r'网络零售额[^\d]*(\d+\.?\d*)\s*亿元'],
    '快递业务量': [r'快递业务量[^\d]*(\d+\.?\d*)\s*亿件', r'快递.*?(\d+\.?\d*)\s*亿件'],
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
    
    print(f"✅ 数据已保存: {filepath}")
    
    # 同时保存CSV
    csv_filepath = filepath.replace('.xlsx', '.csv')
    df.to_csv(csv_filepath, index=False, encoding='utf-8-sig')
    print(f"✅ CSV已保存: {csv_filepath}")
    
    return filepath

def extract_value_from_text(text, patterns):
    """从文本中提取数值"""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def crawl_statistical_bulletin():
    """爬取新余市统计公报数据（2023-2025年）"""
    print("\n" + "="*60)
    print("📊 爬取新余市统计公报数据（2023-2025年）")
    print("="*60)
    
    all_data = []
    
    for year, url in BULLETIN_URLS.items():
        if url is None:
            print(f"⚠️ {year}年统计公报尚未发布，跳过")
            continue
        
        print(f"\n正在爬取: 新余市{year}年国民经济和社会发展统计公报")
        
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 获取正文内容
            content_div = soup.find('div', class_='content') or soup.find('div', class_='article-content') or soup.find('article')
            if content_div:
                text_content = content_div.get_text()
            else:
                text_content = response.text
            
            # 提取各项指标
            extracted_count = 0
            
            # 社会消费品零售总额
            value = extract_value_from_text(text_content, INDICATOR_PATTERNS['社会消费品零售总额'])
            if value:
                all_data.append({
                    '年份': year,
                    '业务域': '宏观规模与结构',
                    '一级指标': '1.总量规模',
                    '二级指标': '1.社会消费品零售总额',
                    '数值': value,
                    '单位': '亿元',
                    '数据来源': f'新余市{year}年国民经济和社会发展统计公报',
                    '发布部门': '新余市统计局'
                })
                extracted_count += 1
            
            # 城镇消费品零售额
            value = extract_value_from_text(text_content, INDICATOR_PATTERNS['城镇消费品零售额'])
            if value:
                all_data.append({
                    '年份': year,
                    '业务域': '宏观规模与结构',
                    '一级指标': '1.总量规模',
                    '二级指标': '7.城镇消费品零售额',
                    '数值': value,
                    '单位': '亿元',
                    '数据来源': f'新余市{year}年国民经济和社会发展统计公报',
                    '发布部门': '新余市统计局'
                })
                extracted_count += 1
            
            # 乡村消费品零售额
            value = extract_value_from_text(text_content, INDICATOR_PATTERNS['乡村消费品零售额'])
            if value:
                all_data.append({
                    '年份': year,
                    '业务域': '宏观规模与结构',
                    '一级指标': '1.总量规模',
                    '二级指标': '8.乡村消费品零售额',
                    '数值': value,
                    '单位': '亿元',
                    '数据来源': f'新余市{year}年国民经济和社会发展统计公报',
                    '发布部门': '新余市统计局'
                })
                extracted_count += 1
            
            # 限额以上单位零售额
            value = extract_value_from_text(text_content, INDICATOR_PATTERNS['限上单位消费品零售额'])
            if value:
                all_data.append({
                    '年份': year,
                    '业务域': '宏观规模与结构',
                    '一级指标': '1.总量规模',
                    '二级指标': '2.限上单位消费品零售额',
                    '数值': value,
                    '单位': '亿元',
                    '数据来源': f'新余市{year}年国民经济和社会发展统计公报',
                    '发布部门': '新余市统计局'
                })
                extracted_count += 1
            
            # 城镇居民人均可支配收入
            value = extract_value_from_text(text_content, INDICATOR_PATTERNS['城镇居民人均可支配收入'])
            if value:
                all_data.append({
                    '年份': year,
                    '业务域': '宏观规模与结构',
                    '一级指标': '居民收入',
                    '二级指标': '城镇居民人均可支配收入',
                    '数值': value,
                    '单位': '元',
                    '数据来源': f'新余市{year}年国民经济和社会发展统计公报',
                    '发布部门': '新余市统计局'
                })
                extracted_count += 1
            
            # 农村居民人均可支配收入
            value = extract_value_from_text(text_content, INDICATOR_PATTERNS['农村居民人均可支配收入'])
            if value:
                all_data.append({
                    '年份': year,
                    '业务域': '宏观规模与结构',
                    '一级指标': '居民收入',
                    '二级指标': '农村居民人均可支配收入',
                    '数值': value,
                    '单位': '元',
                    '数据来源': f'新余市{year}年国民经济和社会发展统计公报',
                    '发布部门': '新余市统计局'
                })
                extracted_count += 1
            
            # 城镇居民人均消费支出
            value = extract_value_from_text(text_content, INDICATOR_PATTERNS['城镇居民人均消费支出'])
            if value:
                all_data.append({
                    '年份': year,
                    '业务域': '宏观规模与结构',
                    '一级指标': '居民消费',
                    '二级指标': '城镇居民人均消费支出',
                    '数值': value,
                    '单位': '元',
                    '数据来源': f'新余市{year}年国民经济和社会发展统计公报',
                    '发布部门': '新余市统计局'
                })
                extracted_count += 1
            
            # 农村居民人均消费支出
            value = extract_value_from_text(text_content, INDICATOR_PATTERNS['农村居民人均消费支出'])
            if value:
                all_data.append({
                    '年份': year,
                    '业务域': '宏观规模与结构',
                    '一级指标': '居民消费',
                    '二级指标': '农村居民人均消费支出',
                    '数值': value,
                    '单位': '元',
                    '数据来源': f'新余市{year}年国民经济和社会发展统计公报',
                    '发布部门': '新余市统计局'
                })
                extracted_count += 1
            
            # CPI
            value = extract_value_from_text(text_content, INDICATOR_PATTERNS['居民消费价格指数'])
            if value:
                all_data.append({
                    '年份': year,
                    '业务域': '供应链与营商环境',
                    '一级指标': '25.民生价格',
                    '二级指标': '186.居民消费价格指数（CPI）',
                    '数值': value,
                    '单位': '%',
                    '数据来源': f'新余市{year}年国民经济和社会发展统计公报',
                    '发布部门': '国家统计局新余调查队'
                })
                extracted_count += 1
            
            # GDP
            value = extract_value_from_text(text_content, INDICATOR_PATTERNS['地区生产总值'])
            if value:
                all_data.append({
                    '年份': year,
                    '业务域': '宏观规模与结构',
                    '一级指标': '经济总量',
                    '二级指标': '地区生产总值(GDP)',
                    '数值': value,
                    '单位': '亿元',
                    '数据来源': f'新余市{year}年国民经济和社会发展统计公报',
                    '发布部门': '新余市统计局'
                })
                extracted_count += 1
            
            print(f"  ✅ 提取到 {extracted_count} 条数据")
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ 爬取失败: {str(e)}")
    
    # 保存数据
    if all_data:
        save_to_excel(all_data, '新余市统计公报消费数据_2023-2025.xlsx')
    
    return all_data

def crawl_tourism_data():
    """爬取旅游消费数据"""
    print("\n" + "="*60)
    print("📊 爬取新余市旅游消费数据")
    print("="*60)
    
    all_data = []
    
    # 旅游数据来源URL
    tourism_urls = [
        {
            'url': 'https://jx.ifeng.com/c/8dZJfi0vqiX',
            'name': '国庆假期新余旅游数据',
            'year': '2024'
        },
        {
            'url': 'https://m.huaon.com/channel/distdata/866501.html',
            'name': '新余市旅游年度数据',
            'year': '2021'
        }
    ]
    
    for item in tourism_urls:
        print(f"正在爬取: {item['name']}")
        
        try:
            response = requests.get(item['url'], headers=HEADERS, timeout=30)
            response.encoding = 'utf-8'
            text_content = response.text
            
            # 提取游客人数
            visitor_match = re.search(r'接待游客[^\d]*(\d+\.?\d*)\s*万人次', text_content)
            if visitor_match:
                all_data.append({
                    '年份': item['year'],
                    '业务域': '消费活力与趋势',
                    '一级指标': '18.旅游消费',
                    '二级指标': '131.接待游客总人数',
                    '数值': visitor_match.group(1),
                    '单位': '万人次',
                    '数据来源': item['name'],
                    '发布部门': '新余市文广旅局'
                })
            
            # 提取旅游收入
            income_match = re.search(r'旅游收入[^\d]*(\d+\.?\d*)\s*亿元', text_content)
            if income_match:
                all_data.append({
                    '年份': item['year'],
                    '业务域': '消费活力与趋势',
                    '一级指标': '18.旅游消费',
                    '二级指标': '132.旅游总收入',
                    '数值': income_match.group(1),
                    '单位': '亿元',
                    '数据来源': item['name'],
                    '发布部门': '新余市文广旅局'
                })
            
            print(f"  ✅ 提取到数据")
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ 爬取失败: {str(e)}")
    
    # 保存数据
    if all_data:
        save_to_excel(all_data, '新余市旅游消费数据_2023-2025.xlsx')
    
    return all_data

def crawl_ecommerce_data():
    """爬取电商快递数据"""
    print("\n" + "="*60)
    print("📊 爬取新余市电商快递数据")
    print("="*60)
    
    all_data = []
    
    # 电商快递数据来源
    ecommerce_urls = [
        {
            'url': 'https://jx.ifeng.com/c/8rXiKfanN6b',
            'name': '新余市快递物流数据',
            'year': '2025'
        },
        {
            'url': 'https://jx.ifeng.com/c/8rAZJaDumLs',
            'name': '新余消费市场数据',
            'year': '2024'
        }
    ]
    
    for item in ecommerce_urls:
        print(f"正在爬取: {item['name']}")
        
        try:
            response = requests.get(item['url'], headers=HEADERS, timeout=30)
            response.encoding = 'utf-8'
            text_content = response.text
            
            # 提取快递业务量
            express_match = re.search(r'快递业务量[^\d]*(\d+\.?\d*)\s*亿件', text_content)
            if express_match:
                all_data.append({
                    '年份': item['year'],
                    '业务域': '新消费与新业态',
                    '一级指标': '9.电商直播',
                    '二级指标': '快递业务量',
                    '数值': express_match.group(1),
                    '单位': '亿件',
                    '数据来源': item['name'],
                    '发布部门': '新余市邮政管理局'
                })
            
            # 提取网络零售额
            retail_match = re.search(r'网络零售额[^\d]*(\d+\.?\d*)\s*亿元', text_content)
            if retail_match:
                all_data.append({
                    '年份': item['year'],
                    '业务域': '宏观规模与结构',
                    '一级指标': '2.行业结构',
                    '二级指标': '15.线上消费品零售额',
                    '数值': retail_match.group(1),
                    '单位': '亿元',
                    '数据来源': item['name'],
                    '发布部门': '新余市商务局'
                })
            
            print(f"  ✅ 提取到数据")
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ 爬取失败: {str(e)}")
    
    # 保存数据
    if all_data:
        save_to_excel(all_data, '新余市电商快递数据_2023-2025.xlsx')
    
    return all_data

def crawl_auto_data():
    """爬取汽车消费数据"""
    print("\n" + "="*60)
    print("📊 爬取新余市汽车消费数据")
    print("="*60)
    
    all_data = []
    
    # 汽车数据来源
    auto_urls = [
        {
            'url': 'https://jx.ifeng.com/c/8rtksLV2hZh',
            'name': '新余仙女湖汽车城数据',
            'year': '2024'
        }
    ]
    
    for item in auto_urls:
        print(f"正在爬取: {item['name']}")
        
        try:
            response = requests.get(item['url'], headers=HEADERS, timeout=30)
            response.encoding = 'utf-8'
            text_content = response.text
            
            # 提取汽车销量
            auto_match = re.search(r'年销量[^\d]*(\d+\.?\d*)\s*万辆', text_content)
            if auto_match:
                all_data.append({
                    '年份': item['year'],
                    '业务域': '消费活力与趋势',
                    '一级指标': '20.汽车消费',
                    '二级指标': '151.汽车销量',
                    '数值': auto_match.group(1),
                    '单位': '万辆',
                    '数据来源': item['name'],
                    '发布部门': '新余市商务局'
                })
            
            # 提取新能源汽车销量
            new_energy_match = re.search(r'新能源.*?销量[^\d]*(\d+\.?\d*)\s*辆', text_content)
            if new_energy_match:
                all_data.append({
                    '年份': item['year'],
                    '业务域': '消费活力与趋势',
                    '一级指标': '20.汽车消费',
                    '二级指标': '152.新能源汽车销量',
                    '数值': new_energy_match.group(1),
                    '单位': '辆',
                    '数据来源': item['name'],
                    '发布部门': '新余市商务局'
                })
            
            print(f"  ✅ 提取到数据")
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ 爬取失败: {str(e)}")
    
    # 保存数据
    if all_data:
        save_to_excel(all_data, '新余市汽车消费数据_2023-2025.xlsx')
    
    return all_data

def crawl_price_monitoring_data():
    """爬取价格监测数据"""
    print("\n" + "="*60)
    print("📊 爬取新余市生活必需品价格监测数据")
    print("="*60)
    
    all_data = []
    
    # 商务部价格监测数据
    price_urls = [
        {
            'url': 'https://cif.mofcom.gov.cn/cif/html/inland_month_report//2026/3/1774252158744.html',
            'name': '新余市重要生产资料价格',
            'year': '2026'
        }
    ]
    
    for item in price_urls:
        print(f"正在爬取: {item['name']}")
        
        try:
            response = requests.get(item['url'], headers=HEADERS, timeout=30)
            response.encoding = 'utf-8'
            text_content = response.text
            
            # 提取价格数据（示例）
            soup = BeautifulSoup(text_content, 'html.parser')
            content = soup.get_text()
            
            # 查找价格信息
            price_patterns = [
                (r'成品油.*?价格[^\d]*(\d+\.?\d*)', '成品油价格'),
                (r'钢材.*?价格[^\d]*(\d+\.?\d*)', '钢材价格'),
                (r'化肥.*?价格[^\d]*(\d+\.?\d*)', '化肥价格'),
            ]
            
            for pattern, name in price_patterns:
                match = re.search(pattern, content)
                if match:
                    all_data.append({
                        '年份': item['year'],
                        '业务域': '供应链与营商环境',
                        '一级指标': '25.民生价格',
                        '二级指标': name,
                        '数值': match.group(1),
                        '单位': '元',
                        '数据来源': '商务部商务预报',
                        '发布部门': '新余市商务局'
                    })
            
            print(f"  ✅ 提取到数据")
            time.sleep(1)
            
        except Exception as e:
            print(f"  ❌ 爬取失败: {str(e)}")
    
    # 保存数据
    if all_data:
        save_to_excel(all_data, '新余市价格监测数据_2023-2025.xlsx')
    
    return all_data

def generate_summary_report(all_data_dict):
    """生成数据汇总报告"""
    print("\n" + "="*60)
    print("📊 生成数据汇总报告")
    print("="*60)
    
    # 合并所有数据
    all_data = []
    for category, data_list in all_data_dict.items():
        all_data.extend(data_list)
    
    if not all_data:
        print("⚠️ 无数据可汇总")
        return None
    
    df = pd.DataFrame(all_data)
    
    # 按年份和业务域统计
    summary = df.groupby(['年份', '业务域']).size().reset_index(name='指标数量')
    
    # 保存汇总报告
    filepath = os.path.join(OUTPUT_DIR, '新余市消费数据汇总报告_2023-2025.xlsx')
    
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # 全部数据
        df.to_excel(writer, sheet_name='全部数据', index=False)
        
        # 按年份统计
        year_summary = df.groupby('年份').size().reset_index(name='指标数量')
        year_summary.to_excel(writer, sheet_name='按年份统计', index=False)
        
        # 按业务域统计
        domain_summary = df.groupby('业务域').size().reset_index(name='指标数量')
        domain_summary.to_excel(writer, sheet_name='按业务域统计', index=False)
        
        # 数据来源统计
        source_summary = df.groupby('数据来源').size().reset_index(name='指标数量')
        source_summary.to_excel(writer, sheet_name='按数据来源统计', index=False)
        
        print(f"✅ 汇总报告已保存: {filepath}")
        
        # 同时保存CSV
        csv_filepath = filepath.replace('.xlsx', '.csv')
        df.to_csv(csv_filepath, index=False, encoding='utf-8-sig')
        print(f"✅ CSV汇总已保存: {csv_filepath}")
    
    return summary

def generate_indicator_template():
    """生成指标填报模板"""
    print("\n" + "="*60)
    print("📊 生成指标填报模板")
    print("="*60)
    
    # 读取指标字典
    indicator_file = '/home/z/my-project/upload/69d0a1914cb0fcbae6806c3e_新余市消费运行监测指标体系字典（初稿）.xlsx'
    
    try:
        xl = pd.ExcelFile(indicator_file)
        all_indicators = []
        
        for sheet_name in xl.sheet_names:
            df = pd.read_excel(indicator_file, sheet_name=sheet_name)
            
            current_domain = None
            current_level1 = None
            
            for idx, row in df.iterrows():
                if pd.notna(row.get('业务域')):
                    current_domain = row['业务域']
                if pd.notna(row.get('一级指标')):
                    current_level1 = row['一级指标']
                
                indicator = row.get('二级指标（详细字典内容）', '')
                if pd.notna(indicator):
                    all_indicators.append({
                        '业务域': current_domain,
                        '一级指标': current_level1,
                        '二级指标': indicator,
                        '计算公式': row.get('计算公式', ''),
                        '备注': row.get('备注', ''),
                        '2023年数值': '',
                        '2024年数值': '',
                        '2025年数值': '',
                        '单位': '',
                        '数据来源': '',
                        '发布部门': '',
                        '数据可获取性': '待确认',
                        '备注说明': ''
                    })
        
        # 保存模板
        template_df = pd.DataFrame(all_indicators)
        filepath = os.path.join(OUTPUT_DIR, '新余市消费运行监测指标填报模板.xlsx')
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            template_df.to_excel(writer, sheet_name='指标填报模板', index=False)
            
            # 调整列宽
            worksheet = writer.sheets['指标填报模板']
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
        
        print(f"✅ 指标填报模板已保存: {filepath}")
        print(f"  总指标数: {len(all_indicators)}")
        
        return template_df
        
    except Exception as e:
        print(f"❌ 生成模板失败: {str(e)}")
        return None

def main():
    """主函数"""
    print("\n" + "="*60)
    print("🚀 新余市消费运行监测数据爬取脚本 V2")
    print("📊 基于《新余市消费运行监测指标体系字典（初稿）》")
    print("📅 数据年份: 2023-2025")
    print("="*60)
    print(f"📁 输出目录: {OUTPUT_DIR}")
    print("="*60)
    
    all_data = {}
    
    # 1. 生成指标填报模板
    generate_indicator_template()
    
    # 2. 爬取统计公报数据
    all_data['统计公报'] = crawl_statistical_bulletin()
    
    # 3. 爬取旅游消费数据
    all_data['旅游消费'] = crawl_tourism_data()
    
    # 4. 爬取电商快递数据
    all_data['电商快递'] = crawl_ecommerce_data()
    
    # 5. 爬取汽车消费数据
    all_data['汽车消费'] = crawl_auto_data()
    
    # 6. 爬取价格监测数据
    all_data['价格监测'] = crawl_price_monitoring_data()
    
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
