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

# ==================== 配置 ====================
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'performance.db')
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

# 创建上传目录
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# 页面配置
st.set_page_config(
    page_title="第三方绩效评估管理平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
            real_name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('super_admin', 'org_admin', 'org_user')),
            org_id INTEGER,
            email TEXT,
            phone TEXT,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'frozen', 'deleted')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(id)
        )
    ''')
    
    # 机构表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS organizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_code TEXT UNIQUE NOT NULL,
            org_name TEXT NOT NULL,
            org_type TEXT,
            credit_code TEXT,
            legal_person TEXT,
            contact_person TEXT,
            contact_phone TEXT,
            contact_email TEXT,
            address TEXT,
            description TEXT,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'frozen', 'deleted')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 项目表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_code TEXT UNIQUE NOT NULL,
            project_name TEXT NOT NULL,
            org_id INTEGER NOT NULL,
            project_type TEXT,
            client_name TEXT,
            client_contact TEXT,
            budget DECIMAL(15,2),
            start_date DATE,
            end_date DATE,
            status TEXT DEFAULT 'draft' CHECK(status IN ('draft', 'submitted', 'reviewing', 'approved', 'rejected', 'completed')),
            current_step INTEGER DEFAULT 1,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(id),
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    
    # 项目阶段表（5阶段）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            step_number INTEGER NOT NULL CHECK(step_number BETWEEN 1 AND 5),
            step_name TEXT NOT NULL,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'submitted', 'reviewing', 'approved', 'rejected')),
            submit_time TIMESTAMP,
            submit_by INTEGER,
            review_time TIMESTAMP,
            review_by INTEGER,
            review_comment TEXT,
            attachments TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (submit_by) REFERENCES users(id),
            FOREIGN KEY (review_by) REFERENCES users(id)
        )
    ''')
    
    # 主评人表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS evaluators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            id_number TEXT,
            qualification TEXT,
            specialty TEXT,
            experience_years INTEGER,
            phone TEXT,
            email TEXT,
            status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(id)
        )
    ''')
    
    # 业绩记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL,
            project_name TEXT NOT NULL,
            project_type TEXT,
            client_name TEXT,
            contract_amount DECIMAL(15,2),
            start_date DATE,
            end_date DATE,
            result TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(id)
        )
    ''')
    
    # 培训记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trainings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id INTEGER NOT NULL,
            training_name TEXT NOT NULL,
            training_type TEXT,
            organizer TEXT,
            start_date DATE,
            end_date DATE,
            participants TEXT,
            result TEXT,
            certificate TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (org_id) REFERENCES organizations(id)
        )
    ''')
    
    # 指标库表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indicator_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            indicator_name TEXT NOT NULL,
            indicator_code TEXT,
            description TEXT,
            calculation_method TEXT,
            data_source TEXT,
            weight DECIMAL(5,2),
            status TEXT DEFAULT 'active',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    
    # 政策文件表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS policy_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            file_type TEXT,
            file_path TEXT,
            file_size INTEGER,
            description TEXT,
            publisher TEXT,
            publish_date DATE,
            status TEXT DEFAULT 'active',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES users(id)
        )
    ''')
    
    # 待办事项表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            priority TEXT DEFAULT 'normal' CHECK(priority IN ('high', 'normal', 'low')),
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'completed')),
            due_date DATE,
            related_type TEXT,
            related_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 消息通知表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            msg_type TEXT DEFAULT 'system' CHECK(msg_type IN ('system', 'review', 'project', 'notice')),
            is_read INTEGER DEFAULT 0,
            related_type TEXT,
            related_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        )
    ''')
    
    # 操作日志表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT NOT NULL,
            target_type TEXT,
            target_id INTEGER,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    
    # 初始化超级管理员账号
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'super_admin'")
    if cursor.fetchone()[0] == 0:
        # 创建默认超级管理员
        default_password = "Admin@123456"
        password_hash = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('''
            INSERT INTO users (username, password_hash, real_name, role, email, phone, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('admin', password_hash, '超级管理员', 'super_admin', 'admin@system.com', '13800000000', 'active'))
        conn.commit()
    
    conn.close()

