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
from datetime import datetime, timedelta
from io import BytesIO
import plotly.express as px
import plotly.graph_objects as go
import time
import tempfile
import shutil
from filelock import FileLock
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill

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

# 页面配置
st.set_page_config(
    page_title="第三方绩效评估管理平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 自定义CSS样式 ====================
def apply_custom_styles():
    """应用自定义样式"""
    st.markdown("""
    <style>
    /* 全局深蓝主背景 */
    .main {
        background: linear-gradient(180deg, #00264D 0%, #001f3b 100%);
        color: #f8fbff;
        min-height: 100vh;
    }

    /* 侧边栏（蓝绿色） */
    .css-1d391kg, .stSidebar, .sidebar .block-container {
        background: linear-gradient(180deg, #008B8B 0%, #005f6b 50%, #00264D 100%);
        color: #ffffff;
    }

    /* 卡片样式（蓝绿色卡片） */
    .metric-card, .nav-menu, .stCard, .card {
        background: linear-gradient(135deg, #008B8B 0%, #006b6b 50%, #00435a 100%);
        color: #ffffff;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.35);
    }

    /* 标题高对比 */
    h1, h2, h3, .login-title {
        color: #ffffff;
        text-shadow: 0 2px 6px rgba(0,0,0,0.6);
    }

    /* 按钮样式 */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        background: linear-gradient(90deg, #00a3a3 0%, #006b8f 100%);
        color: #ffffff;
        border: none;
        padding: 8px 14px;
    }

    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.35);
    }

    /* 数据框与表格 */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 6px 20px rgba(0,0,0,0.25);
        background: rgba(255,255,255,0.04);
    }

    .data-table th {
        background: linear-gradient(90deg, #008B8B 0%, #00264D 100%);
        color: white;
        padding: 12px;
        text-align: left;
    }

    .data-table td {
        padding: 12px 15px;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        color: #eaf6fb;
    }

    .data-table tr:hover {
        background: rgba(255,255,255,0.03);
    }

    /* 成功/错误消息 */
    .success-message { background: linear-gradient(90deg,#00c2a3,#00a38f); color: white; padding:15px; border-radius:10px;}
    .error-message { background: linear-gradient(90deg,#eb3349,#f45c43); color: white; padding:15px; border-radius:10px;}

    /* 隐藏Streamlit默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* 进度条 */
    .progress-bar { height: 8px; background: rgba(255,255,255,0.06); border-radius:4px; overflow:hidden; }
    .progress-fill { height:100%; background: linear-gradient(90deg,#00a3a3,#005f6b); border-radius:4px; }
    </style>
    """, unsafe_allow_html=True)

# ==================== 数据库初始化 ====================
def init_database():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    try:
        # 启用 WAL 模式以改善并发读写性能
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    
    # 用户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'org_user',
            org_id INTEGER,
            real_name TEXT,
            phone TEXT,
            email TEXT,
            is_active INTEGER DEFAULT 1,
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
            credit_code TEXT,
            legal_person TEXT,
            contact_person TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            address TEXT,
            description TEXT,
            is_active INTEGER DEFAULT 1,
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
            category_id TEXT,
            subcategory_id TEXT,
            project_code TEXT,
            description TEXT,
            status TEXT DEFAULT 'pending',
            current_stage INTEGER DEFAULT 1,
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
            stage_name TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            submitted_at TIMESTAMP,
            submitted_by INTEGER,
            reviewed_at TIMESTAMP,
            reviewed_by INTEGER,
            review_comment TEXT,
            file_path TEXT,
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
            project_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            category_id TEXT,
            subcategory_id TEXT,
            title TEXT,
            description TEXT,
            publish_org TEXT,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            uploaded_by INTEGER,
            status TEXT DEFAULT 'pending',
            evaluated INTEGER DEFAULT 0,
            evaluation_score REAL,
            evaluated_by INTEGER,
            evaluated_at TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
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
            introduction TEXT,
            is_active INTEGER DEFAULT 1,
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
            duration TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(id)
        )
    ''')
    
    # 指标库表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indicator_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id TEXT NOT NULL,
            subcategory_id TEXT,
            indicator_name TEXT NOT NULL,
            indicator_desc TEXT,
            weight REAL DEFAULT 10,
            max_score INTEGER DEFAULT 100,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 政策文件表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS policy_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            description TEXT,
            uploaded_by INTEGER,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
        )
    ''')
    
    # 待办事项表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            type TEXT,
            related_id INTEGER,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 1,
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
            type TEXT DEFAULT 'system',
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
            org_id INTEGER,
            org_name TEXT,
            action TEXT NOT NULL,
            action_type TEXT,
            target_type TEXT,
            target_id INTEGER,
            ip_address TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 文件评估明细表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            indicator_id INTEGER NOT NULL,
            score REAL DEFAULT 0,
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
        # 创建默认超级管理员
        password = "Admin@123456"
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        cursor.execute('''
            INSERT INTO users (username, password_hash, role, real_name, phone, email, is_active)
            VALUES (?, ?, 'super_admin', '系统管理员', '13800000000', 'admin@system.com', 1)
        ''', ('admin', password_hash))
    
    # 初始化默认指标库
    cursor.execute("SELECT COUNT(*) FROM indicator_library")
    if cursor.fetchone()[0] == 0:
        default_indicators = [
            # 统计调查研究 - 多源数据采集
            ('1', '1', '数据采集完整性', '数据采集范围是否覆盖全部目标', 15),
            ('1', '1', '数据准确性', '采集数据的准确程度', 20),
            ('1', '1', '数据时效性', '数据采集的及时性', 15),
            ('1', '1', '方法科学性', '采集方法的科学合理性', 15),
            ('1', '1', '流程规范性', '采集流程的规范程度', 10),
            ('1', '1', '质量控制', '数据质量控制措施', 10),
            ('1', '1', '文档完整性', '相关文档的完整程度', 5),
            ('1', '1', '团队专业性', '团队专业能力', 5),
            ('1', '1', '创新性', '方法或技术创新', 3),
            ('1', '1', '成果应用', '成果的实际应用价值', 2),
            # 统计调查研究 - 专项调查研究
            ('1', '2', '调研方案设计', '调研方案的科学性', 15),
            ('1', '2', '样本代表性', '样本选择的代表性', 15),
            ('1', '2', '问卷设计质量', '问卷设计的合理性', 15),
            ('1', '2', '数据收集规范', '数据收集的规范性', 15),
            ('1', '2', '分析方法', '分析方法的科学性', 15),
            ('1', '2', '报告质量', '调研报告的质量', 10),
            ('1', '2', '结论可靠性', '研究结论的可靠性', 8),
            ('1', '2', '建议可行性', '建议的可操作性', 5),
            ('1', '2', '时间控制', '项目进度控制', 2),
            ('1', '2', '成本控制', '项目成本控制', 0),
            # 政府绩效评估 - 财政绩效评估
            ('2', '1', '评估框架设计', '评估框架的科学性', 15),
            ('2', '1', '指标体系', '指标体系的完整性', 20),
            ('2', '1', '数据来源', '数据来源的可靠性', 15),
            ('2', '1', '分析方法', '分析方法的科学性', 15),
            ('2', '1', '评估过程', '评估过程的规范性', 10),
            ('2', '1', '报告质量', '评估报告的质量', 10),
            ('2', '1', '结论客观性', '评估结论的客观性', 8),
            ('2', '1', '建议针对性', '建议的针对性', 5),
            ('2', '1', '沟通协调', '与委托方的沟通', 2),
            ('2', '1', '保密工作', '信息保密工作', 0),
            # 政府绩效评估 - 行政绩效评估
            ('2', '2', '评估方案', '评估方案的科学性', 15),
            ('2', '2', '指标设计', '指标设计的合理性', 20),
            ('2', '2', '数据采集', '数据采集的全面性', 15),
            ('2', '2', '分析深度', '分析的深度和广度', 15),
            ('2', '2', '评估方法', '评估方法的科学性', 10),
            ('2', '2', '报告撰写', '报告撰写的规范性', 10),
            ('2', '2', '结果应用', '评估结果的应用价值', 8),
            ('2', '2', '改进建议', '改进建议的质量', 5),
            ('2', '2', '过程管理', '项目管理水平', 2),
            ('2', '2', '服务质量', '服务响应及时性', 0),
            # 社会经济咨询 - 企业管理咨询
            ('3', '1', '需求理解', '对客户需求的理解程度', 15),
            ('3', '1', '方案设计', '咨询方案的科学性', 20),
            ('3', '1', '专业能力', '团队专业能力', 15),
            ('3', '1', '方法工具', '方法工具的先进性', 15),
            ('3', '1', '实施指导', '实施指导的有效性', 10),
            ('3', '1', '成果交付', '成果交付的质量', 10),
            ('3', '1', '客户满意度', '客户满意程度', 8),
            ('3', '1', '创新价值', '创新性价值', 5),
            ('3', '1', '时间管理', '项目时间管理', 2),
            ('3', '1', '成本效益', '成本效益比', 0),
            # 社会经济咨询 - 公共决策咨询
            ('3', '2', '问题识别', '问题识别的准确性', 15),
            ('3', '2', '分析框架', '分析框架的科学性', 20),
            ('3', '2', '数据支撑', '数据支撑的充分性', 15),
            ('3', '2', '研究方法', '研究方法的科学性', 15),
            ('3', '2', '政策建议', '政策建议的可操作性', 10),
            ('3', '2', '报告质量', '研究报告的质量', 10),
            ('3', '2', '决策支持', '对决策的支持程度', 8),
            ('3', '2', '社会效益', '预期社会效益', 5),
            ('3', '2', '沟通协调', '与相关方沟通协调', 2),
            ('3', '2', '风险控制', '风险识别与控制', 0),
        ]
        
        for cat_id, subcat_id, name, desc, weight in default_indicators:
            cursor.execute('''
                INSERT INTO indicator_library (category_id, subcategory_id, indicator_name, indicator_desc, weight)
                VALUES (?, ?, ?, ?, ?)
            ''', (cat_id, subcat_id, name, desc, weight))
    
    conn.commit()

# ==================== 数据库操作函数 ====================
def get_db_connection():
    """获取数据库连接"""
    # 增加较长的 timeout 并允许跨线程使用连接（Streamlit 多线程场景）
    conn = sqlite3.connect(DATABASE_PATH, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def execute_query(query, params=None, fetch=False, retries=5, backoff=0.1):
    """执行数据库查询，遇到锁冲突时带重试机制"""
    attempt = 0
    while True:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            if fetch:
                result = cursor.fetchall()
            else:
                result = cursor.lastrowid
                conn.commit()
            return result
        except sqlite3.OperationalError as e:
            conn.rollback()
            # 处理数据库被锁定的情况，重试
            if 'locked' in str(e).lower() and attempt < retries:
                attempt += 1
                time.sleep(backoff * (2 ** (attempt - 1)))
                continue
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def save_uploaded_file_atomic(uploaded_file, dest_dir=UPLOAD_DIR, prefix=None, lock_timeout=10):
    """原子性保存上传文件：先写临时文件，再使用 os.replace 原子替换。使用文件锁保护目录写入。"""
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir, exist_ok=True)

    name = uploaded_file.name if hasattr(uploaded_file, 'name') else f"upload_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    if prefix:
        final_name = f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{name}"
    else:
        final_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{name}"

    final_path = os.path.join(dest_dir, final_name)

    # 使用临时文件写入
    tmp_fd, tmp_path = tempfile.mkstemp(dir=dest_dir)
    os.close(tmp_fd)
    try:
        with open(tmp_path, 'wb') as f:
            # uploaded_file 可能是 BytesIO-like
            try:
                f.write(uploaded_file.getbuffer())
            except Exception:
                # fallback: read in chunks
                uploaded_file.seek(0)
                shutil.copyfileobj(uploaded_file, f)

        # 使用目录级别锁，避免并发写入冲突
        lock_path = os.path.join(dest_dir, '.upload.lock')
        lock = FileLock(lock_path, timeout=lock_timeout)
        with lock:
            os.replace(tmp_path, final_path)
    except Exception:
        # 清理临时文件
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise

    return final_path

def get_client_ip():
    """获取客户端IP地址"""
    try:
        return st.get_option("browser.serverAddress") or "127.0.0.1"
    except:
        return "127.0.0.1"

def add_log(user_id, username, org_id, org_name, action, action_type='操作', target_type=None, target_id=None, details=None):
    """添加操作日志"""
    ip_address = get_client_ip()
    execute_query('''
        INSERT INTO logs (user_id, username, org_id, org_name, action, action_type, target_type, target_id, ip_address, details)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, username, org_id, org_name, action, action_type, target_type, target_id, ip_address, details))

def add_message(user_id, title, content, msg_type='system'):
    """添加消息通知"""
    execute_query('''
        INSERT INTO messages (user_id, title, content, type)
        VALUES (?, ?, ?, ?)
    ''', (user_id, title, content, msg_type))

def add_todo(user_id, title, content, todo_type='general', related_id=None, priority=1, due_date=None):
    """添加待办事项"""
    execute_query('''
        INSERT INTO todos (user_id, title, content, type, related_id, priority, due_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, title, content, todo_type, related_id, priority, due_date))

# ==================== 认证函数 ====================
def hash_password(password):
    """密码哈希"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password, password_hash):
    """验证密码"""
    if isinstance(password_hash, str):
        password_hash = password_hash.encode('utf-8')
    return bcrypt.checkpw(password.encode('utf-8'), password_hash)

def authenticate_user(login_id, password):
    """用户认证 - 支持用户名/手机号/邮箱登录"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 尝试通过用户名、手机号或邮箱查找用户
    cursor.execute('''
        SELECT * FROM users 
        WHERE (username = ? OR phone = ? OR email = ?) AND is_active = 1
    ''', (login_id, login_id, login_id))
    
    user = cursor.fetchone()
    conn.close()
    
    if user and verify_password(password, user['password_hash']):
        return dict(user)
    return None

