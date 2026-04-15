#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第三方绩效评估管理平台 - 双端系统
管理端 + 第三方机构端
支持多电脑部署、数据实时同步、账号互通、权限隔离
"""

import streamlit as st
import sqlite3
import pandas as pd
import bcrypt
import os
import json
import base64
import hashlib
import socket
import tempfile
import mimetypes
from datetime import datetime, timedelta
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
import shutil
import re

# ==================== 配置 ====================
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'performance.db')
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

# 创建上传目录
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# 项目分类配置
PROJECT_CATEGORIES = {
    '1': {
        'name': '统计调查研究',
        'subcategories': {
            '1': '多源数据采集',
            '2': '专项调查研究'
        }
    },
    '2': {
        'name': '政府绩效评估',
        'subcategories': {
            '1': '财政绩效评估',
            '2': '行政绩效评估'
        }
    },
    '3': {
        'name': '社会经济咨询',
        'subcategories': {
            '1': '企业管理咨询',
            '2': '公共决策咨询'
        }
    },
    '0': {
        'name': '其他项目',
        'subcategories': {}
    }
}

# 阶段名称
STAGE_NAMES = {
    1: '阶段1: 项目立项',
    2: '阶段2: 方案设计',
    3: '阶段3: 数据采集',
    4: '阶段4: 分析评估',
    5: '阶段5: 方案报告'
}

# 页面配置
st.set_page_config(
    page_title="第三方绩效评估管理平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 自定义样式 ====================
def apply_custom_styles():
    """应用自定义CSS样式"""
    st.markdown('''
    <style>
    /* 主色调 */
    :root {
        --primary-color: #1f77b4;
        --secondary-color: #2ca02c;
        --danger-color: #d62728;
        --warning-color: #ff7f0e;
        --info-color: #17becf;
        --bg-color: #f8f9fa;
        --card-bg: #ffffff;
        --text-color: #333333;
    }
    
    /* 隐藏Streamlit默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 登录页面样式 */
    .login-container {
        max-width: 450px;
        margin: 50px auto;
        padding: 40px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }
    
    .login-title {
        text-align: center;
        color: #000;
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 30px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .login-subtitle {
        text-align: center;
        color: rgba(0,0,0,0.9);
        font-size: 16px;
        margin-bottom: 20px;
    }
    
    /* 卡片样式 */
    .stat-card {
        background: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        text-align: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        cursor: pointer;
    }
    
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    }
    
    .stat-number {
        font-size: 36px;
        font-weight: bold;
        color: #1f77b4;
    }
    
    .stat-label {
        font-size: 14px;
        color: #666;
        margin-top: 5px;
    }
    
    .stat-icon {
        font-size: 40px;
        margin-bottom: 10px;
    }
    
    /* 按钮样式 */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        padding: 12px 24px;
        font-weight: 600;
        transition: all 0.3s ease;
        color: #000 !important;
        background-color: #fff !important;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        color: #000 !important;
    }
    
    /* 数据大盘/模块卡片字体 */
    .stat-card, .stat-card * {
        color: #000 !important;
    }
    
    /* 侧边栏样式 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #000 !important;
    }
    
    /* 表格样式 */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    /* 成功/错误消息 */
    .element-container .stSuccess, .element-container .stError, 
    .element-container .stWarning, .element-container .stInfo {
        border-radius: 10px;
        padding: 15px;
    }
    
    /* 输入框样式 */
    .stTextInput>div>div>input, .stSelectbox>div>div>select {
        border-radius: 8px;
    }
    
    /* 文件夹样式 */
    .folder-item {
        padding: 10px 15px;
        margin: 5px 0;
        background: #f8f9fa;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .folder-item:hover {
        background: #e9ecef;
    }
    
    /* 进度条样式 */
    .stProgress > div > div > div {
        border-radius: 10px;
    }
    
    /* 标签页样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 10px 20px;
    }
    
    /* 徽章样式 */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    
    .badge-success { background: #d4edda; color: #155724; }
    .badge-warning { background: #fff3cd; color: #856404; }
    .badge-danger { background: #f8d7da; color: #721c24; }
    .badge-info { background: #d1ecf1; color: #0c5460; }
    
    /* 滚动条样式 */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #c1c1c1;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #a8a8a8;
    }
    </style>
    ''', unsafe_allow_html=True)

# ==================== 数据库初始化 ====================
def init_database():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'org_user',
            org_id INTEGER,
            phone TEXT,
            email TEXT,
            real_name TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(id)
        )
    ''')
    
    # 机构表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            org_type TEXT,
            credit_code TEXT UNIQUE,
            legal_person TEXT,
            contact_person TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            address TEXT,
            description TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 项目表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            org_id INTEGER NOT NULL,
            category TEXT,
            subcategory TEXT,
            description TEXT,
            current_stage INTEGER DEFAULT 1,
            status TEXT DEFAULT 'pending',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    
    # 项目阶段表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            stage INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            submitted_by INTEGER,
            submitted_at TIMESTAMP,
            reviewed_by INTEGER,
            reviewed_at TIMESTAMP,
            review_comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (submitted_by) REFERENCES users(id),
            FOREIGN KEY (reviewed_by) REFERENCES users(id)
        )
    ''')
    
    # 项目文件表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            step_id INTEGER,
            title TEXT NOT NULL,
            file_type TEXT,
            category TEXT,
            subcategory TEXT,
            file_path TEXT,
            file_name TEXT,
            file_size INTEGER,
            publish_org TEXT,
            description TEXT,
            upload_by INTEGER,
            upload_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approval_status TEXT DEFAULT 'pending',
            approved_by INTEGER,
            approved_at TIMESTAMP,
            approval_comment TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (step_id) REFERENCES project_steps(id),
            FOREIGN KEY (upload_by) REFERENCES users(id)
        )
    ''')
    
    # 主评人表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            title TEXT,
            specialty TEXT,
            phone TEXT,
            email TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(id)
        )
    ''')
    
    # 业绩记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            achievement_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(id)
        )
    ''')
    
    # 培训记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trainings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            trainer TEXT,
            training_date DATE,
            duration INTEGER,
            participants INTEGER,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(id)
        )
    ''')
    
    # 指标库表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indicator_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            subcategory TEXT,
            indicator_name TEXT NOT NULL,
            weight REAL DEFAULT 10,
            description TEXT,
            max_score INTEGER DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 政策文件表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS policy_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            file_path TEXT,
            file_name TEXT,
            file_size INTEGER,
            upload_by INTEGER,
            upload_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (upload_by) REFERENCES users(id)
        )
    ''')
    
    # 待办事项表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            due_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 消息通知表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            msg_type TEXT DEFAULT 'system',
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 操作日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            org_name TEXT,
            action TEXT,
            module TEXT,
            ip_address TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 文件评估表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            indicator_id INTEGER NOT NULL,
            score REAL,
            comment TEXT,
            evaluated_by INTEGER,
            evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES project_files(id),
            FOREIGN KEY (indicator_id) REFERENCES indicator_library(id),
            FOREIGN KEY (evaluated_by) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    
    # 初始化默认数据
    init_default_data(conn)
    
    conn.close()

def init_default_data(conn):
    """初始化默认数据"""
    cursor = conn.cursor()
    
    # 检查是否已有超级管理员
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'super_admin'")
    if cursor.fetchone()[0] == 0:
        # 创建超级管理员
        password_hash = bcrypt.hashpw("Admin@123456".encode('utf-8'), bcrypt.gensalt())
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, real_name, status)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', password_hash, 'super_admin', '超级管理员', 'active'))
    
    # 初始化指标库（每类10个默认指标）
    cursor.execute("SELECT COUNT(*) FROM indicator_library")
    if cursor.fetchone()[0] == 0:
        default_indicators = []
        for cat_key, cat_val in PROJECT_CATEGORIES.items():
            if cat_key == '0':
                continue
            for sub_key, sub_name in cat_val['subcategories'].items():
                for i in range(1, 11):
                    indicator_name = f"{sub_name}指标{i}"
                    default_indicators.append((cat_key, sub_key, indicator_name, 10, f"{indicator_name}描述", 100))
        
        cursor.executemany('''
            INSERT INTO indicator_library (category, subcategory, indicator_name, weight, description, max_score)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', default_indicators)
    
    conn.commit()

# ==================== 数据库操作 ====================
def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(query, params=(), fetch=False, commit=False):
    """执行数据库查询"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        if commit:
            conn.commit()
            return cursor.lastrowid
        if fetch:
            columns = [description[0] for description in cursor.description]
            results = cursor.fetchall()
            return [dict(zip(columns, row)) for row in results]
        return cursor
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def add_log(user_id, username, org_name, action, module, details, ip_address=""):
    """添加操作日志"""
    # 使用系统本地时间作为日志时间，避免 SQLite 的 CURRENT_TIMESTAMP 返回 UTC
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    execute_query('''
        INSERT INTO logs (user_id, username, org_name, action, module, ip_address, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, org_name, action, module, ip_address, details, created_at), commit=True)

def add_message(user_id, title, content, msg_type='system'):
    """添加消息通知"""
    execute_query('''
        INSERT INTO messages (user_id, title, content, msg_type)
        VALUES (?, ?, ?, ?)
    ''', (user_id, title, content, msg_type), commit=True)

def add_todo(user_id, title, content, priority='medium', due_date=None):
    """添加待办事项"""
    execute_query('''
        INSERT INTO todos (user_id, title, content, priority, due_date)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, title, content, priority, due_date), commit=True)

# ==================== 认证系统 ====================
def authenticate_user(login_id, password):
    """用户认证（支持用户名/手机号/邮箱登录）"""
    user = execute_query('''
        SELECT * FROM users 
        WHERE (username = ? OR phone = ? OR email = ?) AND status = 'active'
    ''', (login_id, login_id, login_id), fetch=True)
    
    if user and bcrypt.checkpw(password.encode('utf-8'), user[0]['password_hash']):
        return user[0]
    return None

def get_client_ip():
    """获取客户端IP地址"""
    try:
        return socket.gethostbyname(socket.gethostname())
    except:
        return "unknown"

def hash_password(password):
    """密码加密"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, password_hash):
    """验证密码"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash)