# ==================== 数据库操作类 ====================
class DatabaseManager:
    """数据库管理器"""
    
    @staticmethod
    def get_connection():
        """获取数据库连接"""
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def execute_query(sql, params=None, fetch=True):
        """执行查询"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            if fetch:
                result = cursor.fetchall()
                return [dict(row) for row in result]
            else:
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    @staticmethod
    def execute_insert(sql, params):
        """执行插入"""
        return DatabaseManager.execute_query(sql, params, fetch=False)
    
    @staticmethod
    def execute_update(sql, params):
        """执行更新"""
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(sql, params)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

# ==================== 用户认证管理 ====================
class AuthManager:
    """用户认证管理器"""
    
    @staticmethod
    def login(username, password):
        """用户登录"""
        users = DatabaseManager.execute_query(
            "SELECT * FROM users WHERE username = ? AND status = 'active'",
            (username,)
        )
        if not users:
            return None, "用户名不存在或账号已被禁用"
        
        user = users[0]
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            # 更新最后登录时间
            DatabaseManager.execute_update(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now(), user['id'])
            )
            # 记录登录日志
            log_action(user['id'], user['username'], '登录', 'user', user['id'], '用户登录成功')
            return user, None
        return None, "密码错误"
    
    @staticmethod
    def create_user(username, password, real_name, role, org_id=None, email=None, phone=None):
        """创建用户"""
        # 验证必填项
        if not username or not password or not real_name or not role:
            return None, "用户名、密码、真实姓名、角色为必填项"
        
        # 检查用户名是否已存在
        existing = DatabaseManager.execute_query(
            "SELECT id FROM users WHERE username = ?", (username,)
        )
        if existing:
            return None, "用户名已存在"
        
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        try:
            user_id = DatabaseManager.execute_insert(
                '''INSERT INTO users (username, password_hash, real_name, role, org_id, email, phone, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'active')''',
                (username, password_hash, real_name, role, org_id, email, phone)
            )
            return user_id, None
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def update_password(user_id, new_password):
        """更新密码"""
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        return DatabaseManager.execute_update(
            "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (password_hash, datetime.now(), user_id)
        )
    
    @staticmethod
    def reset_password(user_id):
        """重置密码为默认密码"""
        default_password = "Reset@123456"
        return AuthManager.update_password(user_id, default_password)
    
    @staticmethod
    def freeze_user(user_id):
        """冻结用户"""
        return DatabaseManager.execute_update(
            "UPDATE users SET status = 'frozen', updated_at = ? WHERE id = ?",
            (datetime.now(), user_id)
        )
    
    @staticmethod
    def activate_user(user_id):
        """激活用户"""
        return DatabaseManager.execute_update(
            "UPDATE users SET status = 'active', updated_at = ? WHERE id = ?",
            (datetime.now(), user_id)
        )

# ==================== 机构管理 ====================
class OrganizationManager:
    """机构管理器"""
    
    @staticmethod
    def create_org(org_data):
        """创建机构"""
        # 生成机构编码
        org_code = f"ORG{datetime.now().strftime('%Y%m%d%H%M%S')}"
        org_data['org_code'] = org_code
        org_data['created_at'] = datetime.now()
        org_data['updated_at'] = datetime.now()
        
        sql = '''
            INSERT INTO organizations (org_code, org_name, org_type, credit_code, legal_person,
                contact_person, contact_phone, contact_email, address, description, status, created_at, updated_at)
            VALUES (:org_code, :org_name, :org_type, :credit_code, :legal_person,
                :contact_person, :contact_phone, :contact_email, :address, :description, 'active', :created_at, :updated_at)
        '''
        return DatabaseManager.execute_insert(sql, org_data)
    
    @staticmethod
    def get_org_by_id(org_id):
        """获取机构信息"""
        orgs = DatabaseManager.execute_query(
            "SELECT * FROM organizations WHERE id = ?", (org_id,)
        )
        return orgs[0] if orgs else None
    
    @staticmethod
    def get_all_orgs(status=None):
        """获取所有机构"""
        if status:
            return DatabaseManager.execute_query(
                "SELECT * FROM organizations WHERE status = ? ORDER BY created_at DESC", (status,)
            )
        return DatabaseManager.execute_query(
            "SELECT * FROM organizations ORDER BY created_at DESC"
        )
    
    @staticmethod
    def update_org(org_id, org_data):
        """更新机构信息"""
        org_data['updated_at'] = datetime.now()
        sql = '''
            UPDATE organizations SET 
                org_name = :org_name, org_type = :org_type, credit_code = :credit_code,
                legal_person = :legal_person, contact_person = :contact_person,
                contact_phone = :contact_phone, contact_email = :contact_email,
                address = :address, description = :description, updated_at = :updated_at
            WHERE id = :org_id
        '''
        org_data['org_id'] = org_id
        return DatabaseManager.execute_update(sql, org_data)
    
    @staticmethod
    def freeze_org(org_id):
        """冻结机构"""
        # 冻结机构
        DatabaseManager.execute_update(
            "UPDATE organizations SET status = 'frozen', updated_at = ? WHERE id = ?",
            (datetime.now(), org_id)
        )
        # 冻结该机构所有用户
        return DatabaseManager.execute_update(
            "UPDATE users SET status = 'frozen', updated_at = ? WHERE org_id = ?",
            (datetime.now(), org_id)
        )
    
    @staticmethod
    def activate_org(org_id):
        """激活机构"""
        DatabaseManager.execute_update(
            "UPDATE organizations SET status = 'active', updated_at = ? WHERE id = ?",
            (datetime.now(), org_id)
        )
        return DatabaseManager.execute_update(
            "UPDATE users SET status = 'active', updated_at = ? WHERE org_id = ?",
            (datetime.now(), org_id)
        )

# ==================== 项目管理 ====================
class ProjectManager:
    """项目管理器"""
    
    # 项目阶段定义
    STEPS = {
        1: "项目立项",
        2: "方案设计",
        3: "数据采集",
        4: "分析评估",
        5: "报告编制"
    }
    
    @staticmethod
    def create_project(project_data, user_id):
        """创建项目"""
        # 生成项目编码
        project_code = f"PRJ{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        sql = '''
            INSERT INTO projects (project_code, project_name, org_id, project_type, client_name,
                client_contact, budget, start_date, end_date, status, current_step, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', 1, ?, ?, ?)
        '''
        project_id = DatabaseManager.execute_insert(sql, (
            project_code, project_data['project_name'], project_data['org_id'],
            project_data.get('project_type'), project_data.get('client_name'),
            project_data.get('client_contact'), project_data.get('budget'),
            project_data.get('start_date'), project_data.get('end_date'),
            user_id, datetime.now(), datetime.now()
        ))
        
        # 创建5个阶段记录
        for step_num, step_name in ProjectManager.STEPS.items():
            DatabaseManager.execute_insert(
                '''INSERT INTO project_steps (project_id, step_number, step_name, status, created_at, updated_at)
                   VALUES (?, ?, ?, 'pending', ?, ?)''',
                (project_id, step_num, step_name, datetime.now(), datetime.now())
            )
        
        return project_id
    
    @staticmethod
    def get_project_by_id(project_id):
        """获取项目详情"""
        projects = DatabaseManager.execute_query(
            '''SELECT p.*, o.org_name, u.real_name as creator_name
               FROM projects p
               LEFT JOIN organizations o ON p.org_id = o.id
               LEFT JOIN users u ON p.created_by = u.id
               WHERE p.id = ?''',
            (project_id,)
        )
        if projects:
            project = projects[0]
            # 获取阶段信息
            steps = DatabaseManager.execute_query(
                "SELECT * FROM project_steps WHERE project_id = ? ORDER BY step_number",
                (project_id,)
            )
            project['steps'] = steps
            return project
        return None
    
    @staticmethod
    def get_projects_by_org(org_id, status=None):
        """获取机构的项目列表"""
        if status:
            return DatabaseManager.execute_query(
                '''SELECT p.*, o.org_name FROM projects p
                   LEFT JOIN organizations o ON p.org_id = o.id
                   WHERE p.org_id = ? AND p.status = ?
                   ORDER BY p.created_at DESC''',
                (org_id, status)
            )
        return DatabaseManager.execute_query(
            '''SELECT p.*, o.org_name FROM projects p
               LEFT JOIN organizations o ON p.org_id = o.id
               WHERE p.org_id = ?
               ORDER BY p.created_at DESC''',
            (org_id,)
        )
    
    @staticmethod
    def get_all_projects(status=None):
        """获取所有项目"""
        if status:
            return DatabaseManager.execute_query(
                '''SELECT p.*, o.org_name, u.real_name as creator_name
                   FROM projects p
                   LEFT JOIN organizations o ON p.org_id = o.id
                   LEFT JOIN users u ON p.created_by = u.id
                   WHERE p.status = ?
                   ORDER BY p.created_at DESC''',
                (status,)
            )
        return DatabaseManager.execute_query(
            '''SELECT p.*, o.org_name, u.real_name as creator_name
               FROM projects p
               LEFT JOIN organizations o ON p.org_id = o.id
               LEFT JOIN users u ON p.created_by = u.id
               ORDER BY p.created_at DESC'''
        )
    
    @staticmethod
    def submit_step(project_id, step_number, user_id, attachments=None):
        """提交阶段"""
        # 更新阶段状态
        DatabaseManager.execute_update(
            '''UPDATE project_steps 
               SET status = 'submitted', submit_time = ?, submit_by = ?, attachments = ?, updated_at = ?
               WHERE project_id = ? AND step_number = ?''',
            (datetime.now(), user_id, attachments, datetime.now(), project_id, step_number)
        )
        
        # 更新项目状态
        DatabaseManager.execute_update(
            '''UPDATE projects SET status = 'reviewing', updated_at = ? WHERE id = ?''',
            (datetime.now(), project_id)
        )
        
        # 发送通知给管理员
        admins = DatabaseManager.execute_query(
            "SELECT id FROM users WHERE role = 'super_admin' AND status = 'active'"
        )
        project = ProjectManager.get_project_by_id(project_id)
        for admin in admins:
            create_message(
                None, admin['id'],
                f"项目审核通知 - {project['project_name']}",
                f"项目 {project['project_name']} 的 {ProjectManager.STEPS[step_number]} 阶段已提交，请及时审核。",
                'review', 'project', project_id
            )
    
    @staticmethod
    def review_step(project_id, step_number, reviewer_id, approved, comment):
        """审核阶段"""
        status = 'approved' if approved else 'rejected'
        
        # 更新阶段状态
        DatabaseManager.execute_update(
            '''UPDATE project_steps 
               SET status = ?, review_time = ?, review_by = ?, review_comment = ?, updated_at = ?
               WHERE project_id = ? AND step_number = ?''',
            (status, datetime.now(), reviewer_id, comment, datetime.now(), project_id, step_number)
        )
        
        project = ProjectManager.get_project_by_id(project_id)
        
        if approved:
            # 如果通过，更新到下一阶段
            if step_number < 5:
                DatabaseManager.execute_update(
                    '''UPDATE projects SET current_step = ?, status = 'submitted', updated_at = ? WHERE id = ?''',
                    (step_number + 1, datetime.now(), project_id)
                )
            else:
                # 项目完成
                DatabaseManager.execute_update(
                    '''UPDATE projects SET status = 'completed', updated_at = ? WHERE id = ?''',
                    (datetime.now(), project_id)
                )
        else:
            # 驳回，项目状态改为rejected
            DatabaseManager.execute_update(
                '''UPDATE projects SET status = 'rejected', updated_at = ? WHERE id = ?''',
                (datetime.now(), project_id)
            )
        
        # 发送通知给项目创建者
        create_message(
            reviewer_id, project['created_by'],
            f"审核结果通知 - {project['project_name']}",
            f"您的项目 {project['project_name']} 的 {ProjectManager.STEPS[step_number]} 阶段已{'通过' if approved else '被驳回'}。{'审核意见：' + comment if comment else ''}",
            'review', 'project', project_id
        )

# ==================== 消息和待办 ====================
def create_message(sender_id, receiver_id, title, content, msg_type='system', related_type=None, related_id=None):
    """创建消息"""
    return DatabaseManager.execute_insert(
        '''INSERT INTO messages (sender_id, receiver_id, title, content, msg_type, related_type, related_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (sender_id, receiver_id, title, content, msg_type, related_type, related_id, datetime.now())
    )

def get_unread_messages(user_id):
    """获取未读消息"""
    return DatabaseManager.execute_query(
        '''SELECT * FROM messages WHERE receiver_id = ? AND is_read = 0 ORDER BY created_at DESC''',
        (user_id,)
    )

def mark_message_read(message_id):
    """标记消息已读"""
    return DatabaseManager.execute_update(
        "UPDATE messages SET is_read = 1 WHERE id = ?", (message_id,)
    )

def create_todo(user_id, title, content, priority='normal', due_date=None, related_type=None, related_id=None):
    """创建待办"""
    return DatabaseManager.execute_insert(
        '''INSERT INTO todos (user_id, title, content, priority, due_date, related_type, related_id, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (user_id, title, content, priority, due_date, related_type, related_id, datetime.now())
    )

def get_todos(user_id, status='pending'):
    """获取待办事项"""
    return DatabaseManager.execute_query(
        '''SELECT * FROM todos WHERE user_id = ? AND status = ? ORDER BY 
           CASE priority WHEN 'high' THEN 1 WHEN 'normal' THEN 2 ELSE 3 END,
           due_date ASC, created_at DESC''',
        (user_id, status)
    )

def log_action(user_id, username, action, target_type=None, target_id=None, details=None):
    """记录操作日志"""
    return DatabaseManager.execute_insert(
        '''INSERT INTO logs (user_id, username, action, target_type, target_id, details, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (user_id, username, action, target_type, target_id, details, datetime.now())
    )

# ==================== 绩效智库管理 ====================
class IndicatorManager:
    """指标库管理"""
    
    @staticmethod
    def add_indicator(data, user_id):
        """添加指标"""
        return DatabaseManager.execute_insert(
            '''INSERT INTO indicator_library (category, indicator_name, indicator_code, description,
                calculation_method, data_source, weight, status, created_by, created_at, updated_at)
               VALUES (:category, :indicator_name, :indicator_code, :description,
                :calculation_method, :data_source, :weight, 'active', ?, ?, ?)''',
            {**data, 'created_by': user_id, 'created_at': datetime.now(), 'updated_at': datetime.now()}
        )
    
    @staticmethod
    def get_all_indicators():
        """获取所有指标"""
        return DatabaseManager.execute_query(
            "SELECT * FROM indicator_library WHERE status = 'active' ORDER BY category, indicator_name"
        )

class PolicyManager:
    """政策文件管理"""
    
    @staticmethod
    def add_policy(data, user_id):
        """添加政策文件"""
        data['created_by'] = user_id
        data['created_at'] = datetime.now()
        sql = '''
            INSERT INTO policy_files (title, file_type, file_path, file_size, description,
                publisher, publish_date, status, created_by, created_at)
            VALUES (:title, :file_type, :file_path, :file_size, :description,
                :publisher, :publish_date, 'active', :created_by, :created_at)
        '''
        return DatabaseManager.execute_insert(sql, data)
    
    @staticmethod
    def get_all_policies():
        """获取所有政策文件"""
        return DatabaseManager.execute_query(
            "SELECT * FROM policy_files WHERE status = 'active' ORDER BY publish_date DESC"
        )

# ==================== 数据导出 ====================
def export_to_excel(data, filename, sheet_name='Sheet1'):
    """导出数据到Excel"""
    output = BytesIO()
    df = pd.DataFrame(data)
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output

def export_to_pdf(data, title, columns):
    """导出数据到PDF"""
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=A4)
    elements = []
    
    # 添加标题
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=20,
        alignment=1  # 居中
    )
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 20))
    
    # 创建表格
    if data:
        table_data = [columns]  # 表头
        for row in data:
            table_data.append([str(row.get(col.lower().replace(' ', '_'), '')) for col in columns])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
    
    doc.build(elements)
    output.seek(0)
    return output

# ==================== UI样式 ====================
def apply_custom_styles():
    """应用自定义样式"""
    st.markdown('''
    <style>
        /* 主色调 */
        :root {
            --primary-color: #1f77b4;
            --secondary-color: #ff7f0e;
            --success-color: #2ca02c;
            --danger-color: #d62728;
            --warning-color: #ffbb33;
            --info-color: #17a2b8;
        }
        
        /* 侧边栏样式 */
        .css-1d391kg {
            background-color: #f8f9fa;
        }
        
        /* 卡片样式 */
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        
        /* 统计卡片 */
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            margin-bottom: 15px;
        }
        
        .stat-card h2 {
            color: white;
            font-size: 2.5rem;
            margin-bottom: 5px;
        }
        
        .stat-card p {
            color: rgba(255,255,255,0.9);
            font-size: 1rem;
            margin: 0;
        }
        
        /* 按钮样式 */
        .stButton>button {
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        /* 表格样式 */
        .stDataFrame {
            border-radius: 10px;
            overflow: hidden;
        }
        
        /* 标签样式 */
        .tag {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .tag-success { background-color: #d4edda; color: #155724; }
        .tag-warning { background-color: #fff3cd; color: #856404; }
        .tag-danger { background-color: #f8d7da; color: #721c24; }
        .tag-info { background-color: #d1ecf1; color: #0c5460; }
        
        /* 登录页面样式 */
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 40px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        
        /* 导航菜单样式 */
        .nav-menu {
            padding: 10px 0;
        }
        
        .nav-item {
            padding: 12px 20px;
            margin: 5px 0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .nav-item:hover {
            background-color: #e9ecef;
        }
        
        .nav-item.active {
            background-color: #1f77b4;
            color: white;
        }
        
        /* 进度条样式 */
        .step-progress {
            display: flex;
            justify-content: space-between;
            margin: 30px 0;
        }
        
        .step-item {
            text-align: center;
            flex: 1;
        }
        
        .step-circle {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .step-pending { background-color: #e9ecef; color: #6c757d; }
        .step-active { background-color: #007bff; color: white; }
        .step-done { background-color: #28a745; color: white; }
        .step-rejected { background-color: #dc3545; color: white; }
        
        /* 消息通知样式 */
        .message-item {
            padding: 15px;
            border-bottom: 1px solid #e9ecef;
            transition: background-color 0.3s ease;
        }
        
        .message-item:hover {
            background-color: #f8f9fa;
        }
        
        .message-unread {
            background-color: #e7f3ff;
            border-left: 3px solid #007bff;
        }
        
        /* 响应式调整 */
        @media (max-width: 768px) {
            .stat-card {
                padding: 15px;
            }
            .stat-card h2 {
                font-size: 1.8rem;
            }
        }
    </style>
    ''', unsafe_allow_html=True)

# ==================== 页面组件 ====================
def render_stat_card(title, value, icon="📊", color="#667eea"):
    """渲染统计卡片"""
    st.markdown(f'''
    <div class="stat-card" style="background: linear-gradient(135deg, {color} 0%, {color}dd 100%);">
        <h2>{icon} {value}</h2>
        <p>{title}</p>
    </div>
    ''', unsafe_allow_html=True)

def render_status_tag(status, status_map=None):
    """渲染状态标签"""
    if status_map is None:
        status_map = {
            'active': ('正常', 'success'),
            'frozen': ('已冻结', 'danger'),
            'pending': ('待处理', 'warning'),
            'submitted': ('已提交', 'info'),
            'reviewing': ('审核中', 'warning'),
            'approved': ('已通过', 'success'),
            'rejected': ('已驳回', 'danger'),
            'completed': ('已完成', 'success'),
            'draft': ('草稿', 'info'),
        }
    
    text, tag_type = status_map.get(status, (status, 'info'))
    return f'<span class="tag tag-{tag_type}">{text}</span>'

def render_step_progress(current_step, steps_status):
    """渲染项目阶段进度"""
    steps_html = '<div class="step-progress">'
    for i in range(1, 6):
        status = steps_status.get(i, 'pending')
        if status == 'approved':
            css_class = 'step-done'
        elif status == 'rejected':
            css_class = 'step-rejected'
        elif i == current_step:
            css_class = 'step-active'
        else:
            css_class = 'step-pending'
        
        steps_html += f'''
        <div class="step-item">
            <div class="step-circle {css_class}">{i}</div>
            <div style="font-size: 12px;">{ProjectManager.STEPS[i]}</div>
        </div>
        '''
    steps_html += '</div>'
    st.markdown(steps_html, unsafe_allow_html=True)

# ==================== 登录页面 ====================
def render_login_page():
    """渲染登录页面"""
    st.markdown('''
    <div style="text-align: center; padding: 50px 0;">
        <h1 style="font-size: 2.5rem; color: #1f77b4; margin-bottom: 10px;">📊 第三方绩效评估管理平台</h1>
        <p style="color: #6c757d; font-size: 1.1rem;">管理端 + 第三方机构端 双端系统</p>
    </div>
    ''', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.markdown("### 🔐 用户登录")
            username = st.text_input("用户名", placeholder="请输入用户名")
            password = st.text_input("密码", type="password", placeholder="请输入密码")
            
            col_a, col_b = st.columns(2)
            with col_a:
                login_btn = st.form_submit_button("登录", use_container_width=True)
            with col_b:
                client_type = st.selectbox("客户端类型", ["自动识别", "管理端", "机构端"])
            
            if login_btn:
                if not username or not password:
                    st.error("请输入用户名和密码")
                else:
                    user, error = AuthManager.login(username, password)
                    if user:
                        st.session_state['user'] = user
                        st.session_state['logged_in'] = True
                        st.rerun()
                    else:
                        st.error(error)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # 默认账号提示
        st.info("""
        **默认超级管理员账号：**
        - 用户名：`admin`
        - 密码：`Admin@123456`
        """)

# ==================== 管理端页面 ====================
def render_admin_dashboard():
    """管理端 - 数据大盘"""
    st.title("📊 数据大盘")
    
    # 统计数据
    orgs = OrganizationManager.get_all_orgs()
    projects = ProjectManager.get_all_projects()
    users = DatabaseManager.execute_query("SELECT * FROM users WHERE status = 'active'")
    
    active_orgs = len([o for o in orgs if o['status'] == 'active'])
    active_projects = len([p for p in projects if p['status'] in ('submitted', 'reviewing')])
    completed_projects = len([p for p in projects if p['status'] == 'completed'])
    
    # 统计卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_stat_card("机构总数", active_orgs, "🏢", "#667eea")
    with col2:
        render_stat_card("用户总数", len(users), "👥", "#764ba2")
    with col3:
        render_stat_card("进行中项目", active_projects, "📋", "#f093fb")
    with col4:
        render_stat_card("已完成项目", completed_projects, "✅", "#4facfe")
    
    st.markdown("---")
    
    # 图表区域
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📈 项目状态分布")
        status_counts = {}
        for p in projects:
            status_counts[p['status']] = status_counts.get(p['status'], 0) + 1
        
        if status_counts:
            fig = px.pie(
                values=list(status_counts.values()),
                names=list(status_counts.keys()),
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无项目数据")
    
    with col_right:
        st.subheader("📊 机构项目统计")
        org_project_counts = {}
        for p in projects:
            org_name = p.get('org_name', '未知')
            org_project_counts[org_name] = org_project_counts.get(org_name, 0) + 1
        
        if org_project_counts:
            fig = px.bar(
                x=list(org_project_counts.keys()),
                y=list(org_project_counts.values()),
                labels={'x': '机构', 'y': '项目数量'},
                color=list(org_project_counts.values()),
                color_continuous_scale='Blues'
            )
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0), xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无机构数据")
    
    # 最近项目
    st.subheader("📋 最近项目")
    recent_projects = projects[:10] if projects else []
    if recent_projects:
        df = pd.DataFrame([{
            '项目编码': p['project_code'],
            '项目名称': p['project_name'],
            '所属机构': p.get('org_name', '-'),
            '状态': p['status'],
            '当前阶段': f"第{p['current_step']}阶段",
            '创建时间': p['created_at'][:10] if p.get('created_at') else '-'
        } for p in recent_projects])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无项目数据")

def render_admin_organizations():
    """管理端 - 机构管理"""
    st.title("🏢 机构管理")
    
    tab1, tab2 = st.tabs(["机构列表", "新增机构"])
    
    with tab1:
        # 筛选
        col1, col2 = st.columns([3, 1])
        with col2:
            status_filter = st.selectbox("状态筛选", ["全部", "正常", "已冻结"])
        
        orgs = OrganizationManager.get_all_orgs()
        if status_filter == "正常":
            orgs = [o for o in orgs if o['status'] == 'active']
        elif status_filter == "已冻结":
            orgs = [o for o in orgs if o['status'] == 'frozen']
        
        if orgs:
            for org in orgs:
                with st.expander(f"**{org['org_name']}** ({org['org_code']})", expanded=False):
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"""
                        - **机构类型**: {org.get('org_type') or '-'}
                        - **统一社会信用代码**: {org.get('credit_code') or '-'}
                        - **法定代表人**: {org.get('legal_person') or '-'}
                        - **联系人**: {org.get('contact_person') or '-'}
                        - **联系电话**: {org.get('contact_phone') or '-'}
                        - **联系邮箱**: {org.get('contact_email') or '-'}
                        - **地址**: {org.get('address') or '-'}
                        - **简介**: {org.get('description') or '-'}
                        - **创建时间**: {org['created_at'][:10] if org.get('created_at') else '-'}
                        """)
                    with col2:
                        st.markdown(f"**状态**: {render_status_tag(org['status'])}", unsafe_allow_html=True)
                        
                        if org['status'] == 'active':
                            if st.button("❄️ 冻结机构", key=f"freeze_{org['id']}"):
                                OrganizationManager.freeze_org(org['id'])
                                st.success("机构已冻结")
                                st.rerun()
                        else:
                            if st.button("✅ 启用机构", key=f"activate_{org['id']}"):
                                OrganizationManager.activate_org(org['id'])
                                st.success("机构已启用")
                                st.rerun()
        else:
            st.info("暂无机构数据")
    
    with tab2:
        st.subheader("新增机构")
        with st.form("add_org_form"):
            col1, col2 = st.columns(2)
            with col1:
                org_name = st.text_input("机构名称 *", placeholder="必填")
                org_type = st.selectbox("机构类型", ["评估机构", "咨询机构", "审计机构", "其他"])
                credit_code = st.text_input("统一社会信用代码")
                legal_person = st.text_input("法定代表人")
                contact_person = st.text_input("联系人 *", placeholder="必填")
            with col2:
                contact_phone = st.text_input("联系电话 *", placeholder="必填")
                contact_email = st.text_input("联系邮箱")
                address = st.text_input("机构地址")
            
            description = st.text_area("机构简介", height=100)
            
            if st.form_submit_button("创建机构", use_container_width=True):
                if not org_name or not contact_person or not contact_phone:
                    st.error("请填写必填项（机构名称、联系人、联系电话）")
                else:
                    org_data = {
                        'org_name': org_name,
                        'org_type': org_type,
                        'credit_code': credit_code,
                        'legal_person': legal_person,
                        'contact_person': contact_person,
                        'contact_phone': contact_phone,
                        'contact_email': contact_email,
                        'address': address,
                        'description': description
                    }
                    try:
                        org_id = OrganizationManager.create_org(org_data)
                        # 创建机构主账号
                        default_password = "Org@123456"
                        username = f"org_{org_id}"
                        AuthManager.create_user(
                            username, default_password, 
                            f"{org_name}管理员", 'org_admin', 
                            org_id, contact_email, contact_phone
                        )
                        st.success(f"机构创建成功！主账号：{username}，默认密码：{default_password}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"创建失败：{str(e)}")

def render_admin_users():
    """管理端 - 账号管理"""
    st.title("👥 账号管理")
    
    # 筛选
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        role_filter = st.selectbox("角色筛选", ["全部", "超级管理员", "机构主账号", "机构子账号"])
    with col2:
        status_filter = st.selectbox("状态筛选", ["全部", "正常", "已冻结"])
    with col3:
        if st.button("🔄 刷新", use_container_width=True):
            st.rerun()
    
    role_map = {"超级管理员": "super_admin", "机构主账号": "org_admin", "机构子账号": "org_user"}
    status_map = {"正常": "active", "已冻结": "frozen"}
    
    users = DatabaseManager.execute_query('''
        SELECT u.*, o.org_name FROM users u
        LEFT JOIN organizations o ON u.org_id = o.id
        ORDER BY u.created_at DESC
    ''')
    
    # 应用筛选
    if role_filter != "全部":
        users = [u for u in users if u['role'] == role_map[role_filter]]
    if status_filter != "全部":
        users = [u for u in users if u['status'] == status_map[status_filter]]
    
    if users:
        for user in users:
            role_names = {'super_admin': '超级管理员', 'org_admin': '机构主账号', 'org_user': '机构子账号'}
            with st.expander(f"**{user['real_name']}** ({user['username']})", expanded=False):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"""
                    - **用户名**: {user['username']}
                    - **真实姓名**: {user['real_name']}
                    - **角色**: {role_names.get(user['role'], user['role'])}
                    - **所属机构**: {user.get('org_name') or '-'}
                    - **邮箱**: {user.get('email') or '-'}
                    - **电话**: {user.get('phone') or '-'}
                    - **创建时间**: {user['created_at'][:10] if user.get('created_at') else '-'}
                    - **最后登录**: {user['last_login'][:16] if user.get('last_login') else '从未登录'}
                    """)
                with col2:
                    st.markdown(f"**状态**: {render_status_tag(user['status'])}", unsafe_allow_html=True)
                    
                    if user['role'] != 'super_admin':
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if user['status'] == 'active':
                                if st.button("❄️ 冻结", key=f"freeze_user_{user['id']}"):
                                    AuthManager.freeze_user(user['id'])
                                    st.success("账号已冻结")
                                    st.rerun()
                            else:
                                if st.button("✅ 启用", key=f"activate_user_{user['id']}"):
                                    AuthManager.activate_user(user['id'])
                                    st.success("账号已启用")
                                    st.rerun()
                        with col_b:
                            if st.button("🔑 重置密码", key=f"reset_pwd_{user['id']}"):
                                AuthManager.reset_password(user['id'])
                                st.success("密码已重置为：Reset@123456")
    else:
        st.info("暂无用户数据")

def render_admin_projects():
    """管理端 - 项目审核"""
    st.title("📋 项目审核")
    
    # 筛选
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        status_filter = st.selectbox("状态筛选", ["全部", "审核中", "已通过", "已驳回", "已完成"])
    with col2:
        org_filter = st.selectbox("机构筛选", ["全部"] + [o['org_name'] for o in OrganizationManager.get_all_orgs()])
    with col3:
        if st.button("🔄 刷新", use_container_width=True):
            st.rerun()
    
    projects = ProjectManager.get_all_projects()
    
    # 应用筛选
    if status_filter != "全部":
        status_map = {"审核中": "reviewing", "已通过": "approved", "已驳回": "rejected", "已完成": "completed"}
        projects = [p for p in projects if p['status'] == status_map.get(status_filter, status_filter)]
    if org_filter != "全部":
        projects = [p for p in projects if p.get('org_name') == org_filter]
    
    if projects:
        for project in projects:
            with st.expander(f"**{project['project_name']}** ({project['project_code']})", expanded=False):
                # 项目基本信息
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"""
                    - **项目编码**: {project['project_code']}
                    - **所属机构**: {project.get('org_name', '-')}
                    - **项目类型**: {project.get('project_type') or '-'}
                    - **委托方**: {project.get('client_name') or '-'}
                    - **预算金额**: {project.get('budget') or '-'}
                    - **开始日期**: {project.get('start_date') or '-'}
                    - **结束日期**: {project.get('end_date') or '-'}
                    - **创建人**: {project.get('creator_name') or '-'}
                    - **创建时间**: {project['created_at'][:10] if project.get('created_at') else '-'}
                    """)
                with col2:
                    st.markdown(f"**状态**: {render_status_tag(project['status'])}", unsafe_allow_html=True)
                    st.markdown(f"**当前阶段**: 第{project['current_step']}阶段")
                
                # 阶段进度
                steps_status = {s['step_number']: s['status'] for s in project.get('steps', [])}
                render_step_progress(project['current_step'], steps_status)
                
                # 阶段详情和审核
                st.markdown("---")
                st.subheader("阶段审核")
                
                for step in project.get('steps', []):
                    step_name = ProjectManager.STEPS[step['step_number']]
                    with st.container():
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col1:
                            st.markdown(f"**{step_name}**")
                            st.markdown(f"状态: {render_status_tag(step['status'])}", unsafe_allow_html=True)
                        with col2:
                            if step.get('submit_time'):
                                st.markdown(f"提交时间: {step['submit_time'][:16]}")
                            if step.get('review_time'):
                                st.markdown(f"审核时间: {step['review_time'][:16]}")
                            if step.get('review_comment'):
                                st.markdown(f"审核意见: {step['review_comment']}")
                        with col3:
                            if step['status'] == 'submitted' and project['status'] == 'reviewing':
                                col_a, col_b = st.columns(2)
                                with col_a:
                                    if st.button("✅ 通过", key=f"approve_{project['id']}_{step['step_number']}"):
                                        ProjectManager.review_step(
                                            project['id'], step['step_number'],
                                            st.session_state['user']['id'], True, "审核通过"
                                        )
                                        st.success("审核通过")
                                        st.rerun()
                                with col_b:
                                    if st.button("❌ 驳回", key=f"reject_{project['id']}_{step['step_number']}"):
                                        st.session_state[f'rejecting_{project["id"]}_{step["step_number"]}'] = True
                                        st.rerun()
                        
                        # 驳回意见输入
                        if st.session_state.get(f'rejecting_{project["id"]}_{step["step_number"]}'):
                            reject_reason = st.text_area("驳回原因", key=f"reject_reason_{project['id']}_{step['step_number']}")
                            if st.button("确认驳回", key=f"confirm_reject_{project['id']}_{step['step_number']}"):
                                ProjectManager.review_step(
                                    project['id'], step['step_number'],
                                    st.session_state['user']['id'], False, reject_reason
                                )
                                st.session_state[f'rejecting_{project["id"]}_{step["step_number"]}'] = False
                                st.success("已驳回")
                                st.rerun()
    else:
        st.info("暂无项目数据")

def render_admin_export():
    """管理端 - 数据导出"""
    st.title("📥 数据导出")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("导出机构数据")
        if st.button("导出机构列表 (Excel)", use_container_width=True):
            orgs = OrganizationManager.get_all_orgs()
            if orgs:
                output = export_to_excel(orgs, "机构列表", "机构数据")
                st.download_button(
                    "下载 Excel 文件", output,
                    file_name=f"机构列表_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("暂无数据可导出")
        
        if st.button("导出用户列表 (Excel)", use_container_width=True):
            users = DatabaseManager.execute_query('''
                SELECT u.*, o.org_name FROM users u
                LEFT JOIN organizations o ON u.org_id = o.id
            ''')
            if users:
                output = export_to_excel(users, "用户列表", "用户数据")
                st.download_button(
                    "下载 Excel 文件", output,
                    file_name=f"用户列表_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("暂无数据可导出")
    
    with col2:
        st.subheader("导出项目数据")
        if st.button("导出项目列表 (Excel)", use_container_width=True):
            projects = ProjectManager.get_all_projects()
            if projects:
                output = export_to_excel(projects, "项目列表", "项目数据")
                st.download_button(
                    "下载 Excel 文件", output,
                    file_name=f"项目列表_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("暂无数据可导出")
        
        if st.button("导出项目详情 (Excel)", use_container_width=True):
            all_data = []
            projects = ProjectManager.get_all_projects()
            for p in projects:
                project_detail = ProjectManager.get_project_by_id(p['id'])
                for step in project_detail.get('steps', []):
                    all_data.append({
                        '项目编码': p['project_code'],
                        '项目名称': p['project_name'],
                        '机构': p.get('org_name'),
                        '阶段': ProjectManager.STEPS[step['step_number']],
                        '阶段状态': step['status'],
                        '提交时间': step.get('submit_time'),
                        '审核时间': step.get('review_time'),
                        '审核意见': step.get('review_comment')
                    })
            if all_data:
                output = export_to_excel(all_data, "项目详情", "项目阶段数据")
                st.download_button(
                    "下载 Excel 文件", output,
                    file_name=f"项目详情_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.warning("暂无数据可导出")

def render_admin_indicators():
    """管理端 - 绩效智库管理"""
    st.title("📚 绩效智库管理")
    
    tab1, tab2, tab3 = st.tabs(["指标库管理", "政策文件管理", "新增指标"])
    
    with tab1:
        indicators = IndicatorManager.get_all_indicators()
        if indicators:
            df = pd.DataFrame([{
                '分类': i['category'],
                '指标名称': i['indicator_name'],
                '指标编码': i.get('indicator_code') or '-',
                '描述': i.get('description') or '-',
                '权重': i.get('weight') or '-',
                '状态': i['status']
            } for i in indicators])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("暂无指标数据")
    
    with tab2:
        policies = PolicyManager.get_all_policies()
        if policies:
            for policy in policies:
                with st.expander(f"**{policy['title']}**"):
                    st.markdown(f"""
                    - **文件类型**: {policy.get('file_type') or '-'}
                    - **发布单位**: {policy.get('publisher') or '-'}
                    - **发布日期**: {policy.get('publish_date') or '-'}
                    - **描述**: {policy.get('description') or '-'}
                    """)
                    if policy.get('file_path'):
                        st.markdown(f"📎 [下载文件]({policy['file_path']})")
        else:
            st.info("暂无政策文件")
        
        # 上传政策文件
        st.markdown("---")
        st.subheader("上传政策文件")
        with st.form("upload_policy"):
            title = st.text_input("文件标题 *")
            file_type = st.selectbox("文件类型", ["政策法规", "行业标准", "技术规范", "其他"])
            publisher = st.text_input("发布单位")
            publish_date = st.date_input("发布日期")
            description = st.text_area("文件描述")
            uploaded_file = st.file_uploader("上传文件", type=['pdf', 'doc', 'docx', 'xls', 'xlsx'])
            
            if st.form_submit_button("上传"):
                if not title:
                    st.error("请填写文件标题")
                else:
                    file_path = None
                    if uploaded_file:
                        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                        with open(file_path, 'wb') as f:
                            f.write(uploaded_file.getbuffer())
                    
                    PolicyManager.add_policy({
                        'title': title,
                        'file_type': file_type,
                        'file_path': file_path,
                        'file_size': uploaded_file.size if uploaded_file else 0,
                        'description': description,
                        'publisher': publisher,
                        'publish_date': publish_date
                    }, st.session_state['user']['id'])
                    st.success("文件上传成功")
                    st.rerun()
    
    with tab3:
        st.subheader("新增指标")
        with st.form("add_indicator"):
            col1, col2 = st.columns(2)
            with col1:
                category = st.selectbox("指标分类", ["财务指标", "运营指标", "服务指标", "管理指标", "其他"])
                indicator_name = st.text_input("指标名称 *")
                indicator_code = st.text_input("指标编码")
                weight = st.number_input("权重(%)", 0, 100, 0)
            with col2:
                description = st.text_area("指标描述")
                calculation_method = st.text_area("计算方法")
                data_source = st.text_input("数据来源")
            
            if st.form_submit_button("添加指标"):
                if not indicator_name:
                    st.error("请填写指标名称")
                else:
                    IndicatorManager.add_indicator({
                        'category': category,
                        'indicator_name': indicator_name,
                        'indicator_code': indicator_code,
                        'description': description,
                        'calculation_method': calculation_method,
                        'data_source': data_source,
                        'weight': weight
                    }, st.session_state['user']['id'])
                    st.success("指标添加成功")
                    st.rerun()

# ==================== 机构端页面 ====================
def render_org_dashboard():
    """机构端 - 工作台"""
    st.title("🏠 工作台")
    
    user = st.session_state['user']
    org_id = user['org_id']
    
    # 统计数据
    projects = ProjectManager.get_projects_by_org(org_id)
    evaluators = DatabaseManager.execute_query(
        "SELECT * FROM evaluators WHERE org_id = ? AND status = 'active'", (org_id,)
    )
    pending_todos = get_todos(user['id'], 'pending')
    unread_messages = get_unread_messages(user['id'])
    
    # 统计卡片
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_stat_card("项目总数", len(projects), "📋", "#667eea")
    with col2:
        render_stat_card("进行中", len([p for p in projects if p['status'] in ('submitted', 'reviewing')]), "🔄", "#f093fb")
    with col3:
        render_stat_card("主评人", len(evaluators), "👥", "#4facfe")
    with col4:
        render_stat_card("待办事项", len(pending_todos), "📝", "#43e97b")
    
    st.markdown("---")
    
    # 快捷入口
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📌 待办事项")
        if pending_todos:
            for todo in pending_todos[:5]:
                priority_colors = {'high': '🔴', 'normal': '🟡', 'low': '🟢'}
                st.markdown(f"{priority_colors.get(todo['priority'], '⚪')} {todo['title']}")
                if todo.get('due_date'):
                    st.caption(f"截止日期: {todo['due_date']}")
        else:
            st.info("暂无待办事项")
        
        st.markdown("---")
        st.subheader("📬 未读消息")
        if unread_messages:
            for msg in unread_messages[:5]:
                st.markdown(f"**{msg['title']}**")
                st.caption(f"{msg['created_at'][:16]}")
        else:
            st.info("暂无未读消息")
    
    with col2:
        st.subheader("📊 项目状态分布")
        status_counts = {}
        for p in projects:
            status_counts[p['status']] = status_counts.get(p['status'], 0) + 1
        
        if status_counts:
            fig = px.pie(
                values=list(status_counts.values()),
                names=list(status_counts.keys()),
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无项目数据")
        
        st.markdown("---")
        st.subheader("📈 近期项目")
        recent_projects = projects[:5] if projects else []
        if recent_projects:
            for p in recent_projects:
                st.markdown(f"- **{p['project_name']}** ({render_status_tag(p['status'])})", unsafe_allow_html=True)
        else:
            st.info("暂无项目")

def render_org_info():
    """机构端 - 信息维护"""
    st.title("🏢 信息维护")
    
    user = st.session_state['user']
    org_id = user['org_id']
    
    tab1, tab2, tab3, tab4 = st.tabs(["机构信息", "主评人管理", "业绩记录", "培训记录"])
    
    with tab1:
        org = OrganizationManager.get_org_by_id(org_id)
        if org:
            with st.form("update_org"):
                col1, col2 = st.columns(2)
                with col1:
                    org_name = st.text_input("机构名称", org['org_name'])
                    org_type = st.selectbox("机构类型", 
                        ["评估机构", "咨询机构", "审计机构", "其他"],
                        index=["评估机构", "咨询机构", "审计机构", "其他"].index(org.get('org_type')) if org.get('org_type') else 0)
                    credit_code = st.text_input("统一社会信用代码", org.get('credit_code') or '')
                    legal_person = st.text_input("法定代表人", org.get('legal_person') or '')
                    contact_person = st.text_input("联系人", org.get('contact_person') or '')
                with col2:
                    contact_phone = st.text_input("联系电话", org.get('contact_phone') or '')
                    contact_email = st.text_input("联系邮箱", org.get('contact_email') or '')
                    address = st.text_input("机构地址", org.get('address') or '')
                
                description = st.text_area("机构简介", org.get('description') or '', height=100)
                
                if st.form_submit_button("保存修改"):
                    OrganizationManager.update_org(org_id, {
                        'org_name': org_name,
                        'org_type': org_type,
                        'credit_code': credit_code,
                        'legal_person': legal_person,
                        'contact_person': contact_person,
                        'contact_phone': contact_phone,
                        'contact_email': contact_email,
                        'address': address,
                        'description': description
                    })
                    st.success("保存成功")
                    st.rerun()
    
    with tab2:
        evaluators = DatabaseManager.execute_query(
            "SELECT * FROM evaluators WHERE org_id = ? ORDER BY created_at DESC", (org_id,)
        )
        
        # 新增主评人
        with st.expander("➕ 新增主评人"):
            with st.form("add_evaluator"):
                col1, col2 = st.columns(2)
                with col1:
                    name = st.text_input("姓名 *")
                    id_number = st.text_input("身份证号")
                    qualification = st.text_input("资质证书")
                with col2:
                    specialty = st.text_input("专业领域")
                    experience_years = st.number_input("从业年限", 0, 50, 0)
                    phone = st.text_input("联系电话")
                
                email = st.text_input("电子邮箱")
                
                if st.form_submit_button("添加"):
                    if not name:
                        st.error("请填写姓名")
                    else:
                        DatabaseManager.execute_insert(
                            '''INSERT INTO evaluators (org_id, name, id_number, qualification, specialty,
                                experience_years, phone, email, status, created_at, updated_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)''',
                            (org_id, name, id_number, qualification, specialty,
                             experience_years, phone, email, datetime.now(), datetime.now())
                        )
                        st.success("添加成功")
                        st.rerun()
        
        # 主评人列表
        if evaluators:
            for ev in evaluators:
                with st.expander(f"**{ev['name']}**"):
                    st.markdown(f"""
                    - **身份证号**: {ev.get('id_number') or '-'}
                    - **资质证书**: {ev.get('qualification') or '-'}
                    - **专业领域**: {ev.get('specialty') or '-'}
                    - **从业年限**: {ev.get('experience_years') or 0}年
                    - **联系电话**: {ev.get('phone') or '-'}
                    - **电子邮箱**: {ev.get('email') or '-'}
                    """)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if ev['status'] == 'active':
                            if st.button("禁用", key=f"deactivate_ev_{ev['id']}"):
                                DatabaseManager.execute_update(
                                    "UPDATE evaluators SET status = 'inactive', updated_at = ? WHERE id = ?",
                                    (datetime.now(), ev['id'])
                                )
                                st.success("已禁用")
                                st.rerun()
                        else:
                            if st.button("启用", key=f"activate_ev_{ev['id']}"):
                                DatabaseManager.execute_update(
                                    "UPDATE evaluators SET status = 'active', updated_at = ? WHERE id = ?",
                                    (datetime.now(), ev['id'])
                                )
                                st.success("已启用")
                                st.rerun()
    
    with tab3:
        achievements = DatabaseManager.execute_query(
            "SELECT * FROM achievements WHERE org_id = ? ORDER BY created_at DESC", (org_id,)
        )
        
        with st.expander("➕ 新增业绩记录"):
            with st.form("add_achievement"):
                col1, col2 = st.columns(2)
                with col1:
                    ach_project_name = st.text_input("项目名称 *")
                    ach_project_type = st.selectbox("项目类型", ["绩效评估", "专项审计", "咨询服务", "其他"])
                    ach_client = st.text_input("委托方")
                with col2:
                    ach_amount = st.number_input("合同金额(元)", 0.0)
                    ach_start_date = st.date_input("开始日期")
                    ach_end_date = st.date_input("结束日期")
                
                ach_result = st.text_input("项目成果")
                ach_description = st.text_area("项目描述")
                
                if st.form_submit_button("添加"):
                    if not ach_project_name:
                        st.error("请填写项目名称")
                    else:
                        DatabaseManager.execute_insert(
                            '''INSERT INTO achievements (org_id, project_name, project_type, client_name,
                                contract_amount, start_date, end_date, result, description, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (org_id, ach_project_name, ach_project_type, ach_client,
                             ach_amount, str(ach_start_date), str(ach_end_date), ach_result, ach_description, datetime.now())
                        )
                        st.success("添加成功")
                        st.rerun()
        
        if achievements:
            df = pd.DataFrame([{
                '项目名称': a['project_name'],
                '项目类型': a['project_type'],
                '委托方': a['client_name'],
                '合同金额': a['contract_amount'],
                '开始日期': a['start_date'],
                '结束日期': a['end_date'],
                '项目成果': a['result']
            } for a in achievements])
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    with tab4:
        trainings = DatabaseManager.execute_query(
            "SELECT * FROM trainings WHERE org_id = ? ORDER BY created_at DESC", (org_id,)
        )
        
        with st.expander("➕ 新增培训记录"):
            with st.form("add_training"):
                col1, col2 = st.columns(2)
                with col1:
                    train_name = st.text_input("培训名称 *")
                    train_type = st.selectbox("培训类型", ["业务培训", "技能培训", "管理培训", "其他"])
                    train_organizer = st.text_input("培训机构")
                with col2:
                    train_start = st.date_input("开始日期")
                    train_end = st.date_input("结束日期")
                    train_result = st.text_input("培训结果")
                
                train_participants = st.text_area("参训人员")
                train_certificate = st.text_input("证书编号")
                
                if st.form_submit_button("添加"):
                    if not train_name:
                        st.error("请填写培训名称")
                    else:
                        DatabaseManager.execute_insert(
                            '''INSERT INTO trainings (org_id, training_name, training_type, organizer,
                                start_date, end_date, participants, result, certificate, created_at)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (org_id, train_name, train_type, train_organizer,
                             str(train_start), str(train_end), train_participants, train_result, train_certificate, datetime.now())
                        )
                        st.success("添加成功")
                        st.rerun()
        
        if trainings:
            df = pd.DataFrame([{
                '培训名称': t['training_name'],
                '培训类型': t['training_type'],
                '培训机构': t['organizer'],
                '开始日期': t['start_date'],
                '结束日期': t['end_date'],
                '培训结果': t['result']
            } for t in trainings])
            st.dataframe(df, use_container_width=True, hide_index=True)

def render_org_sub_accounts():
    """机构端 - 子账号管理"""
    st.title("👥 子账号管理")
    
    user = st.session_state['user']
    org_id = user['org_id']
    
    # 获取子账号列表
    sub_users = DatabaseManager.execute_query(
        "SELECT * FROM users WHERE org_id = ? AND role = 'org_user' ORDER BY created_at DESC",
        (org_id,)
    )
    
    tab1, tab2 = st.tabs(["子账号列表", "新增子账号"])
    
    with tab1:
        if sub_users:
            for su in sub_users:
                with st.expander(f"**{su['real_name']}** ({su['username']})"):
                    st.markdown(f"""
                    - **用户名**: {su['username']}
                    - **真实姓名**: {su['real_name']}
                    - **邮箱**: {su.get('email') or '-'}
                    - **电话**: {su.get('phone') or '-'}
                    - **状态**: {render_status_tag(su['status'])}
                    - **创建时间**: {su['created_at'][:10] if su.get('created_at') else '-'}
                    - **最后登录**: {su['last_login'][:16] if su.get('last_login') else '从未登录'}
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if su['status'] == 'active':
                            if st.button("❄️ 冻结", key=f"freeze_sub_{su['id']}"):
                                AuthManager.freeze_user(su['id'])
                                st.success("已冻结")
                                st.rerun()
                        else:
                            if st.button("✅ 启用", key=f"activate_sub_{su['id']}"):
                                AuthManager.activate_user(su['id'])
                                st.success("已启用")
                                st.rerun()
                    with col2:
                        if st.button("🔑 重置密码", key=f"reset_sub_{su['id']}"):
                            AuthManager.reset_password(su['id'])
                            st.success("密码已重置为：Reset@123456")
        else:
            st.info("暂无子账号")
    
    with tab2:
        with st.form("add_sub_account"):
            col1, col2 = st.columns(2)
            with col1:
                sub_username = st.text_input("用户名 *", placeholder="必填，用于登录")
                sub_real_name = st.text_input("真实姓名 *", placeholder="必填")
            with col2:
                sub_password = st.text_input("密码 *", type="password", placeholder="必填")
                sub_confirm = st.text_input("确认密码 *", type="password")
            
            sub_email = st.text_input("邮箱")
            sub_phone = st.text_input("电话")
            
            if st.form_submit_button("创建子账号"):
                if not sub_username or not sub_real_name or not sub_password:
                    st.error("用户名、真实姓名、密码为必填项")
                elif sub_password != sub_confirm:
                    st.error("两次输入的密码不一致")
                else:
                    user_id, error = AuthManager.create_user(
                        sub_username, sub_password, sub_real_name,
                        'org_user', org_id, sub_email, sub_phone
                    )
                    if user_id:
                        st.success(f"子账号创建成功！用户名：{sub_username}")
                        st.rerun()
                    else:
                        st.error(error)