def get_user_by_id(user_id):
    """根据ID获取用户"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def change_password(user_id, new_password):
    """修改密码"""
    password_hash = hash_password(new_password)
    execute_query('''
        UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (password_hash, user_id))

# ==================== 登录页面 ====================
def render_login_page():
    """渲染登录页面"""
    # 页面背景
    st.markdown("""
    <style>
    .login-background {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(180deg, #00264D 0%, #001f3b 100%);
        z-index: -1;
    }
    
    .login-card {
        max-width: 420px;
        margin: 0 auto;
        margin-top: 80px;
        padding: 40px;
        background: linear-gradient(135deg, #008B8B 0%, #005f6b 60%, rgba(0,38,77,0.95) 100%);
        border-radius: 20px;
        box-shadow: 0 25px 60px rgba(0,0,0,0.45);
        color: #ffffff;
    }
    
    .login-header {
        text-align: center;
        margin-bottom: 35px;
    }
    
    .login-logo {
        font-size: 50px;
        margin-bottom: 15px;
    }
    
    .login-title {
        font-size: 26px;
        font-weight: bold;
        color: #ffffff;
        margin-bottom: 8px;
        text-shadow: 0 2px 6px rgba(0,0,0,0.6);
    }
    
    .login-subtitle {
        font-size: 14px;
        color: rgba(255,255,255,0.85);
    }
    
    .client-type-label {
        font-size: 14px;
        color: rgba(255,255,255,0.9);
        margin-bottom: 8px;
        font-weight: 600;
    }
    
    .login-footer {
        text-align: center;
        margin-top: 25px;
        padding-top: 20px;
        border-top: 1px solid rgba(255,255,255,0.06);
        color: rgba(255,255,255,0.7);
        font-size: 12px;
    }
    
    /* 输入框样式 */
    .stTextInput > div > div > input {
        border-radius: 10px;
        border: 2px solid rgba(255,255,255,0.12);
        padding: 12px 15px;
        font-size: 15px;
        background: rgba(255,255,255,0.04);
        color: #ffffff;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: rgba(0,163,163,0.9);
        box-shadow: 0 0 0 4px rgba(0,163,163,0.08);
    }
    
    /* 选择框样式 */
    .stSelectbox > div > div > select {
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        padding: 10px 15px;
    }
    
    /* 登录按钮 */
    .login-button {
        width: 100%;
        padding: 15px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .login-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
    }
    </style>
    
    <div class="login-background"></div>
    """, unsafe_allow_html=True)
    
    # 登录卡片
    st.markdown('<div class="login-card">', unsafe_allow_html=True)
    
    # 头部
    st.markdown("""
    <div class="login-header">
        <div class="login-logo">📊</div>
        <div class="login-title">第三方绩效评估管理平台</div>
        <div class="login-subtitle">Third-Party Performance Evaluation Platform</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 登录表单
    with st.form("login_form", clear_on_submit=False):
        # 客户端类型选择
        st.markdown('<div class="client-type-label">客户端类型</div>', unsafe_allow_html=True)
        client_type = st.selectbox(
            "客户端类型",
            options=["自动识别", "管理端", "机构端"],
            label_visibility="collapsed"
        )
        
        # 登录账号
        login_id = st.text_input(
            "登录账号",
            placeholder="请输入账号/手机号 / 邮箱",
            label_visibility="collapsed"
        )
        
        # 密码
        password = st.text_input(
            "密码",
            type="password",
            placeholder="请输入密码",
            label_visibility="collapsed"
        )
        
        # 登录按钮
        submit_button = st.form_submit_button("登 录", use_container_width=True)
        
        if submit_button:
            if not login_id or not password:
                st.error("请输入登录账号和密码")
            else:
                user = authenticate_user(login_id, password)
                
                if user:
                    # 根据客户端类型验证
                    actual_client = ""
                    if client_type == "自动识别":
                        if user['role'] == 'super_admin':
                            actual_client = "管理端"
                        else:
                            actual_client = "机构端"
                    elif client_type == "管理端":
                        if user['role'] != 'super_admin':
                            st.error("该账号无权访问管理端")
                            st.stop()
                        actual_client = "管理端"
                    else:  # 机构端
                        if user['role'] == 'super_admin':
                            st.error("超级管理员请使用管理端登录")
                            st.stop()
                        actual_client = "机构端"
                    
                    # 登录成功
                    st.session_state['logged_in'] = True
                    st.session_state['user'] = user
                    st.session_state['client_type'] = actual_client
                    
                    # 获取机构名称
                    org_name = ""
                    if user['org_id']:
                        org = execute_query("SELECT name FROM organizations WHERE id = ?", (user['org_id'],), fetch=True)
                        if org:
                            org_name = org[0]['name']
                    
                    # 记录登录日志
                    add_log(user['id'], user['username'], user['org_id'], org_name, 
                           f"用户登录成功 - {actual_client}", '登录')
                    
                    # 添加登录成功消息
                    add_message(user['id'], '登录成功', f'您于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} 成功登录系统')
                    
                    st.rerun()
                else:
                    st.error("登录账号或密码错误")
    
    # 底部
    st.markdown("""
    <div class="login-footer">
        © 2026 第三方绩效评估管理平台 · 技术支持
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

# ==================== 侧边栏 ====================
def render_sidebar():
    """渲染侧边栏"""
    user = st.session_state['user']
    role = user['role']
    client_type = st.session_state.get('client_type', '机构端')
    
    with st.sidebar:
        # 用户信息
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 20px; border-radius: 15px; margin-bottom: 20px; color: white;">
            <div style="font-size: 18px; font-weight: bold; margin-bottom: 5px;">
                {user.get('real_name') or user['username']}
            </div>
            <div style="font-size: 12px; opacity: 0.9;">
                {'超级管理员' if role == 'super_admin' else ('机构主账号' if role == 'org_admin' else '机构子账号')}
            </div>
            <div style="font-size: 12px; opacity: 0.8; margin-top: 5px;">
                🖥️ {client_type}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 导航菜单
        if role == 'super_admin':
            # 管理端菜单
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
            # 机构端菜单
            menu_items = [
                ("🏠", "工作台", "dashboard"),
                ("🏢", "信息维护", "info"),
                ("👥", "子账号管理", "sub_accounts"),
                ("📋", "项目管理", "projects"),
                ("📚", "项目智库", "knowledge"),
                ("✅", "待办事项", "todos"),
                ("📨", "消息通知", "messages"),
            ]
        
        for icon, name, page in menu_items:
            if st.button(f"{icon} {name}", key=f"nav_{page}", use_container_width=True):
                st.session_state['current_page'] = page
                st.rerun()
        
        st.markdown("---")
        
        # 修改密码
        with st.expander("🔐 修改密码"):
            with st.form("change_password_form"):
                old_password = st.text_input("原密码", type="password")
                new_password = st.text_input("新密码", type="password")
                confirm_password = st.text_input("确认新密码", type="password")
                
                if st.form_submit_button("确认修改"):
                    if not old_password or not new_password or not confirm_password:
                        st.error("请填写所有密码字段")
                    elif not verify_password(old_password, user['password_hash']):
                        st.error("原密码错误")
                    elif new_password != confirm_password:
                        st.error("两次输入的新密码不一致")
                    elif len(new_password) < 6:
                        st.error("新密码长度不能少于6位")
                    else:
                        change_password(user['id'], new_password)
                        
                        # 获取机构名称
                        org_name = ""
                        if user['org_id']:
                            org = execute_query("SELECT name FROM organizations WHERE id = ?", (user['org_id'],), fetch=True)
                            if org:
                                org_name = org[0]['name']
                        
                        add_log(user['id'], user['username'], user['org_id'], org_name, 
                               "修改密码成功", '密码')
                        add_message(user['id'], '密码修改成功', f'您于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} 成功修改密码')
                        
                        st.success("密码修改成功！")
        
        # 退出登录
        if st.button("🚪 退出登录", use_container_width=True):
            # 获取机构名称
            org_name = ""
            if user['org_id']:
                org = execute_query("SELECT name FROM organizations WHERE id = ?", (user['org_id'],), fetch=True)
                if org:
                    org_name = org[0]['name']
            
            add_log(user['id'], user['username'], user['org_id'], org_name, "退出登录", '登录')
            st.session_state.clear()
            st.rerun()

# ==================== 管理端页面 ====================
def render_admin_dashboard():
    """管理端 - 数据大盘"""
    st.title("📊 数据大盘")
    
    # 获取统计数据
    # 机构总数
    org_count = execute_query("SELECT COUNT(*) as cnt FROM organizations", fetch=True)[0]['cnt']
    
    # 启用的机构数
    active_org_count = execute_query("SELECT COUNT(*) as cnt FROM organizations WHERE is_active = 1", fetch=True)[0]['cnt']
    
    # 用户总数
    user_count = execute_query("SELECT COUNT(*) as cnt FROM users", fetch=True)[0]['cnt']
    
    # 进行中的项目（启用的机构下的项目）
    active_projects = execute_query('''
        SELECT COUNT(*) as cnt FROM projects p
        JOIN organizations o ON p.org_id = o.id
        WHERE o.is_active = 1 AND p.status = 'in_progress'
    ''', fetch=True)[0]['cnt']
    
    # 已完成的项目（所有机构已完成的项目）
    completed_projects = execute_query('''
        SELECT COUNT(*) as cnt FROM projects WHERE status = 'completed'
    ''', fetch=True)[0]['cnt']
    
    # 待审核项目
    pending_projects = execute_query('''
        SELECT COUNT(*) as cnt FROM project_steps WHERE status = 'pending'
    ''', fetch=True)[0]['cnt']
    
    # 统计卡片
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <div class="stat-number">{org_count}</div>
            <div class="stat-label">机构总数</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="stat-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
            <div class="stat-number">{user_count}</div>
            <div class="stat-label">用户总数</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <div class="stat-number">{active_projects}</div>
            <div class="stat-label">进行中项目</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <div class="stat-number">{completed_projects}</div>
            <div class="stat-label">已完成项目</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div class="stat-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <div class="stat-number">{pending_projects}</div>
            <div class="stat-label">待审核</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 图表区域
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 项目状态分布")
        
        # 项目状态统计
        status_data = execute_query('''
            SELECT status, COUNT(*) as cnt FROM projects GROUP BY status
        ''', fetch=True)
        
        if status_data:
            df_status = pd.DataFrame([dict(row) for row in status_data])
            status_map = {
                'pending': '待审核',
                'in_progress': '进行中',
                'completed': '已完成',
                'rejected': '已驳回'
            }
            df_status['status_name'] = df_status['status'].map(status_map)
            
            fig = px.pie(df_status, values='cnt', names='status_name', 
                        color_discrete_sequence=px.colors.sequential.Plasma)
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无项目数据")
    
    with col2:
        st.subheader("🏢 各机构项目统计")
        
        # 各机构项目数
        org_projects = execute_query('''
            SELECT o.name, COUNT(p.id) as project_count
            FROM organizations o
            LEFT JOIN projects p ON o.id = p.org_id
            GROUP BY o.id
            ORDER BY project_count DESC
            LIMIT 10
        ''', fetch=True)
        
        if org_projects:
            df_org = pd.DataFrame([dict(row) for row in org_projects])
            fig = px.bar(df_org, x='name', y='project_count',
                        color='project_count',
                        color_continuous_scale='Viridis')
            fig.update_layout(height=350, xaxis_title="机构名称", yaxis_title="项目数量")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无机构数据")
    
    # 最近项目
    st.subheader("📋 最近项目")
    recent_projects = execute_query('''
        SELECT p.*, o.name as org_name, u.username as creator_name
        FROM projects p
        JOIN organizations o ON p.org_id = o.id
        LEFT JOIN users u ON p.created_by = u.id
        ORDER BY p.created_at DESC
        LIMIT 10
    ''', fetch=True)
    
    if recent_projects:
        df_projects = pd.DataFrame([dict(row) for row in recent_projects])
        df_projects['created_at'] = pd.to_datetime(df_projects['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        status_map = {'pending': '待审核', 'in_progress': '进行中', 'completed': '已完成', 'rejected': '已驳回'}
        df_projects['status_name'] = df_projects['status'].map(status_map)
        
        st.dataframe(df_projects[['name', 'org_name', 'status_name', 'current_stage', 'created_at', 'creator_name']],
                    use_container_width=True,
                    column_config={
                        'name': '项目名称',
                        'org_name': '所属机构',
                        'status_name': '状态',
                        'current_stage': '当前阶段',
                        'created_at': '创建时间',
                        'creator_name': '创建人'
                    })
    else:
        st.info("暂无项目数据")

def render_admin_organizations():
    """管理端 - 机构管理"""
    st.title("🏢 机构管理")
    
    user = st.session_state['user']
    
    # 操作标签页
    tab1, tab2 = st.tabs(["机构列表", "新增机构"])
    
    with tab1:
        # 机构列表
        orgs = execute_query('''
            SELECT o.*, 
                   (SELECT COUNT(*) FROM users WHERE org_id = o.id) as user_count,
                   (SELECT COUNT(*) FROM projects WHERE org_id = o.id) as project_count
            FROM organizations o
            ORDER BY o.created_at DESC
        ''', fetch=True)
        
        if orgs:
            for org in orgs:
                org_dict = dict(org)
                status_color = "#28a745" if org_dict['is_active'] else "#dc3545"
                status_text = "启用" if org_dict['is_active'] else "停用"
                
                with st.container():
                    st.markdown(f"""
                    <div style="background: white; border-radius: 15px; padding: 20px; margin-bottom: 15px; 
                                box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <h3 style="margin: 0; color: #1a1a2e;">{org_dict['name']}</h3>
                                <p style="color: #666; margin: 5px 0;">
                                    类型: {org_dict['org_type'] or '-'} | 
                                    信用代码: {org_dict['credit_code'] or '-'} |
                                    法人: {org_dict['legal_person'] or '-'}
                                </p>
                            </div>
                            <div style="text-align: right;">
                                <span style="background: {status_color}; color: white; padding: 5px 15px; 
                                            border-radius: 20px; font-size: 12px;">{status_text}</span>
                            </div>
                        </div>
                        <hr style="margin: 15px 0; border-color: #eee;">
                        <div style="display: flex; gap: 30px; color: #666; font-size: 14px;">
                            <span>👤 联系人: {org_dict['contact_person'] or '-'}</span>
                            <span>📞 电话: {org_dict['contact_phone'] or '-'}</span>
                            <span>📧 邮箱: {org_dict['contact_email'] or '-'}</span>
                            <span>👥 用户数: {org_dict['user_count']}</span>
                            <span>📋 项目数: {org_dict['project_count']}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if st.button("📝 编辑", key=f"edit_org_{org_dict['id']}"):
                            st.session_state['edit_org_id'] = org_dict['id']
                            st.rerun()
                    
                    with col2:
                        if org_dict['is_active']:
                            if st.button("⏸️ 停用", key=f"deactivate_org_{org_dict['id']}"):
                                execute_query("UPDATE organizations SET is_active = 0 WHERE id = ?", (org_dict['id'],))
                                add_log(user['id'], user['username'], None, None, f"停用机构: {org_dict['name']}", '机构管理')
                                st.success("机构已停用")
                                st.rerun()
                        else:
                            if st.button("▶️ 启用", key=f"activate_org_{org_dict['id']}"):
                                execute_query("UPDATE organizations SET is_active = 1 WHERE id = ?", (org_dict['id'],))
                                add_log(user['id'], user['username'], None, None, f"启用机构: {org_dict['name']}", '机构管理')
                                st.success("机构已启用")
                                st.rerun()
                    
                    with col3:
                        # 查看详情
                        if st.button("🔍 详情", key=f"view_org_{org_dict['id']}"):
                            st.session_state['view_org_id'] = org_dict['id']
                    
                    with col4:
                        if st.button("🗑️ 删除", key=f"delete_org_{org_dict['id']}"):
                            # 检查是否有关联数据
                            if org_dict['user_count'] > 0 or org_dict['project_count'] > 0:
                                st.error("该机构下有关联用户或项目，无法删除")
                            else:
                                execute_query("DELETE FROM organizations WHERE id = ?", (org_dict['id'],))
                                add_log(user['id'], user['username'], None, None, f"删除机构: {org_dict['name']}", '机构管理')
                                st.success("机构已删除")
                                st.rerun()
        
        # 编辑机构弹窗
        if 'edit_org_id' in st.session_state:
            st.markdown("---")
            st.subheader("编辑机构")
            
            org_id = st.session_state['edit_org_id']
            org_data = execute_query("SELECT * FROM organizations WHERE id = ?", (org_id,), fetch=True)
            
            if org_data:
                org_dict = dict(org_data[0])
                
                with st.form("edit_org_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        name = st.text_input("机构名称 *", value=org_dict['name'])
                        org_type = st.text_input("机构类型", value=org_dict['org_type'] or '')
                        credit_code = st.text_input("统一社会信用代码", value=org_dict['credit_code'] or '')
                        legal_person = st.text_input("法定代表人", value=org_dict['legal_person'] or '')
                        contact_person = st.text_input("联系人 *", value=org_dict['contact_person'] or '')
                    
                    with col2:
                        contact_phone = st.text_input("联系电话 *", value=org_dict['contact_phone'] or '')
                        contact_email = st.text_input("联系邮箱 *", value=org_dict['contact_email'] or '')
                        address = st.text_input("机构地址", value=org_dict['address'] or '')
                    
                    description = st.text_area("机构简介（选填）", value=org_dict['description'] or '')
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("保存修改"):
                            if not name or not contact_person or not contact_phone or not contact_email:
                                st.error("请填写必填项（带*号的字段）")
                            else:
                                execute_query('''
                                    UPDATE organizations SET 
                                        name = ?, org_type = ?, credit_code = ?, legal_person = ?,
                                        contact_person = ?, contact_phone = ?, contact_email = ?,
                                        address = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                                    WHERE id = ?
                                ''', (name, org_type, credit_code, legal_person, contact_person, 
                                     contact_phone, contact_email, address, description, org_id))
                                
                                add_log(user['id'], user['username'], None, None, f"编辑机构: {name}", '机构管理')
                                st.success("机构信息已更新")
                                del st.session_state['edit_org_id']
                                st.rerun()
                    
                    with col2:
                        if st.form_submit_button("取消"):
                            del st.session_state['edit_org_id']
                            st.rerun()
        
        # 查看机构详情
        if 'view_org_id' in st.session_state:
            st.markdown("---")
            st.subheader("机构详情")
            
            org_id = st.session_state['view_org_id']
            org_data = execute_query("SELECT * FROM organizations WHERE id = ?", (org_id,), fetch=True)
            
            if org_data:
                org_dict = dict(org_data[0])
                
                st.json(org_dict)
                
                if st.button("关闭详情"):
                    del st.session_state['view_org_id']
                    st.rerun()
        
        else:
            st.info("暂无机构数据")
    
    with tab2:
        st.subheader("新增机构")
        
        with st.form("add_org_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("机构名称 *")
                org_type = st.text_input("机构类型")
                credit_code = st.text_input("统一社会信用代码")
                legal_person = st.text_input("法定代表人")
                contact_person = st.text_input("联系人 *")
            
            with col2:
                contact_phone = st.text_input("联系电话 *")
                contact_email = st.text_input("联系邮箱 *")
                address = st.text_input("机构地址")
            
            description = st.text_area("机构简介（选填）")
            
            if st.form_submit_button("创建机构"):
                if not name or not contact_person or not contact_phone or not contact_email:
                    st.error("请填写必填项（带*号的字段）")
                else:
                    # 创建机构
                    org_id = execute_query('''
                        INSERT INTO organizations (name, org_type, credit_code, legal_person, 
                                                  contact_person, contact_phone, contact_email, address, description)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (name, org_type, credit_code, legal_person, contact_person, 
                         contact_phone, contact_email, address, description))
                    
                    # 创建机构主账号
                    username = f"org_{org_id}"
                    default_password = "Org@123456"
                    password_hash = hash_password(default_password)
                    
                    user_id = execute_query('''
                        INSERT INTO users (username, password_hash, role, org_id, real_name, phone, email)
                        VALUES (?, ?, 'org_admin', ?, ?, ?, ?)
                    ''', (username, password_hash, org_id, contact_person, contact_phone, contact_email))
                    
                    add_log(user['id'], user['username'], None, None, f"新增机构: {name}", '机构管理')
                    
                    st.success(f"机构创建成功！主账号: {username}，默认密码: {default_password}")

def render_admin_users():
    """管理端 - 账号管理"""
    st.title("👥 账号管理")
    
    user = st.session_state['user']
    
    # 筛选
    col1, col2, col3 = st.columns(3)
    
    with col1:
        role_filter = st.selectbox("角色筛选", ["全部", "超级管理员", "机构主账号", "机构子账号"])
    
    with col2:
        org_filter = st.selectbox("机构筛选", ["全部"] + [dict(r)['name'] for r in execute_query("SELECT name FROM organizations", fetch=True)])
    
    with col3:
        status_filter = st.selectbox("状态筛选", ["全部", "启用", "冻结"])
    
    # 构建查询
    query = '''
        SELECT u.*, o.name as org_name
        FROM users u
        LEFT JOIN organizations o ON u.org_id = o.id
        WHERE 1=1
    '''
    params = []
    
    if role_filter != "全部":
        role_map = {"超级管理员": "super_admin", "机构主账号": "org_admin", "机构子账号": "org_user"}
        query += " AND u.role = ?"
        params.append(role_map[role_filter])
    
    if org_filter != "全部":
        query += " AND o.name = ?"
        params.append(org_filter)
    
    if status_filter != "全部":
        query += " AND u.is_active = ?"
        params.append(1 if status_filter == "启用" else 0)
    
    query += " ORDER BY u.created_at DESC"
    
    users = execute_query(query, params if params else None, fetch=True)
    
    if users:
        # 用户列表
        for u in users:
            u_dict = dict(u)
            status_color = "#28a745" if u_dict['is_active'] else "#dc3545"
            status_text = "启用" if u_dict['is_active'] else "冻结"
            role_map = {"super_admin": "超级管理员", "org_admin": "机构主账号", "org_user": "机构子账号"}
            
            with st.container():
                st.markdown(f"""
                <div style="background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong style="font-size: 16px;">{u_dict['real_name'] or u_dict['username']}</strong>
                            <span style="background: #667eea; color: white; padding: 2px 8px; border-radius: 10px; 
                                        font-size: 11px; margin-left: 10px;">{role_map.get(u_dict['role'], u_dict['role'])}</span>
                            <span style="background: {status_color}; color: white; padding: 2px 8px; border-radius: 10px; 
                                        font-size: 11px; margin-left: 5px;">{status_text}</span>
                        </div>
                        <div style="color: #666; font-size: 13px;">
                            📞 {u_dict['phone'] or '-'} | 📧 {u_dict['email'] or '-'} | 🏢 {u_dict['org_name'] or '-'}
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if u_dict['role'] != 'super_admin':
                        if u_dict['is_active']:
                            if st.button("🔒 冻结", key=f"freeze_user_{u_dict['id']}"):
                                execute_query("UPDATE users SET is_active = 0 WHERE id = ?", (u_dict['id'],))
                                add_log(user['id'], user['username'], None, None, f"冻结用户: {u_dict['username']}", '账号管理')
                                st.success("用户已冻结")
                                st.rerun()
                        else:
                            if st.button("🔓 启用", key=f"activate_user_{u_dict['id']}"):
                                execute_query("UPDATE users SET is_active = 1 WHERE id = ?", (u_dict['id'],))
                                add_log(user['id'], user['username'], None, None, f"启用用户: {u_dict['username']}", '账号管理')
                                st.success("用户已启用")
                                st.rerun()
                
                with col2:
                    if st.button("🔑 重置密码", key=f"reset_pwd_{u_dict['id']}"):
                        new_pwd = "Reset@123456"
                        pwd_hash = hash_password(new_pwd)
                        execute_query("UPDATE users SET password_hash = ? WHERE id = ?", (pwd_hash, u_dict['id']))
                        add_log(user['id'], user['username'], None, None, f"重置用户密码: {u_dict['username']}", '账号管理')
                        st.success(f"密码已重置为: {new_pwd}")
                
                with col3:
                    if u_dict['role'] != 'super_admin':
                        if st.button("📝 修改", key=f"edit_user_{u_dict['id']}"):
                            st.session_state['edit_user_id'] = u_dict['id']
                            st.rerun()
                
                with col4:
                    if u_dict['role'] != 'super_admin':
                        if st.button("🗑️ 删除", key=f"delete_user_{u_dict['id']}"):
                            execute_query("DELETE FROM users WHERE id = ?", (u_dict['id'],))
                            add_log(user['id'], user['username'], None, None, f"删除用户: {u_dict['username']}", '账号管理')
                            st.success("用户已删除")
                            st.rerun()
        
        # 编辑用户弹窗
        if 'edit_user_id' in st.session_state:
            st.markdown("---")
            st.subheader("编辑用户")
            
            edit_user_id = st.session_state['edit_user_id']
            edit_user_data = execute_query("SELECT * FROM users WHERE id = ?", (edit_user_id,), fetch=True)
            
            if edit_user_data:
                edit_dict = dict(edit_user_data[0])
                
                with st.form("edit_user_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edit_username = st.text_input("用户名 *", value=edit_dict['username'])
                        edit_real_name = st.text_input("姓名 *", value=edit_dict['real_name'] or '')
                        edit_phone = st.text_input("手机号 *", value=edit_dict['phone'] or '')
                    
                    with col2:
                        edit_email = st.text_input("邮箱 *", value=edit_dict['email'] or '')
                        edit_role = st.selectbox("角色", ["机构主账号", "机构子账号"], 
                                                index=0 if edit_dict['role'] == 'org_admin' else 1)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("保存"):
                            if not edit_username or not edit_real_name or not edit_phone or not edit_email:
                                st.error("请填写所有必填项")
                            else:
                                role_value = 'org_admin' if edit_role == "机构主账号" else 'org_user'
                                execute_query('''
                                    UPDATE users SET username = ?, real_name = ?, phone = ?, email = ?, role = ?
                                    WHERE id = ?
                                ''', (edit_username, edit_real_name, edit_phone, edit_email, role_value, edit_user_id))
                                
                                add_log(user['id'], user['username'], None, None, f"编辑用户: {edit_username}", '账号管理')
                                st.success("用户信息已更新")
                                del st.session_state['edit_user_id']
                                st.rerun()
                    
                    with col2:
                        if st.form_submit_button("取消"):
                            del st.session_state['edit_user_id']
                            st.rerun()
    
    else:
        st.info("暂无用户数据")
    
    # 新增用户
    st.markdown("---")
    st.subheader("新增用户")
    
    orgs = execute_query("SELECT id, name FROM organizations WHERE is_active = 1", fetch=True)
    
    if orgs:
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("用户名 *")
                new_real_name = st.text_input("姓名 *")
                new_phone = st.text_input("手机号 *")
            
            with col2:
                new_email = st.text_input("邮箱 *")
                new_role = st.selectbox("角色 *", ["机构主账号", "机构子账号"])
                new_org = st.selectbox("所属机构 *", [dict(r)['name'] for r in orgs])
            
            if st.form_submit_button("创建用户"):
                if not new_username or not new_real_name or not new_phone or not new_email or not new_org:
                    st.error("请填写所有必填项")
                else:
                    # 检查用户名是否已存在
                    existing = execute_query("SELECT id FROM users WHERE username = ?", (new_username,), fetch=True)
                    if existing:
                        st.error("用户名已存在")
                    else:
                        # 获取机构ID
                        org_id = None
                        for o in orgs:
                            if dict(o)['name'] == new_org:
                                org_id = dict(o)['id']
                                break
                        
                        role_value = 'org_admin' if new_role == "机构主账号" else 'org_user'
                        default_pwd = "User@123456"
                        pwd_hash = hash_password(default_pwd)
                        
                        execute_query('''
                            INSERT INTO users (username, password_hash, role, org_id, real_name, phone, email)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (new_username, pwd_hash, role_value, org_id, new_real_name, new_phone, new_email))
                        
                        add_log(user['id'], user['username'], None, None, f"新增用户: {new_username}", '账号管理')
                        st.success(f"用户创建成功！默认密码: {default_pwd}")
    else:
        st.warning("请先创建机构")

def render_admin_projects():
    """管理端 - 项目审核"""
    st.title("📋 项目审核")
    
    user = st.session_state['user']
    
    # 筛选
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox("审核状态", ["全部", "待审核", "已通过", "已驳回"])
    
    with col2:
        stage_filter = st.selectbox("项目阶段", ["全部", "阶段1", "阶段2", "阶段3", "阶段4", "阶段5"])
    
    with col3:
        org_filter = st.selectbox("所属机构", ["全部"] + [dict(r)['name'] for r in execute_query("SELECT name FROM organizations", fetch=True)])
    
    # 构建查询
    query = '''
        SELECT ps.*, p.name as project_name, p.project_code, o.name as org_name,
               u1.username as submitter_name, u2.username as reviewer_name
        FROM project_steps ps
        JOIN projects p ON ps.project_id = p.id
        JOIN organizations o ON p.org_id = o.id
        LEFT JOIN users u1 ON ps.submitted_by = u1.id
        LEFT JOIN users u2 ON ps.reviewed_by = u2.id
        WHERE 1=1
    '''
    params = []
    
    if status_filter != "全部":
        status_map = {"待审核": "pending", "已通过": "approved", "已驳回": "rejected"}
        query += " AND ps.status = ?"
        params.append(status_map[status_filter])
    
    if stage_filter != "全部":
        query += " AND ps.stage = ?"
        params.append(int(stage_filter.replace("阶段", "")))
    
    if org_filter != "全部":
        query += " AND o.name = ?"
        params.append(org_filter)
    
    query += " ORDER BY ps.submitted_at DESC NULLS LAST, ps.created_at DESC"
    
    steps = execute_query(query, params if params else None, fetch=True)
    
    if steps:
        stage_names = {
            1: "阶段1: 项目立项",
            2: "阶段2: 方案设计", 
            3: "阶段3: 数据采集",
            4: "阶段4: 分析评估",
            5: "阶段5: 报告编制"
        }
        
        for step in steps:
            step_dict = dict(step)
            
            status_color = {"pending": "#ffc107", "approved": "#28a745", "rejected": "#dc3545"}
            status_text = {"pending": "待审核", "approved": "已通过", "rejected": "已驳回"}
            
            with st.container():
                st.markdown(f"""
                <div style="background: white; border-radius: 15px; padding: 20px; margin-bottom: 15px; 
                            box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 5px solid {status_color.get(step_dict['status'], '#666')};">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <div>
                            <h4 style="margin: 0; color: #1a1a2e;">{step_dict['project_name']}</h4>
                            <span style="color: #666; font-size: 13px;">
                                项目编号: {step_dict['project_code'] or '-'} | 所属机构: {step_dict['org_name']}
                            </span>
                        </div>
                        <span style="background: {status_color.get(step_dict['status'], '#666')}; color: white; 
                                    padding: 5px 15px; border-radius: 20px; font-size: 12px;">
                            {status_text.get(step_dict['status'], step_dict['status'])}
                        </span>
                    </div>
                    <div style="color: #666; font-size: 14px;">
                        <strong>{stage_names.get(step_dict['stage'], f"阶段{step_dict['stage']}")}</strong>
                        <br>提交人: {step_dict['submitter_name'] or '-'} | 
                        提交时间: {step_dict['submitted_at'] or '-'} |
                        审核人: {step_dict['reviewer_name'] or '-'} |
                        审核时间: {step_dict['reviewed_at'] or '-'}
                    </div>
                    {f'<div style="margin-top: 10px; padding: 10px; background: #f8f9fa; border-radius: 8px;"><strong>审核意见:</strong> {step_dict["review_comment"]}</div>' if step_dict['review_comment'] else ''}
                </div>
                """, unsafe_allow_html=True)
                
                if step_dict['status'] == 'pending':
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("✅ 通过", key=f"approve_{step_dict['id']}", use_container_width=True):
                            # 更新阶段状态
                            execute_query('''
                                UPDATE project_steps SET status = 'approved', reviewed_by = ?, 
                                reviewed_at = CURRENT_TIMESTAMP WHERE id = ?
                            ''', (user['id'], step_dict['id']))
                            
                            # 更新项目当前阶段
                            project = execute_query("SELECT * FROM projects WHERE id = ?", (step_dict['project_id'],), fetch=True)
                            if project:
                                proj = dict(project[0])
                                new_stage = step_dict['stage'] + 1
                                if new_stage > 5:
                                    # 项目完成
                                    execute_query("UPDATE projects SET status = 'completed', current_stage = 5 WHERE id = ?", (step_dict['project_id'],))
                                else:
                                    execute_query("UPDATE projects SET current_stage = ? WHERE id = ?", (new_stage, step_dict['project_id']))
                            
                            # 添加消息通知
                            if step_dict['submitted_by']:
                                add_message(step_dict['submitted_by'], '审核通过', 
                                          f'您的项目 {step_dict["project_name"]} {stage_names.get(step_dict["stage"], "")} 已审核通过')
                            
                            add_log(user['id'], user['username'], None, None, 
                                   f"审核通过: {step_dict['project_name']} - {stage_names.get(step_dict['stage'], '')}", '项目审核')
                            st.success("审核通过")
                            st.rerun()
                    
                    with col2:
                        # 驳回需要填写原因
                        with st.form(f"reject_form_{step_dict['id']}"):
                            reject_reason = st.text_area("驳回原因")
                            if st.form_submit_button("❌ 驳回"):
                                if not reject_reason:
                                    st.error("请填写驳回原因")
                                else:
                                    execute_query('''
                                        UPDATE project_steps SET status = 'rejected', reviewed_by = ?, 
                                        reviewed_at = CURRENT_TIMESTAMP, review_comment = ? WHERE id = ?
                                    ''', (user['id'], reject_reason, step_dict['id']))
                                    
                                    # 添加消息通知
                                    if step_dict['submitted_by']:
                                        add_message(step_dict['submitted_by'], '审核驳回', 
                                                  f'您的项目 {step_dict["project_name"]} {stage_names.get(step_dict["stage"], "")} 被驳回，原因: {reject_reason}')
                                    
                                    add_log(user['id'], user['username'], None, None, 
                                           f"审核驳回: {step_dict['project_name']} - {stage_names.get(step_dict['stage'], '')}", '项目审核')
                                    st.success("已驳回")
                                    st.rerun()
                
                st.markdown("---")
    else:
        st.info("暂无审核数据")

def render_admin_logs():
    """管理端 - 日志查看"""
    st.title("📝 操作日志")
    
    # 时间范围筛选
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        time_range = st.selectbox("时间范围", ["全部", "最近1天", "最近7天", "最近30天", "自定义"])
    
    with col2:
        user_filter = st.text_input("用户名筛选")
    
    with col3:
        action_filter = st.selectbox("操作类型", ["全部", "登录", "密码", "机构管理", "账号管理", "项目审核", "项目管理"])
    
    with col4:
        if time_range == "自定义":
            date_range = st.date_input("选择日期范围", value=(datetime.now() - timedelta(days=7), datetime.now()))
    
    # 构建查询
    query = "SELECT * FROM logs WHERE 1=1"
    params = []
    
    if time_range == "最近1天":
        query += " AND created_at >= datetime('now', '-1 day')"
    elif time_range == "最近7天":
        query += " AND created_at >= datetime('now', '-7 days')"
    elif time_range == "最近30天":
        query += " AND created_at >= datetime('now', '-30 days')"
    elif time_range == "自定义" and len(date_range) == 2:
        query += " AND date(created_at) BETWEEN ? AND ?"
        params.extend([str(date_range[0]), str(date_range[1])])
    
    if user_filter:
        query += " AND username LIKE ?"
        params.append(f"%{user_filter}%")
    
    if action_filter != "全部":
        query += " AND action_type = ?"
        params.append(action_filter)
    
    query += " ORDER BY created_at DESC LIMIT 500"
    
    logs = execute_query(query, params if params else None, fetch=True)
    
    if logs:
        df_logs = pd.DataFrame([dict(row) for row in logs])
        df_logs['created_at'] = pd.to_datetime(df_logs['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # 重命名列
        df_logs = df_logs.rename(columns={
            'id': '日志编号',
            'username': '用户名',
            'org_name': '机构名',
            'action': '操作内容',
            'action_type': '操作类型',
            'ip_address': 'IP地址',
            'created_at': '操作时间'
        })
        
        st.dataframe(df_logs[['日志编号', '用户名', '机构名', '操作内容', '操作类型', 'IP地址', '操作时间']],
                    use_container_width=True,
                    hide_index=True)
        
        # 导出按钮
        if st.button("📥 导出日志数据"):
            export_to_excel(df_logs, "操作日志")
    else:
        st.info("暂无日志数据")

def render_admin_export():
    """管理端 - 数据导出"""
    st.title("📥 数据导出")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 导出数据")
        
        export_type = st.selectbox("选择导出类型", [
            "用户数据",
            "机构数据", 
            "项目数据",
            "项目文件数据",
            "操作日志数据",
            "全部数据"
        ])
        
        if st.button("导出Excel", use_container_width=True):
            if export_type == "用户数据":
                users = execute_query("SELECT u.*, o.name as org_name FROM users u LEFT JOIN organizations o ON u.org_id = o.id", fetch=True)
                df = pd.DataFrame([dict(row) for row in users])
                export_to_excel(df, "用户数据")
            
            elif export_type == "机构数据":
                orgs = execute_query("SELECT * FROM organizations", fetch=True)
                df = pd.DataFrame([dict(row) for row in orgs])
                export_to_excel(df, "机构数据")
            
            elif export_type == "项目数据":
                projects = execute_query('''
                    SELECT p.*, o.name as org_name, u.username as creator_name
                    FROM projects p
                    LEFT JOIN organizations o ON p.org_id = o.id
                    LEFT JOIN users u ON p.created_by = u.id
                ''', fetch=True)
                df = pd.DataFrame([dict(row) for row in projects])
                export_to_excel(df, "项目数据")
            
            elif export_type == "项目文件数据":
                files = execute_query('''
                    SELECT pf.*, p.name as project_name, u.username as uploader_name
                    FROM project_files pf
                    LEFT JOIN projects p ON pf.project_id = p.id
                    LEFT JOIN users u ON pf.uploaded_by = u.id
                ''', fetch=True)
                df = pd.DataFrame([dict(row) for row in files])
                export_to_excel(df, "项目文件数据")
            
            elif export_type == "操作日志数据":
                logs = execute_query("SELECT * FROM logs ORDER BY created_at DESC", fetch=True)
                df = pd.DataFrame([dict(row) for row in logs])
                export_to_excel(df, "操作日志数据")
            
            elif export_type == "全部数据":
                # 导出所有数据到多个sheet
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # 用户数据
                    users = execute_query("SELECT u.*, o.name as org_name FROM users u LEFT JOIN organizations o ON u.org_id = o.id", fetch=True)
                    if users:
                        pd.DataFrame([dict(row) for row in users]).to_excel(writer, sheet_name='用户数据', index=False)
                    
                    # 机构数据
                    orgs = execute_query("SELECT * FROM organizations", fetch=True)
                    if orgs:
                        pd.DataFrame([dict(row) for row in orgs]).to_excel(writer, sheet_name='机构数据', index=False)
                    
                    # 项目数据
                    projects = execute_query('''
                        SELECT p.*, o.name as org_name FROM projects p
                        LEFT JOIN organizations o ON p.org_id = o.id
                    ''', fetch=True)
                    if projects:
                        pd.DataFrame([dict(row) for row in projects]).to_excel(writer, sheet_name='项目数据', index=False)
                    
                    # 文件数据
                    files = execute_query("SELECT * FROM project_files", fetch=True)
                    if files:
                        pd.DataFrame([dict(row) for row in files]).to_excel(writer, sheet_name='项目文件', index=False)
                    
                    # 日志数据
                    logs = execute_query("SELECT * FROM logs", fetch=True)
                    if logs:
                        pd.DataFrame([dict(row) for row in logs]).to_excel(writer, sheet_name='操作日志', index=False)
                
                output.seek(0)
                st.download_button(
                    label="下载全部数据Excel",
                    data=output,
                    file_name=f"全部数据_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    
    with col2:
        st.subheader("📥 导入数据")
        
        import_type = st.selectbox("选择导入类型", [
            "用户数据",
            "机构数据",
            "项目数据"
        ])
        
        uploaded_file = st.file_uploader("上传Excel文件", type=['xlsx', 'xls'])
        
        if uploaded_file and st.button("导入数据", use_container_width=True):
            try:
                df = pd.read_excel(uploaded_file)
                st.write("预览数据:")
                st.dataframe(df.head())
                
                # 这里可以添加具体的导入逻辑
                st.success(f"成功读取 {len(df)} 条数据")
            except Exception as e:
                st.error(f"导入失败: {str(e)}")

def export_to_excel(df, filename):
    """导出DataFrame到Excel"""
    if df.empty:
        st.warning("没有数据可导出")
        return
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=filename, index=False)
    
    output.seek(0)
    st.download_button(
        label=f"下载 {filename}",
        data=output,
        file_name=f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def render_admin_approval():
    """管理端 - 审批待办"""
    st.title("✅ 审批待办")
    
    user = st.session_state['user']
    
    # 获取待审核的项目阶段
    pending_steps = execute_query('''
        SELECT ps.*, p.name as project_name, p.project_code, o.name as org_name,
               u.username as submitter_name
        FROM project_steps ps
        JOIN projects p ON ps.project_id = p.id
        JOIN organizations o ON p.org_id = o.id
        LEFT JOIN users u ON ps.submitted_by = u.id
        WHERE ps.status = 'pending'
        ORDER BY ps.submitted_at DESC NULLS LAST
    ''', fetch=True)
    
    # 获取待审核的项目文件
    pending_files = execute_query('''
        SELECT pf.*, p.name as project_name, o.name as org_name, u.username as uploader_name
        FROM project_files pf
        JOIN projects p ON pf.project_id = p.id
        JOIN organizations o ON p.org_id = o.id
        LEFT JOIN users u ON pf.uploaded_by = u.id
        WHERE pf.status = 'pending'
        ORDER BY pf.upload_time DESC
    ''', fetch=True)
    
    tab1, tab2 = st.tabs([f"项目阶段审核 ({len(pending_steps) if pending_steps else 0})", 
                         f"项目文件审核 ({len(pending_files) if pending_files else 0})"])
    
    stage_names = {
        1: "阶段1: 项目立项",
        2: "阶段2: 方案设计", 
        3: "阶段3: 数据采集",
        4: "阶段4: 分析评估",
        5: "阶段5: 报告编制"
    }
    
    with tab1:
        if pending_steps:
            for step in pending_steps:
                step_dict = dict(step)
                
                with st.container():
                    st.markdown(f"""
                    <div style="background: white; border-radius: 15px; padding: 20px; margin-bottom: 15px; 
                                box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 5px solid #ffc107;">
                        <h4 style="margin: 0;">{step_dict['project_name']}</h4>
                        <p style="color: #666; margin: 5px 0;">
                            项目编号: {step_dict['project_code'] or '-'} | 
                            所属机构: {step_dict['org_name']} |
                            当前阶段: {stage_names.get(step_dict['stage'], f"阶段{step_dict['stage']}")}
                        </p>
                        <p style="color: #888; font-size: 13px;">
                            提交人: {step_dict['submitter_name'] or '-'} | 
                            提交时间: {step_dict['submitted_at'] or '-'}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(f"✅ 通过", key=f"todo_approve_{step_dict['id']}", use_container_width=True):
                            execute_query('''
                                UPDATE project_steps SET status = 'approved', reviewed_by = ?, 
                                reviewed_at = CURRENT_TIMESTAMP WHERE id = ?
                            ''', (user['id'], step_dict['id']))
                            
                            # 更新项目状态
                            new_stage = step_dict['stage'] + 1
                            if new_stage > 5:
                                execute_query("UPDATE projects SET status = 'completed' WHERE id = ?", (step_dict['project_id'],))
                            else:
                                execute_query("UPDATE projects SET current_stage = ? WHERE id = ?", (new_stage, step_dict['project_id']))
                            
                            if step_dict['submitted_by']:
                                add_message(step_dict['submitted_by'], '审核通过', 
                                          f'您的项目 {step_dict["project_name"]} {stage_names.get(step_dict["stage"], "")} 已审核通过')
                            
                            add_log(user['id'], user['username'], None, None, 
                                   f"审批通过: {step_dict['project_name']}", '项目审核')
                            st.success("已通过")
                            st.rerun()
                    
                    with col2:
                        with st.form(f"todo_reject_{step_dict['id']}"):
                            reason = st.text_input("驳回原因")
                            if st.form_submit_button("❌ 驳回", use_container_width=True):
                                if not reason:
                                    st.error("请填写驳回原因")
                                else:
                                    execute_query('''
                                        UPDATE project_steps SET status = 'rejected', reviewed_by = ?, 
                                        reviewed_at = CURRENT_TIMESTAMP, review_comment = ? WHERE id = ?
                                    ''', (user['id'], reason, step_dict['id']))
                                    
                                    if step_dict['submitted_by']:
                                        add_message(step_dict['submitted_by'], '审核驳回', 
                                                  f'您的项目 {step_dict["project_name"]} 被驳回，原因: {reason}')
                                    
                                    add_log(user['id'], user['username'], None, None, 
                                           f"审批驳回: {step_dict['project_name']}", '项目审核')
                                    st.success("已驳回")
                                    st.rerun()
        else:
            st.info("暂无待审核的项目阶段")
    
    with tab2:
        if pending_files:
            for file in pending_files:
                file_dict = dict(file)
                
                with st.container():
                    st.markdown(f"""
                    <div style="background: white; border-radius: 15px; padding: 20px; margin-bottom: 15px; 
                                box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 5px solid #17a2b8;">
                        <h4 style="margin: 0;">{file_dict['title'] or file_dict['file_name']}</h4>
                        <p style="color: #666; margin: 5px 0;">
                            所属项目: {file_dict['project_name']} | 
                            所属机构: {file_dict['org_name']} |
                            文件类型: {file_dict['file_type'] or '-'}
                        </p>
                        <p style="color: #888; font-size: 13px;">
                            上传人: {file_dict['uploader_name'] or '-'} | 
                            上传时间: {file_dict['upload_time']}
                        </p>
                        {f'<p style="color: #666;">描述: {file_dict["description"]}</p>' if file_dict['description'] else ''}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(f"✅ 通过", key=f"file_approve_{file_dict['id']}", use_container_width=True):
                            execute_query("UPDATE project_files SET status = 'approved' WHERE id = ?", (file_dict['id'],))
                            
                            if file_dict['uploaded_by']:
                                add_message(file_dict['uploaded_by'], '文件审核通过', 
                                          f'您上传的文件 {file_dict["title"] or file_dict["file_name"]} 已审核通过')
                            
                            add_log(user['id'], user['username'], None, None, 
                                   f"文件审核通过: {file_dict['title'] or file_dict['file_name']}", '项目审核')
                            st.success("已通过")
                            st.rerun()
                    
                    with col2:
                        with st.form(f"file_reject_{file_dict['id']}"):
                            reason = st.text_input("驳回原因")
                            if st.form_submit_button("❌ 驳回", use_container_width=True):
                                if not reason:
                                    st.error("请填写驳回原因")
                                else:
                                    execute_query("UPDATE project_files SET status = 'rejected' WHERE id = ?", (file_dict['id'],))
                                    
                                    if file_dict['uploaded_by']:
                                        add_message(file_dict['uploaded_by'], '文件审核驳回', 
                                                  f'您上传的文件 {file_dict["title"] or file_dict["file_name"]} 被驳回，原因: {reason}')
                                    
                                    add_log(user['id'], user['username'], None, None, 
                                           f"文件审核驳回: {file_dict['title'] or file_dict['file_name']}", '项目审核')
                                    st.success("已驳回")
                                    st.rerun()
        else:
            st.info("暂无待审核的项目文件")

def render_admin_messages():
    """管理端 - 消息通知"""
    st.title("📨 消息通知")
    
    user = st.session_state['user']
    
    # 获取消息
    messages = execute_query('''
        SELECT * FROM messages WHERE user_id = ?
        ORDER BY created_at DESC
    ''', (user['id'],), fetch=True)
    
    if messages:
        # 一键已读按钮
        if st.button("✅ 一键全部已读"):
            execute_query("UPDATE messages SET is_read = 1 WHERE user_id = ?", (user['id'],))
            st.success("所有消息已标记为已读")
            st.rerun()
        
        for msg in messages:
            msg_dict = dict(msg)
            read_status = "已读" if msg_dict['is_read'] else "未读"
            read_color = "#28a745" if msg_dict['is_read'] else "#dc3545"
            
            with st.container():
                st.markdown(f"""
                <div style="background: {'#f8f9fa' if msg_dict['is_read'] else 'white'}; 
                            border-radius: 10px; padding: 15px; margin-bottom: 10px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                            border-left: 4px solid {read_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong>{msg_dict['title']}</strong>
                        <span style="background: {read_color}; color: white; padding: 2px 8px; 
                                    border-radius: 10px; font-size: 11px;">{read_status}</span>
                    </div>
                    <p style="color: #666; margin: 5px 0;">{msg_dict['content'] or ''}</p>
                    <p style="color: #999; font-size: 12px;">{msg_dict['created_at']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if not msg_dict['is_read']:
                    if st.button("标记已读", key=f"read_msg_{msg_dict['id']}"):
                        execute_query("UPDATE messages SET is_read = 1 WHERE id = ?", (msg_dict['id'],))
                        st.rerun()
    else:
        st.info("暂无消息通知")

def render_admin_indicators():
    """管理端 - 项目智库管理"""
    st.title("📚 项目智库管理")
    
    user = st.session_state['user']
    
    tab1, tab2, tab3 = st.tabs(["项目分类管理", "指标管理", "政策文件管理"])
    
    with tab1:
        st.subheader("项目分类体系")
        
        for cat_id, cat_info in PROJECT_CATEGORIES.items():
            if cat_id == '0':
                continue  # 其他项目不显示二级分类
            
            st.markdown(f"""
            <div style="background: white; border-radius: 15px; padding: 20px; margin-bottom: 15px; 
                        box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                <h4 style="margin: 0; color: #1a1a2e;">
                    编号{cat_id}: {cat_info['name']}
                </h4>
            """, unsafe_allow_html=True)
            
            for sub_id, sub_name in cat_info['subcategories'].items():
                st.markdown(f"""
                <div style="margin-left: 20px; padding: 10px; background: #f8f9fa; border-radius: 8px; margin: 5px 0;">
                    <strong>{cat_id}-{sub_id}</strong>: {sub_name}
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        # 其他项目说明
        st.info("编号0: 其他项目 - 用于无法归入以上分类的项目，无二级分类")
    
    with tab2:
        st.subheader("指标管理")
        
        # 选择分类
        col1, col2 = st.columns(2)
        
        with col1:
            cat_options = []
            for cat_id, cat_info in PROJECT_CATEGORIES.items():
                if cat_id != '0':
                    for sub_id, sub_name in cat_info['subcategories'].items():
                        cat_options.append(f"{cat_id}-{sub_id}: {cat_info['name']} - {sub_name}")
            
            selected_cat = st.selectbox("选择分类", cat_options)
        
        with col2:
            if st.button("添加新指标"):
                st.session_state['add_indicator'] = True
        
        if selected_cat:
            cat_id = selected_cat.split("-")[0]
            subcat_id = selected_cat.split("-")[1].split(":")[0]
            
            # 获取该分类的指标
            indicators = execute_query('''
                SELECT * FROM indicator_library 
                WHERE category_id = ? AND subcategory_id = ?
                ORDER BY weight DESC
            ''', (cat_id, subcat_id), fetch=True)
            
            if indicators:
                st.markdown("#### 当前指标列表")
                
                for ind in indicators:
                    ind_dict = dict(ind)
                    
                    with st.container():
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                        
                        with col1:
                            st.write(f"**{ind_dict['indicator_name']}**")
                            st.caption(ind_dict['indicator_desc'] or '')
                        
                        with col2:
                            st.write(f"权重: {ind_dict['weight']}%")
                        
                        with col3:
                            st.write(f"满分: {ind_dict['max_score']}")
                        
                        with col4:
                            if st.button("编辑", key=f"edit_ind_{ind_dict['id']}"):
                                st.session_state['edit_indicator_id'] = ind_dict['id']
            
            # 添加/编辑指标
            if st.session_state.get('add_indicator') or st.session_state.get('edit_indicator_id'):
                st.markdown("---")
                st.subheader("添加/编辑指标")
                
                edit_id = st.session_state.get('edit_indicator_id')
                edit_data = None
                if edit_id:
                    edit_data = execute_query("SELECT * FROM indicator_library WHERE id = ?", (edit_id,), fetch=True)
                    if edit_data:
                        edit_data = dict(edit_data[0])
                
                with st.form("indicator_form"):
                    ind_name = st.text_input("指标名称 *", value=edit_data['indicator_name'] if edit_data else '')
                    ind_desc = st.text_area("指标描述", value=edit_data['indicator_desc'] if edit_data else '')
                    ind_weight = st.number_input("权重 (%)", min_value=0, max_value=100, 
                                                value=edit_data['weight'] if edit_data else 10)
                    ind_max_score = st.number_input("满分", min_value=0, max_value=1000, 
                                                   value=edit_data['max_score'] if edit_data else 100)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("保存"):
                            if not ind_name:
                                st.error("请填写指标名称")
                            else:
                                if edit_id:
                                    execute_query('''
                                        UPDATE indicator_library SET 
                                        indicator_name = ?, indicator_desc = ?, weight = ?, max_score = ?, updated_at = CURRENT_TIMESTAMP
                                        WHERE id = ?
                                    ''', (ind_name, ind_desc, ind_weight, ind_max_score, edit_id))
                                    st.success("指标已更新")
                                else:
                                    execute_query('''
                                        INSERT INTO indicator_library (category_id, subcategory_id, indicator_name, indicator_desc, weight, max_score)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    ''', (cat_id, subcat_id, ind_name, ind_desc, ind_weight, ind_max_score))
                                    st.success("指标已添加")
                                
                                add_log(user['id'], user['username'], None, None, 
                                       f"{'编辑' if edit_id else '添加'}指标: {ind_name}", '项目智库')
                                
                                st.session_state['add_indicator'] = False
                                st.session_state['edit_indicator_id'] = None
                                st.rerun()
                    
                    with col2:
                        if st.form_submit_button("取消"):
                            st.session_state['add_indicator'] = False
                            st.session_state['edit_indicator_id'] = None
                            st.rerun()
                
                # 删除指标
                if edit_id:
                    if st.button("删除该指标", type="primary"):
                        execute_query("DELETE FROM indicator_library WHERE id = ?", (edit_id,))
                        st.success("指标已删除")
                        st.session_state['edit_indicator_id'] = None
                        st.rerun()
    
    with tab3:
        st.subheader("政策文件管理")
        
        # 上传政策文件
        with st.form("upload_policy"):
            policy_title = st.text_input("文件标题 *")
            policy_desc = st.text_area("文件描述")
            policy_file = st.file_uploader("上传文件", type=['pdf', 'doc', 'docx', 'xls', 'xlsx'])
            
            if st.form_submit_button("上传"):
                if not policy_title or not policy_file:
                    st.error("请填写标题并选择文件")
                else:
                    # 保存文件（原子写入）
                    file_path = save_uploaded_file_atomic(policy_file, UPLOAD_DIR, prefix="policy")
                    
                    execute_query('''
                        INSERT INTO policy_files (title, file_path, file_type, description, uploaded_by)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (policy_title, file_path, policy_file.type, policy_desc, user['id']))
                    
                    add_log(user['id'], user['username'], None, None, f"上传政策文件: {policy_title}", '项目智库')
                    st.success("文件上传成功")
                    st.rerun()
        
        # 政策文件列表
        policies = execute_query("SELECT * FROM policy_files WHERE is_active = 1 ORDER BY upload_time DESC", fetch=True)
        
        if policies:
            st.markdown("#### 已上传文件")
            
            for policy in policies:
                policy_dict = dict(policy)
                
                with st.container():
                    col1, col2, col3 = st.columns([4, 2, 1])
                    
                    with col1:
                        st.write(f"**{policy_dict['title']}**")
                        st.caption(policy_dict['description'] or '')
                    
                    with col2:
                        st.write(policy_dict['upload_time'])
                    
                    with col3:
                        if st.button("删除", key=f"del_policy_{policy_dict['id']}"):
                            execute_query("UPDATE policy_files SET is_active = 0 WHERE id = ?", (policy_dict['id'],))
                            st.success("已删除")
                            st.rerun()

def render_admin_visualization():
    """管理端 - 可视化大屏"""
    st.title("📈 可视化大屏")
    
    # 项目分类统计
    st.subheader("📊 各分类项目文件统计")
    
    # 获取各分类文件数量
    file_stats = execute_query('''
        SELECT category_id, subcategory_id, COUNT(*) as file_count,
               SUM(CASE WHEN evaluated = 1 THEN 1 ELSE 0 END) as evaluated_count,
               SUM(CASE WHEN evaluated = 0 THEN 1 ELSE 0 END) as unevaluated_count
        FROM project_files
        WHERE status = 'approved'
        GROUP BY category_id, subcategory_id
    ''', fetch=True)
    
    if file_stats:
        df_stats = pd.DataFrame([dict(row) for row in file_stats])
        
        # 添加分类名称
        def get_category_name(row):
            cat_id = row['category_id']
            subcat_id = row['subcategory_id']
            
            if cat_id == '0':
                return '其他项目'
            
            cat_info = PROJECT_CATEGORIES.get(cat_id, {})
            cat_name = cat_info.get('name', f'分类{cat_id}')
            
            if subcat_id and subcat_id in cat_info.get('subcategories', {}):
                subcat_name = cat_info['subcategories'][subcat_id]
                return f"{cat_name} - {subcat_name}"
            
            return cat_name
        
        df_stats['category_name'] = df_stats.apply(get_category_name, axis=1)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 文件数量柱状图
            fig = px.bar(df_stats, x='category_name', y='file_count',
                        title='各分类文件数量',
                        color='file_count',
                        color_continuous_scale='Viridis')
            fig.update_layout(xaxis_title="分类", yaxis_title="文件数量")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # 评估状态堆叠柱状图
            fig = go.Figure(data=[
                go.Bar(name='已评估', x=df_stats['category_name'], y=df_stats['evaluated_count'], marker_color='#28a745'),
                go.Bar(name='未评估', x=df_stats['category_name'], y=df_stats['unevaluated_count'], marker_color='#ffc107')
            ])
            fig.update_layout(barmode='stack', title='评估状态分布', xaxis_title="分类", yaxis_title="文件数量")
            st.plotly_chart(fig, use_container_width=True)
    
    # 总体统计
    st.subheader("📈 总体统计")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_files = execute_query("SELECT COUNT(*) as cnt FROM project_files WHERE status = 'approved'", fetch=True)[0]['cnt']
    evaluated_files = execute_query("SELECT COUNT(*) as cnt FROM project_files WHERE status = 'approved' AND evaluated = 1", fetch=True)[0]['cnt']
    unevaluated_files = total_files - evaluated_files
    avg_score = execute_query("SELECT AVG(evaluation_score) as avg FROM project_files WHERE evaluated = 1", fetch=True)[0]['avg'] or 0
    
    with col1:
        st.metric("总文件数", total_files)
    
    with col2:
        st.metric("已评估", evaluated_files)
    
    with col3:
        st.metric("未评估", unevaluated_files)
    
    with col4:
        st.metric("平均评分", f"{avg_score:.1f}")
    
    # 机构项目分布
    st.subheader("🏢 机构项目分布")
    
    org_projects = execute_query('''
        SELECT o.name, COUNT(DISTINCT p.id) as project_count, COUNT(pf.id) as file_count
        FROM organizations o
        LEFT JOIN projects p ON o.id = p.org_id
        LEFT JOIN project_files pf ON p.id = pf.project_id AND pf.status = 'approved'
        GROUP BY o.id
        ORDER BY project_count DESC
    ''', fetch=True)
    
    if org_projects:
        df_org = pd.DataFrame([dict(row) for row in org_projects])
        
        fig = px.scatter(df_org, x='project_count', y='file_count', text='name',
                        title='机构项目与文件分布',
                        size_max=30)
        fig.update_traces(textposition='top center')
        fig.update_layout(xaxis_title="项目数量", yaxis_title="文件数量")
        st.plotly_chart(fig, use_container_width=True)

# ==================== 机构端页面 ====================
def render_org_dashboard():
    """机构端 - 工作台"""
    st.title("🏠 工作台")
    
    user = st.session_state['user']
    org_id = user['org_id']
    
    # 获取机构信息
    org = execute_query("SELECT * FROM organizations WHERE id = ?", (org_id,), fetch=True)
    org_name = dict(org[0])['name'] if org else ''
    
    # 统计数据
    project_count = execute_query("SELECT COUNT(*) as cnt FROM projects WHERE org_id = ?", (org_id,), fetch=True)[0]['cnt']
    in_progress = execute_query("SELECT COUNT(*) as cnt FROM projects WHERE org_id = ? AND status = 'in_progress'", (org_id,), fetch=True)[0]['cnt']
    completed = execute_query("SELECT COUNT(*) as cnt FROM projects WHERE org_id = ? AND status = 'completed'", (org_id,), fetch=True)[0]['cnt']
    
    # 待办数量
    pending_todos = execute_query("SELECT COUNT(*) as cnt FROM todos WHERE user_id = ? AND status = 'pending'", (user['id'],), fetch=True)[0]['cnt']
    
    # 未读消息
    unread_msgs = execute_query("SELECT COUNT(*) as cnt FROM messages WHERE user_id = ? AND is_read = 0", (user['id'],), fetch=True)[0]['cnt']
    
    # 统计卡片
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("项目总数", project_count)
    
    with col2:
        st.metric("进行中", in_progress)
    
    with col3:
        st.metric("已完成", completed)
    
    with col4:
        st.metric("待办事项", pending_todos)
    
    with col5:
        st.metric("未读消息", unread_msgs)
    
    st.markdown("---")
    
    # 最近项目
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 最近项目")
        
        recent_projects = execute_query('''
            SELECT * FROM projects WHERE org_id = ?
            ORDER BY created_at DESC LIMIT 5
        ''', (org_id,), fetch=True)
        
        if recent_projects:
            for proj in recent_projects:
                proj_dict = dict(proj)
                status_map = {'pending': '待审核', 'in_progress': '进行中', 'completed': '已完成', 'rejected': '已驳回'}
                
                st.markdown(f"""
                <div style="background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                    <strong>{proj_dict['name']}</strong>
                    <br><span style="color: #666; font-size: 13px;">
                        状态: {status_map.get(proj_dict['status'], proj_dict['status'])} | 
                        当前阶段: {proj_dict['current_stage']}
                    </span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("暂无项目")
    
    with col2:
        st.subheader("✅ 待办事项")
        
        todos = execute_query('''
            SELECT * FROM todos WHERE user_id = ? AND status = 'pending'
            ORDER BY priority DESC, created_at DESC LIMIT 5
        ''', (user['id'],), fetch=True)
        
        if todos:
            for todo in todos:
                todo_dict = dict(todo)
                st.markdown(f"""
                <div style="background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                    <strong>{todo_dict['title']}</strong>
                    <br><span style="color: #666; font-size: 13px;">{todo_dict['content'] or ''}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("暂无待办")

def render_org_info():
    """机构端 - 信息维护"""
    st.title("🏢 信息维护")
    
    user = st.session_state['user']
    org_id = user['org_id']
    
    tab1, tab2, tab3, tab4 = st.tabs(["机构信息", "主评人管理", "业绩记录", "培训记录"])
    
    with tab1:
        # 获取机构信息
        org = execute_query("SELECT * FROM organizations WHERE id = ?", (org_id,), fetch=True)
        
        if org:
            org_dict = dict(org[0])
            
            with st.form("update_org_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    name = st.text_input("机构名称", value=org_dict['name'], disabled=True)
                    org_type = st.text_input("机构类型", value=org_dict['org_type'] or '')
                    credit_code = st.text_input("统一社会信用代码", value=org_dict['credit_code'] or '')
                    legal_person = st.text_input("法定代表人", value=org_dict['legal_person'] or '')
                    contact_person = st.text_input("联系人", value=org_dict['contact_person'] or '')
                
                with col2:
                    contact_phone = st.text_input("联系电话", value=org_dict['contact_phone'] or '')
                    contact_email = st.text_input("联系邮箱", value=org_dict['contact_email'] or '')
                    address = st.text_input("机构地址", value=org_dict['address'] or '')
                
                description = st.text_area("机构简介", value=org_dict['description'] or '')
                
                if st.form_submit_button("保存修改"):
                    execute_query('''
                        UPDATE organizations SET 
                            org_type = ?, credit_code = ?, legal_person = ?,
                            contact_person = ?, contact_phone = ?, contact_email = ?,
                            address = ?, description = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (org_type, credit_code, legal_person, contact_person, 
                         contact_phone, contact_email, address, description, org_id))
                    
                    add_log(user['id'], user['username'], org_id, org_dict['name'], "更新机构信息", '信息维护')
                    st.success("机构信息已更新")
    
    with tab2:
        st.subheader("主评人管理")
        
        # 添加主评人
        with st.expander("添加主评人"):
            with st.form("add_evaluator_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    eva_name = st.text_input("姓名 *")
                    eva_title = st.text_input("职称")
                    eva_specialty = st.text_input("专业领域")
                
                with col2:
                    eva_phone = st.text_input("联系电话")
                    eva_email = st.text_input("邮箱")
                
                eva_intro = st.text_area("简介")
                
                if st.form_submit_button("添加"):
                    if not eva_name:
                        st.error("请填写姓名")
                    else:
                        execute_query('''
                            INSERT INTO evaluators (org_id, name, title, specialty, phone, email, introduction)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (org_id, eva_name, eva_title, eva_specialty, eva_phone, eva_email, eva_intro))
                        
                        add_log(user['id'], user['username'], org_id, None, f"添加主评人: {eva_name}", '信息维护')
                        st.success("主评人已添加")
                        st.rerun()
        
        # 主评人列表
        evaluators = execute_query("SELECT * FROM evaluators WHERE org_id = ? AND is_active = 1", (org_id,), fetch=True)
        
        if evaluators:
            for eva in evaluators:
                eva_dict = dict(eva)
                
                with st.container():
                    st.markdown(f"""
                    <div style="background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; 
                                box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                        <strong>{eva_dict['name']}</strong> - {eva_dict['title'] or '未设置职称'}
                        <br><span style="color: #666; font-size: 13px;">
                            专业: {eva_dict['specialty'] or '-'} | 
                            电话: {eva_dict['phone'] or '-'} | 
                            邮箱: {eva_dict['email'] or '-'}
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("删除", key=f"del_eva_{eva_dict['id']}"):
                        execute_query("UPDATE evaluators SET is_active = 0 WHERE id = ?", (eva_dict['id'],))
                        st.success("已删除")
                        st.rerun()
    
    with tab3:
        st.subheader("业绩记录")
        
        # 添加业绩
        with st.expander("添加业绩记录"):
            with st.form("add_achievement_form"):
                ach_title = st.text_input("业绩标题 *")
                ach_content = st.text_area("业绩内容")
                ach_date = st.date_input("业绩日期")
                
                if st.form_submit_button("添加"):
                    if not ach_title:
                        st.error("请填写业绩标题")
                    else:
                        execute_query('''
                            INSERT INTO achievements (org_id, title, content, achievement_date)
                            VALUES (?, ?, ?, ?)
                        ''', (org_id, ach_title, ach_content, str(ach_date)))
                        
                        add_log(user['id'], user['username'], org_id, None, f"添加业绩: {ach_title}", '信息维护')
                        st.success("业绩已添加")
                        st.rerun()
        
        # 业绩列表
        achievements = execute_query("SELECT * FROM achievements WHERE org_id = ? ORDER BY achievement_date DESC", (org_id,), fetch=True)
        
        if achievements:
            for ach in achievements:
                ach_dict = dict(ach)
                
                with st.container():
                    st.markdown(f"""
                    <div style="background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; 
                                box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                        <strong>{ach_dict['title']}</strong>
                        <br><span style="color: #666; font-size: 13px;">日期: {ach_dict['achievement_date']}</span>
                        <br><span style="color: #888;">{ach_dict['content'] or ''}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("删除", key=f"del_ach_{ach_dict['id']}"):
                        execute_query("DELETE FROM achievements WHERE id = ?", (ach_dict['id'],))
                        st.success("已删除")
                        st.rerun()
    
    with tab4:
        st.subheader("培训记录")
        
        # 添加培训
        with st.expander("添加培训记录"):
            with st.form("add_training_form"):
                train_title = st.text_input("培训标题 *")
                train_trainer = st.text_input("培训讲师")
                train_date = st.date_input("培训日期")
                train_duration = st.text_input("培训时长")
                train_content = st.text_area("培训内容")
                
                if st.form_submit_button("添加"):
                    if not train_title:
                        st.error("请填写培训标题")
                    else:
                        execute_query('''
                            INSERT INTO trainings (org_id, title, trainer, training_date, duration, content)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (org_id, train_title, train_trainer, str(train_date), train_duration, train_content))
                        
                        add_log(user['id'], user['username'], org_id, None, f"添加培训: {train_title}", '信息维护')
                        st.success("培训记录已添加")
                        st.rerun()
        
        # 培训列表
        trainings = execute_query("SELECT * FROM trainings WHERE org_id = ? ORDER BY training_date DESC", (org_id,), fetch=True)
        
        if trainings:
            for train in trainings:
                train_dict = dict(train)
                
                with st.container():
                    st.markdown(f"""
                    <div style="background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; 
                                box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                        <strong>{train_dict['title']}</strong>
                        <br><span style="color: #666; font-size: 13px;">
                            讲师: {train_dict['trainer'] or '-'} | 
                            日期: {train_dict['training_date']} | 
                            时长: {train_dict['duration'] or '-'}
                        </span>
                        <br><span style="color: #888;">{train_dict['content'] or ''}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("删除", key=f"del_train_{train_dict['id']}"):
                        execute_query("DELETE FROM trainings WHERE id = ?", (train_dict['id'],))
                        st.success("已删除")
                        st.rerun()

def render_org_sub_accounts():
    """机构端 - 子账号管理"""
    st.title("👥 子账号管理")
    
    user = st.session_state['user']
    org_id = user['org_id']
    
    # 只有机构主账号可以管理子账号
    if user['role'] != 'org_admin':
        st.warning("您没有权限管理子账号")
        return
    
    # 获取机构名称
    org = execute_query("SELECT name FROM organizations WHERE id = ?", (org_id,), fetch=True)
    org_name = dict(org[0])['name'] if org else ''
    
    # 子账号列表
    sub_users = execute_query('''
        SELECT * FROM users WHERE org_id = ? AND role = 'org_user'
        ORDER BY created_at DESC
    ''', (org_id,), fetch=True)
    
    if sub_users:
        st.subheader("子账号列表")
        
        for sub in sub_users:
            sub_dict = dict(sub)
            status_text = "启用" if sub_dict['is_active'] else "冻结"
            status_color = "#28a745" if sub_dict['is_active'] else "#dc3545"
            
            with st.container():
                st.markdown(f"""
                <div style="background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                    <strong>{sub_dict['real_name'] or sub_dict['username']}</strong>
                    <span style="background: {status_color}; color: white; padding: 2px 8px; 
                                border-radius: 10px; font-size: 11px; margin-left: 10px;">{status_text}</span>
                    <br><span style="color: #666; font-size: 13px;">
                        用户名: {sub_dict['username']} | 
                        电话: {sub_dict['phone'] or '-'} | 
                        邮箱: {sub_dict['email'] or '-'}
                    </span>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if sub_dict['is_active']:
                        if st.button("冻结", key=f"freeze_sub_{sub_dict['id']}"):
                            execute_query("UPDATE users SET is_active = 0 WHERE id = ?", (sub_dict['id'],))
                            add_log(user['id'], user['username'], org_id, org_name, f"冻结子账号: {sub_dict['username']}", '子账号管理')
                            st.success("已冻结")
                            st.rerun()
                    else:
                        if st.button("启用", key=f"activate_sub_{sub_dict['id']}"):
                            execute_query("UPDATE users SET is_active = 1 WHERE id = ?", (sub_dict['id'],))
                            add_log(user['id'], user['username'], org_id, org_name, f"启用子账号: {sub_dict['username']}", '子账号管理')
                            st.success("已启用")
                            st.rerun()
                
                with col2:
                    if st.button("重置密码", key=f"reset_sub_pwd_{sub_dict['id']}"):
                        new_pwd = "Reset@123456"
                        pwd_hash = hash_password(new_pwd)
                        execute_query("UPDATE users SET password_hash = ? WHERE id = ?", (pwd_hash, sub_dict['id']))
                        add_log(user['id'], user['username'], org_id, org_name, f"重置子账号密码: {sub_dict['username']}", '子账号管理')
                        st.success(f"密码已重置为: {new_pwd}")
                
                with col3:
                    if st.button("修改", key=f"edit_sub_{sub_dict['id']}"):
                        st.session_state['edit_sub_id'] = sub_dict['id']
                        st.rerun()
                
                with col4:
                    if st.button("删除", key=f"del_sub_{sub_dict['id']}"):
                        execute_query("DELETE FROM users WHERE id = ?", (sub_dict['id'],))
                        add_log(user['id'], user['username'], org_id, org_name, f"删除子账号: {sub_dict['username']}", '子账号管理')
                        st.success("已删除")
                        st.rerun()
    
    # 编辑子账号
    if 'edit_sub_id' in st.session_state:
        st.markdown("---")
        st.subheader("编辑子账号")
        
        edit_id = st.session_state['edit_sub_id']
        edit_data = execute_query("SELECT * FROM users WHERE id = ?", (edit_id,), fetch=True)
        
        if edit_data:
            edit_dict = dict(edit_data[0])
            
            with st.form("edit_sub_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    edit_username = st.text_input("用户名", value=edit_dict['username'])
                    edit_real_name = st.text_input("姓名", value=edit_dict['real_name'] or '')
                    edit_phone = st.text_input("电话", value=edit_dict['phone'] or '')
                
                with col2:
                    edit_email = st.text_input("邮箱", value=edit_dict['email'] or '')
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("保存"):
                        execute_query('''
                            UPDATE users SET username = ?, real_name = ?, phone = ?, email = ?
                            WHERE id = ?
                        ''', (edit_username, edit_real_name, edit_phone, edit_email, edit_id))
                        
                        add_log(user['id'], user['username'], org_id, org_name, f"编辑子账号: {edit_username}", '子账号管理')
                        st.success("已更新")
                        del st.session_state['edit_sub_id']
                        st.rerun()
                
                with col2:
                    if st.form_submit_button("取消"):
                        del st.session_state['edit_sub_id']
                        st.rerun()
    
    # 添加子账号
    st.markdown("---")
    st.subheader("添加子账号")
    
    with st.form("add_sub_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("用户名 *")
            new_real_name = st.text_input("姓名 *")
            new_phone = st.text_input("电话 *")
        
        with col2:
            new_email = st.text_input("邮箱 *")
        
        if st.form_submit_button("创建子账号"):
            if not new_username or not new_real_name or not new_phone or not new_email:
                st.error("请填写所有必填项")
            else:
                # 检查用户名是否存在
                existing = execute_query("SELECT id FROM users WHERE username = ?", (new_username,), fetch=True)
                if existing:
                    st.error("用户名已存在")
                else:
                    default_pwd = "User@123456"
                    pwd_hash = hash_password(default_pwd)
                    
                    execute_query('''
                        INSERT INTO users (username, password_hash, role, org_id, real_name, phone, email)
                        VALUES (?, ?, 'org_user', ?, ?, ?, ?)
                    ''', (new_username, pwd_hash, org_id, new_real_name, new_phone, new_email))
                    
                    add_log(user['id'], user['username'], org_id, org_name, f"添加子账号: {new_username}", '子账号管理')
                    st.success(f"子账号创建成功！默认密码: {default_pwd}")

def render_org_projects():
    """机构端 - 项目管理"""
    st.title("📋 项目管理")
    
    user = st.session_state['user']
    org_id = user['org_id']
    
    # 获取机构名称
    org = execute_query("SELECT name FROM organizations WHERE id = ?", (org_id,), fetch=True)
    org_name = dict(org[0])['name'] if org else ''
    
    tab1, tab2 = st.tabs(["项目列表", "新建项目"])
    
    with tab1:
        # 项目列表
        projects = execute_query('''
            SELECT p.*, 
                   (SELECT COUNT(*) FROM project_steps WHERE project_id = p.id AND status = 'pending') as pending_steps
            FROM projects p
            WHERE p.org_id = ?
            ORDER BY p.created_at DESC
        ''', (org_id,), fetch=True)
        
        if projects:
            stage_names = {
                1: "阶段1: 项目立项",
                2: "阶段2: 方案设计", 
                3: "阶段3: 数据采集",
                4: "阶段4: 分析评估",
                5: "阶段5: 报告编制"
            }
            
            status_map = {'pending': '待审核', 'in_progress': '进行中', 'completed': '已完成', 'rejected': '已驳回'}
            
            for proj in projects:
                proj_dict = dict(proj)
                
                with st.container():
                    st.markdown(f"""
                    <div style="background: white; border-radius: 15px; padding: 20px; margin-bottom: 15px; 
                                box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                        <h4 style="margin: 0;">{proj_dict['name']}</h4>
                        <p style="color: #666; margin: 5px 0;">
                            项目编号: {proj_dict['project_code'] or '-'} | 
                            状态: {status_map.get(proj_dict['status'], proj_dict['status'])} | 
                            当前阶段: {stage_names.get(proj_dict['current_stage'], f"阶段{proj_dict['current_stage']}")}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 阶段进度
                    st.markdown("**阶段进度:**")
                    cols = st.columns(5)
                    
                    for i in range(1, 6):
                        with cols[i-1]:
                            step = execute_query('''
                                SELECT * FROM project_steps WHERE project_id = ? AND stage = ?
                            ''', (proj_dict['id'], i), fetch=True)
                            
                            if step:
                                step_dict = dict(step[0])
                                if step_dict['status'] == 'approved':
                                    st.success(f"✅ 阶段{i}")
                                elif step_dict['status'] == 'rejected':
                                    st.error(f"❌ 阶段{i}")
                                else:
                                    st.warning(f"⏳ 阶段{i}")
                            else:
                                st.info(f"○ 阶段{i}")
                    
                    # 操作按钮
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("查看详情", key=f"view_proj_{proj_dict['id']}"):
                            st.session_state['view_project_id'] = proj_dict['id']
                            st.rerun()
                    
                    with col2:
                        # 提交阶段
                        if proj_dict['status'] != 'completed':
                            if st.button("提交阶段", key=f"submit_stage_{proj_dict['id']}"):
                                st.session_state['submit_project_id'] = proj_dict['id']
                                st.rerun()
                    
                    with col3:
                        # 上传文件
                        if st.button("上传文件", key=f"upload_file_{proj_dict['id']}"):
                            st.session_state['upload_project_id'] = proj_dict['id']
                            st.rerun()
                    
                    st.markdown("---")
        
        else:
            st.info("暂无项目")
        
        # 查看项目详情
        if 'view_project_id' in st.session_state:
            st.markdown("---")
            st.subheader("项目详情")
            
            proj_id = st.session_state['view_project_id']
            proj_data = execute_query('''
                SELECT p.*, o.name as org_name FROM projects p
                JOIN organizations o ON p.org_id = o.id
                WHERE p.id = ?
            ''', (proj_id,), fetch=True)
            
            if proj_data:
                proj_dict = dict(proj_data[0])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**项目名称:** {proj_dict['name']}")
                    st.write(f"**项目编号:** {proj_dict['project_code'] or '-'}")
                    st.write(f"**所属机构:** {proj_dict['org_name']}")
                
                with col2:
                    st.write(f"**状态:** {status_map.get(proj_dict['status'], proj_dict['status'])}")
                    current_stage = proj_dict['current_stage']
                    st.write(f"**当前阶段:** {stage_names.get(current_stage, f'阶段{current_stage}')}")
                    st.write(f"**创建时间:** {proj_dict['created_at']}")
                
                # 阶段详情
                st.subheader("阶段详情")
                
                steps = execute_query('''
                    SELECT ps.*, u.username as submitter_name, r.username as reviewer_name
                    FROM project_steps ps
                    LEFT JOIN users u ON ps.submitted_by = u.id
                    LEFT JOIN users r ON ps.reviewed_by = r.id
                    WHERE ps.project_id = ?
                    ORDER BY ps.stage
                ''', (proj_id,), fetch=True)
                
                if steps:
                    for step in steps:
                        step_dict = dict(step)
                        status_text = {"pending": "待审核", "approved": "已通过", "rejected": "已驳回"}
                        
                        st.markdown(f"""
                        <div style="background: #f8f9fa; border-radius: 10px; padding: 15px; margin-bottom: 10px;">
                            <strong>{stage_names.get(step_dict['stage'], f"阶段{step_dict['stage']}")}</strong>
                            <span style="margin-left: 10px;">状态: {status_text.get(step_dict['status'], step_dict['status'])}</span>
                            <br><span style="color: #666; font-size: 13px;">
                                提交人: {step_dict['submitter_name'] or '-'} | 
                                提交时间: {step_dict['submitted_at'] or '-'} |
                                审核人: {step_dict['reviewer_name'] or '-'} |
                                审核时间: {step_dict['reviewed_at'] or '-'}
                            </span>
                            {f'<br><span style="color: #dc3545;">驳回原因: {step_dict["review_comment"]}</span>' if step_dict['review_comment'] else ''}
                        </div>
                        """, unsafe_allow_html=True)
                
                # 项目文件
                st.subheader("项目文件")
                
                files = execute_query('''
                    SELECT pf.*, u.username as uploader_name
                    FROM project_files pf
                    LEFT JOIN users u ON pf.uploaded_by = u.id
                    WHERE pf.project_id = ?
                    ORDER BY pf.upload_time DESC
                ''', (proj_id,), fetch=True)
                
                if files:
                    for file in files:
                        file_dict = dict(file)
                        st.write(f"- {file_dict['title'] or file_dict['file_name']} ({file_dict['upload_time']})")
                else:
                    st.info("暂无文件")
                
                if st.button("关闭详情"):
                    del st.session_state['view_project_id']
                    st.rerun()
        
        # 提交阶段
        if 'submit_project_id' in st.session_state:
            st.markdown("---")
            st.subheader("提交阶段")
            
            proj_id = st.session_state['submit_project_id']
            proj_data = execute_query("SELECT * FROM projects WHERE id = ?", (proj_id,), fetch=True)
            
            if proj_data:
                proj_dict = dict(proj_data[0])
                current_stage = proj_dict['current_stage']
                
                st.write(f"**项目:** {proj_dict['name']}")
                st.write(f"**当前阶段:** {stage_names.get(current_stage, f'阶段{current_stage}')}")
                
                with st.form("submit_stage_form"):
                    stage_note = st.text_area("阶段说明")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("提交审核"):
                            # 检查是否已有该阶段的记录
                            existing = execute_query('''
                                SELECT id FROM project_steps WHERE project_id = ? AND stage = ?
                            ''', (proj_id, current_stage), fetch=True)
                            
                            if existing:
                                execute_query('''
                                    UPDATE project_steps SET status = 'pending', submitted_at = CURRENT_TIMESTAMP,
                                    submitted_by = ?, review_comment = NULL
                                    WHERE project_id = ? AND stage = ?
                                ''', (user['id'], proj_id, current_stage))
                            else:
                                execute_query('''
                                    INSERT INTO project_steps (project_id, stage, stage_name, status, submitted_at, submitted_by)
                                    VALUES (?, ?, ?, 'pending', CURRENT_TIMESTAMP, ?)
                                ''', (proj_id, current_stage, stage_names.get(current_stage, f"阶段{current_stage}"), user['id']))
                            
                            # 更新项目状态
                            if proj_dict['status'] == 'pending':
                                execute_query("UPDATE projects SET status = 'in_progress' WHERE id = ?", (proj_id,))
                            
                            add_log(user['id'], user['username'], org_id, org_name, 
                                   f"提交阶段审核: {proj_dict['name']} - {stage_names.get(current_stage, '')}", '项目管理')
                            
                            # 通知超级管理员
                            admins = execute_query("SELECT id FROM users WHERE role = 'super_admin'", fetch=True)
                            for admin in admins:
                                add_message(dict(admin)['id'], '新项目待审核', 
                                          f'机构 {org_name} 提交了项目 {proj_dict["name"]} 的{stage_names.get(current_stage, "")}审核')
                            
                            st.success("已提交审核")
                            del st.session_state['submit_project_id']
                            st.rerun()
                    
                    with col2:
                        if st.form_submit_button("取消"):
                            del st.session_state['submit_project_id']
                            st.rerun()
        
        # 上传文件
        if 'upload_project_id' in st.session_state:
            st.markdown("---")
            st.subheader("上传项目文件")
            
            proj_id = st.session_state['upload_project_id']
            
            with st.form("upload_file_form"):
                file_title = st.text_input("文件标题 *")
                
                # 文件类型选择
                file_type_options = []
                for cat_id, cat_info in PROJECT_CATEGORIES.items():
                    if cat_id == '0':
                        file_type_options.append(f"0: 其他项目")
                    else:
                        for sub_id, sub_name in cat_info['subcategories'].items():
                            file_type_options.append(f"{cat_id}-{sub_id}: {cat_info['name']} - {sub_name}")
                
                file_type = st.selectbox("文件类型 *", file_type_options)
                publish_org = st.text_input("发布机构")
                file_desc = st.text_area("文件描述（选填）")
                
                uploaded_file = st.file_uploader("选择文件", type=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt'])
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("上传"):
                        if not file_title or not uploaded_file:
                            st.error("请填写文件标题并选择文件")
                        else:
                            # 解析文件类型
                            type_parts = file_type.split(":")[0].split("-")
                            cat_id = type_parts[0]
                            subcat_id = type_parts[1] if len(type_parts) > 1 else None
                            
                            # 保存文件（原子写入）
                            file_path = save_uploaded_file_atomic(uploaded_file, UPLOAD_DIR, prefix=f"proj_{proj_id}")
                            
                            # 插入数据库
                            execute_query('''
                                INSERT INTO project_files (project_id, file_name, file_path, file_type, 
                                                          category_id, subcategory_id, title, description, 
                                                          publish_org, uploaded_by, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                            ''', (proj_id, uploaded_file.name, file_path, uploaded_file.type,
                                 cat_id, subcat_id, file_title, file_desc, publish_org, user['id']))
                            
                            add_log(user['id'], user['username'], org_id, org_name, 
                                   f"上传项目文件: {file_title}", '项目管理')
                            
                            # 通知上级
                            if user['role'] == 'org_user':
                                # 通知机构主账号
                                org_admin = execute_query('''
                                    SELECT id FROM users WHERE org_id = ? AND role = 'org_admin'
                                ''', (org_id,), fetch=True)
                                if org_admin:
                                    add_message(dict(org_admin[0])['id'], '新文件待审核', 
                                              f'子账号上传了文件 {file_title}，请审核')
                            
                            # 通知超级管理员
                            admins = execute_query("SELECT id FROM users WHERE role = 'super_admin'", fetch=True)
                            for admin in admins:
                                add_message(dict(admin)['id'], '新文件待审核', 
                                          f'机构 {org_name} 上传了文件 {file_title}，请审核')
                            
                            st.success("文件上传成功，等待审核")
                            del st.session_state['upload_project_id']
                            st.rerun()
                
                with col2:
                    if st.form_submit_button("取消"):
                        del st.session_state['upload_project_id']
                        st.rerun()
    
    with tab2:
        st.subheader("新建项目")
        
        with st.form("create_project_form"):
            proj_name = st.text_input("项目名称 *")
            
            # 项目分类
            cat_options = []
            for cat_id, cat_info in PROJECT_CATEGORIES.items():
                if cat_id == '0':
                    cat_options.append(f"0: 其他项目")
                else:
                    for sub_id, sub_name in cat_info['subcategories'].items():
                        cat_options.append(f"{cat_id}-{sub_id}: {cat_info['name']} - {sub_name}")
            
            proj_category = st.selectbox("项目分类 *", cat_options)
            proj_desc = st.text_area("项目描述")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("创建项目"):
                    if not proj_name:
                        st.error("请填写项目名称")
                    else:
                        # 解析分类
                        cat_parts = proj_category.split(":")[0].split("-")
                        cat_id = cat_parts[0]
                        subcat_id = cat_parts[1] if len(cat_parts) > 1 else None
                        
                        # 生成项目编号
                        if cat_id == '0':
                            project_code = f"0-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        else:
                            project_code = f"{cat_id}-{subcat_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                        
                        # 创建项目
                        project_id = execute_query('''
                            INSERT INTO projects (name, org_id, category_id, subcategory_id, project_code, description, created_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (proj_name, org_id, cat_id, subcat_id, project_code, proj_desc, user['id']))
                        
                        # 创建5个阶段记录
                        for i in range(1, 6):
                            execute_query('''
                                INSERT INTO project_steps (project_id, stage, stage_name, status)
                                VALUES (?, ?, ?, 'pending')
                            ''', (project_id, i, stage_names.get(i, f"阶段{i}")))
                        
                        add_log(user['id'], user['username'], org_id, org_name, f"创建项目: {proj_name}", '项目管理')
                        
                        # 通知超级管理员
                        admins = execute_query("SELECT id FROM users WHERE role = 'super_admin'", fetch=True)
                        for admin in admins:
                            add_message(dict(admin)['id'], '新项目创建', 
                                      f'机构 {org_name} 创建了新项目 {proj_name}')
                        
                        st.success(f"项目创建成功！项目编号: {project_code}")

def render_org_knowledge():
    """机构端 - 项目智库"""
    st.title("📚 项目智库")
    
    user = st.session_state['user']
    org_id = user['org_id']
    
    tab1, tab2, tab3 = st.tabs(["我的项目", "项目文件", "政策文件"])
    
    with tab1:
        st.subheader("我的项目")
        
        # 搜索
        search_keyword = st.text_input("搜索项目", placeholder="输入关键词搜索...")
        
        # 获取项目列表
        query = '''
            SELECT p.*, o.name as org_name,
                   (SELECT COUNT(*) FROM project_files WHERE project_id = p.id) as file_count
            FROM projects p
            JOIN organizations o ON p.org_id = o.id
            WHERE p.org_id = ?
        '''
        params = [org_id]
        
        if search_keyword:
            query += " AND (p.name LIKE ? OR p.description LIKE ? OR p.project_code LIKE ?)"
            params.extend([f"%{search_keyword}%", f"%{search_keyword}%", f"%{search_keyword}%"])
        
        query += " ORDER BY p.created_at DESC"
        
        projects = execute_query(query, params, fetch=True)
        
        if projects:
            status_map = {'pending': '待审核', 'in_progress': '进行中', 'completed': '已完成', 'rejected': '已驳回'}
            
            for proj in projects:
                proj_dict = dict(proj)
                
                with st.container():
                    st.markdown(f"""
                    <div style="background: white; border-radius: 15px; padding: 20px; margin-bottom: 15px; 
                                box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
                        <h4 style="margin: 0;">{proj_dict['name']}</h4>
                        <p style="color: #666; margin: 5px 0;">
                            项目编号: {proj_dict['project_code']} | 
                            状态: {status_map.get(proj_dict['status'], proj_dict['status'])} |
                            文件数: {proj_dict['file_count']}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("暂无项目")
    
    with tab2:
        st.subheader("项目文件")
        
        # 搜索
        file_search = st.text_input("搜索文件", placeholder="输入关键词搜索...", key="file_search")
        
        # 获取文件列表
        query = '''
            SELECT pf.*, p.name as project_name, u.username as uploader_name
            FROM project_files pf
            JOIN projects p ON pf.project_id = p.id
            LEFT JOIN users u ON pf.uploaded_by = u.id
            WHERE p.org_id = ? AND pf.status = 'approved'
        '''
        params = [org_id]
        
        if file_search:
            query += " AND (pf.title LIKE ? OR pf.description LIKE ? OR pf.file_name LIKE ?)"
            params.extend([f"%{file_search}%", f"%{file_search}%", f"%{file_search}%"])
        
        query += " ORDER BY pf.upload_time DESC"
        
        files = execute_query(query, params, fetch=True)
        
        if files:
            for file in files:
                file_dict = dict(file)
                
                eval_status = "已评估" if file_dict['evaluated'] else "未评估"
                eval_color = "#28a745" if file_dict['evaluated'] else "#ffc107"
                
                with st.container():
                    st.markdown(f"""
                    <div style="background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; 
                                box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                        <strong>{file_dict['title'] or file_dict['file_name']}</strong>
                        <span style="background: {eval_color}; color: white; padding: 2px 8px; 
                                    border-radius: 10px; font-size: 11px; margin-left: 10px;">{eval_status}</span>
                        <br><span style="color: #666; font-size: 13px;">
                            所属项目: {file_dict['project_name']} | 
                            上传人: {file_dict['uploader_name'] or '-'} | 
                            上传时间: {file_dict['upload_time']}
                        </span>
                        {f'<br><span style="color: #28a745;">评分: {file_dict["evaluation_score"]}</span>' if file_dict['evaluated'] else ''}
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("暂无文件")
    
    with tab3:
        st.subheader("政策文件")
        
        policies = execute_query('''
            SELECT * FROM policy_files WHERE is_active = 1
            ORDER BY upload_time DESC
        ''', fetch=True)
        
        if policies:
            for policy in policies:
                policy_dict = dict(policy)
                
                with st.container():
                    st.markdown(f"""
                    <div style="background: white; border-radius: 10px; padding: 15px; margin-bottom: 10px; 
                                box-shadow: 0 2px 10px rgba(0,0,0,0.08);">
                        <strong>{policy_dict['title']}</strong>
                        <br><span style="color: #666; font-size: 13px;">
                            上传时间: {policy_dict['upload_time']}
                        </span>
                        {f'<br><span style="color: #888;">{policy_dict["description"]}</span>' if policy_dict['description'] else ''}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 下载按钮
                    if os.path.exists(policy_dict['file_path']):
                        with open(policy_dict['file_path'], 'rb') as f:
                            st.download_button(
                                label="下载文件",
                                data=f,
                                file_name=policy_dict['title'],
                                key=f"dl_policy_{policy_dict['id']}"
                            )
        else:
            st.info("暂无政策文件")

def render_org_todos():
    """机构端 - 待办事项"""
    st.title("✅ 待办事项")
    
    user = st.session_state['user']
    
    tab1, tab2 = st.tabs(["待办列表", "新建待办"])
    
    with tab1:
        # 获取待办
        todos = execute_query('''
            SELECT * FROM todos WHERE user_id = ?
            ORDER BY status ASC, priority DESC, created_at DESC
        ''', (user['id'],), fetch=True)
        
        if todos:
            for todo in todos:
                todo_dict = dict(todo)
                status_text = "已完成" if todo_dict['status'] == 'completed' else "待处理"
                status_color = "#28a745" if todo_dict['status'] == 'completed' else "#ffc107"
                
                with st.container():
                    st.markdown(f"""
                    <div style="background: {'#f8f9fa' if todo_dict['status'] == 'completed' else 'white'}; 
                                border-radius: 10px; padding: 15px; margin-bottom: 10px; 
                                box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                                border-left: 4px solid {status_color};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong>{todo_dict['title']}</strong>
                            <span style="background: {status_color}; color: white; padding: 2px 8px; 
                                        border-radius: 10px; font-size: 11px;">{status_text}</span>
                        </div>
                        <p style="color: #666; margin: 5px 0;">{todo_dict['content'] or ''}</p>
                        <p style="color: #999; font-size: 12px;">
                            创建时间: {todo_dict['created_at']}
                            {f' | 截止日期: {todo_dict["due_date"]}' if todo_dict['due_date'] else ''}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if todo_dict['status'] == 'pending':
                        if st.button("标记完成", key=f"complete_todo_{todo_dict['id']}"):
                            execute_query('''
                                UPDATE todos SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                                WHERE id = ?
                            ''', (todo_dict['id'],))
                            st.success("已完成")
                            st.rerun()
        
        else:
            st.info("暂无待办事项")
    
    with tab2:
        with st.form("add_todo_form"):
            todo_title = st.text_input("待办标题 *")
            todo_content = st.text_area("待办内容")
            todo_priority = st.selectbox("优先级", ["普通", "重要", "紧急"])
            todo_due = st.date_input("截止日期（选填）", value=None)
            
            if st.form_submit_button("创建待办"):
                if not todo_title:
                    st.error("请填写待办标题")
                else:
                    priority_map = {"普通": 1, "重要": 2, "紧急": 3}
                    
                    execute_query('''
                        INSERT INTO todos (user_id, title, content, priority, due_date)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (user['id'], todo_title, todo_content, priority_map[todo_priority], 
                         str(todo_due) if todo_due else None))
                    
                    st.success("待办创建成功")
                    st.rerun()

def render_org_messages():
    """机构端 - 消息通知"""
    st.title("📨 消息通知")
    
    user = st.session_state['user']
    
    # 获取消息
    messages = execute_query('''
        SELECT * FROM messages WHERE user_id = ?
        ORDER BY is_read ASC, created_at DESC
    ''', (user['id'],), fetch=True)
    
    if messages:
        # 一键已读
        if st.button("✅ 一键全部已读"):
            execute_query("UPDATE messages SET is_read = 1 WHERE user_id = ?", (user['id'],))
            st.success("所有消息已标记为已读")
            st.rerun()
        
        for msg in messages:
            msg_dict = dict(msg)
            read_status = "已读" if msg_dict['is_read'] else "未读"
            read_color = "#28a745" if msg_dict['is_read'] else "#dc3545"
            
            with st.container():
                st.markdown(f"""
                <div style="background: {'#f8f9fa' if msg_dict['is_read'] else 'white'}; 
                            border-radius: 10px; padding: 15px; margin-bottom: 10px; 
                            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
                            border-left: 4px solid {read_color};">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <strong>{msg_dict['title']}</strong>
                        <span style="background: {read_color}; color: white; padding: 2px 8px; 
                                    border-radius: 10px; font-size: 11px;">{read_status}</span>
                    </div>
                    <p style="color: #666; margin: 5px 0;">{msg_dict['content'] or ''}</p>
                    <p style="color: #999; font-size: 12px;">{msg_dict['created_at']}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if not msg_dict['is_read']:
                    if st.button("标记已读", key=f"read_org_msg_{msg_dict['id']}"):
                        execute_query("UPDATE messages SET is_read = 1 WHERE id = ?", (msg_dict['id'],))
                        st.rerun()
    
    else:
        st.info("暂无消息通知")

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