# ==================== 文件操作 ====================
def save_uploaded_file(uploaded_file, subfolder="", project_id=None):
    """保存上传的文件"""
    if uploaded_file is None:
        return None, None, 0
    
    # 创建子文件夹
    save_dir = os.path.join(UPLOAD_DIR, subfolder) if subfolder else UPLOAD_DIR
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # 生成唯一文件名，带项目ID前缀（如提供）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(uploaded_file.name)[1]
    base_name = uploaded_file.name
    if project_id:
        file_name = f"{project_id}_{timestamp}_{base_name}"
    else:
        file_name = f"{timestamp}_{base_name}"
    file_path = os.path.join(save_dir, file_name)
    
    # 保存文件
    with open(file_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path, file_name, uploaded_file.size

def get_file_content(file_path, file_name):
    """获取文件内容用于预览"""
    if not os.path.exists(file_path):
        return None, None
    
    file_ext = os.path.splitext(file_name)[1].lower()
    
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    mime_type, _ = mimetypes.guess_type(file_name)
    if mime_type is None:
        mime_type = 'application/octet-stream'
    
    return file_content, mime_type


def safe_fname(name: str) -> str:
    """生成文件/文件夹安全名称，保留中文、字母和数字，其他替换为下划线"""
    if not name:
        return "unnamed"
    return re.sub(r"[^0-9A-Za-z\u4e00-\u9fa5_-]", "_", name)


def ensure_project_export_dirs_and_copy(project_id):
    """为项目创建 1_<项目名>,2_<项目名>,3_<项目名> 目录并复制已通过的文件到对应目录。
    返回字典：{'base': base_dir, 'copied': n, 'failed': m, 'paths': [...]}
    """
    try:
        proj_rows = execute_query("SELECT * FROM projects WHERE id = ?", (project_id,), fetch=True)
        if not proj_rows:
            return None
        proj = proj_rows[0]
        safe_name = safe_fname(proj.get('name') or f"proj_{project_id}")

        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
        if not os.path.exists(base_dir):
            os.makedirs(base_dir, exist_ok=True)

        dest_dirs = {}
        for i in (1,2,3):
            d = os.path.join(base_dir, f"{i}_{safe_name}")
            os.makedirs(d, exist_ok=True)
            dest_dirs[i] = d

        other_dir = os.path.join(base_dir, f"other_{safe_name}")
        os.makedirs(other_dir, exist_ok=True)

        # 查询已通过的文件并按所属阶段复制
        rows = execute_query(
            "SELECT pf.*, ps.stage as stage FROM project_files pf LEFT JOIN project_steps ps ON pf.step_id = ps.id WHERE pf.project_id = ? AND pf.approval_status = 'approved'",
            (project_id,), fetch=True
        )

        copied = 0
        failed = 0
        paths = []
        for r in rows or []:
            src = r.get('file_path') or os.path.join(UPLOAD_DIR, r.get('file_name') or '')
            if not src or not os.path.exists(src):
                failed += 1
                continue
            stage = r.get('stage')
            if stage in (1,2,3):
                dest = os.path.join(dest_dirs[stage], r.get('file_name'))
            else:
                dest = os.path.join(other_dir, r.get('file_name'))
            try:
                shutil.copy2(src, dest)
                copied += 1
                paths.append(dest)
            except Exception:
                failed += 1

        return {'base': base_dir, 'copied': copied, 'failed': failed, 'paths': paths, 'proj_name': proj.get('name')}
    except Exception:
        return None

def display_file_preview(file_path, file_name):
    """显示文件预览"""
    if not os.path.exists(file_path):
        st.warning("文件不存在")
        return

    # safe_fname & ensure_project_export_dirs_and_copy 已移动到模块作用域

    file_ext = os.path.splitext(file_name)[1].lower()

    try:
        file_size = os.path.getsize(file_path)
    except Exception:
        file_size = 0

    # 严格限制内联预览阈值以避免冻结：PDF <=1MB, 文本 <=512KB, Excel <=1MB
    if file_ext == '.pdf':
        if file_size > 1 * 1024 * 1024:
            st.warning("PDF 文件较大，已切换为下载以避免卡顿。")
            with open(file_path, 'rb') as f:
                st.download_button(label="📥 下载 PDF", data=f, file_name=file_name, mime='application/pdf')
            return
        # 文件较小，尝试内联预览
        try:
            with open(file_path, 'rb') as f:
                base64_pdf = base64.b64encode(f.read()).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)
        except Exception:
            st.warning("无法在浏览器中预览该PDF，提供下载。")
            with open(file_path, 'rb') as f:
                st.download_button(label="📥 下载 PDF", data=f, file_name=file_name, mime='application/pdf')
        return
    
    elif file_ext in ['.txt', '.md']:
        # 对于较大的文本文件，避免一次性读取到内存中导致卡顿
        if file_size > 512 * 1024:
            st.warning("文本文件较大，已切换为下载以避免卡顿。")
            with open(file_path, 'rb') as f:
                st.download_button(label="📥 下载文件", data=f, file_name=file_name)
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            st.text_area("文件内容", content, height=400)
        return
    
    elif file_ext in ['.xlsx', '.xls']:
        # 对于较大的 Excel 文件，避免读取到内存导致卡顿；提供下载
        if file_size > 1 * 1024 * 1024:
            st.warning("Excel 文件较大，已切换为下载以避免卡顿。")
            with open(file_path, 'rb') as f:
                st.download_button(label="📥 下载 Excel", data=f, file_name=file_name, mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            return
        try:
            df = pd.read_excel(file_path)
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"无法读取Excel文件: {e}")
        return
    
    elif file_ext in ['.docx', '.doc']:
        st.info("Word文件预览功能需要安装python-docx库，请下载后查看")
        with open(file_path, 'rb') as f:
            st.download_button(
                label="📥 下载文件",
                data=f,
                file_name=file_name,
                mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
    else:
        with open(file_path, 'rb') as f:
            st.download_button(
                label="📥 下载文件",
                data=f,
                file_name=file_name
            )

# ==================== 登录页面 ====================
def render_login_page():
    """渲染登录页面"""
    apply_custom_styles()
    
    # 登录容器
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    # 标题
    st.markdown('''
        <div class="login-title">📊 第三方绩效评估管理平台</div>
        <div class="login-subtitle">Third-party Performance Evaluation Management Platform</div>
    ''', unsafe_allow_html=True)
    
    # 客户端类型选择
    client_type = st.selectbox(
        "🖥️ 客户端类型",
        options=["auto", "admin", "org"],
        format_func=lambda x: {
            "auto": "🔄 自动识别",
            "admin": "🏢 管理端",
            "org": "🏛️ 机构端"
        }[x],
        key="client_type_select"
    )
    
    st.markdown("---")
    
    # 登录表单
    with st.form("login_form"):
        login_id = st.text_input("👤 用户名/手机号/邮箱", placeholder="请输入用户名、手机号或邮箱")
        password = st.text_input("🔑 密码", type="password", placeholder="请输入密码")
        
        submit = st.form_submit_button("🔐 登录", use_container_width=True)
        
        if submit:
            if not login_id or not password:
                st.error("请填写完整的登录信息")
            else:
                user = authenticate_user(login_id, password)
                
                if user:
                    # 根据客户端类型验证
                    if client_type == "admin" and user['role'] != 'super_admin':
                        st.error("该账号无权访问管理端")
                    elif client_type == "org" and user['role'] == 'super_admin':
                        st.error("超级管理员请选择管理端登录")
                    else:
                        # 登录成功
                        st.session_state['logged_in'] = True
                        st.session_state['user'] = dict(user)
                        st.session_state['current_page'] = 'dashboard'
                        
                        # 获取机构名称
                        org_name = ""
                        if user['org_id']:
                            org = execute_query("SELECT name FROM organizations WHERE id = ?", (user['org_id'],), fetch=True)
                            if org:
                                org_name = org[0]['name']
                        
                        # 记录登录日志
                        add_log(user['id'], user['username'], org_name, '登录', 'auth', '用户登录成功', get_client_ip())
                        
                        # 添加登录消息
                        add_message(user['id'], '登录成功', f'您于{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}成功登录系统')
                        
                        st.rerun()
                else:
                    st.error("用户名或密码错误，或账号已被冻结")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 底部信息
    st.markdown('''
        <div style="text-align: center; margin-top: 30px; color: #666;">
            <p>© 2026 第三方绩效评估管理平台 | 技术支持</p>
        </div>
    ''', unsafe_allow_html=True)

# ==================== 侧边栏 ====================
def render_sidebar():
    """渲染侧边栏"""
    user = st.session_state['user']
    role = user['role']
    
    with st.sidebar:
        # 用户信息
        st.markdown(f"""
        <div style="text-align: center; padding: 20px; background: rgba(255,255,255,0.1); border-radius: 10px; margin-bottom: 20px;">
            <div style="font-size: 40px; margin-bottom: 10px;">👤</div>
            <div style="color: #000; font-weight: bold; font-size: 16px;">{user.get('real_name') or user['username']}</div>
            <div style="color: rgba(0,0,0,0.7); font-size: 12px;">{'超级管理员' if role == 'super_admin' else ('机构主账号' if role == 'org_admin' else '机构子账号')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 导航菜单
        if role == 'super_admin':
            menu_items = [
                ("📊", "数据大盘", "dashboard"),
                ("🏢", "机构管理", "organizations"),
                ("👥", "账号管理", "users"),
                ("📋", "项目审核", "projects"),
                ("📝", "日志查看", "logs"),
                ("📥", "数据导出", "export"),
                ("✅", "审批待办", "approval"),
                ("📨", "消息通知", "messages"),
                ("📚", "项目智库", "indicators"),
                ("📈", "可视化大屏", "visualization"),
            ]
        else:
            menu_items = [
                ("🏠", "工作台", "dashboard"),
                ("🏢", "信息维护", "info"),
                ("👥", "子账号管理", "sub_accounts"),
                ("📋", "项目管理", "projects"),
                ("📚", "项目智库", "knowledge"),
                ("✅", "待办事项", "todos"),
                ("📨", "消息通知", "messages"),
            ]

        # 实时计数：待审批（阶段 + 文件）与未读消息
        try:
            pending_approvals = execute_query("SELECT COUNT(*) as cnt FROM project_steps WHERE status = 'pending'", fetch=True)[0]['cnt']
        except Exception:
            pending_approvals = 0
        try:
            pending_files = execute_query("SELECT COUNT(*) as cnt FROM project_files WHERE approval_status = 'pending'", fetch=True)[0]['cnt']
        except Exception:
            pending_files = 0
        pending_total = (pending_approvals or 0) + (pending_files or 0)

        try:
            msg_unread = execute_query("SELECT COUNT(*) as cnt FROM messages WHERE user_id = ? AND is_read = 0", (user['id'],), fetch=True)[0]['cnt']
        except Exception:
            msg_unread = 0

        # 渲染菜单，使用两列：按钮 + 气泡计数
        for icon, name, page in menu_items:
            col_a, col_b = st.columns([8, 1])
            with col_a:
                if st.button(f"{icon} {name}", key=f"nav_{page}", use_container_width=True):
                    st.session_state['current_page'] = page
                    st.rerun()
            with col_b:
                badge_count = 0
                if page == 'approval':
                    badge_count = pending_total
                elif page == 'messages':
                    badge_count = msg_unread

                if badge_count and badge_count > 0:
                    # 缩小间距并拉近到按钮侧边
                    st.markdown(f"<div style=\"background:#ff4d4f;color:#fff;border-radius:999px;padding:4px 8px;text-align:center;font-weight:700;margin-left:-18px;line-height:20px;\">{badge_count}</div>", unsafe_allow_html=True)
                else:
                    st.markdown("", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 修改密码 & 退出登录（调整为与菜单按钮一致的宽度）
        col_a, col_b = st.columns([8,1])
        with col_a:
            if st.button("🔑 修改密码", key="change_pwd_btn"):
                st.session_state['show_change_pwd'] = True
        with col_b:
            st.markdown("", unsafe_allow_html=True)

        col_c, col_d = st.columns([8,1])
        with col_c:
            if st.button("🚪 退出登录", key="logout_btn"):
                user = st.session_state.get('user', {})
                org_name = ""
                if user.get('org_id'):
                    org = execute_query("SELECT name FROM organizations WHERE id = ?", (user['org_id'],), fetch=True)
                    if org:
                        org_name = org[0]['name']
                add_log(user.get('id'), user.get('username'), org_name, '退出登录', 'auth', '用户退出登录', get_client_ip())
                st.session_state.clear()
                st.rerun()
        with col_d:
            st.markdown("", unsafe_allow_html=True)
        
        # 修改密码弹窗
        if st.session_state.get('show_change_pwd'):
            render_change_password_modal()

def render_change_password_modal():
    """修改密码弹窗"""
    st.markdown("### 🔑 修改密码")
    
    user = st.session_state['user']
    
    with st.form("change_pwd_form"):
        old_pwd = st.text_input("原密码", type="password")
        new_pwd = st.text_input("新密码", type="password")
        confirm_pwd = st.text_input("确认新密码", type="password")
        
        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("确认修改", use_container_width=True)
        with col2:
            cancel = st.form_submit_button("取消", use_container_width=True)
        
        if cancel:
            st.session_state['show_change_pwd'] = False
            st.rerun()
        
        if submit:
            if not old_pwd or not new_pwd or not confirm_pwd:
                st.error("请填写所有字段")
            elif new_pwd != confirm_pwd:
                st.error("两次输入的新密码不一致")
            elif len(new_pwd) < 6:
                st.error("新密码长度不能少于6位")
            else:
                # 验证原密码
                current_user = execute_query("SELECT * FROM users WHERE id = ?", (user['id'],), fetch=True)
                if current_user and check_password(old_pwd, current_user[0]['password_hash']):
                    # 更新密码
                    new_hash = hash_password(new_pwd)
                    execute_query("UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?", 
                                (new_hash, datetime.now(), user['id']), commit=True)
                    
                    org_name = ""
                    if user.get('org_id'):
                        org = execute_query("SELECT name FROM organizations WHERE id = ?", (user['org_id'],), fetch=True)
                        if org:
                            org_name = org[0]['name']
                    
                    add_log(user['id'], user['username'], org_name, '修改密码', 'auth', '用户修改密码成功', get_client_ip())
                    add_message(user['id'], '密码修改成功', f'您于{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}成功修改密码')
                    
                    st.success("密码修改成功")
                    st.session_state['show_change_pwd'] = False
                    st.rerun()
                else:
                    st.error("原密码错误")

# ==================== 管理端页面 ====================
def render_admin_dashboard():
    """管理端数据大盘"""
    st.title("📊 数据大盘")
    
    # 统计数据
    # 机构总数
    org_count = execute_query("SELECT COUNT(*) as cnt FROM organizations", fetch=True)[0]['cnt']
    
    # 用户总数
    user_count = execute_query("SELECT COUNT(*) as cnt FROM users WHERE status = 'active'", fetch=True)[0]['cnt']
    
    # 进行中的项目（启用的机构下的项目）
    active_projects = execute_query('''
        SELECT COUNT(*) as cnt FROM projects p
        JOIN organizations o ON p.org_id = o.id
        WHERE o.status = 'active' AND p.status IN ('pending', 'in_progress')
    ''', fetch=True)[0]['cnt']
    
    # 已完成的项目（停用的机构下项目数量）
    completed_projects = execute_query('''
        SELECT COUNT(*) as cnt FROM projects p
        JOIN organizations o ON p.org_id = o.id
        WHERE o.status = 'inactive' AND p.status = 'completed'
    ''', fetch=True)[0]['cnt']
    
    # 待审批数量
    pending_approvals = execute_query('''
        SELECT COUNT(*) as cnt FROM project_steps WHERE status = 'pending'
    ''', fetch=True)[0]['cnt']
    
    pending_files = execute_query('''
        SELECT COUNT(*) as cnt FROM project_files WHERE approval_status = 'pending'
    ''', fetch=True)[0]['cnt']
    
    # 统计卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card" onclick="window.parent.postMessage({{type: 'streamlit:setComponentValue', value: 'organizations'}}, '*')">
            <div class="stat-icon">🏢</div>
            <div class="stat-number">{org_count}</div>
            <div class="stat-label">机构总数</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("查看机构", key="goto_orgs", use_container_width=True):
            st.session_state['current_page'] = 'organizations'
            st.rerun()
    
    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">👥</div>
            <div class="stat-number">{user_count}</div>
            <div class="stat-label">用户总数</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("查看用户", key="goto_users", use_container_width=True):
            st.session_state['current_page'] = 'users'
            st.rerun()
    
    with col3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">📈</div>
            <div class="stat-number">{active_projects}</div>
            <div class="stat-label">进行中项目</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("查看项目", key="goto_projects", use_container_width=True):
            st.session_state['current_page'] = 'projects'
            st.rerun()
    
    with col4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-icon">✅</div>
            <div class="stat-number">{completed_projects}</div>
            <div class="stat-label">已完成项目</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 待办提醒
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⏳ 待处理事项")
        if pending_approvals + pending_files > 0:
            st.warning(f"待审批项目阶段: {pending_approvals} 个")
            st.warning(f"待审批项目文件: {pending_files} 个")
            if st.button("去处理审批", key="goto_approval", use_container_width=True):
                st.session_state['current_page'] = 'approval'
                st.rerun()
        else:
            st.success("暂无待处理事项")
    
    with col2:
        st.subheader("📊 项目状态分布")
        
        # 项目状态统计
        status_data = execute_query('''
            SELECT status, COUNT(*) as cnt FROM projects GROUP BY status
        ''', fetch=True)
        
        if status_data:
            df = pd.DataFrame(status_data)
            status_map = {'pending': '待审核', 'in_progress': '进行中', 'completed': '已完成', 'rejected': '已驳回'}
            df['status_name'] = df['status'].map(status_map)
            
            fig = px.pie(df, values='cnt', names='status_name', 
                        color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无项目数据")
    
    # 最近活动
    st.subheader("📋 最近活动")
    recent_logs = execute_query('''
        SELECT * FROM logs ORDER BY created_at DESC LIMIT 10
    ''', fetch=True)
    
    if recent_logs:
        df = pd.DataFrame(recent_logs)
        df = df[['id', 'username', 'org_name', 'action', 'module', 'ip_address', 'created_at']]
        df.columns = ['日志ID', '用户名', '机构名', '操作', '模块', 'IP地址', '操作时间']
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无活动记录")

def render_admin_organizations():
    """管理端机构管理"""
    st.title("🏢 机构管理")
    
    tab1, tab2 = st.tabs(["机构列表", "新增机构"])
    
    with tab1:
        # 搜索和筛选
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            search = st.text_input("搜索机构", placeholder="输入机构名称或信用代码")
        with col2:
            status_filter = st.selectbox("状态筛选", ["全部", "active", "inactive"], format_func=lambda x: {"全部": "全部", "active": "启用", "inactive": "停用"}.get(x, x))
        with col3:
            st.write("")  # 占位
        
        # 查询机构列表
        query = '''
            SELECT o.*, 
                   (SELECT COUNT(*) FROM users WHERE org_id = o.id) as user_count,
                   (SELECT COUNT(*) FROM projects WHERE org_id = o.id) as project_count
            FROM organizations o WHERE 1=1
        '''
        params = []
        
        if search:
            query += " AND (o.name LIKE ? OR o.credit_code LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])
        
        if status_filter != "全部":
            query += " AND o.status = ?"
            params.append(status_filter)
        
        query += " ORDER BY o.created_at DESC"
        
        orgs = execute_query(query, params, fetch=True)
        
        if orgs:
            for org in orgs:
                with st.expander(f"**{org['name']}** ({'启用' if org['status'] == 'active' else '停用'})"):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        st.write(f"**机构类型:** {org['org_type'] or '-'}")
                        st.write(f"**统一社会信用代码:** {org['credit_code'] or '-'}")
                        st.write(f"**法定代表人:** {org['legal_person'] or '-'}")
                        st.write(f"**联系人:** {org['contact_person'] or '-'}")
                    
                    with col2:
                        st.write(f"**联系电话:** {org['contact_phone'] or '-'}")
                        st.write(f"**联系邮箱:** {org['contact_email'] or '-'}")
                        st.write(f"**机构地址:** {org['address'] or '-'}")
                        st.write(f"**创建时间:** {org['created_at']}")
                    
                    with col3:
                        st.write(f"**用户数:** {org['user_count']}")
                        st.write(f"**项目数:** {org['project_count']}")
                    
                    if org['description']:
                        st.write(f"**机构简介:** {org['description']}")
                    
                    # 操作按钮
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if org['status'] == 'active':
                            if st.button("⏸️ 停用", key=f"deactivate_{org['id']}"):
                                execute_query("UPDATE organizations SET status = 'inactive', updated_at = ? WHERE id = ?", 
                                            (datetime.now(), org['id']), commit=True)
                                st.success("机构已停用")
                                st.rerun()
                        else:
                            if st.button("▶️ 启用", key=f"activate_{org['id']}"):
                                execute_query("UPDATE organizations SET status = 'active', updated_at = ? WHERE id = ?", 
                                            (datetime.now(), org['id']), commit=True)
                                st.success("机构已启用")
                                st.rerun()
                    
                    with col2:
                        if st.button("✏️ 编辑", key=f"edit_{org['id']}"):
                            st.session_state['edit_org_id'] = org['id']
                            st.rerun()
                    
                    with col3:
                        if st.button("🔑 重置密码", key=f"reset_pwd_{org['id']}"):
                            # 获取机构主账号
                            main_user = execute_query("SELECT * FROM users WHERE org_id = ? AND role = 'org_admin'", 
                                                     (org['id'],), fetch=True)
                            if main_user:
                                new_hash = hash_password("Org@123456")
                                execute_query("UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?", 
                                            (new_hash, datetime.now(), main_user[0]['id']), commit=True)
                                st.success("密码已重置为: Org@123456")
                            else:
                                st.warning("未找到机构主账号")
                    
                    with col4:
                        if st.button("🗑️ 删除", key=f"delete_{org['id']}"):
                            # 检查是否有关联数据
                            if org['user_count'] > 0 or org['project_count'] > 0:
                                st.error("该机构下有用户或项目，无法删除")
                            else:
                                execute_query("DELETE FROM organizations WHERE id = ?", (org['id'],), commit=True)
                                execute_query("DELETE FROM users WHERE org_id = ?", (org['id'],), commit=True)
                                st.success("机构已删除")
                                st.rerun()
        else:
            st.info("暂无机构数据")
    
    # 如果从列表点击编辑机构，展示编辑表单（优先于新增机构）
    if st.session_state.get('edit_org_id'):
        edit_id = st.session_state.get('edit_org_id')
        org_row = execute_query("SELECT * FROM organizations WHERE id = ?", (edit_id,), fetch=True)
        if org_row:
            org_obj = org_row[0]
            st.subheader(f"编辑机构: {org_obj.get('name')}")
            with st.form("edit_org_form"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("机构名称 *", value=org_obj.get('name') or "")
                    org_type = st.selectbox("机构类型 *", ["企业", "事业单位", "社会团体", "民办非企业", "其他"], index=0)
                    credit_code = st.text_input("统一社会信用代码 *", value=org_obj.get('credit_code') or "")
                    legal_person = st.text_input("法定代表人 *", value=org_obj.get('legal_person') or "")
                    contact_person = st.text_input("联系人 *", value=org_obj.get('contact_person') or "")
                with col2:
                    contact_phone = st.text_input("联系电话 *", value=org_obj.get('contact_phone') or "")
                    contact_email = st.text_input("联系邮箱 *", value=org_obj.get('contact_email') or "")
                    address = st.text_input("机构地址 *", value=org_obj.get('address') or "")
                    description = st.text_area("机构简介", value=org_obj.get('description') or "")
                submit = st.form_submit_button("✅ 保存修改", use_container_width=True)
                cancel = st.form_submit_button("取消", use_container_width=True)
                if cancel:
                    del st.session_state['edit_org_id']
                    st.experimental_rerun()
                if submit:
                    # 基本验证
                    required_fields = [name, org_type, credit_code, legal_person, contact_person, contact_phone, contact_email, address]
                    if not all(required_fields):
                        st.error("请填写所有必填项")
                    else:
                        # 检查信用代码冲突（排除当前机构）
                        existing = execute_query("SELECT id FROM organizations WHERE credit_code = ? AND id != ?", (credit_code, edit_id), fetch=True)
                        if existing:
                            st.error("该统一社会信用代码已被其他机构使用")
                        else:
                            execute_query('''
                                UPDATE organizations SET name = ?, org_type = ?, credit_code = ?, legal_person = ?, contact_person = ?,
                                                   contact_phone = ?, contact_email = ?, address = ?, description = ?, updated_at = ?
                                WHERE id = ?
                            ''', (name, org_type, credit_code, legal_person, contact_person, contact_phone, contact_email, address, description, datetime.now(), edit_id), commit=True)
                            add_log(st.session_state['user']['id'], st.session_state['user']['username'], '', '编辑机构', 'organizations', f'编辑机构: {name}', get_client_ip())
                            st.success("机构信息已更新")
                            del st.session_state['edit_org_id']
                            st.experimental_rerun()
    
    with tab2:
        st.subheader("新增机构")
        
        with st.form("add_org_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("机构名称 *", placeholder="请输入机构名称")
                org_type = st.selectbox("机构类型 *", ["企业", "事业单位", "社会团体", "民办非企业", "其他"])
                credit_code = st.text_input("统一社会信用代码 *", placeholder="请输入18位信用代码")
                legal_person = st.text_input("法定代表人 *", placeholder="请输入法定代表人姓名")
                contact_person = st.text_input("联系人 *", placeholder="请输入联系人姓名")
            
            with col2:
                contact_phone = st.text_input("联系电话 *", placeholder="请输入联系电话")
                contact_email = st.text_input("联系邮箱 *", placeholder="请输入联系邮箱")
                address = st.text_input("机构地址 *", placeholder="请输入机构地址")
                description = st.text_area("机构简介", placeholder="请输入机构简介（选填）")
            
            submit = st.form_submit_button("✅ 创建机构", use_container_width=True)
            
            if submit:
                # 验证必填项
                required_fields = [name, org_type, credit_code, legal_person, contact_person, contact_phone, contact_email, address]
                if not all(required_fields):
                    st.error("请填写所有必填项")
                else:
                    # 检查信用代码是否重复
                    existing = execute_query("SELECT id FROM organizations WHERE credit_code = ?", (credit_code,), fetch=True)
                    if existing:
                        st.error("该统一社会信用代码已存在")
                    else:
                        # 创建机构
                        org_id = execute_query('''
                            INSERT INTO organizations (name, org_type, credit_code, legal_person, contact_person, 
                                                      contact_phone, contact_email, address, description)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (name, org_type, credit_code, legal_person, contact_person, 
                              contact_phone, contact_email, address, description), commit=True)
                        
                        # 创建机构主账号
                        username = f"org_{org_id}"
                        password_hash = hash_password("Org@123456")
                        
                        execute_query('''
                            INSERT INTO users (username, password_hash, role, org_id, real_name, phone, email, status)
                            VALUES (?, ?, 'org_admin', ?, ?, ?, ?, 'active')
                        ''', (username, password_hash, org_id, contact_person, contact_phone, contact_email), commit=True)
                        
                        # 记录日志
                        user = st.session_state['user']
                        add_log(user['id'], user['username'], '', '新增机构', 'organizations', 
                               f'创建机构: {name}', get_client_ip())
                        
                        st.success(f"机构创建成功！主账号: {username}，默认密码: Org@123456")
                        st.rerun()

def render_admin_users():
    """管理端账号管理"""
    st.title("👥 账号管理")
    
    tab1, tab2 = st.tabs(["账号列表", "新增账号"])
    
    with tab1:
        # 筛选
        col1, col2, col3 = st.columns(3)
        with col1:
            search = st.text_input("搜索账号", placeholder="用户名/手机号/邮箱")
        with col2:
            role_filter = st.selectbox("角色筛选", ["全部", "super_admin", "org_admin", "org_user"],
                                       format_func=lambda x: {"全部": "全部", "super_admin": "超级管理员", 
                                                             "org_admin": "机构主账号", "org_user": "机构子账号"}.get(x, x))
        with col3:
            status_filter = st.selectbox("状态筛选", ["全部", "active", "inactive"],
                                        format_func=lambda x: {"全部": "全部", "active": "正常", "inactive": "冻结"}.get(x, x))
        
        # 查询用户列表
        query = '''
            SELECT u.*, o.name as org_name 
            FROM users u 
            LEFT JOIN organizations o ON u.org_id = o.id 
            WHERE 1=1
        '''
        params = []
        
        if search:
            query += " AND (u.username LIKE ? OR u.phone LIKE ? OR u.email LIKE ? OR u.real_name LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])
        
        if role_filter != "全部":
            query += " AND u.role = ?"
            params.append(role_filter)
        
        if status_filter != "全部":
            query += " AND u.status = ?"
            params.append(status_filter)
        
        query += " ORDER BY u.created_at DESC"
        
        users = execute_query(query, params, fetch=True)
        
        if users:
            for user in users:
                role_names = {'super_admin': '超级管理员', 'org_admin': '机构主账号', 'org_user': '机构子账号'}
                status_names = {'active': '正常', 'inactive': '冻结'}
                
                with st.expander(f"**{user['username']}** - {role_names.get(user['role'], user['role'])} ({status_names.get(user['status'], user['status'])})"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write(f"**姓名:** {user['real_name'] or '-'}")
                        st.write(f"**手机号:** {user['phone'] or '-'}")
                        st.write(f"**邮箱:** {user['email'] or '-'}")
                    
                    with col2:
                        st.write(f"**所属机构:** {user['org_name'] or '-'}")
                        st.write(f"**创建时间:** {user['created_at']}")
                    
                    with col3:
                        st.write(f"**角色:** {role_names.get(user['role'], user['role'])}")
                        st.write(f"**状态:** {status_names.get(user['status'], user['status'])}")
                    
                    # 操作按钮
                    if user['role'] != 'super_admin':
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            if user['status'] == 'active':
                                if st.button("🔒 冻结", key=f"freeze_{user['id']}"):
                                    execute_query("UPDATE users SET status = 'inactive' WHERE id = ?", (user['id'],), commit=True)
                                    st.success("账号已冻结")
                                    st.rerun()
                            else:
                                if st.button("🔓 解冻", key=f"unfreeze_{user['id']}"):
                                    execute_query("UPDATE users SET status = 'active' WHERE id = ?", (user['id'],), commit=True)
                                    st.success("账号已解冻")
                                    st.rerun()
                        
                        with col2:
                            if st.button("🔑 重置密码", key=f"resetpwd_{user['id']}"):
                                new_hash = hash_password("Reset@123456")
                                execute_query("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user['id']), commit=True)
                                st.success("密码已重置为: Reset@123456")
                        
                        with col3:
                            if st.button("✏️ 编辑", key=f"edituser_{user['id']}"):
                                st.session_state['edit_user_id'] = user['id']
                                st.rerun()
                        
                        with col4:
                            if st.button("🗑️ 删除", key=f"deleteuser_{user['id']}"):
                                execute_query("DELETE FROM users WHERE id = ?", (user['id'],), commit=True)
                                st.success("账号已删除")
                                st.rerun()
        else:
            st.info("暂无账号数据")
    
    with tab2:
        st.subheader("新增账号")
        
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("用户名 *", placeholder="请输入用户名")
                new_real_name = st.text_input("姓名 *", placeholder="请输入姓名")
                new_phone = st.text_input("手机号 *", placeholder="请输入手机号")
                new_email = st.text_input("邮箱 *", placeholder="请输入邮箱")
            
            with col2:
                new_role = st.selectbox("角色 *", ["org_admin", "org_user"],
                                       format_func=lambda x: {"org_admin": "机构主账号", "org_user": "机构子账号"}[x])
                
                # 获取机构列表
                orgs = execute_query("SELECT id, name FROM organizations WHERE status = 'active' ORDER BY name", fetch=True)
                org_options = {f"{o['name']}": o['id'] for o in orgs} if orgs else {}
                
                new_org = st.selectbox("所属机构 *", list(org_options.keys()) if org_options else ["暂无可用机构"])
                new_password = st.text_input("初始密码 *", type="password", placeholder="请输入初始密码")
            
            submit = st.form_submit_button("✅ 创建账号", use_container_width=True)
            
            if submit:
                required_fields = [new_username, new_real_name, new_phone, new_email, new_password]
                if not all(required_fields):
                    st.error("请填写所有必填项")
                elif not org_options:
                    st.error("请先创建机构")
                else:
                    # 检查用户名是否重复
                    existing = execute_query("SELECT id FROM users WHERE username = ? OR phone = ? OR email = ?", 
                                           (new_username, new_phone, new_email), fetch=True)
                    if existing:
                        st.error("用户名、手机号或邮箱已存在")
                    else:
                        password_hash = hash_password(new_password)
                        org_id = org_options.get(new_org)
                        
                        execute_query('''
                            INSERT INTO users (username, password_hash, role, org_id, real_name, phone, email, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
                        ''', (new_username, password_hash, new_role, org_id, new_real_name, new_phone, new_email), commit=True)
                        
                        # 记录日志
                        user = st.session_state['user']
                        add_log(user['id'], user['username'], '', '新增账号', 'users', 
                               f'创建账号: {new_username}', get_client_ip())
                        
                        st.success("账号创建成功")
                        st.rerun()

def render_admin_projects():
    """管理端项目审核"""
    st.title("📋 项目审核")
    
    # 筛选
    col1, col2, col3 = st.columns(3)
    with col1:
        org_filter = st.text_input("机构名称", placeholder="输入机构名称搜索")
    with col2:
        status_filter = st.selectbox("状态筛选", ["全部", "pending", "in_progress", "completed", "rejected"],
                                    format_func=lambda x: {"全部": "全部", "pending": "待审核", "in_progress": "进行中", 
                                                          "completed": "已完成", "rejected": "已驳回"}.get(x, x))
    with col3:
        stage_filter = st.selectbox("阶段筛选", ["全部", 1, 2, 3, 4, 5],
                                   format_func=lambda x: {"全部": "全部", 1: "阶段1", 2: "阶段2", 3: "阶段3", 4: "阶段4", 5: "阶段5"}.get(x, x))
    
    # 查询项目
    query = '''
        SELECT p.*, o.name as org_name, u.username as creator_name
        FROM projects p
        JOIN organizations o ON p.org_id = o.id
        LEFT JOIN users u ON p.created_by = u.id
        WHERE 1=1
    '''
    params = []
    
    if org_filter:
        query += " AND o.name LIKE ?"
        params.append(f"%{org_filter}%")
    
    if status_filter != "全部":
        query += " AND p.status = ?"
        params.append(status_filter)
    
    if stage_filter != "全部":
        query += " AND p.current_stage = ?"
        params.append(stage_filter)
    
    query += " ORDER BY p.created_at DESC"
    
    projects = execute_query(query, params, fetch=True)
    
    if projects:
        for proj in projects:
            status_map = {'pending': '待审核', 'in_progress': '进行中', 'completed': '已完成', 'rejected': '已驳回'}
            
            with st.expander(f"**{proj['name']}** - {proj['org_name']} ({status_map.get(proj['status'], proj['status'])})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**项目ID:** {proj['id']}")
                    st.write(f"**所属机构:** {proj['org_name']}")
                    st.write(f"**项目分类:** {PROJECT_CATEGORIES.get(proj['category'], {}).get('name', '-') if proj['category'] else '-'}")
                    st.write(f"**创建人:** {proj['creator_name'] or '-'}")
                
                with col2:
                    st.write(f"**状态:** {status_map.get(proj['status'], proj['status'])}")
                    current_stage = proj['current_stage']
                    st.write(f"**当前阶段:** {STAGE_NAMES.get(current_stage, f'阶段{current_stage}')}")
                    st.write(f"**创建时间:** {proj['created_at']}")
                
                if proj['description']:
                    st.write(f"**项目描述:** {proj['description']}")
                
                # 阶段详情
                st.subheader("阶段详情")
                
                steps = execute_query('''
                    SELECT ps.*, u.username as submitter_name, r.username as reviewer_name
                    FROM project_steps ps
                    LEFT JOIN users u ON ps.submitted_by = u.id
                    LEFT JOIN users r ON ps.reviewed_by = r.id
                    WHERE ps.project_id = ?
                    ORDER BY ps.stage
                ''', (proj['id'],), fetch=True)
                
                if steps:
                    for step in steps:
                        step_status_map = {'pending': '⏳ 待审核', 'approved': '✅ 已通过', 'rejected': '❌ 已驳回'}
                        
                        step_stage = step['stage']
                        st.markdown(f"**{STAGE_NAMES.get(step_stage, f'阶段{step_stage}')}** - {step_status_map.get(step['status'], step['status'])}")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"提交人: {step['submitter_name'] or '-'}")
                        with col2:
                            st.write(f"提交时间: {step['submitted_at'] or '-'}")
                        with col3:
                            st.write(f"审核人: {step['reviewer_name'] or '-'}")
                        
                        if step['review_comment']:
                            st.write(f"审核意见: {step['review_comment']}")
                        
                        # 查看该阶段的文件
                        step_files = execute_query('''
                            SELECT * FROM project_files WHERE step_id = ?
                        ''', (step['id'],), fetch=True)
                        
                        if step_files:
                            st.write("📁 阶段文件:")
                            for f in step_files:
                                col1, col2, col3 = st.columns([4, 1, 1])
                                with col1:
                                    st.write(f"  - {f['file_name']}")
                                with col2:
                                    if st.button("👁️ 查看", key=f"view_step_file_{f['id']}"):
                                        st.session_state['view_file_id'] = f['id']
                                        st.rerun()
                                with col3:
                                    # 通过 & 驳回按钮（仅在待审批状态显示）
                                    if f.get('approval_status') == 'pending':
                                        if st.button("✅ 通过", key=f"approve_file_{f['id']}"):
                                            execute_query(
                                                "UPDATE project_files SET approval_status = 'approved', approved_by = ?, approved_at = ? WHERE id = ?",
                                                (st.session_state['user']['id'], datetime.now(), f['id']),
                                                commit=True
                                            )
                                            # 发送消息给上传者
                                            add_message(f.get('upload_by'), '文件审核通过', f'您上传的文件"{f.get("title") or f.get("file_name")}"已审核通过')
                                            st.success("文件已通过")
                                            st.rerun()
                                    else:
                                        # 显示当前状态简短标签
                                        st.markdown(f"<div style='font-size:12px;color:#666'>{f.get('approval_status')}</div>", unsafe_allow_html=True)
                                # 驳回原因输入和按钮单独一行以避免布局挤压
                                if f.get('approval_status') == 'pending':
                                    reject_col1, reject_col2 = st.columns([5,1])
                                    with reject_col1:
                                        reason = st.text_input("驳回原因（可选）", key=f"reject_reason_{f['id']}")
                                    with reject_col2:
                                        if st.button("❌ 驳回", key=f"reject_file_{f['id']}"):
                                            if not reason:
                                                st.error("请填写驳回原因")
                                            else:
                                                execute_query(
                                                    "UPDATE project_files SET approval_status = 'rejected', approved_by = ?, approved_at = ?, approval_comment = ? WHERE id = ?",
                                                    (st.session_state['user']['id'], datetime.now(), reason, f['id']),
                                                    commit=True
                                                )
                                                add_message(f.get('upload_by'), '文件审核驳回', f'您上传的文件"{f.get("title") or f.get("file_name")}"被驳回，原因: {reason}')
                                                st.success("已驳回")
                                                st.rerun()
                        
                        # 审核操作
                        if step['status'] == 'pending':
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("✅ 通过", key=f"approve_step_{step['id']}"):
                                    execute_query('''
                                        UPDATE project_steps SET status = 'approved', reviewed_by = ?, reviewed_at = ?, review_comment = '审核通过'
                                        WHERE id = ?
                                    ''', (st.session_state['user']['id'], datetime.now(), step['id']), commit=True)

                                    # 更新 current_stage（如果不是最后阶段）
                                    if step['stage'] < 5:
                                        execute_query('''
                                            UPDATE projects SET current_stage = ?, updated_at = ?
                                            WHERE id = ?
                                        ''', (step['stage'] + 1, datetime.now(), proj['id']), commit=True)

                                    # 刷新项目总体状态（completed/in_progress/rejected）
                                    try:
                                        refresh_project_status(proj['id'])
                                    except Exception:
                                        pass

                                    # 发送消息
                                    add_message(proj['created_by'], '项目阶段审核通过', 
                                              f'您的项目"{proj["name"]}"{STAGE_NAMES.get(step["stage"], "")}已审核通过')

                                    st.success("审核通过")
                                    st.rerun()
                            
                            with col2:
                                comment = st.text_input("驳回原因", key=f"reject_reason_{step['id']}")
                                if st.button("❌ 驳回", key=f"reject_step_{step['id']}"):
                                    if not comment:
                                        st.error("请填写驳回原因")
                                    else:
                                        execute_query('''
                                            UPDATE project_steps SET status = 'rejected', reviewed_by = ?, reviewed_at = ?, review_comment = ?
                                            WHERE id = ?
                                        ''', (st.session_state['user']['id'], datetime.now(), comment, step['id']), commit=True)

                                        # 刷新项目总体状态
                                        try:
                                            refresh_project_status(proj['id'])
                                        except Exception:
                                            pass

                                        add_message(proj['created_by'], '项目阶段审核驳回', 
                                                  f'您的项目"{proj["name"]}"{STAGE_NAMES.get(step["stage"], "")}已被驳回，原因: {comment}')

                                        st.success("已驳回")
                                        st.rerun()
                        
                        st.markdown("---")
                else:
                    st.info("暂无阶段数据")
    else:
        st.info("暂无项目数据")

def render_admin_logs():
    """管理端日志查看"""
    st.title("📝 日志查看")
    
    # 筛选条件
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        username_search = st.text_input("用户名", placeholder="输入用户名")
    
    with col2:
        module_filter = st.selectbox("功能模块", ["全部", "auth", "organizations", "users", "projects", "files", "indicators"],
                                    format_func=lambda x: {"全部": "全部", "auth": "认证", "organizations": "机构管理", 
                                                          "users": "账号管理", "projects": "项目管理", 
                                                          "files": "文件管理", "indicators": "指标管理"}.get(x, x))
    
    with col3:
        time_range = st.selectbox("时间范围", ["全部", "1天", "7天", "30天", "自定义"])
    
    with col4:
        if time_range == "自定义":
            start_date = st.date_input("开始日期")
            end_date = st.date_input("结束日期")
    
    # 构建查询
    query = "SELECT * FROM logs WHERE 1=1"
    params = []
    
    if username_search:
        query += " AND username LIKE ?"
        params.append(f"%{username_search}%")
    
    if module_filter != "全部":
        query += " AND module = ?"
        params.append(module_filter)
    
    if time_range == "1天":
        query += " AND created_at >= datetime('now', '-1 day')"
    elif time_range == "7天":
        query += " AND created_at >= datetime('now', '-7 days')"
    elif time_range == "30天":
        query += " AND created_at >= datetime('now', '-30 days')"
    elif time_range == "自定义":
        query += " AND created_at >= ? AND created_at <= ?"
        params.extend([f"{start_date} 00:00:00", f"{end_date} 23:59:59"])
    
    query += " ORDER BY created_at DESC"
    
    logs = execute_query(query, params, fetch=True)
    
    if logs:
        df = pd.DataFrame(logs)
        df = df[['id', 'username', 'org_name', 'action', 'module', 'ip_address', 'created_at']]
        df.columns = ['日志编号', '用户名', '机构名', '操作', '功能模块', 'IP地址', '操作时间']
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 导出按钮
        if st.button("📥 导出日志"):
            export_to_excel(df, "操作日志")
    else:
        st.info("暂无日志数据")

def render_admin_export():
    """管理端数据导出"""
    st.title("📥 数据导出")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 导出数据")
        
        export_type = st.selectbox("选择导出类型", [
            "用户数据", "机构数据", "项目数据", "项目文件数据", "用户日志数据"
        ])
        
        if st.button("📥 导出Excel", use_container_width=True):
            if export_type == "用户数据":
                data = execute_query('''
                    SELECT u.id, u.username, u.real_name, u.phone, u.email, u.role, o.name as org_name, u.status, u.created_at
                    FROM users u LEFT JOIN organizations o ON u.org_id = o.id
                ''', fetch=True)
                df = pd.DataFrame(data) if data else pd.DataFrame()
                df.columns = ['用户ID', '用户名', '姓名', '手机号', '邮箱', '角色', '所属机构', '状态', '创建时间']
            
            elif export_type == "机构数据":
                data = execute_query('''
                    SELECT id, name, org_type, credit_code, legal_person, contact_person, 
                           contact_phone, contact_email, address, status, created_at
                    FROM organizations
                ''', fetch=True)
                df = pd.DataFrame(data) if data else pd.DataFrame()
                df.columns = ['机构ID', '机构名称', '机构类型', '信用代码', '法定代表人', '联系人', 
                             '联系电话', '联系邮箱', '机构地址', '状态', '创建时间']
            
            elif export_type == "项目数据":
                data = execute_query('''
                    SELECT p.id, p.name, o.name as org_name, p.category, p.subcategory, 
                           p.current_stage, p.status, p.created_at
                    FROM projects p JOIN organizations o ON p.org_id = o.id
                ''', fetch=True)
                df = pd.DataFrame(data) if data else pd.DataFrame()
                df.columns = ['项目ID', '项目名称', '所属机构', '项目分类', '子分类', '当前阶段', '状态', '创建时间']
            
            elif export_type == "项目文件数据":
                data = execute_query('''
                    SELECT pf.id, pf.title, pf.file_name, pf.category, pf.subcategory, 
                           pf.approval_status, u.username as uploader, pf.upload_at
                    FROM project_files pf LEFT JOIN users u ON pf.upload_by = u.id
                ''', fetch=True)
                df = pd.DataFrame(data) if data else pd.DataFrame()
                df.columns = ['文件ID', '文件标题', '文件名', '分类', '子分类', '审批状态', '上传者', '上传时间']
            
            elif export_type == "用户日志数据":
                data = execute_query("SELECT * FROM logs ORDER BY created_at DESC", fetch=True)
                df = pd.DataFrame(data) if data else pd.DataFrame()
                df.columns = ['日志ID', '用户ID', '用户名', '机构名', '操作', '模块', 'IP地址', '详情', '操作时间']
            
            if not df.empty:
                export_to_excel(df, export_type)
            else:
                st.warning("暂无数据可导出")
    
    with col2:
        st.subheader("📥 导入数据")
        
        import_type = st.selectbox("选择导入类型", [
            "用户数据", "机构数据"
        ])
        
        uploaded_file = st.file_uploader("上传Excel文件", type=['xlsx', 'xls'])
        
        if uploaded_file and st.button("📤 导入数据", use_container_width=True):
            try:
                df = pd.read_excel(uploaded_file)
                
                if import_type == "用户数据":
                    for _, row in df.iterrows():
                        password_hash = hash_password("Reset@123456")
                        execute_query('''
                            INSERT OR REPLACE INTO users (username, password_hash, role, real_name, phone, email, status)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (row.get('用户名'), password_hash, row.get('角色', 'org_user'), 
                              row.get('姓名'), row.get('手机号'), row.get('邮箱'), 'active'), commit=True)
                
                elif import_type == "机构数据":
                    for _, row in df.iterrows():
                        execute_query('''
                            INSERT OR REPLACE INTO organizations (name, org_type, credit_code, legal_person, 
                                                                  contact_person, contact_phone, contact_email, address)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (row.get('机构名称'), row.get('机构类型'), row.get('信用代码'), 
                              row.get('法定代表人'), row.get('联系人'), row.get('联系电话'), 
                              row.get('联系邮箱'), row.get('机构地址')), commit=True)
                
                st.success(f"成功导入 {len(df)} 条数据")
            except Exception as e:
                st.error(f"导入失败: {e}")

def export_to_excel(df, filename):
    """导出DataFrame到Excel"""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='数据')
        
        # 获取工作表并设置样式
        workbook = writer.book
        worksheet = writer.sheets['数据']
        
        # 设置列宽
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
    
    output.seek(0)
    
    st.download_button(
        label=f"📥 下载 {filename}.xlsx",
        data=output,
        file_name=f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def render_admin_approval():
    """管理端审批待办"""
    st.title("✅ 审批待办")
    
    tab1, tab2 = st.tabs(["项目阶段审批", "项目文件审批"])
    
    with tab1:
        st.subheader("项目阶段审批")
        
        pending_steps = execute_query('''
            SELECT ps.*, p.name as project_name, o.name as org_name, u.username as submitter
            FROM project_steps ps
            JOIN projects p ON ps.project_id = p.id
            JOIN organizations o ON p.org_id = o.id
            LEFT JOIN users u ON ps.submitted_by = u.id
            WHERE ps.status = 'pending'
            ORDER BY ps.submitted_at ASC
        ''', fetch=True)
        
        if pending_steps:
            for step in pending_steps:
                with st.container():
                    st.markdown(f"""
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin: 10px 0;">
                        <h4>{step['project_name']} - {STAGE_NAMES.get(step['stage'], f'阶段{step["stage"]}')}</h4>
                        <p>所属机构: {step['org_name']} | 提交人: {step['submitter'] or '-'} | 提交时间: {step['submitted_at'] or '-'}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        if st.button("✅ 通过", key=f"approve_{step['id']}", use_container_width=True):
                            execute_query('''
                                UPDATE project_steps SET status = 'approved', reviewed_by = ?, reviewed_at = ?, review_comment = '审核通过'
                                WHERE id = ?
                            ''', (st.session_state['user']['id'], datetime.now(), step['id']), commit=True)
                            
                            # 更新项目
                            if step['stage'] < 5:
                                execute_query('''
                                    UPDATE projects SET current_stage = ?, updated_at = ?
                                    WHERE id = ?
                                ''', (step['stage'] + 1, datetime.now(), step['project_id']), commit=True)

                            # 刷新项目总体状态
                            try:
                                refresh_project_status(step['project_id'])
                            except Exception:
                                pass
                            
                            # 获取项目创建者
                            proj = execute_query("SELECT created_by, name FROM projects WHERE id = ?", (step['project_id'],), fetch=True)
                            if proj:
                                add_message(proj[0]['created_by'], '项目阶段审核通过', 
                                          f'您的项目"{proj[0]["name"]}"{STAGE_NAMES.get(step["stage"], "")}已审核通过')
                            
                            st.success("审核通过")
                            st.rerun()
                    
                    with col2:
                        reject_reason = st.text_input("驳回原因", key=f"reason_{step['id']}")
                    
                    with col3:
                        if st.button("❌ 驳回", key=f"reject_{step['id']}", use_container_width=True):
                            if not reject_reason:
                                st.error("请填写驳回原因")
                            else:
                                execute_query('''
                                    UPDATE project_steps SET status = 'rejected', reviewed_by = ?, reviewed_at = ?, review_comment = ?
                                    WHERE id = ?
                                ''', (st.session_state['user']['id'], datetime.now(), reject_reason, step['id']), commit=True)
                                
                                execute_query('''
                                    UPDATE projects SET status = 'rejected', updated_at = ?
                                    WHERE id = ?
                                ''', (datetime.now(), step['project_id']), commit=True)
                                
                                proj = execute_query("SELECT created_by, name FROM projects WHERE id = ?", (step['project_id'],), fetch=True)
                                if proj:
                                    add_message(proj[0]['created_by'], '项目阶段审核驳回', 
                                              f'您的项目"{proj[0]["name"]}"{STAGE_NAMES.get(step["stage"], "")}已被驳回，原因: {reject_reason}')
                                
                                st.success("已驳回")
                                st.rerun()
        else:
            st.info("暂无待审批的项目阶段")
    
    with tab2:
        st.subheader("项目文件审批")
        
        pending_files = execute_query('''
            SELECT pf.*, p.name as project_name, o.name as org_name, u.username as uploader
            FROM project_files pf
            LEFT JOIN projects p ON pf.project_id = p.id
            LEFT JOIN organizations o ON p.org_id = o.id
            LEFT JOIN users u ON pf.upload_by = u.id
            WHERE pf.approval_status = 'pending'
            ORDER BY pf.upload_at ASC
        ''', fetch=True)
        
        if pending_files:
            for file in pending_files:
                with st.container():
                    st.markdown(f"""
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin: 10px 0;">
                        <h4>{file['title']}</h4>
                        <p>文件名: {file['file_name']} | 所属机构: {file['org_name'] or '-'} | 上传者: {file['uploader'] or '-'} | 上传时间: {file['upload_at']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 查看文件
                    if st.button("👁️ 查看文件", key=f"view_file_{file['id']}"):
                        st.session_state['view_file_id'] = file['id']
                    
                    col1, col2, col3 = st.columns([2, 2, 1])
                    
                    with col1:
                        if st.button("✅ 通过", key=f"approve_file_{file['id']}", use_container_width=True):
                            execute_query('''
                                UPDATE project_files SET approval_status = 'approved', approved_by = ?, approved_at = ?
                                WHERE id = ?
                            ''', (st.session_state['user']['id'], datetime.now(), file['id']), commit=True)
                            
                            if file['upload_by']:
                                add_message(file['upload_by'], '文件审核通过', f'您上传的文件"{file["title"]}"已审核通过')
                            
                            st.success("审核通过")
                            st.rerun()
                    
                    with col2:
                        file_reject_reason = st.text_input("驳回原因", key=f"file_reason_{file['id']}")
                    
                    with col3:
                        if st.button("❌ 驳回", key=f"reject_file_{file['id']}", use_container_width=True):
                            if not file_reject_reason:
                                st.error("请填写驳回原因")
                            else:
                                execute_query('''
                                    UPDATE project_files SET approval_status = 'rejected', approved_by = ?, approved_at = ?, approval_comment = ?
                                    WHERE id = ?
                                ''', (st.session_state['user']['id'], datetime.now(), file_reject_reason, file['id']), commit=True)
                                
                                if file['upload_by']:
                                    add_message(file['upload_by'], '文件审核驳回', 
                                              f'您上传的文件"{file["title"]}"已被驳回，原因: {file_reject_reason}')
                                
                                st.success("已驳回")
                                st.rerun()
        else:
            st.info("暂无待审批的项目文件")

def render_admin_messages():
    """管理端消息通知"""
    st.title("📨 消息通知")
    
    user = st.session_state['user']
    
    # 一键已读按钮
    if st.button("✅ 一键已读", use_container_width=True):
        execute_query("UPDATE messages SET is_read = 1 WHERE user_id = ?", (user['id'],), commit=True)
        st.success("所有消息已标记为已读")
        st.rerun()
    
    # 获取消息列表
    messages = execute_query('''
        SELECT * FROM messages WHERE user_id = ? ORDER BY created_at DESC
    ''', (user['id'],), fetch=True)
    
    if messages:
        for msg in messages:
            read_status = "✅" if msg['is_read'] else "🔔"
            bg_color = "#f8f9fa" if msg['is_read'] else "#e3f2fd"
            
            st.markdown(f"""
            <div style="background: {bg_color}; padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 4px solid {'#4caf50' if msg['is_read'] else '#2196f3'};">
                <h4>{read_status} {msg['title']}</h4>
                <p>{msg['content']}</p>
                <small>{msg['created_at']}</small>
            </div>
            """, unsafe_allow_html=True)
            
            if not msg['is_read']:
                if st.button("标记已读", key=f"read_{msg['id']}"):
                    execute_query("UPDATE messages SET is_read = 1 WHERE id = ?", (msg['id'],), commit=True)
                    st.rerun()
    else:
        st.info("暂无消息")

def render_admin_indicators():
    """管理端项目智库管理"""
    st.title("📚 项目智库管理")
    # 辅助：刷新项目状态（根据各阶段状态设置项目状态）
    def refresh_project_status(project_id):
        try:
            steps = execute_query('SELECT status FROM project_steps WHERE project_id = ?', (project_id,), fetch=True)
            if not steps:
                return
            statuses = [s['status'] for s in steps]
            if all(s == 'approved' for s in statuses):
                execute_query('UPDATE projects SET status = ?, updated_at = ? WHERE id = ?', ('completed', datetime.now(), project_id), commit=True)
            elif any(s == 'rejected' for s in statuses):
                execute_query('UPDATE projects SET status = ?, updated_at = ? WHERE id = ?', ('rejected', datetime.now(), project_id), commit=True)
            else:
                execute_query('UPDATE projects SET status = ?, updated_at = ? WHERE id = ?', ('in_progress', datetime.now(), project_id), commit=True)
        except Exception:
            pass

    # 一次性迁移：将历史 project_files 的文件名与磁盘文件重命名为 项目ID_原名 格式
    def migrate_files_to_project_prefix():
        migrated = 0
        failed = 0
        rows = execute_query("SELECT id, project_id, file_name, file_path FROM project_files", fetch=True)
        for r in rows:
            try:
                pid = r['project_id']
                if not pid:
                    continue
                old_name = r['file_name'] or ''
                # 如果已经以 projectID_ 开头，跳过
                if old_name.startswith(f"{pid}_"):
                    continue
                old_path = r['file_path']
                if not old_path or not os.path.exists(old_path):
                    failed += 1
                    continue
                dirpath = os.path.dirname(old_path)
                new_name = f"{pid}_{old_name}"
                new_path = os.path.join(dirpath, new_name)
                # 如果目标已存在，跳过或使用唯一后缀
                if os.path.exists(new_path):
                    # 改用时间戳后缀
                    ts = datetime.now().strftime("%Y%m%d%H%M%S")
                    new_name = f"{pid}_{ts}_{old_name}"
                    new_path = os.path.join(dirpath, new_name)
                os.rename(old_path, new_path)
                # 更新数据库字段：file_name 与 file_path
                execute_query("UPDATE project_files SET file_name = ?, file_path = ? WHERE id = ?", (new_name, new_path, r['id']), commit=True)
                migrated += 1
            except Exception:
                failed += 1
        return migrated, failed

    # 仅在未迁移过时自动运行一次（由 session_state 标记）
    if 'files_migrated' not in st.session_state:
        # 默认自动迁移（用户之前已同意）
        try:
            mig, fail = migrate_files_to_project_prefix()
            st.session_state['files_migrated'] = True
            st.success(f"已完成文件迁移: {mig} 个，失败: {fail} 个（如有失败请检查文件权限或路径）")
        except Exception as e:
            st.session_state['files_migrated'] = True
            st.error(f"文件迁移时发生错误: {e}")
    
    tab1, tab2, tab3, tab4 = st.tabs(["当前项目", "项目文件管理", "指标管理", "项目文件评估"])
    
    with tab1:
        st.subheader("当前项目")
        st.info("显示机构创建且处于审核流程中的项目；可直接打开项目文件夹查看已通过文件。")
        
        # 查询未完成的项目
        current_projects = execute_query('''
            SELECT p.*, o.name as org_name, 
                   (SELECT COUNT(*) FROM project_steps WHERE project_id = p.id AND status != 'approved') as pending_stages
            FROM projects p
            JOIN organizations o ON p.org_id = o.id
            WHERE p.status IN ('pending', 'in_progress', 'rejected')
            ORDER BY p.created_at DESC
        ''', fetch=True)
        
        if current_projects:
            for proj in current_projects:
                with st.expander(f"**{proj['name']}** - {proj['org_name']} (待处理阶段: {proj['pending_stages']})"):
                    st.write(f"**项目分类:** {PROJECT_CATEGORIES.get(proj['category'], {}).get('name', '-') if proj['category'] else '-'}")
                    st.write(f"**当前阶段:** {STAGE_NAMES.get(proj['current_stage'], '-')}")
                    st.write(f"**状态:** {proj['status']}")
                    st.write(f"**创建时间:** {proj['created_at']}")

                    # 打开至项目文件管理（在 tab2 中显示该项目）
                    if st.button("📂 打开项目文件夹", key=f"open_proj_{proj['id']}"):
                        # 导出已通过文件到本地目录 1_<项目名>/2_<项目名>/3_<项目名>
                        export_result = ensure_project_export_dirs_and_copy(proj['id'])
                        st.session_state['export_info'] = export_result
                        if export_result:
                            st.session_state['export_base'] = export_result.get('base')
                        st.session_state['indicators_open_project'] = proj['id']
                        st.experimental_rerun()

                    # 查看各阶段文件统计
                    st.markdown("**阶段文件:**")
                    steps = execute_query('''
                        SELECT ps.*, (SELECT COUNT(*) FROM project_files WHERE step_id = ps.id) as file_count
                        FROM project_steps ps WHERE ps.project_id = ?
                    ''', (proj['id'],), fetch=True)

                    if steps:
                        for step in steps:
                            step_stage = step['stage']
                            st.write(f"- {STAGE_NAMES.get(step_stage, f'阶段{step_stage}')}: {step['file_count']} 个文件")
        else:
            st.info("暂无当前项目")
    
    with tab2:
        st.subheader("项目文件管理")
        
        # 搜索
        search = st.text_input("搜索项目或文件", placeholder="输入关键词")

        # 如果用户从当前项目点击打开，则显示导出目录并允许进入查看
        proj_open_id = st.session_state.get('indicators_open_project')
        if proj_open_id:
            proj_rows = execute_query("SELECT * FROM projects WHERE id = ?", (proj_open_id,), fetch=True)
            if proj_rows:
                proj_obj = proj_rows[0]
                safe_name = safe_fname(proj_obj.get('name') or f'proj_{proj_open_id}')
                export_base = st.session_state.get('export_base') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
                st.markdown(f"### 📂 导出目录（项目: {proj_obj.get('name')}）")

                # 列出 1_,2_,3_ 以及 other_ 目录
                folders = []
                for i in (1,2,3):
                    p = os.path.join(export_base, f"{i}_{safe_name}")
                    if os.path.exists(p):
                        folders.append((f"{i}_{proj_obj.get('name')}", p))
                other_p = os.path.join(export_base, f"other_{safe_name}")
                if os.path.exists(other_p):
                    folders.append((f"other_{proj_obj.get('name')}", other_p))

                if folders:
                    for label, path in folders:
                        col_a, col_b = st.columns([8,1])
                        with col_a:
                            if st.button(label, key=f"open_export_{label}"):
                                st.session_state['export_current_folder'] = path
                                st.experimental_rerun()
                        with col_b:
                            # 显示文件数量
                            try:
                                cnt = len([n for n in os.listdir(path) if os.path.isfile(os.path.join(path, n))])
                            except Exception:
                                cnt = 0
                            st.markdown(f"<div style='background:#eee;padding:4px 8px;border-radius:8px'>{cnt}</div>", unsafe_allow_html=True)
                else:
                    st.info("当前项目暂无导出目录或无已通过文件")

                # 如果在某个导出目录内部，展示文件列表与下载按钮
                cur_folder = st.session_state.get('export_current_folder')
                if cur_folder and cur_folder.startswith(export_base):
                    st.markdown(f"#### 当前目录: {os.path.basename(cur_folder)}")
                    files = [f for f in os.listdir(cur_folder) if os.path.isfile(os.path.join(cur_folder, f))]
                    if files:
                        for fn in files:
                            fp = os.path.join(cur_folder, fn)
                            col1, col2 = st.columns([8,2])
                            with col1:
                                st.write(fn)
                            with col2:
                                try:
                                    with open(fp, 'rb') as fh:
                                        st.download_button(label='📥 下载', data=fh, file_name=fn)
                                except Exception:
                                    st.write('无法下载')

                    if st.button('⬅ 返回上级', key='export_back'):
                        del st.session_state['export_current_folder']
                        st.experimental_rerun()

        
        # 分类文件夹视图
        st.markdown("### 📁 项目分类文件夹")
        
        # 获取有文件的分类
        categories_with_files = execute_query('''
            SELECT DISTINCT category, subcategory FROM project_files 
            WHERE approval_status = 'approved' AND category IS NOT NULL
            ORDER BY category, subcategory
        ''', fetch=True)
        
        # 构建分类树
        category_tree = {}
        for cat in categories_with_files or []:
            cat_key = cat['category']
            sub_key = cat['subcategory']
            
            if cat_key not in category_tree:
                category_tree[cat_key] = {'name': PROJECT_CATEGORIES.get(cat_key, {}).get('name', '其他项目'), 'subs': {}}
            
            if sub_key:
                sub_name = PROJECT_CATEGORIES.get(cat_key, {}).get('subcategories', {}).get(sub_key, sub_key)
                category_tree[cat_key]['subs'][sub_key] = sub_name
        
        # 显示文件夹：分类 -> 项目 -> 已通过文件（点击项目名展开）
        for cat_key, cat_info in category_tree.items():
            with st.expander(f"📂 {cat_key} - {cat_info['name']}"):
                # 获取该分类下的项目（仅显示有已通过文件的项目）
                projects_in_cat = execute_query('''
                    SELECT DISTINCT p.id, p.name FROM projects p
                    JOIN project_files pf ON pf.project_id = p.id
                    WHERE p.category = ? AND pf.approval_status = 'approved'
                ''', (cat_key,), fetch=True)

                if projects_in_cat:
                    for proj in projects_in_cat:
                        open_flag = (st.session_state.get('indicators_open_project') == proj['id'])
                        with st.expander(f"📁 {cat_key}-{proj['name']}", expanded=open_flag):
                            # 获取项目已通过文件
                            files = execute_query('''
                                SELECT pf.*, u.username as uploader FROM project_files pf
                                LEFT JOIN users u ON pf.upload_by = u.id
                                WHERE pf.project_id = ? AND pf.approval_status = 'approved'
                                ORDER BY pf.upload_at DESC
                            ''', (proj['id'],), fetch=True)

                            if files:
                                for f in files:
                                    display_name = f"{proj['id']}_{f['file_name']}"
                                    col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
                                    with col1:
                                        st.write(f"📄 {display_name}")
                                    with col2:
                                        st.write(f"{f['upload_at'][:10]}")
                                    with col3:
                                        if st.button("👁️", key=f"view_pf_{f['id']}"):
                                            st.session_state['view_file_id'] = f['id']
                                            st.rerun()
                                    with col4:
                                        if st.button("📝 评估", key=f"eval_pf_{f['id']}"):
                                            st.session_state['indicators_eval_file'] = f['id']
                                            st.experimental_rerun()
                            else:
                                st.info("暂无已通过的文件")
                else:
                    # 显示子分类文件
                    for sub_key, sub_name in cat_info['subs'].items():
                        with st.expander(f"📁 {cat_key}-{sub_key} {sub_name}"):
                            files = execute_query('''
                                SELECT pf.*, u.username as uploader, p.id as project_id, p.name as project_name
                                FROM project_files pf
                                LEFT JOIN users u ON pf.upload_by = u.id
                                LEFT JOIN projects p ON pf.project_id = p.id
                                WHERE pf.category = ? AND pf.subcategory = ? AND pf.approval_status = 'approved'
                                ORDER BY pf.upload_at DESC
                            ''', (cat_key, sub_key), fetch=True)

                            if files:
                                for f in files:
                                    display_name = f"{f['project_id']}_{f['file_name']}"
                                    col1, col2, col3, col4 = st.columns([4,1,1,1])
                                    with col1:
                                        st.write(f"📄 {display_name}")
                                    with col2:
                                        st.write(f"{f['upload_at'][:10]}")
                                    with col3:
                                        if st.button("👁️", key=f"view_pf_sub_{f['id']}"):
                                            st.session_state['view_file_id'] = f['id']
                                            st.rerun()
                                    with col4:
                                        if st.button("📝 评估", key=f"eval_pf_sub_{f['id']}"):
                                            st.session_state['indicators_eval_file'] = f['id']
                                            st.experimental_rerun()
    
    with tab3:
        st.subheader("指标管理")
        
        # 选择项目分类
        cat_select = st.selectbox("选择项目分类", list(PROJECT_CATEGORIES.keys()),
                                 format_func=lambda x: f"{x} - {PROJECT_CATEGORIES[x]['name']}")
        
        # 获取子分类
        subcats = PROJECT_CATEGORIES[cat_select].get('subcategories', {})
        if subcats:
            sub_select = st.selectbox("选择二级分类", list(subcats.keys()),
                                     format_func=lambda x: f"{x} - {subcats[x]}")
        else:
            sub_select = None
        
        # 获取指标列表
        if sub_select:
            indicators = execute_query('''
                SELECT * FROM indicator_library WHERE category = ? AND subcategory = ?
            ''', (cat_select, sub_select), fetch=True)
        else:
            indicators = execute_query('''
                SELECT * FROM indicator_library WHERE category = ?
            ''', (cat_select,), fetch=True)
        
        if indicators:
            st.markdown("#### 当前指标")
            
            for ind in indicators:
                col1, col2, col3, col4 = st.columns([3, 1, 2, 1])
                
                with col1:
                    st.write(f"**{ind['indicator_name']}**")
                
                with col2:
                    new_weight = st.number_input("权重", value=ind['weight'], min_value=0.0, max_value=100.0, 
                                                key=f"weight_{ind['id']}", label_visibility="collapsed")
                
                with col3:
                    new_desc = st.text_input("描述", value=ind['description'] or "", 
                                            key=f"desc_{ind['id']}", label_visibility="collapsed")
                
                with col4:
                    if st.button("💾", key=f"save_ind_{ind['id']}"):
                        execute_query('''
                            UPDATE indicator_library SET weight = ?, description = ?, updated_at = ?
                            WHERE id = ?
                        ''', (new_weight, new_desc, datetime.now(), ind['id']), commit=True)
                        st.success("已保存")
                    
                    if st.button("🗑️", key=f"del_ind_{ind['id']}"):
                        execute_query("DELETE FROM indicator_library WHERE id = ?", (ind['id'],), commit=True)
                        st.success("已删除")
                        st.rerun()
        
        # 添加新指标
        st.markdown("#### 添加新指标")
        
        with st.form("add_indicator_form"):
            new_ind_name = st.text_input("指标名称")
            new_ind_weight = st.number_input("权重", value=10.0, min_value=0.0, max_value=100.0)
            new_ind_desc = st.text_area("描述")
            
            if st.form_submit_button("添加指标"):
                if new_ind_name:
                    execute_query('''
                        INSERT INTO indicator_library (category, subcategory, indicator_name, weight, description)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (cat_select, sub_select, new_ind_name, new_ind_weight, new_ind_desc), commit=True)
                    st.success("指标添加成功")
                    st.rerun()
    
    with tab4:
        st.subheader("项目文件评估")
        # 支持从文件列表跳转直接评估（通过 session 标记）
        pre_file_id = st.session_state.get('indicators_eval_file')
        if pre_file_id:
            file_row = execute_query('SELECT pf.*, p.name as project_name FROM project_files pf LEFT JOIN projects p ON pf.project_id = p.id WHERE pf.id = ?', (pre_file_id,), fetch=True)
            if file_row:
                file_info = file_row[0]
                st.write(f"**文件:** {file_info.get('file_name') or file_info.get('title')} (项目: {file_info.get('project_name') or '-'})")

                file_cat = file_info.get('category')
                subcats = PROJECT_CATEGORIES.get(file_cat, {}).get('subcategories', {}) if file_cat else {}
                if file_cat and subcats:
                    sub_select_eval = st.selectbox("选择二级分类", list(subcats.keys()), format_func=lambda x: f"{x} - {subcats[x]}", key="sub_eval_pre")
                    indicators = execute_query('SELECT * FROM indicator_library WHERE category = ? AND subcategory = ?', (file_cat, sub_select_eval), fetch=True)
                elif file_cat:
                    indicators = execute_query('SELECT * FROM indicator_library WHERE category = ?', (file_cat,), fetch=True)
                else:
                    indicators = []

                if indicators:
                    st.markdown("#### 评估打分")
                    total_score = 0
                    total_weight = sum(ind['weight'] for ind in indicators)
                    for ind in indicators:
                        col1, col2, col3 = st.columns([3,1,1])
                        with col1:
                            st.write(f"**{ind['indicator_name']}** (权重: {ind['weight']})")
                        with col2:
                            score = st.slider("得分", 0, 100, 80, key=f"score_pre_{ind['id']}")
                        with col3:
                            weighted_score = score * ind['weight'] / 100 if total_weight > 0 else score
                            total_score += weighted_score
                            st.write(f"加权: {weighted_score:.1f}")

                    st.markdown(f"### 总分: {total_score:.1f} / 100")
                    if st.button("提交评估", key="submit_eval_pre"):
                        for ind in indicators:
                            score = st.session_state.get(f"score_pre_{ind['id']}", 80)
                            execute_query('''INSERT INTO file_evaluations (file_id, indicator_id, score, evaluated_by) VALUES (?, ?, ?, ?)''', (pre_file_id, ind['id'], score, st.session_state['user']['id']), commit=True)
                        st.success("评估提交成功")
                        # 清除会话以避免重复提交
                        del st.session_state['indicators_eval_file']
                        st.experimental_rerun()
                else:
                    st.info("该文件所属分类暂无可用指标")
                return
        # 评估方式：按分类 或 按项目
        eval_mode = st.radio("选择评估方式", ["按分类", "按项目"], horizontal=True, index=0)

        if eval_mode == "按分类":
            eval_cat = st.selectbox("选择项目分类", list(PROJECT_CATEGORIES.keys()),
                                   format_func=lambda x: f"{x} - {PROJECT_CATEGORIES[x]['name']}", key="eval_cat")

            # 获取该分类下已审批的文件
            eval_files = execute_query('''
                SELECT pf.*, p.name as project_name FROM project_files pf
                LEFT JOIN projects p ON pf.project_id = p.id
                WHERE pf.category = ? AND pf.approval_status = 'approved'
            ''', (eval_cat,), fetch=True)

        else:
            # 按项目选择（显示有已通过文件的项目）
            projects_with_files = execute_query('''
                SELECT DISTINCT p.id, p.name FROM projects p
                JOIN project_files pf ON pf.project_id = p.id
                WHERE pf.approval_status = 'approved'
                ORDER BY p.created_at DESC
            ''', fetch=True)
            proj_options = {p['id']: p['name'] for p in projects_with_files} if projects_with_files else {}
            selected_proj = st.selectbox("选择项目", list(proj_options.keys()) if proj_options else [],
                                        format_func=lambda x: proj_options.get(x, ''), key="eval_proj") if proj_options else None

            if selected_proj:
                eval_files = execute_query('''
                    SELECT pf.*, p.name as project_name FROM project_files pf
                    LEFT JOIN projects p ON pf.project_id = p.id
                    WHERE pf.project_id = ? AND pf.approval_status = 'approved'
                ''', (selected_proj,), fetch=True)
            else:
                eval_files = []

        if eval_files:
            selected_file = st.selectbox("选择要评估的文件", [f['id'] for f in eval_files],
                                        format_func=lambda x: next((f['file_name'] if f.get('file_name') else f['title']) for f in eval_files if f['id'] == x))

            if selected_file:
                file_info = next(f for f in eval_files if f['id'] == selected_file)
                st.write(f"**文件:** {file_info.get('file_name') or file_info.get('title')} (项目: {file_info.get('project_name') or '-'})")

                # 获取指标（根据文件所属分类选择指标）
                file_cat = file_info.get('category')
                subcats = PROJECT_CATEGORIES.get(file_cat, {}).get('subcategories', {}) if file_cat else {}
                if file_cat and subcats:
                    sub_select_eval = st.selectbox("选择二级分类", list(subcats.keys()),
                                                  format_func=lambda x: f"{x} - {subcats[x]}", key="sub_eval")
                    indicators = execute_query('''
                        SELECT * FROM indicator_library WHERE category = ? AND subcategory = ?
                    ''', (file_cat, sub_select_eval), fetch=True)
                elif file_cat:
                    indicators = execute_query('''
                        SELECT * FROM indicator_library WHERE category = ?
                    ''', (file_cat,), fetch=True)
                else:
                    indicators = []

                if indicators:
                    st.markdown("#### 评估打分")

                    total_score = 0
                    total_weight = sum(ind['weight'] for ind in indicators)

                    for ind in indicators:
                        col1, col2, col3 = st.columns([3, 1, 1])

                        with col1:
                            st.write(f"**{ind['indicator_name']}** (权重: {ind['weight']})")

                        with col2:
                            score = st.slider("得分", 0, 100, 80, key=f"score_{ind['id']}")

                        with col3:
                            weighted_score = score * ind['weight'] / 100 if total_weight > 0 else score
                            total_score += weighted_score
                            st.write(f"加权: {weighted_score:.1f}")

                    st.markdown(f"### 总分: {total_score:.1f} / 100")

                    if st.button("提交评估"):
                        for ind in indicators:
                            score = st.session_state.get(f"score_{ind['id']}", 80)
                            execute_query('''
                                INSERT INTO file_evaluations (file_id, indicator_id, score, evaluated_by)
                                VALUES (?, ?, ?, ?)
                            ''', (selected_file, ind['id'], score, st.session_state['user']['id']), commit=True)

                        st.success("评估提交成功")
        else:
            st.info("暂无可评估的已通过文件")

def render_admin_visualization():
    """管理端可视化大屏"""
    st.title("📈 可视化大屏")
    
    # 统计数据
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_files = execute_query("SELECT COUNT(*) as cnt FROM project_files WHERE approval_status = 'approved'", fetch=True)[0]['cnt']
        st.metric("总文件数", total_files)
    
    with col2:
        evaluated_files = execute_query('''
            SELECT COUNT(DISTINCT file_id) as cnt FROM file_evaluations
        ''', fetch=True)[0]['cnt']
        st.metric("已评估文件", evaluated_files)
    
    with col3:
        unevaluated = total_files - evaluated_files
        st.metric("未评估文件", unevaluated)
    
    with col4:
        avg_score = execute_query('''
            SELECT AVG(score) as avg FROM file_evaluations
        ''', fetch=True)[0]['avg'] or 0
        st.metric("平均得分", f"{avg_score:.1f}")
    
    st.markdown("---")
    
    # 图表
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("各分类项目文件数量")
        
        file_stats = execute_query('''
            SELECT category, COUNT(*) as cnt FROM project_files 
            WHERE approval_status = 'approved' AND category IS NOT NULL
            GROUP BY category
        ''', fetch=True)
        
        if file_stats:
            df = pd.DataFrame(file_stats)
            df['category_name'] = df['category'].map(lambda x: PROJECT_CATEGORIES.get(x, {}).get('name', x))
            
            fig = px.bar(df, x='category_name', y='cnt', color='category_name',
                        color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(xaxis_title="项目分类", yaxis_title="文件数量", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无数据")
    
    with col2:
        st.subheader("评估状态分布")
        
        eval_data = {
            '状态': ['已评估', '未评估'],
            '数量': [evaluated_files, unevaluated]
        }
        df = pd.DataFrame(eval_data)
        
        fig = px.pie(df, values='数量', names='状态', 
                    color_discrete_sequence=['#2ca02c', '#ff7f0e'])
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # 各分类评估情况
    st.subheader("各分类评估情况")
    
    eval_by_cat = execute_query('''
        SELECT pf.category, 
               COUNT(DISTINCT pf.id) as total,
               COUNT(DISTINCT fe.file_id) as evaluated
        FROM project_files pf
        LEFT JOIN file_evaluations fe ON pf.id = fe.file_id
        WHERE pf.approval_status = 'approved' AND pf.category IS NOT NULL
        GROUP BY pf.category
    ''', fetch=True)
    
    if eval_by_cat:
        df = pd.DataFrame(eval_by_cat)
        df['category_name'] = df['category'].map(lambda x: PROJECT_CATEGORIES.get(x, {}).get('name', x))
        df['unevaluated'] = df['total'] - df['evaluated']
        
        fig = go.Figure(data=[
            go.Bar(name='已评估', x=df['category_name'], y=df['evaluated'], marker_color='#2ca02c'),
            go.Bar(name='未评估', x=df['category_name'], y=df['unevaluated'], marker_color='#ff7f0e')
        ])
        fig.update_layout(barmode='stack', xaxis_title="项目分类", yaxis_title="文件数量")
        st.plotly_chart(fig, use_container_width=True)

# ==================== 机构端页面 ====================
def render_org_dashboard():
    """机构端工作台"""
    st.title("🏠 工作台")
    
    user = st.session_state['user']
    org_id = user['org_id']
    
    # 获取机构信息
    org = execute_query("SELECT * FROM organizations WHERE id = ?", (org_id,), fetch=True)
    org_name = org[0]['name'] if org else "未知机构"
    
    st.markdown(f"### 欢迎，{user.get('real_name') or user['username']} ({org_name})")
    
    # 统计数据
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        project_count = execute_query("SELECT COUNT(*) as cnt FROM projects WHERE org_id = ?", (org_id,), fetch=True)[0]['cnt']
        st.metric("项目总数", project_count)
    
    with col2:
        active_count = execute_query("SELECT COUNT(*) as cnt FROM projects WHERE org_id = ? AND status IN ('pending', 'in_progress')", (org_id,), fetch=True)[0]['cnt']
        st.metric("进行中项目", active_count)
    
    with col3:
        completed_count = execute_query("SELECT COUNT(*) as cnt FROM projects WHERE org_id = ? AND status = 'completed'", (org_id,), fetch=True)[0]['cnt']
        st.metric("已完成项目", completed_count)
    
    with col4:
        file_count = execute_query("SELECT COUNT(*) as cnt FROM project_files WHERE upload_by = ?", (user['id'],), fetch=True)[0]['cnt']
        st.metric("上传文件数", file_count)
    
    st.markdown("---")
    
    # 待办事项
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 待办事项")
        
        todos = execute_query('''
            SELECT * FROM todos WHERE user_id = ? AND status = 'pending' ORDER BY created_at DESC LIMIT 5
        ''', (user['id'],), fetch=True)
        
        if todos:
            for todo in todos:
                st.checkbox(todo['title'], key=f"todo_{todo['id']}")
        else:
            st.info("暂无待办事项")
    
    with col2:
        st.subheader("📨 最新消息")
        
        messages = execute_query('''
            SELECT * FROM messages WHERE user_id = ? ORDER BY created_at DESC LIMIT 5
        ''', (user['id'],), fetch=True)
        
        if messages:
            for msg in messages:
                read_icon = "✅" if msg['is_read'] else "🔔"
                st.markdown(f"{read_icon} **{msg['title']}** - {msg['created_at'][:10]}")
        else:
            st.info("暂无消息")
    
    # 最近项目
    st.subheader("📊 最近项目")
    
    recent_projects = execute_query('''
        SELECT * FROM projects WHERE org_id = ? ORDER BY created_at DESC LIMIT 5
    ''', (org_id,), fetch=True)
    
    if recent_projects:
        df = pd.DataFrame(recent_projects)
        df = df[['name', 'current_stage', 'status', 'created_at']]
        df.columns = ['项目名称', '当前阶段', '状态', '创建时间']
        
        status_map = {'pending': '待审核', 'in_progress': '进行中', 'completed': '已完成', 'rejected': '已驳回'}
        df['状态'] = df['状态'].map(status_map)
        df['当前阶段'] = df['当前阶段'].map(lambda x: STAGE_NAMES.get(x, f'阶段{x}'))
        
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无项目")

def render_org_info():
    """机构端信息维护"""
    st.title("🏢 信息维护")
    
    user = st.session_state['user']
    org_id = user['org_id']
    
    tab1, tab2, tab3, tab4 = st.tabs(["机构信息", "主评人管理", "业绩记录", "培训记录"])
    
    with tab1:
        st.subheader("机构信息")
        
        org = execute_query("SELECT * FROM organizations WHERE id = ?", (org_id,), fetch=True)
        
        if org:
            org_data = org[0]
            
            with st.form("update_org_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    name = st.text_input("机构名称", value=org_data['name'])
                    org_type = st.selectbox("机构类型", ["企业", "事业单位", "社会团体", "民办非企业", "其他"],
                                           index=["企业", "事业单位", "社会团体", "民办非企业", "其他"].index(org_data['org_type']) if org_data['org_type'] else 0)
                    credit_code = st.text_input("统一社会信用代码", value=org_data['credit_code'] or "")
                    legal_person = st.text_input("法定代表人", value=org_data['legal_person'] or "")
                    contact_person = st.text_input("联系人", value=org_data['contact_person'] or "")
                
                with col2:
                    contact_phone = st.text_input("联系电话", value=org_data['contact_phone'] or "")
                    contact_email = st.text_input("联系邮箱", value=org_data['contact_email'] or "")
                    address = st.text_input("机构地址", value=org_data['address'] or "")
                    description = st.text_area("机构简介", value=org_data['description'] or "")
                
                if st.form_submit_button("更新信息", use_container_width=True):
                    execute_query('''
                        UPDATE organizations SET name = ?, org_type = ?, credit_code = ?, legal_person = ?,
                        contact_person = ?, contact_phone = ?, contact_email = ?, address = ?, description = ?, updated_at = ?
                        WHERE id = ?
                    ''', (name, org_type, credit_code, legal_person, contact_person, 
                          contact_phone, contact_email, address, description, datetime.now(), org_id), commit=True)
                    
                    add_log(user['id'], user['username'], name, '更新机构信息', 'organizations', '更新机构信息', get_client_ip())
                    st.success("信息更新成功")
    
    with tab2:
        st.subheader("主评人管理")
        
        evaluators = execute_query("SELECT * FROM evaluators WHERE org_id = ?", (org_id,), fetch=True)
        
        if evaluators:
            for eva in evaluators:
                with st.expander(f"**{eva['name']}** - {eva['title'] or '未设置职称'}"):
                    st.write(f"**专业领域:** {eva['specialty'] or '-'}")
                    st.write(f"**联系电话:** {eva['phone'] or '-'}")
                    st.write(f"**邮箱:** {eva['email'] or '-'}")
                    
                    if st.button("删除", key=f"del_eva_{eva['id']}"):
                        execute_query("DELETE FROM evaluators WHERE id = ?", (eva['id'],), commit=True)
                        st.success("已删除")
                        st.rerun()
        
        st.markdown("---")
        st.markdown("#### 添加主评人")
        
        with st.form("add_evaluator_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                eva_name = st.text_input("姓名 *")
                eva_title = st.text_input("职称")
                eva_specialty = st.text_input("专业领域")
            
            with col2:
                eva_phone = st.text_input("联系电话")
                eva_email = st.text_input("邮箱")
            
            if st.form_submit_button("添加"):
                if eva_name:
                    execute_query('''
                        INSERT INTO evaluators (org_id, name, title, specialty, phone, email)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (org_id, eva_name, eva_title, eva_specialty, eva_phone, eva_email), commit=True)
                    st.success("添加成功")
                    st.rerun()
    
    with tab3:
        st.subheader("业绩记录")
        
        achievements = execute_query("SELECT * FROM achievements WHERE org_id = ? ORDER BY achievement_date DESC", (org_id,), fetch=True)
        
        if achievements:
            for ach in achievements:
                with st.expander(f"**{ach['title']}** - {ach['achievement_date'] or '-'}"):
                    st.write(ach['content'] or '')
                    
                    if st.button("删除", key=f"del_ach_{ach['id']}"):
                        execute_query("DELETE FROM achievements WHERE id = ?", (ach['id'],), commit=True)
                        st.success("已删除")
                        st.rerun()
        
        st.markdown("---")
        st.markdown("#### 添加业绩记录")
        
        with st.form("add_achievement_form"):
            ach_title = st.text_input("业绩标题 *")
            ach_content = st.text_area("业绩内容")
            ach_date = st.date_input("业绩日期")
            
            if st.form_submit_button("添加"):
                if ach_title:
                    execute_query('''
                        INSERT INTO achievements (org_id, title, content, achievement_date)
                        VALUES (?, ?, ?, ?)
                    ''', (org_id, ach_title, ach_content, ach_date), commit=True)
                    st.success("添加成功")
                    st.rerun()
    
    with tab4:
        st.subheader("培训记录")
        
        trainings = execute_query("SELECT * FROM trainings WHERE org_id = ? ORDER BY training_date DESC", (org_id,), fetch=True)
        
        if trainings:
            for train in trainings:
                with st.expander(f"**{train['title']}** - {train['training_date'] or '-'}"):
                    st.write(f"**培训讲师:** {train['trainer'] or '-'}")
                    st.write(f"**培训时长:** {train['duration'] or '-'} 小时")
                    st.write(f"**参与人数:** {train['participants'] or '-'} 人")
                    st.write(f"**培训内容:** {train['content'] or '-'}")
                    
                    if st.button("删除", key=f"del_train_{train['id']}"):
                        execute_query("DELETE FROM trainings WHERE id = ?", (train['id'],), commit=True)
                        st.success("已删除")
                        st.rerun()
        
        st.markdown("---")
        st.markdown("#### 添加培训记录")
        
        with st.form("add_training_form"):
            train_title = st.text_input("培训标题 *")
            train_trainer = st.text_input("培训讲师")
            train_date = st.date_input("培训日期")
            train_duration = st.number_input("培训时长(小时)", min_value=0)
            train_participants = st.number_input("参与人数", min_value=0)
            train_content = st.text_area("培训内容")
            
            if st.form_submit_button("添加"):
                if train_title:
                    execute_query('''
                        INSERT INTO trainings (org_id, title, trainer, training_date, duration, participants, content)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (org_id, train_title, train_trainer, train_date, train_duration, train_participants, train_content), commit=True)
                    st.success("添加成功")
                    st.rerun()

def render_org_sub_accounts():
    """机构端子账号管理"""
    st.title("👥 子账号管理")
    
    user = st.session_state['user']
    org_id = user['org_id']
    
    # 只有主账号可以管理子账号
    if user['role'] != 'org_admin':
        st.warning("您没有权限管理子账号")
        return
    
    tab1, tab2 = st.tabs(["子账号列表", "新增子账号"])
    
    with tab1:
        sub_users = execute_query('''
            SELECT * FROM users WHERE org_id = ? AND role = 'org_user' ORDER BY created_at DESC
        ''', (org_id,), fetch=True)
        
        if sub_users:
            for sub in sub_users:
                status_name = "正常" if sub['status'] == 'active' else "冻结"
                
                with st.expander(f"**{sub['username']}** - {sub['real_name'] or '-'} ({status_name})"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**姓名:** {sub['real_name'] or '-'}")
                        st.write(f"**手机号:** {sub['phone'] or '-'}")
                        st.write(f"**邮箱:** {sub['email'] or '-'}")
                    
                    with col2:
                        st.write(f"**状态:** {status_name}")
                        st.write(f"**创建时间:** {sub['created_at']}")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if sub['status'] == 'active':
                            if st.button("🔒 冻结", key=f"freeze_sub_{sub['id']}"):
                                execute_query("UPDATE users SET status = 'inactive' WHERE id = ?", (sub['id'],), commit=True)
                                st.success("已冻结")
                                st.rerun()
                        else:
                            if st.button("🔓 解冻", key=f"unfreeze_sub_{sub['id']}"):
                                execute_query("UPDATE users SET status = 'active' WHERE id = ?", (sub['id'],), commit=True)
                                st.success("已解冻")
                                st.rerun()
                    
                    with col2:
                        if st.button("🔑 重置密码", key=f"reset_sub_{sub['id']}"):
                            new_hash = hash_password("Reset@123456")
                            execute_query("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, sub['id']), commit=True)
                            st.success("密码已重置为: Reset@123456")
                    
                    with col3:
                        if st.button("✏️ 编辑", key=f"edit_sub_{sub['id']}"):
                            st.session_state['edit_sub_id'] = sub['id']
                            st.rerun()
                    
                    with col4:
                        if st.button("🗑️ 删除", key=f"del_sub_{sub['id']}"):
                            execute_query("DELETE FROM users WHERE id = ?", (sub['id'],), commit=True)
                            st.success("已删除")
                            st.rerun()
        else:
            st.info("暂无子账号")
    
    with tab2:
        st.subheader("新增子账号")
        
        with st.form("add_sub_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                sub_username = st.text_input("用户名 *")
                sub_real_name = st.text_input("姓名 *")
                sub_phone = st.text_input("手机号 *")
            
            with col2:
                sub_email = st.text_input("邮箱 *")
                sub_password = st.text_input("初始密码 *", type="password")
            
            if st.form_submit_button("创建子账号", use_container_width=True):
                required = [sub_username, sub_real_name, sub_phone, sub_email, sub_password]
                if not all(required):
                    st.error("请填写所有必填项")
                else:
                    existing = execute_query("SELECT id FROM users WHERE username = ? OR phone = ? OR email = ?",
                                           (sub_username, sub_phone, sub_email), fetch=True)
                    if existing:
                        st.error("用户名、手机号或邮箱已存在")
                    else:
                        password_hash = hash_password(sub_password)
                        execute_query('''
                            INSERT INTO users (username, password_hash, role, org_id, real_name, phone, email, status)
                            VALUES (?, ?, 'org_user', ?, ?, ?, ?, 'active')
                        ''', (sub_username, password_hash, org_id, sub_real_name, sub_phone, sub_email), commit=True)
                        
                        add_log(user['id'], user['username'], '', '新增子账号', 'users', f'创建子账号: {sub_username}', get_client_ip())
                        st.success("子账号创建成功")
                        st.rerun()

def render_org_projects():
    """机构端项目管理"""
    st.title("📋 项目管理")
    
    user = st.session_state['user']
    org_id = user['org_id']
    
    tab1, tab2 = st.tabs(["项目列表", "新建项目"])
    
    with tab1:
        projects = execute_query('''
            SELECT * FROM projects WHERE org_id = ? ORDER BY created_at DESC
        ''', (org_id,), fetch=True)
        
        if projects:
            for proj in projects:
                status_map = {'pending': '待审核', 'in_progress': '进行中', 'completed': '已完成', 'rejected': '已驳回'}
                
                with st.expander(f"**{proj['name']}** - {status_map.get(proj['status'], proj['status'])}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**项目分类:** {PROJECT_CATEGORIES.get(proj['category'], {}).get('name', '-') if proj['category'] else '-'}")
                        st.write(f"**当前阶段:** {STAGE_NAMES.get(proj['current_stage'], '-')}")
                    
                    with col2:
                        st.write(f"**状态:** {status_map.get(proj['status'], proj['status'])}")
                        st.write(f"**创建时间:** {proj['created_at']}")
                    
                    if proj['description']:
                        st.write(f"**描述:** {proj['description']}")
                    
                    # 阶段操作
                    st.markdown("#### 阶段操作")
                    
                    steps = execute_query('''
                        SELECT ps.*, (SELECT COUNT(*) FROM project_files WHERE step_id = ps.id) as file_count
                        FROM project_steps ps WHERE ps.project_id = ? ORDER BY ps.stage
                    ''', (proj['id'],), fetch=True)
                    
                    if not steps:
                        # 初始化阶段
                        for stage in range(1, 6):
                            execute_query('''
                                INSERT INTO project_steps (project_id, stage, status)
                                VALUES (?, ?, 'pending')
                            ''', (proj['id'], stage), commit=True)
                        st.rerun()
                    
                    for step in steps:
                        step_status = {'pending': '⏳ 待提交', 'submitted': '📤 已提交', 'approved': '✅ 已通过', 'rejected': '❌ 已驳回'}
                        
                        step_stage = step['stage']
                        st.markdown(f"**{STAGE_NAMES.get(step_stage, f'阶段{step_stage}')}** - {step_status.get(step['status'], step['status'])}")
                        
                        # 显示已上传文件
                        if step['file_count'] > 0:
                            st.write(f"📁 已上传 {step['file_count']} 个文件")
                        
                        # 上传文件（允许重新提交被驳回的阶段）
                        if step['status'] in ('pending', 'rejected') and step['stage'] == proj['current_stage']:
                            uploaded_file = st.file_uploader(
                                f"上传{STAGE_NAMES.get(step['stage'], '')}文件",
                                type=['pdf', 'docx', 'doc', 'xlsx', 'xls', 'txt'],
                                key=f"upload_{step['id']}"
                            )
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                if st.button(f"📤 上传文件", key=f"upload_btn_{step['id']}"):
                                    if uploaded_file:
                                        file_path, file_name, file_size = save_uploaded_file(uploaded_file, f"projects/{proj['id']}/{step['stage']}", project_id=proj['id'])
                                        
                                        execute_query('''
                                            INSERT INTO project_files (project_id, step_id, title, file_name, file_path, file_size, upload_by)
                                            VALUES (?, ?, ?, ?, ?, ?, ?)
                                        ''', (proj['id'], step['id'], uploaded_file.name, file_name, file_path, file_size, user['id']), commit=True)
                                        
                                        st.success("文件上传成功")
                                        st.rerun()
                            
                            with col2:
                                if st.button(f"✅ 提交审核", key=f"submit_btn_{step['id']}"):
                                    # 检查是否上传了文件
                                    files = execute_query("SELECT id FROM project_files WHERE step_id = ?", (step['id'],), fetch=True)
                                    if files:
                                        execute_query('''
                                            UPDATE project_steps SET status = 'submitted', submitted_by = ?, submitted_at = ?
                                            WHERE id = ?
                                        ''', (user['id'], datetime.now(), step['id']), commit=True)
                                        
                                        execute_query("UPDATE projects SET status = 'pending' WHERE id = ?", (proj['id'],), commit=True)
                                        
                                        # 通知超级管理员
                                        admins = execute_query("SELECT id FROM users WHERE role = 'super_admin'", fetch=True)
                                        for admin in admins:
                                            add_message(admin['id'], '新项目待审批', 
                                                      f'机构有新的项目阶段待审批: {proj["name"]} - {STAGE_NAMES.get(step["stage"], "")}')
                                        
                                        st.success("已提交审核")
                                        st.rerun()
                                    else:
                                        st.error("请先上传文件")
                        
                        # 查看文件
                        if step['file_count'] > 0:
                            step_files = execute_query("SELECT * FROM project_files WHERE step_id = ?", (step['id'],), fetch=True)
                            for f in step_files:
                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.write(f"  📄 {f['file_name']}")
                                with col2:
                                    if st.button("👁️ 查看", key=f"view_org_file_{f['id']}"):
                                        st.session_state['view_file_id'] = f['id']
                                        st.rerun()
        else:
            st.info("暂无项目，请新建项目")
    
    with tab2:
        st.subheader("新建项目")
        
        with st.form("new_project_form"):
            proj_name = st.text_input("项目名称 *")
            
            col1, col2 = st.columns(2)
            with col1:
                proj_category = st.selectbox("项目分类 *", list(PROJECT_CATEGORIES.keys()),
                                            format_func=lambda x: f"{x} - {PROJECT_CATEGORIES[x]['name']}")
            
            with col2:
                subcats = PROJECT_CATEGORIES[proj_category].get('subcategories', {})
                if subcats:
                    proj_subcategory = st.selectbox("二级分类 *", list(subcats.keys()),
                                                   format_func=lambda x: f"{x} - {subcats[x]}")
                else:
                    proj_subcategory = None
            
            proj_desc = st.text_area("项目描述")
            
            if st.form_submit_button("创建项目", use_container_width=True):
                if proj_name:
                    project_id = execute_query('''
                        INSERT INTO projects (name, org_id, category, subcategory, description, created_by, status)
                        VALUES (?, ?, ?, ?, ?, ?, 'pending')
                    ''', (proj_name, org_id, proj_category, proj_subcategory, proj_desc, user['id']), commit=True)
                    
                    # 创建5个阶段
                    for stage in range(1, 6):
                        execute_query('''
                            INSERT INTO project_steps (project_id, stage, status)
                            VALUES (?, ?, 'pending')
                        ''', (project_id, stage), commit=True)
                    
                    add_log(user['id'], user['username'], '', '新建项目', 'projects', f'创建项目: {proj_name}', get_client_ip())
                    st.success("项目创建成功")
                    st.rerun()

def render_org_knowledge():
    """机构端项目智库管理"""
    st.title("📚 项目智库管理")
    
    user = st.session_state['user']
    org_id = user['org_id']
    
    tab1, tab2 = st.tabs(["我的项目", "上传文件"])
    
    with tab1:
        st.subheader("我的项目")
        
        projects = execute_query('''
            SELECT * FROM projects WHERE org_id = ? ORDER BY created_at DESC
        ''', (org_id,), fetch=True)
        
        if projects:
            for proj in projects:
                with st.expander(f"**{proj['name']}**"):
                    st.write(f"**分类:** {PROJECT_CATEGORIES.get(proj['category'], {}).get('name', '-') if proj['category'] else '-'}")
                    st.write(f"**状态:** {proj['status']}")
                    
                    # 查看项目文件
                    files = execute_query('''
                        SELECT pf.*, ps.stage FROM project_files pf
                        LEFT JOIN project_steps ps ON pf.step_id = ps.id
                        WHERE pf.project_id = ? AND pf.approval_status = 'approved'
                        ORDER BY pf.upload_at DESC
                    ''', (proj['id'],), fetch=True)
                    
                    if files:
                        st.markdown("**项目文件:**")
                        for f in files:
                            display_name = f"{proj['id']}_{f['file_name']}"
                            col1, col2, col3 = st.columns([4, 1, 1])
                            with col1:
                                st.write(f"📄 {display_name}")
                            with col2:
                                st.write(f"{STAGE_NAMES.get(f['stage'], '-')}" )
                            with col3:
                                if st.button("👁️", key=f"view_know_file_{f['id']}"):
                                    st.session_state['view_file_id'] = f['id']
                                    st.rerun()
        else:
            st.info("暂无项目")
    
    with tab2:
        st.subheader("上传文件")
        
        with st.form("upload_file_form"):
            file_title = st.text_input("文件标题 *")
            
            col1, col2 = st.columns(2)
            with col1:
                file_category = st.selectbox("文件类型 *", list(PROJECT_CATEGORIES.keys()),
                                            format_func=lambda x: f"{x} - {PROJECT_CATEGORIES[x]['name']}")
            
            with col2:
                subcats = PROJECT_CATEGORIES[file_category].get('subcategories', {})
                if subcats:
                    file_subcategory = st.selectbox("二级分类", list(subcats.keys()),
                                                   format_func=lambda x: f"{x} - {subcats[x]}")
                else:
                    file_subcategory = None
            
            publish_org = st.text_input("发布机构")
            file_desc = st.text_area("文件描述")
            
            uploaded_file = st.file_uploader("上传文件", type=['pdf', 'docx', 'doc', 'xlsx', 'xls', 'txt'])
            
            if st.form_submit_button("上传文件", use_container_width=True):
                if file_title and uploaded_file:
                    file_path, file_name, file_size = save_uploaded_file(uploaded_file, f"files/{file_category}")
                    
                    # 子账号上传需要审批
                    approval_status = 'pending' if user['role'] == 'org_user' else 'pending'
                    
                    execute_query('''
                        INSERT INTO project_files (title, file_type, category, subcategory, file_path, file_name, 
                                                  file_size, publish_org, description, upload_by, approval_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (file_title, uploaded_file.type, file_category, file_subcategory, file_path, file_name,
                          file_size, publish_org, file_desc, user['id'], approval_status), commit=True)
                    
                    # 通知审批
                    if user['role'] == 'org_user':
                        # 通知机构主账号
                        main_user = execute_query("SELECT id FROM users WHERE org_id = ? AND role = 'org_admin'", (org_id,), fetch=True)
                        if main_user:
                            add_message(main_user[0]['id'], '新文件待审批', f'有新的项目文件待审批: {file_title}')
                    else:
                        # 通知超级管理员
                        admins = execute_query("SELECT id FROM users WHERE role = 'super_admin'", fetch=True)
                        for admin in admins:
                            add_message(admin['id'], '新文件待审批', f'机构上传了新的项目文件待审批: {file_title}')
                    
                    add_log(user['id'], user['username'], '', '上传文件', 'files', f'上传文件: {file_title}', get_client_ip())
                    st.success("文件上传成功，等待审批")
                    st.rerun()

def render_org_todos():
    """机构端待办事项"""
    st.title("✅ 待办事项")
    
    user = st.session_state['user']
    
    tab1, tab2 = st.tabs(["待办列表", "新增待办"])
    
    with tab1:
        todos = execute_query('''
            SELECT * FROM todos WHERE user_id = ? ORDER BY 
            CASE WHEN status = 'pending' THEN 0 ELSE 1 END,
            CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
            created_at DESC
        ''', (user['id'],), fetch=True)
        
        if todos:
            for todo in todos:
                status_icon = "⏳" if todo['status'] == 'pending' else "✅"
                priority_colors = {'high': '#f8d7da', 'medium': '#fff3cd', 'low': '#d4edda'}
                
                st.markdown(f"""
                <div style="background: {priority_colors.get(todo['priority'], '#f8f9fa')}; 
                            padding: 15px; border-radius: 10px; margin: 10px 0;
                            border-left: 4px solid {'#dc3545' if todo['priority'] == 'high' else '#ffc107' if todo['priority'] == 'medium' else '#28a745'};">
                    <h4>{status_icon} {todo['title']}</h4>
                    <p>{todo['content'] or ''}</p>
                    <small>优先级: {todo['priority']} | 截止日期: {todo['due_date'] or '未设置'}</small>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if todo['status'] == 'pending' and st.button("完成", key=f"complete_{todo['id']}"):
                        execute_query("UPDATE todos SET status = 'completed', completed_at = ? WHERE id = ?",
                                    (datetime.now(), todo['id']), commit=True)
                        st.success("已完成")
                        st.rerun()
                
                with col2:
                    if st.button("删除", key=f"del_todo_{todo['id']}"):
                        execute_query("DELETE FROM todos WHERE id = ?", (todo['id'],), commit=True)
                        st.success("已删除")
                        st.rerun()
        else:
            st.info("暂无待办事项")
    
    with tab2:
        with st.form("add_todo_form"):
            todo_title = st.text_input("待办标题 *")
            todo_content = st.text_area("待办内容")
            
            col1, col2 = st.columns(2)
            with col1:
                todo_priority = st.selectbox("优先级", ["high", "medium", "low"],
                                            format_func=lambda x: {"high": "高", "medium": "中", "low": "低"}[x])
            with col2:
                todo_due = st.date_input("截止日期")
            
            if st.form_submit_button("添加待办", use_container_width=True):
                if todo_title:
                    execute_query('''
                        INSERT INTO todos (user_id, title, content, priority, due_date)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user['id'], todo_title, todo_content, todo_priority, todo_due), commit=True)
                    st.success("添加成功")
                    st.rerun()

def render_org_messages():
    """机构端消息通知"""
    st.title("📨 消息通知")
    
    user = st.session_state['user']
    
    # 一键已读
    if st.button("✅ 一键已读", use_container_width=True):
        execute_query("UPDATE messages SET is_read = 1 WHERE user_id = ?", (user['id'],), commit=True)
        st.success("所有消息已标记为已读")
        st.rerun()
    
    messages = execute_query('''
        SELECT * FROM messages WHERE user_id = ? ORDER BY created_at DESC
    ''', (user['id'],), fetch=True)
    
    if messages:
        for msg in messages:
            read_status = "✅" if msg['is_read'] else "🔔"
            bg_color = "#f8f9fa" if msg['is_read'] else "#e3f2fd"
            
            st.markdown(f"""
            <div style="background: {bg_color}; padding: 15px; border-radius: 10px; margin: 10px 0; 
                        border-left: 4px solid {'#4caf50' if msg['is_read'] else '#2196f3'};">
                <h4>{read_status} {msg['title']}</h4>
                <p>{msg['content']}</p>
                <small>{msg['created_at']}</small>
            </div>
            """, unsafe_allow_html=True)
            
            if not msg['is_read']:
                if st.button("标记已读", key=f"read_msg_{msg['id']}"):
                    execute_query("UPDATE messages SET is_read = 1 WHERE id = ?", (msg['id'],), commit=True)
                    st.rerun()
    else:
        st.info("暂无消息")

# ==================== 文件预览弹窗 ====================
def render_file_preview():
    """渲染文件预览弹窗"""
    if 'view_file_id' not in st.session_state:
        return
    
    file_id = st.session_state['view_file_id']
    file_info = execute_query("SELECT * FROM project_files WHERE id = ?", (file_id,), fetch=True)
    
    if file_info:
        file_data = file_info[0]
        
        # 使用 Streamlit 的 modal（如果可用），否则回退到 container
        title = f"📄 {file_data['title']}"
        if hasattr(st, 'modal'):
            with st.modal(title=title):
                st.write(f"**文件名:** {file_data['file_name']}")
                st.write(f"**上传时间:** {file_data['upload_at']}")
                if file_data['file_path'] and os.path.exists(file_data['file_path']):
                    display_file_preview(file_data['file_path'], file_data['file_name'])
                else:
                    st.error("文件不存在")

                if st.button("❌ 关闭", key="close_preview"):
                    del st.session_state['view_file_id']
                    st.rerun()
        else:
            # 兼容旧版本 Streamlit：最小化自定义 overlay 的 DOM 操作
            st.markdown("### " + title)
            st.write(f"**文件名:** {file_data['file_name']}")
            st.write(f"**上传时间:** {file_data['upload_at']}")
            if file_data['file_path'] and os.path.exists(file_data['file_path']):
                display_file_preview(file_data['file_path'], file_data['file_name'])
            else:
                st.error("文件不存在")

            if st.button("❌ 关闭", key="close_preview"):
                del st.session_state['view_file_id']
                st.rerun()

# ==================== 主函数 ====================
def main():
    """主函数"""
    # 初始化数据库
    init_database()
    
    # 应用自定义样式
    apply_custom_styles()
    
    # 检查登录状态
    if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
        render_login_page()
        return
    
    # 渲染侧边栏
    render_sidebar()
    
    # 文件预览弹窗
    render_file_preview()
    
    # 根据角色和页面渲染内容
    user = st.session_state['user']
    role = user['role']
    page = st.session_state.get('current_page', 'dashboard')
    
    if role == 'super_admin':
        # 管理端页面
        if page == 'dashboard':
            render_admin_dashboard()
        elif page == 'organizations':
            render_admin_organizations()
        elif page == 'users':
            render_admin_users()
        elif page == 'projects':
            render_admin_projects()
        elif page == 'logs':
            render_admin_logs()
        elif page == 'export':
            render_admin_export()
        elif page == 'approval':
            render_admin_approval()
        elif page == 'messages':
            render_admin_messages()
        elif page == 'indicators':
            render_admin_indicators()
        elif page == 'visualization':
            render_admin_visualization()
    else:
        # 机构端页面
        if page == 'dashboard':
            render_org_dashboard()
        elif page == 'info':
            render_org_info()
        elif page == 'sub_accounts':
            render_org_sub_accounts()
        elif page == 'projects':
            render_org_projects()
        elif page == 'knowledge':
            render_org_knowledge()
        elif page == 'todos':
            render_org_todos()
        elif page == 'messages':
            render_org_messages()

if __name__ == "__main__":
    main()