def render_org_projects():
    """机构端 - 项目管理"""
    st.title("📋 项目管理")
    
    user = st.session_state['user']
    org_id = user['org_id']
    
    tab1, tab2 = st.tabs(["项目列表", "新建项目"])
    
    with tab1:
        # 筛选
        status_filter = st.selectbox("状态筛选", ["全部", "草稿", "审核中", "已通过", "已驳回", "已完成"])
        
        projects = ProjectManager.get_projects_by_org(org_id)
        
        if status_filter != "全部":
            status_map = {"草稿": "draft", "审核中": "reviewing", "已通过": "approved", "已驳回": "rejected", "已完成": "completed"}
            projects = [p for p in projects if p['status'] == status_map.get(status_filter, status_filter)]
        
        if projects:
            for project in projects:
                with st.expander(f"**{project['project_name']}** ({project['project_code']})", expanded=False):
                    # 项目基本信息
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.markdown(f"""
                        - **项目编码**: {project['project_code']}
                        - **项目类型**: {project.get('project_type') or '-'}
                        - **委托方**: {project.get('client_name') or '-'}
                        - **联系方式**: {project.get('client_contact') or '-'}
                        - **预算金额**: {project.get('budget') or '-'}
                        - **开始日期**: {project.get('start_date') or '-'}
                        - **结束日期**: {project.get('end_date') or '-'}
                        - **创建时间**: {project['created_at'][:10] if project.get('created_at') else '-'}
                        """)
                    with col2:
                        st.markdown(f"**状态**: {render_status_tag(project['status'])}", unsafe_allow_html=True)
                        st.markdown(f"**当前阶段**: 第{project['current_step']}阶段")
                    
                    # 阶段进度
                    steps_status = {s['step_number']: s['status'] for s in project.get('steps', [])}
                    render_step_progress(project['current_step'], steps_status)
                    
                    # 阶段操作
                    st.markdown("---")
                    st.subheader("阶段操作")
                    
                    for step in project.get('steps', []):
                        step_name = ProjectManager.STEPS[step['step_number']]
                        with st.container():
                            col1, col2, col3 = st.columns([1, 2, 1])
                            with col1:
                                st.markdown(f"**{step_name}**")
                                st.markdown(f"状态: {render_status_tag(step['status'])}", unsafe_allow_html=True)
                            with col2:
                                if step.get('review_comment'):
                                    st.markdown(f"审核意见: {step['review_comment']}")
                            with col3:
                                # 只有当前阶段且状态为pending时可以提交
                                if step['step_number'] == project['current_step'] and step['status'] == 'pending':
                                    if st.button("📤 提交审核", key=f"submit_step_{project['id']}_{step['step_number']}"):
                                        ProjectManager.submit_step(project['id'], step['step_number'], user['id'])
                                        st.success("已提交审核")
                                        st.rerun()
        else:
            st.info("暂无项目数据")
    
    with tab2:
        st.subheader("新建项目")
        with st.form("create_project"):
            col1, col2 = st.columns(2)
            with col1:
                project_name = st.text_input("项目名称 *")
                project_type = st.selectbox("项目类型", ["绩效评估", "专项审计", "咨询服务", "其他"])
                client_name = st.text_input("委托方")
                client_contact = st.text_input("委托方联系方式")
            with col2:
                budget = st.number_input("预算金额(元)", 0.0)
                start_date = st.date_input("开始日期")
                end_date = st.date_input("结束日期")
            
            if st.form_submit_button("创建项目"):
                if not project_name:
                    st.error("请填写项目名称")
                else:
                    project_id = ProjectManager.create_project({
                        'project_name': project_name,
                        'org_id': org_id,
                        'project_type': project_type,
                        'client_name': client_name,
                        'client_contact': client_contact,
                        'budget': budget,
                        'start_date': str(start_date),
                        'end_date': str(end_date)
                    }, user['id'])
                    st.success(f"项目创建成功！项目编码：PRJ{datetime.now().strftime('%Y%m%d%H%M%S')}")
                    st.rerun()

def render_org_knowledge():
    """机构端 - 绩效智库"""
    st.title("📚 绩效智库")
    
    tab1, tab2 = st.tabs(["指标库", "政策文件"])
    
    with tab1:
        indicators = IndicatorManager.get_all_indicators()
        if indicators:
            # 按分类显示
            categories = {}
            for i in indicators:
                if i['category'] not in categories:
                    categories[i['category']] = []
                categories[i['category']].append(i)
            
            for cat, items in categories.items():
                with st.expander(f"**{cat}** ({len(items)}个指标)"):
                    for item in items:
                        st.markdown(f"""
                        **{item['indicator_name']}** ({item.get('indicator_code') or '-'})
                        - 描述: {item.get('description') or '-'}
                        - 计算方法: {item.get('calculation_method') or '-'}
                        - 数据来源: {item.get('data_source') or '-'}
                        - 权重: {item.get('weight') or 0}%
                        """)
                        st.markdown("---")
        else:
            st.info("暂无指标数据")
    
    with tab2:
        policies = PolicyManager.get_all_policies()
        if policies:
            for policy in policies:
                with st.expander(f"**{policy['title']}**"):
                    st.markdown(f"""
                    - **文件类型**: {policy.get('file_type') or '-'}
                    - **发布单位**: {policy.get('publisher') or '-'}
                    - **发布日期**: {policy.get('publish_date') or '-'}
                    - **描述**: {policy.get('description') or '-'}
                    """)
                    if policy.get('file_path'):
                        st.markdown(f"📎 [下载文件]({policy['file_path']})")
        else:
            st.info("暂无政策文件")

def render_org_messages():
    """机构端 - 待办 & 消息"""
    st.title("📨 待办 & 消息")
    
    user = st.session_state['user']
    
    tab1, tab2 = st.tabs(["待办事项", "消息通知"])
    
    with tab1:
        # 新增待办
        with st.expander("➕ 新增待办"):
            with st.form("add_todo"):
                todo_title = st.text_input("待办标题 *")
                todo_content = st.text_area("待办内容")
                col1, col2 = st.columns(2)
                with col1:
                    todo_priority = st.selectbox("优先级", ["普通", "高", "低"])
                with col2:
                    todo_due_date = st.date_input("截止日期")
                
                if st.form_submit_button("添加"):
                    if not todo_title:
                        st.error("请填写待办标题")
                    else:
                        priority_map = {"高": "high", "普通": "normal", "低": "low"}
                        create_todo(user['id'], todo_title, todo_content, 
                                   priority_map[todo_priority], str(todo_due_date))
                        st.success("添加成功")
                        st.rerun()
        
        # 待办列表
        pending_todos = get_todos(user['id'], 'pending')
        completed_todos = get_todos(user['id'], 'completed')
        
        st.subheader("待处理")
        if pending_todos:
            for todo in pending_todos:
                priority_colors = {'high': '🔴', 'normal': '🟡', 'low': '🟢'}
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"{priority_colors.get(todo['priority'], '⚪')} **{todo['title']}**")
                        if todo.get('content'):
                            st.caption(todo['content'])
                        if todo.get('due_date'):
                            st.caption(f"截止: {todo['due_date']}")
                    with col3:
                        if st.button("✓ 完成", key=f"complete_todo_{todo['id']}"):
                            DatabaseManager.execute_update(
                                "UPDATE todos SET status = 'completed', completed_at = ? WHERE id = ?",
                                (datetime.now(), todo['id'])
                            )
                            st.success("已完成")
                            st.rerun()
                    st.markdown("---")
        else:
            st.info("暂无待处理事项")
        
        st.subheader("已完成")
        if completed_todos:
            for todo in completed_todos[:10]:
                st.markdown(f"✅ ~~{todo['title']}~~ (完成于 {todo['completed_at'][:10] if todo.get('completed_at') else '-'})")
    
    with tab2:
        # 消息列表
        all_messages = DatabaseManager.execute_query(
            "SELECT * FROM messages WHERE receiver_id = ? ORDER BY created_at DESC",
            (user['id'],)
        )
        
        if all_messages:
            for msg in all_messages:
                msg_class = "message-unread" if not msg['is_read'] else ""
                with st.container():
                    st.markdown(f"""
                    <div class="message-item {msg_class}">
                        <strong>{msg['title']}</strong><br/>
                        <small>{msg['created_at'][:16]}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if msg.get('content'):
                        st.markdown(f"<div style='padding: 0 15px;'>{msg['content']}</div>", unsafe_allow_html=True)
                    
                    if not msg['is_read']:
                        if st.button("标记已读", key=f"read_msg_{msg['id']}"):
                            mark_message_read(msg['id'])
                            st.rerun()
                    
                    st.markdown("---")
        else:
            st.info("暂无消息")

# ==================== 主应用 ====================
def render_sidebar():
    """渲染侧边栏"""
    user = st.session_state['user']
    role = user['role']
    
    with st.sidebar:
        # 用户信息
        st.markdown(f"""
        <div style="text-align: center; padding: 20px 0; border-bottom: 1px solid #e9ecef;">
            <h3>👤 {user['real_name']}</h3>
            <p style="color: #6c757d; font-size: 14px;">
                {'超级管理员' if role == 'super_admin' else ('机构主账号' if role == 'org_admin' else '机构子账号')}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 未读消息提醒
        unread = get_unread_messages(user['id'])
        if unread:
            st.markdown(f"""
            <div style="background: #e7f3ff; padding: 10px; border-radius: 8px; margin: 10px 0;">
                📬 您有 <strong>{len(unread)}</strong> 条未读消息
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # 导航菜单
        if role == 'super_admin':
            # 管理端菜单
            menu_items = [
                ("📊 数据大盘", "dashboard"),
                ("🏢 机构管理", "organizations"),
                ("👥 账号管理", "users"),
                ("📋 项目审核", "projects"),
                ("📥 数据导出", "export"),
                ("📚 绩效智库管理", "indicators")
            ]
        else:
            # 机构端菜单
            menu_items = [
                ("🏠 工作台", "dashboard"),
                ("🏢 信息维护", "info"),
                ("👥 子账号管理", "sub_accounts"),
                ("📋 项目管理", "projects"),
                ("📚 绩效智库", "knowledge"),
                ("📨 待办 & 消息", "messages")
            ]
        
        # 初始化页面状态
        if 'current_page' not in st.session_state:
            st.session_state['current_page'] = 'dashboard'
        
        for label, page in menu_items:
            # st.button 旧版本 Streamlit 不支持 type 参数，避免异常导致白屏
            if st.button(label, use_container_width=True, key=f"menu_{page}"):
                st.session_state['current_page'] = page
                st.rerun()
        
        st.markdown("---")
        
        # 退出登录
        if st.button("🚪 退出登录", use_container_width=True):
            log_action(user['id'], user['username'], '退出登录', 'user', user['id'], '用户退出登录')
            st.session_state.clear()
            st.rerun()

def debug_status():
    st.markdown('### 🔧 调试信息（仅开发时显示）')
    st.write('session_state keys:', list(st.session_state.keys()))
    st.write('logged_in:', st.session_state.get('logged_in'))
    st.write('user:', st.session_state.get('user'))
    st.write('current_page:', st.session_state.get('current_page'))


def main():
    """主函数"""
    # 初始化数据库
    init_database()

    # 应用自定义样式
    apply_custom_styles()

    # 调试：显示当前 session 状态
    debug_status()

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
        elif page == 'export':
            render_admin_export()
        elif page == 'indicators':
            render_admin_indicators()
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
        elif page == 'messages':
            render_org_messages()

if __name__ == "__main__":
    main()
