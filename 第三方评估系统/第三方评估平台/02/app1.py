import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import datetime
from datetime import timedelta
import openpyxl
from fpdf import FPDF
import json
import requests
import time
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -------------------------- 页面配置（美化）--------------------------
st.set_page_config(
    page_title="第三方机构绩效评估系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------- 现代化CSS样式 --------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

:root {
    --primary-color: #0ea5e9;
    --primary-dark: #0284c7;
    --secondary-color: #6366f1;
    --success-color: #10b981;
    --warning-color: #f59e0b;
    --danger-color: #ef4444;
    --info-color: #3b82f6;
    --bg-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    --card-shadow: 0 10px 40px rgba(0,0,0,0.1);
    --hover-shadow: 0 20px 60px rgba(0,0,0,0.15);
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

/* 主标题样式 */
.main-header {
    font-size: 42px;
    font-weight: 800;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    text-align: center;
    margin-bottom: 30px;
    letter-spacing: -1px;
}

/* 副标题样式 */
.sub-header {
    font-size: 24px;
    color: #1e293b;
    font-weight: 700;
    margin: 20px 0 15px 0;
    padding-bottom: 10px;
    border-bottom: 3px solid linear-gradient(90deg, #667eea, #764ba2);
    position: relative;
}

.sub-header::after {
    content: '';
    position: absolute;
    bottom: -3px;
    left: 0;
    width: 60px;
    height: 3px;
    background: linear-gradient(90deg, #667eea, #764ba2);
    border-radius: 2px;
}

/* 卡片样式 */
.card {
    background: white;
    border-radius: 20px;
    padding: 25px;
    box-shadow: var(--card-shadow);
    transition: all 0.3s ease;
    border: 1px solid rgba(226, 232, 240, 0.8);
    margin-bottom: 20px;
}

.card:hover {
    transform: translateY(-5px);
    box-shadow: var(--hover-shadow);
}

/* 统计卡片 */
.stat-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 16px;
    padding: 25px;
    color: white;
    text-align: center;
    transition: all 0.3s ease;
    cursor: pointer;
}

.stat-card:hover {
    transform: scale(1.05);
    box-shadow: 0 15px 50px rgba(102, 126, 234, 0.4);
}

.stat-card.success {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

.stat-card.warning {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.stat-card.info {
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
}

.stat-number {
    font-size: 36px;
    font-weight: 800;
    margin-bottom: 5px;
}

.stat-label {
    font-size: 14px;
    opacity: 0.9;
    font-weight: 500;
}

/* 按钮样式 */
.stButton > button {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 28px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4) !important;
}

.stButton > button:active {
    transform: translateY(0) !important;
}

/* 次要按钮 */
.btn-secondary > button {
    background: white !important;
    color: #667eea !important;
    border: 2px solid #667eea !important;
}

.btn-secondary > button:hover {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
    color: white !important;
}

/* 危险按钮 */
.btn-danger > button {
    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
    box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3) !important;
}

.btn-danger > button:hover {
    box-shadow: 0 8px 25px rgba(239, 68, 68, 0.4) !important;
}

/* 成功按钮 */
.btn-success > button {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3) !important;
}

/* 登录表单 */
.login-container {
    background: white;
    border-radius: 24px;
    padding: 50px;
    box-shadow: var(--card-shadow);
    max-width: 450px;
    margin: 0 auto;
    position: relative;
    overflow: hidden;
}

.login-container::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 5px;
    background: linear-gradient(90deg, #667eea, #764ba2, #f093fb);
}

/* 输入框样式 */
.stTextInput > div > div > input {
    border-radius: 12px !important;
    border: 2px solid #e2e8f0 !important;
    padding: 14px 18px !important;
    font-size: 15px !important;
    transition: all 0.3s ease !important;
}

.stTextInput > div > div > input:focus {
    border-color: #667eea !important;
    box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1) !important;
}

/* 侧边栏样式 */
.css-1d391kg, .css-163ttbj {
    background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%) !important;
}

.sidebar-content {
    padding: 20px;
}

.sidebar-title {
    color: white;
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

/* 菜单项 */
.menu-item {
    padding: 12px 16px;
    border-radius: 12px;
    margin-bottom: 8px;
    color: rgba(255,255,255,0.8);
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    gap: 12px;
}

.menu-item:hover {
    background: rgba(255,255,255,0.1);
    color: white;
}

.menu-item.active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

/* 表格样式 */
.stDataFrame {
    border-radius: 16px !important;
    overflow: hidden !important;
}

/* 标签样式 */
.badge {
    display: inline-block;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.badge-success {
    background: rgba(16, 185, 129, 0.15);
    color: #059669;
}

.badge-warning {
    background: rgba(245, 158, 11, 0.15);
    color: #d97706;
}

.badge-danger {
    background: rgba(239, 68, 68, 0.15);
    color: #dc2626;
}

.badge-info {
    background: rgba(59, 130, 246, 0.15);
    color: #2563eb;
}

/* 进度条样式 */
.progress-container {
    background: #e2e8f0;
    border-radius: 10px;
    height: 10px;
    overflow: hidden;
    margin: 10px 0;
}

.progress-bar {
    height: 100%;
    border-radius: 10px;
    transition: width 0.5s ease;
}

.progress-bar.excellent {
    background: linear-gradient(90deg, #10b981, #34d399);
}

.progress-bar.good {
    background: linear-gradient(90deg, #3b82f6, #60a5fa);
}

.progress-bar.pass {
    background: linear-gradient(90deg, #f59e0b, #fbbf24);
}

.progress-bar.fail {
    background: linear-gradient(90deg, #ef4444, #f87171);
}

/* 动画 */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.05); }
}

@keyframes slideIn {
    from { transform: translateX(-20px); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

.animate-fadeIn {
    animation: fadeIn 0.5s ease-out;
}

.animate-pulse {
    animation: pulse 2s infinite;
}

.animate-slideIn {
    animation: slideIn 0.4s ease-out;
}

/* 信息提示框 */
.info-box {
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%);
    border-left: 4px solid #3b82f6;
    border-radius: 12px;
    padding: 20px;
    margin: 15px 0;
}

.success-box {
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%);
    border-left: 4px solid #10b981;
    border-radius: 12px;
    padding: 20px;
    margin: 15px 0;
}

.warning-box {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(217, 119, 6, 0.1) 100%);
    border-left: 4px solid #f59e0b;
    border-radius: 12px;
    padding: 20px;
    margin: 15px 0;
}

/* 分隔线 */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
    margin: 30px 0;
}

/* 小标签 */
.small-note {
    font-size: 13px;
    color: #64748b;
    margin-top: 8px;
}

/* 头像 */
.avatar {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 24px;
    font-weight: 700;
    margin: 0 auto 20px;
}

/* 快速操作按钮组 */
.quick-actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin: 20px 0;
}

.quick-action-btn {
    padding: 10px 20px;
    border-radius: 10px;
    background: white;
    border: 2px solid #e2e8f0;
    cursor: pointer;
    transition: all 0.3s ease;
    font-weight: 500;
    display: flex;
    align-items: center;
    gap: 8px;
}

.quick-action-btn:hover {
    border-color: #667eea;
    color: #667eea;
    transform: translateY(-2px);
}

/* 图表容器 */
.chart-container {
    background: white;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.05);
    margin: 15px 0;
}

/* 时间线 */
.timeline {
    position: relative;
    padding-left: 30px;
}

.timeline::before {
    content: '';
    position: absolute;
    left: 8px;
    top: 0;
    bottom: 0;
    width: 2px;
    background: linear-gradient(180deg, #667eea, #764ba2);
}

.timeline-item {
    position: relative;
    padding: 15px 0;
}

.timeline-item::before {
    content: '';
    position: absolute;
    left: -26px;
    top: 20px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: white;
    border: 3px solid #667eea;
}

/* 评分星级 */
.star-rating {
    color: #fbbf24;
    font-size: 20px;
}

/* 响应式 */
@media (max-width: 768px) {
    .main-header {
        font-size: 28px;
    }
    .login-container {
        padding: 30px 20px;
        margin: 20px;
    }
}
</style>
""", unsafe_allow_html=True)

# -------------------------- 数据库初始化（自动建表）--------------------------
def init_db():
    conn = sqlite3.connect('performance_system.db')
    c = conn.cursor()
    
    # 用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  role TEXT NOT NULL,
                  email TEXT,
                  phone TEXT,
                  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  last_login TIMESTAMP)''')
    
    # 机构表
    c.execute('''CREATE TABLE IF NOT EXISTS institutions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  region TEXT,
                  contact TEXT,
                  phone TEXT,
                  email TEXT,
                  address TEXT,
                  status TEXT DEFAULT '正常',
                  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 绩效指标表
    c.execute('''CREATE TABLE IF NOT EXISTS indicators
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  full_score INTEGER NOT NULL,
                  category TEXT,
                  description TEXT,
                  sort INTEGER DEFAULT 0)''')
    
    # 绩效评分表
    c.execute('''CREATE TABLE IF NOT EXISTS scores
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  inst_id INTEGER NOT NULL,
                  year INTEGER NOT NULL,
                  indicator_id INTEGER NOT NULL,
                  score INTEGER NOT NULL,
                  evaluator TEXT NOT NULL,
                  evaluate_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  comment TEXT)''')
    
    # 提交材料审批表
    c.execute('''CREATE TABLE IF NOT EXISTS materials
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  inst_id INTEGER NOT NULL,
                  year INTEGER NOT NULL,
                  file_content BLOB,
                  file_name TEXT,
                  file_type TEXT,
                  status TEXT DEFAULT '待审核',
                  reviewer TEXT,
                  review_comment TEXT,
                  submit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  review_time TIMESTAMP)''')
    
    # 操作日志表
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  operation TEXT NOT NULL,
                  ip_address TEXT,
                  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 通知表
    c.execute('''CREATE TABLE IF NOT EXISTS notifications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  title TEXT NOT NULL,
                  content TEXT,
                  type TEXT DEFAULT 'info',
                  is_read INTEGER DEFAULT 0,
                  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 插入默认账号
    default_users = [
        ('admin', hashlib.md5('123456'.encode()).hexdigest(), '管理员', 'admin@example.com', '13800138000'),
        ('user', hashlib.md5('123456'.encode()).hexdigest(), '评估人员', 'user@example.com', '13800138001'),
        ('inst1', hashlib.md5('123456'.encode()).hexdigest(), '机构用户', 'inst1@example.com', '13800138002')
    ]
    for user in default_users:
        try:
            c.execute('''INSERT INTO users (username, password, role, email, phone) 
                        VALUES (?,?,?,?,?)''', user)
        except sqlite3.IntegrityError:
            pass
    
    # 插入默认指标
    default_indicators = [
        ('服务质量', 30, '服务', '评估服务质量和客户满意度'),
        ('工作效率', 25, '效率', '评估工作完成效率'),
        ('专业能力', 25, '能力', '评估专业技能水平'),
        ('团队协作', 20, '协作', '评估团队合作能力')
    ]
    for ind in default_indicators:
        try:
            c.execute('''INSERT INTO indicators (name, full_score, category, description, sort) 
                        VALUES (?,?,?,?,?)''', (*ind, default_indicators.index(ind)))
        except:
            pass
    
    conn.commit()
    conn.close()

# -------------------------- 通用工具函数 --------------------------
def md5_hash(text):
    return hashlib.md5(text.encode()).hexdigest()

def login_user(username, password):
    conn = sqlite3.connect('performance_system.db')
    c = conn.cursor()
    c.execute('''SELECT * FROM users WHERE username=? AND password=?''', 
              (username, md5_hash(password)))
    user = c.fetchone()
    if user:
        c.execute('UPDATE users SET last_login=? WHERE id=?', 
                  (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user[0]))
        conn.commit()
    conn.close()
    return user

def add_log(username, operation):
    """记录操作日志"""
    conn = sqlite3.connect('performance_system.db')
    c = conn.cursor()
    c.execute('''INSERT INTO logs (username, operation, ip_address) VALUES (?,?,?)''', 
              (username, operation, '127.0.0.1'))
    conn.commit()
    conn.close()

def add_notification(user_id, title, content, type='info'):
    """添加通知"""
    conn = sqlite3.connect('performance_system.db')
    c = conn.cursor()
    c.execute('''INSERT INTO notifications (user_id, title, content, type) VALUES (?,?,?,?)''',
              (user_id, title, content, type))
    conn.commit()
    conn.close()

def get_notifications(user_id):
    """获取用户通知"""
    conn = sqlite3.connect('performance_system.db')
    df = pd.read_sql('''SELECT * FROM notifications 
                        WHERE user_id=? OR user_id IS NULL
                        ORDER BY create_time DESC LIMIT 10''', conn, params=(user_id,))
    conn.close()
    return df

def check_approval_timeout():
    """检查审批超时（7天未审核）"""
    conn = sqlite3.connect('performance_system.db')
    c = conn.cursor()
    timeout_time = datetime.datetime.now() - timedelta(days=7)
    c.execute('''UPDATE materials 
                 SET status = '审批超时' 
                 WHERE status = '待审核' AND submit_time < ?''', 
              (timeout_time.strftime('%Y-%m-%d %H:%M:%S'),))
    conn.commit()
    conn.close()

def ai_evaluate_document(content, rule):
    """AI自动评估文档"""
    prompt = f"""
    文档内容：{content}
    评估规则：{rule}
    请返回严格的JSON格式：
    {{"score": 分数(0-100), "reason": "评估原因", "suggestions": ["建议1","建议2"]}}
    """
    
    mock_result = {
        "score": 85,
        "reason": "数据完整但缺少Q4季度对比数据",
        "suggestions": ["补充2025年Q4财务数据", "完善年度总结报告"]
    }
    return mock_result

def export_pdf(data, title):
    """导出PDF报表"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=16)
    pdf.cell(200, 10, txt=title, ln=True, align='C')
    pdf.set_font("Arial", size=12)
    
    for idx, row in data.iterrows():
        row_text = " | ".join([str(x) for x in row.values])
        pdf.cell(200, 10, txt=row_text, ln=True)
    
    pdf.output(f"{title}.pdf")
    return f"{title}.pdf"

def get_score_level(score):
    """获取评分等级"""
    if score >= 90:
        return "优秀", "badge-success", "progress-bar excellent"
    elif score >= 75:
        return "良好", "badge-warning", "progress-bar good"
    elif score >= 60:
        return "合格", "badge-info", "progress-bar pass"
    else:
        return "不合格", "badge-danger", "progress-bar fail"

def create_gauge_chart(value, title, max_val=100):
    """创建仪表盘图表"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 24}},
        gauge={
            'axis': {'range': [None, max_val], 'tickwidth': 1},
            'bar': {'color': "#667eea"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#ccc",
            'steps': [
                {'range': [0, 60], 'color': '#fee2e2'},
                {'range': [60, 75], 'color': '#fef3c7'},
                {'range': [75, 90], 'color': '#dbeafe'},
                {'range': [90, 100], 'color': '#d1fae5'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    fig.update_layout(height=300)
    return fig

# -------------------------- 页面组件 --------------------------
def render_login_page():
    """渲染登录页面"""
    st.markdown('<div class="animate-fadeIn">', unsafe_allow_html=True)
    
    # 顶部装饰
    st.markdown("""
        <div style="text-align: center; padding: 40px 0 20px;">
            <div style="font-size: 80px; margin-bottom: 10px;">📊</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<p class="main-header">第三方机构绩效评估系统</p>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; color: #64748b; margin-bottom: 30px;">Performance Evaluation System</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            
            # 头像
            st.markdown('<div class="avatar">👤</div>', unsafe_allow_html=True)
            
            with st.form(key='login_form'):
                username = st.text_input("👤 用户名", placeholder="请输入用户名")
                password = st.text_input("🔒 密码", type="password", placeholder="请输入密码")
                
                col_remember, col_forget = st.columns(2)
                with col_remember:
                    st.checkbox("记住我", value=True)
                with col_forget:
                    st.markdown('<p style="text-align: right; font-size: 13px;"><a href="#" style="color: #667eea;">忘记密码?</a></p>', unsafe_allow_html=True)
                
                submitted = st.form_submit_button("🚀 登录系统", use_container_width=True)
                
                if submitted:
                    with st.spinner("正在验证..."):
                        time.sleep(0.5)
                        user = login_user(username, password)
                        if user:
                            st.session_state.user = user
                            st.session_state.logged_in = True
                            add_log(username, "用户登录系统")
                            st.success("✅ 登录成功！正在跳转...")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ 用户名或密码错误，请重试。")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # 底部信息
            st.markdown("""
                <div style="text-align: center; margin-top: 30px; color: #94a3b8; font-size: 13px;">
                    <p>默认账号: admin / 123456 | user / 123456</p>
                    <p>© 2025 第三方机构绩效评估系统 v2.0</p>
                </div>
            """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        # 用户信息卡片
        st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        border-radius: 16px; padding: 20px; margin-bottom: 20px; color: white;">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <div style="width: 50px; height: 50px; border-radius: 50%; background: rgba(255,255,255,0.2); 
                                display: flex; align-items: center; justify-content: center; font-size: 24px;">
                        👤
                    </div>
                    <div>
                        <div style="font-weight: 700; font-size: 16px;">{st.session_state.user[1]}</div>
                        <div style="font-size: 13px; opacity: 0.8;">{st.session_state.user[3]}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # 快捷操作
        st.markdown('<p style="color: rgba(255,255,255,0.6); font-size: 12px; margin-bottom: 10px;">快捷操作</p>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 仪表盘", use_container_width=True):
                st.session_state.page = "dashboard"
                st.rerun()
        with col2:
            if st.button("🔔 通知", use_container_width=True):
                st.session_state.page = "notifications"
                st.rerun()
        
        st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)

def render_stat_cards():
    """渲染统计卡片"""
    conn = sqlite3.connect('performance_system.db')
    
    # 获取统计数据
    user_cnt = pd.read_sql('SELECT COUNT(*) as cnt FROM users', conn)['cnt'].iloc[0]
    inst_cnt = pd.read_sql('SELECT COUNT(*) as cnt FROM institutions', conn)['cnt'].iloc[0]
    score_cnt = pd.read_sql('SELECT COUNT(*) as cnt FROM scores', conn)['cnt'].iloc[0]
    pending_cnt = pd.read_sql("SELECT COUNT(*) as cnt FROM materials WHERE status='待审核'", conn)['cnt'].iloc[0]
    
    conn.close()
    
    st.markdown('<div class="animate-fadeIn">', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{int(user_cnt)}</div>
                <div class="stat-label">👥 系统用户</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="stat-card success">
                <div class="stat-number">{int(inst_cnt)}</div>
                <div class="stat-label">🏢 评估机构</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="stat-card info">
                <div class="stat-number">{int(score_cnt)}</div>
                <div class="stat-label">📝 评分记录</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="stat-card warning">
                <div class="stat-number">{int(pending_cnt)}</div>
                <div class="stat-label">⏳ 待审批</div>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_quick_actions():
    """渲染快速操作按钮"""
    st.markdown('<p class="sub-header">⚡ 快速操作</p>', unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("➕ 添加用户", use_container_width=True):
            st.session_state.show_add_user = True
    
    with col2:
        if st.button("🏢 添加机构", use_container_width=True):
            st.session_state.show_add_inst = True
    
    with col3:
        if st.button("📊 查看报表", use_container_width=True):
            st.session_state.page = "reports"
            st.rerun()
    
    with col4:
        if st.button("📥 导出数据", use_container_width=True):
            st.session_state.show_export = True
    
    with col5:
        if st.button("🤖 AI评估", use_container_width=True):
            st.session_state.page = "ai_eval"
            st.rerun()

def render_admin_dashboard():
    """渲染管理员控制台"""
    st.markdown('<p class="sub-header">🏠 管理员控制台</p>', unsafe_allow_html=True)
    
    # 统计卡片
    render_stat_cards()
    
    # 快速操作
    render_quick_actions()
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # 功能菜单
    menu = st.sidebar.selectbox(
        "📋 功能菜单",
        ["🏠 仪表盘", "👥 用户管理", "🏢 机构管理", "📊 指标管理", 
         "✅ 审批管理", "📈 统计分析", "📝 日志管理", "🤖 AI文档评估", "⚙️ 系统设置"]
    )
    
    if menu == "🏠 仪表盘":
        render_admin_home()
    elif menu == "👥 用户管理":
        render_user_management()
    elif menu == "🏢 机构管理":
        render_institution_management()
    elif menu == "📊 指标管理":
        render_indicator_management()
    elif menu == "✅ 审批管理":
        render_approval_management()
    elif menu == "📈 统计分析":
        render_statistics()
    elif menu == "📝 日志管理":
        render_logs()
    elif menu == "🤖 AI文档评估":
        render_ai_evaluation()
    elif menu == "⚙️ 系统设置":
        render_settings()

def render_admin_home():
    """渲染管理员首页仪表盘"""
    st.markdown('<div class="animate-fadeIn">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">📈 年度评分趋势</p>', unsafe_allow_html=True)
        
        conn = sqlite3.connect('performance_system.db')
        trend_df = pd.read_sql('''
            SELECT year, AVG(score) as avg_score, COUNT(*) as count
            FROM scores
            GROUP BY year
            ORDER BY year
        ''', conn)
        conn.close()
        
        if not trend_df.empty:
            fig = px.line(trend_df, x='year', y='avg_score', 
                         markers=True, 
                         labels={'year': '年份', 'avg_score': '平均分数'},
                         line_shape='spline')
            fig.update_traces(line_color='#667eea', line_width=3)
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无数据")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">📊 评分分布</p>', unsafe_allow_html=True)
        
        conn = sqlite3.connect('performance_system.db')
        dist_df = pd.read_sql('''
            SELECT 
                CASE 
                    WHEN score >= 90 THEN '优秀'
                    WHEN score >= 75 THEN '良好'
                    WHEN score >= 60 THEN '合格'
                    ELSE '不合格'
                END as level,
                COUNT(*) as count
            FROM scores
            GROUP BY level
        ''', conn)
        conn.close()
        
        if not dist_df.empty:
            fig = px.pie(dist_df, values='count', names='level',
                        color_discrete_sequence=['#10b981', '#3b82f6', '#f59e0b', '#ef4444'])
            fig.update_layout(height=300, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无数据")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # 最近活动
    st.markdown('<div class="card" style="margin-top: 20px;">', unsafe_allow_html=True)
    st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">🕐 最近活动</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('performance_system.db')
    logs_df = pd.read_sql('''
        SELECT username, operation, create_time 
        FROM logs 
        ORDER BY create_time DESC 
        LIMIT 10
    ''', conn)
    conn.close()
    
    if not logs_df.empty:
        st.dataframe(logs_df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无活动记录")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_user_management():
    """渲染用户管理"""
    st.markdown('<p class="sub-header">👥 用户管理</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('performance_system.db')
    
    # 用户列表
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    col_search, col_filter = st.columns([2, 1])
    with col_search:
        search = st.text_input("🔍 搜索用户", placeholder="输入用户名搜索")
    with col_filter:
        role_filter = st.selectbox("🎭 角色筛选", ["全部", "管理员", "评估人员", "机构用户"])
    
    query = 'SELECT id, username, role, email, phone, last_login FROM users WHERE 1=1'
    params = []
    if search:
        query += ' AND username LIKE ?'
        params.append(f'%{search}%')
    if role_filter != "全部":
        query += ' AND role = ?'
        params.append(role_filter)
    
    df = pd.read_sql(query, conn, params=params)
    
    # 添加操作列
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 添加用户
    st.markdown('<div class="card" style="margin-top: 20px;">', unsafe_allow_html=True)
    st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">➕ 添加新用户</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        new_user = st.text_input("用户名", key="new_username")
        new_email = st.text_input("邮箱", key="new_email")
    with col2:
        new_pwd = st.text_input("密码", type="password", key="new_password")
        new_phone = st.text_input("电话", key="new_phone")
    with col3:
        new_role = st.selectbox("角色", ["管理员", "评估人员", "机构用户"], key="new_role")
    
    col_btn1, col_btn2, _ = st.columns([1, 1, 3])
    with col_btn1:
        if st.button("✅ 确认添加", use_container_width=True):
            if new_user and new_pwd:
                try:
                    c = conn.cursor()
                    c.execute('''INSERT INTO users (username, password, role, email, phone) VALUES (?,?,?,?,?)''',
                              (new_user, md5_hash(new_pwd), new_role, new_email, new_phone))
                    conn.commit()
                    add_log(st.session_state.user[1], f"添加用户：{new_user}")
                    st.success("✅ 用户添加成功！")
                    time.sleep(0.5)
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("❌ 用户名已存在")
            else:
                st.warning("⚠️ 请填写完整信息")
    
    with col_btn2:
        if st.button("🔄 批量导入", use_container_width=True):
            st.info("📤 批量导入功能开发中...")
    
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def render_institution_management():
    """渲染机构管理"""
    st.markdown('<p class="sub-header">🏢 机构管理</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('performance_system.db')
    
    # 机构列表
    st.markdown('<div class="card">', unsafe_allow_html=True)
    df = pd.read_sql('SELECT * FROM institutions', conn)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 添加机构
    st.markdown('<div class="card" style="margin-top: 20px;">', unsafe_allow_html=True)
    st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">➕ 添加新机构</p>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("机构名称")
        region = st.text_input("所属地区")
        contact = st.text_input("联系人")
    with col2:
        phone = st.text_input("联系电话")
        email = st.text_input("邮箱")
        address = st.text_input("详细地址")
    
    col_btn1, col_btn2, _ = st.columns([1, 1, 3])
    with col_btn1:
        if st.button("✅ 添加机构", use_container_width=True):
            if name:
                c = conn.cursor()
                c.execute('''INSERT INTO institutions (name, region, contact, phone, email, address) 
                            VALUES (?,?,?,?,?,?)''',
                          (name, region, contact, phone, email, address))
                conn.commit()
                add_log(st.session_state.user[1], f"添加机构：{name}")
                st.success("✅ 机构添加成功！")
                st.rerun()
    
    with col_btn2:
        if st.button("📥 导入机构", use_container_width=True):
            st.info("📤 导入功能开发中...")
    
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def render_indicator_management():
    """渲染指标管理"""
    st.markdown('<p class="sub-header">📊 绩效指标管理</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('performance_system.db')
    
    # 指标列表
    st.markdown('<div class="card">', unsafe_allow_html=True)
    df = pd.read_sql('SELECT * FROM indicators ORDER BY sort', conn)
    
    # 显示进度条
    for idx, row in df.iterrows():
        col1, col2, col3 = st.columns([2, 1, 3])
        with col1:
            st.markdown(f"**{row['name']}**")
            st.markdown(f"<span class='small-note'>{row['description'] or '暂无描述'}</span>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<span class='badge badge-info'>满分: {row['full_score']}分</span>", unsafe_allow_html=True)
        with col3:
            st.progress(100, text=f"类别: {row['category'] or '未分类'}")
        st.markdown("---")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 添加指标
    st.markdown('<div class="card" style="margin-top: 20px;">', unsafe_allow_html=True)
    st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">➕ 添加新指标</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        ind_name = st.text_input("指标名称")
        category = st.text_input("所属类别")
    with col2:
        full_score = st.number_input("满分值", min_value=1, max_value=100, value=100)
        sort = st.number_input("排序号", min_value=0, value=0)
    with col3:
        description = st.text_area("指标说明", height=100)
    
    if st.button("✅ 添加指标", use_container_width=True):
        if ind_name:
            c = conn.cursor()
            c.execute('''INSERT INTO indicators (name, full_score, category, description, sort) VALUES (?,?,?,?,?)''',
                      (ind_name, full_score, category, description, sort))
            conn.commit()
            add_log(st.session_state.user[1], f"添加指标：{ind_name}")
            st.success("✅ 指标添加成功！")
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def render_approval_management():
    """渲染审批管理"""
    st.markdown('<p class="sub-header">✅ 材料审批管理</p>', unsafe_allow_html=True)
    
    check_approval_timeout()
    conn = sqlite3.connect('performance_system.db')
    
    # 统计
    col1, col2, col3, col4 = st.columns(4)
    pending = pd.read_sql("SELECT COUNT(*) as cnt FROM materials WHERE status='待审核'", conn)['cnt'].iloc[0]
    approved = pd.read_sql("SELECT COUNT(*) as cnt FROM materials WHERE status='通过'", conn)['cnt'].iloc[0]
    rejected = pd.read_sql("SELECT COUNT(*) as cnt FROM materials WHERE status='驳回'", conn)['cnt'].iloc[0]
    timeout = pd.read_sql("SELECT COUNT(*) as cnt FROM materials WHERE status='审批超时'", conn)['cnt'].iloc[0]
    
    with col1:
        st.metric("⏳ 待审核", int(pending))
    with col2:
        st.metric("✅ 已通过", int(approved))
    with col3:
        st.metric("❌ 已驳回", int(rejected))
    with col4:
        st.metric("⏰ 已超时", int(timeout))
    
    # 材料列表
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    status_filter = st.selectbox("状态筛选", ["全部", "待审核", "通过", "驳回", "审批超时"])
    
    query = '''SELECT m.*, i.name as inst_name 
               FROM materials m 
               JOIN institutions i ON m.inst_id=i.id'''
    if status_filter != "全部":
        query += f" WHERE m.status='{status_filter}'"
    query += " ORDER BY m.submit_time DESC"
    
    df = pd.read_sql(query, conn)
    
    if not df.empty:
        for idx, row in df.iterrows():
            with st.expander(f"📄 {row['inst_name']} - {row['file_name']} ({row['status']})"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**机构:** {row['inst_name']}")
                    st.markdown(f"**文件名:** {row['file_name']}")
                    st.markdown(f"**提交时间:** {row['submit_time']}")
                    st.markdown(f"**当前状态:** <span class='badge badge-{get_status_badge(row['status'])}'>{row['status']}</span>", unsafe_allow_html=True)
                with col2:
                    if row['status'] == '待审核':
                        status = st.selectbox("审批操作", ["通过", "驳回"], key=f"status_{row['id']}")
                        comment = st.text_area("审批意见", key=f"comment_{row['id']}")
                        if st.button("✅ 确认审批", key=f"btn_{row['id']}"):
                            c = conn.cursor()
                            c.execute('''UPDATE materials 
                                         SET status=?, reviewer=?, review_comment=?, review_time=?
                                         WHERE id=?''',
                                      (status, st.session_state.user[1], comment,
                                       datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                       row['id']))
                            conn.commit()
                            add_log(st.session_state.user[1], f"审批材料ID：{row['id']} - {status}")
                            st.success(f"✅ 审批完成：{status}")
                            st.rerun()
    else:
        st.info("暂无材料记录")
    
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def get_status_badge(status):
    """获取状态对应的badge样式"""
    mapping = {
        '通过': 'success',
        '驳回': 'danger',
        '待审核': 'warning',
        '审批超时': 'danger'
    }
    return mapping.get(status, 'info')

def render_statistics():
    """渲染统计分析"""
    st.markdown('<p class="sub-header">📈 统计分析</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('performance_system.db')
    
    # 年度选择
    years = pd.read_sql('SELECT DISTINCT year FROM scores ORDER BY year DESC', conn)['year'].tolist()
    if not years:
        st.info("暂无评分数据")
        conn.close()
        return
    
    select_year = st.selectbox("📅 选择年度", years)
    
    # 机构排名
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">🏆 机构绩效排名</p>', unsafe_allow_html=True)
    
    total_df = pd.read_sql('''
        SELECT i.name, i.region, SUM(s.score) as total_score,
               COUNT(s.id) as eval_count,
               AVG(s.score) as avg_score
        FROM scores s
        JOIN institutions i ON s.inst_id=i.id
        WHERE s.year=?
        GROUP BY i.id
        ORDER BY total_score DESC
    ''', conn, params=(select_year,))
    
    if not total_df.empty:
        # 添加等级
        total_df['等级'] = total_df['total_score'].apply(lambda x: get_score_level(x)[0])
        
        st.dataframe(total_df, use_container_width=True, hide_index=True)
        
        # 图表
        fig = px.bar(total_df.head(10), x='name', y='total_score',
                     color='total_score', color_continuous_scale='Viridis',
                     labels={'name': '机构名称', 'total_score': '总分数'})
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 地区分析
    st.markdown('<div class="card" style="margin-top: 20px;">', unsafe_allow_html=True)
    st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">🗺️ 地区绩效分析</p>', unsafe_allow_html=True)
    
    region_df = pd.read_sql('''
        SELECT i.region, 
               AVG(s.score) as avg_score,
               MAX(s.score) as max_score,
               MIN(s.score) as min_score,
               COUNT(DISTINCT i.id) as inst_count
        FROM scores s
        JOIN institutions i ON s.inst_id=i.id
        WHERE s.year=?
        GROUP BY i.region
    ''', conn, params=(select_year,))
    
    if not region_df.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(region_df, use_container_width=True, hide_index=True)
        with col2:
            fig = px.pie(region_df, values='inst_count', names='region',
                        title='机构地区分布')
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 指标分析
    st.markdown('<div class="card" style="margin-top: 20px;">', unsafe_allow_html=True)
    st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">📊 指标得分分析</p>', unsafe_allow_html=True)
    
    indicator_df = pd.read_sql('''
        SELECT ind.name, ind.full_score,
               AVG(s.score) as avg_score,
               MAX(s.score) as max_score,
               MIN(s.score) as min_score
        FROM scores s
        JOIN indicators ind ON s.indicator_id=ind.id
        WHERE s.year=?
        GROUP BY ind.id
    ''', conn, params=(select_year,))
    
    if not indicator_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name='平均分',
            x=indicator_df['name'],
            y=indicator_df['avg_score'],
            marker_color='#667eea'
        ))
        fig.add_trace(go.Scatter(
            name='满分',
            x=indicator_df['name'],
            y=indicator_df['full_score'],
            mode='lines+markers',
            line=dict(color='#ef4444', dash='dash')
        ))
        fig.update_layout(height=400, barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def render_logs():
    """渲染日志管理"""
    st.markdown('<p class="sub-header">📝 系统操作日志</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('performance_system.db')
    
    # 筛选
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("🔍 搜索操作", placeholder="输入关键词搜索")
    with col2:
        days = st.selectbox("⏰ 时间范围", ["全部", "最近7天", "最近30天", "最近90天"])
    
    query = 'SELECT * FROM logs WHERE 1=1'
    params = []
    
    if search:
        query += ' AND (username LIKE ? OR operation LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    
    if days != "全部":
        day_map = {"最近7天": 7, "最近30天": 30, "最近90天": 90}
        date_from = (datetime.datetime.now() - timedelta(days=day_map[days])).strftime('%Y-%m-%d')
        query += ' AND create_time >= ?'
        params.append(date_from)
    
    query += ' ORDER BY create_time DESC'
    
    df = pd.read_sql(query, conn, params=params)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    col_export, col_clear, _ = st.columns([1, 1, 3])
    with col_export:
        if st.button("📥 导出日志", use_container_width=True):
            st.info("📤 导出功能开发中...")
    with col_clear:
        if st.button("🗑️ 清空日志", use_container_width=True):
            st.warning("⚠️ 确认清空所有日志？")
    
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def render_ai_evaluation():
    """渲染AI文档评估"""
    st.markdown('<p class="sub-header">🤖 AI智能文档评估</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("📤 上传评估文档", type=['txt', 'docx', 'pdf'])
    
    col1, col2 = st.columns(2)
    with col1:
        rule = st.text_area("📋 评估规则", "检查是否包含年度财务数据、人员配置信息、项目完成情况")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**预设规则模板:**")
        templates = st.selectbox("选择模板", ["通用评估", "财务审计", "项目验收", "人员考核"])
    
    if uploaded_file and rule:
        content = uploaded_file.read()
        if st.button("🚀 开始AI评估", use_container_width=True):
            with st.spinner("🤖 AI正在分析文档..."):
                time.sleep(1.5)
                result = ai_evaluate_document(content.decode('utf-8', errors='ignore'), rule)
            
            # 显示结果
            st.markdown('<div class="success-box">', unsafe_allow_html=True)
            st.markdown('<p style="font-weight: 700; margin-bottom: 10px;">📊 评估结果</p>', unsafe_allow_html=True)
            
            col_score, col_reason = st.columns([1, 2])
            with col_score:
                fig = create_gauge_chart(result['score'], "综合评分")
                st.plotly_chart(fig, use_container_width=True)
            with col_reason:
                st.markdown(f"**评估结论:** {result['reason']}")
                st.markdown("**改进建议:**")
                for suggestion in result['suggestions']:
                    st.markdown(f"- {suggestion}")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            add_log(st.session_state.user[1], "使用AI文档评估功能")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_settings():
    """渲染系统设置"""
    st.markdown('<p class="sub-header">⚙️ 系统设置</p>', unsafe_allow_html=True)
    
    tabs = st.tabs(["🔔 通知设置", "🔐 安全设置", "💾 数据备份", "📊 系统信息"])
    
    with tabs[0]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.checkbox("启用邮件通知", value=True)
        st.checkbox("启用短信通知", value=False)
        st.checkbox("审批超时提醒", value=True)
        st.checkbox("评分完成通知", value=True)
        if st.button("💾 保存设置", use_container_width=True):
            st.success("✅ 设置已保存")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tabs[1]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.number_input("登录失败锁定次数", min_value=3, max_value=10, value=5)
        st.number_input("会话超时时间(分钟)", min_value=10, max_value=120, value=30)
        st.checkbox("启用双因素认证", value=False)
        if st.button("💾 保存安全设置", use_container_width=True):
            st.success("✅ 安全设置已保存")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tabs[2]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**数据备份管理**")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 立即备份", use_container_width=True):
                st.success("✅ 备份完成")
        with col2:
            if st.button("📤 恢复数据", use_container_width=True):
                st.info("请选择备份文件")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tabs[3]:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("**系统信息**")
        st.markdown("- **版本:** v2.0.0")
        st.markdown("- **数据库:** SQLite 3")
        st.markdown("- **Python:** 3.9+")
        st.markdown("- **Streamlit:** 1.28+")
        st.markdown("- **最后更新:** 2025-01-15")
        st.markdown('</div>', unsafe_allow_html=True)

def render_evaluator_dashboard():
    """渲染评估人员控制台"""
    st.markdown('<p class="sub-header">📝 评估人员控制台</p>', unsafe_allow_html=True)
    
    menu = st.sidebar.selectbox(
        "📋 功能菜单",
        ["🏠 仪表盘", "⭐ 机构评分", "📊 查看报表", "📤 材料提交", "📥 导出PDF"]
    )
    
    if menu == "🏠 仪表盘":
        render_evaluator_home()
    elif menu == "⭐ 机构评分":
        render_scoring()
    elif menu == "📊 查看报表":
        render_evaluator_reports()
    elif menu == "📤 材料提交":
        render_material_submit()
    elif menu == "📥 导出PDF":
        render_export_pdf()

def render_evaluator_home():
    """渲染评估人员首页"""
    st.markdown('<div class="animate-fadeIn">', unsafe_allow_html=True)
    
    # 待办任务
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">📋 待办任务</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('performance_system.db')
    pending_inst = pd.read_sql('SELECT COUNT(*) as cnt FROM institutions', conn)['cnt'].iloc[0]
    my_scores = pd.read_sql(f"SELECT COUNT(*) as cnt FROM scores WHERE evaluator='{st.session_state.user[1]}'", conn)['cnt'].iloc[0]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🏢 待评估机构", int(pending_inst))
    with col2:
        st.metric("✅ 已完成评分", int(my_scores))
    with col3:
        st.metric("⏰ 本周任务", 5)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 快速评分入口
    st.markdown('<div class="card" style="margin-top: 20px;">', unsafe_allow_html=True)
    st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">⚡ 快速评分</p>', unsafe_allow_html=True)
    
    insts = pd.read_sql('SELECT id, name FROM institutions', conn)
    if not insts.empty:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            quick_inst = st.selectbox("选择机构", insts['id'].tolist(),
                                      format_func=lambda x: insts[insts['id']==x]['name'].iloc[0])
        with col2:
            quick_year = st.number_input("年度", min_value=2020, max_value=2030, value=2025)
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 开始评分", use_container_width=True):
                st.session_state.scoring_inst = quick_inst
                st.session_state.scoring_year = quick_year
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_scoring():
    """渲染评分页面"""
    st.markdown('<p class="sub-header">⭐ 绩效评分</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('performance_system.db')
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    # 选择机构和年度
    col1, col2 = st.columns(2)
    with col1:
        insts = pd.read_sql('SELECT id, name FROM institutions', conn)
        if not insts.empty:
            inst_id = st.selectbox("🏢 选择机构", insts['id'].tolist(),
                                  format_func=lambda x: insts[insts['id']==x]['name'].iloc[0])
    with col2:
        year = st.number_input("📅 评估年度", min_value=2020, max_value=2030, value=2025)
    
    st.markdown("---")
    
    # 加载指标并评分
    indicators = pd.read_sql('SELECT * FROM indicators ORDER BY sort', conn)
    total_score = 0
    scores_map = {}
    comments = {}
    
    st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">📊 指标评分</p>', unsafe_allow_html=True)
    
    for idx, ind in indicators.iterrows():
        with st.expander(f"📌 {ind['name']} (满分{ind['full_score']}分)"):
            col_score, col_comment = st.columns([1, 2])
            with col_score:
                s = st.slider(f"评分", 0, int(ind['full_score']), 
                             int(ind['full_score'] * 0.8),
                             help=ind['description'] or '')
                scores_map[int(ind['id'])] = int(s)
                total_score += int(s)
                
                # 显示进度
                progress = s / ind['full_score']
                st.progress(progress, text=f"{s}/{ind['full_score']}")
            with col_comment:
                comments[int(ind['id'])] = st.text_area("评语", 
                    placeholder=f"请输入{ind['name']}的评语...",
                    key=f"comment_{ind['id']}")
    
    # 总分显示
    st.markdown("---")
    col_total, col_level = st.columns([2, 1])
    with col_total:
        st.markdown(f"<h2 style='color: #667eea;'>总分: {total_score}分</h2>", unsafe_allow_html=True)
    with col_level:
        level, badge_class, _ = get_score_level(total_score)
        st.markdown(f"<span class='badge {badge_class}' style='font-size: 16px;'>{level}</span>", unsafe_allow_html=True)
    
    # 提交按钮
    col_submit, col_draft, _ = st.columns([1, 1, 2])
    with col_submit:
        if st.button("✅ 提交评分", use_container_width=True):
            c = conn.cursor()
            for ind_id, s in scores_map.items():
                c.execute('''INSERT INTO scores (inst_id, year, indicator_id, score, evaluator, comment) 
                            VALUES (?,?,?,?,?,?)''',
                          (inst_id, year, ind_id, s, st.session_state.user[1], comments.get(ind_id, '')))
            conn.commit()
            add_log(st.session_state.user[1], f"为机构{inst_id}提交评分")
            st.success(f"✅ 评分提交成功！总分：{total_score}分")
            st.balloons()
    
    with col_draft:
        if st.button("💾 保存草稿", use_container_width=True):
            st.info("📤 草稿已保存")
    
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def render_evaluator_reports():
    """渲染评估人员报表"""
    st.markdown('<p class="sub-header">📊 绩效报表</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('performance_system.db')
    
    years = pd.read_sql('SELECT DISTINCT year FROM scores ORDER BY year DESC', conn)['year'].tolist()
    if not years:
        st.info("暂无评分数据")
        conn.close()
        return
    
    select_year = st.selectbox("📅 选择年度", years)
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    df = pd.read_sql('''
        SELECT i.name, i.region, SUM(s.score) as total_score,
               CASE WHEN SUM(s.score)>=90 THEN "优秀"
                    WHEN SUM(s.score)>=75 THEN "良好"
                    WHEN SUM(s.score)>=60 THEN "合格"
                    ELSE "不合格" END as level,
               s.evaluator
        FROM scores s
        JOIN institutions i ON s.inst_id=i.id
        WHERE s.year=?
        GROUP BY i.id
        ORDER BY total_score DESC
    ''', conn, params=(select_year,))
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 图表
        fig = px.bar(df, x='name', y='total_score', color='level',
                     color_discrete_map={'优秀': '#10b981', '良好': '#3b82f6', 
                                        '合格': '#f59e0b', '不合格': '#ef4444'},
                     labels={'name': '机构名称', 'total_score': '总分数'})
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无数据")
    
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def render_material_submit():
    """渲染材料提交"""
    st.markdown('<p class="sub-header">📤 评估材料提交</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('performance_system.db')
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    insts = pd.read_sql('SELECT id, name FROM institutions', conn)
    
    col1, col2 = st.columns(2)
    with col1:
        inst_id = st.selectbox("🏢 选择机构", insts['id'].tolist(),
                              format_func=lambda x: insts[insts['id']==x]['name'].iloc[0])
    with col2:
        year = st.number_input("📅 年度", 2020, 2030, 2025)
    
    uploaded_file = st.file_uploader("📎 上传材料", type=['xlsx', 'pdf', 'docx', 'zip'])
    
    if uploaded_file:
        st.markdown(f"**文件名:** {uploaded_file.name}")
        st.markdown(f"**文件大小:** {len(uploaded_file.getvalue()) / 1024:.2f} KB")
    
    col_submit, col_cancel, _ = st.columns([1, 1, 2])
    with col_submit:
        if st.button("✅ 提交材料", use_container_width=True):
            if uploaded_file:
                c = conn.cursor()
                c.execute('''INSERT INTO materials (inst_id, year, file_content, file_name, file_type) 
                            VALUES (?,?,?,?,?)''',
                          (inst_id, year, uploaded_file.read(), uploaded_file.name, uploaded_file.type))
                conn.commit()
                add_log(st.session_state.user[1], f"提交机构{inst_id}材料")
                st.success("✅ 材料提交成功，等待审核")
            else:
                st.warning("⚠️ 请先上传文件")
    
    with col_cancel:
        if st.button("❌ 取消", use_container_width=True):
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 已提交材料列表
    st.markdown('<div class="card" style="margin-top: 20px;">', unsafe_allow_html=True)
    st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">📋 已提交材料</p>', unsafe_allow_html=True)
    
    materials = pd.read_sql('''
        SELECT m.*, i.name as inst_name 
        FROM materials m 
        JOIN institutions i ON m.inst_id=i.id
        WHERE m.inst_id=?
        ORDER BY m.submit_time DESC
    ''', conn, params=(inst_id,))
    
    if not materials.empty:
        st.dataframe(materials[['inst_name', 'file_name', 'status', 'submit_time']], 
                    use_container_width=True, hide_index=True)
    else:
        st.info("暂无提交记录")
    
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def render_export_pdf():
    """渲染PDF导出"""
    st.markdown('<p class="sub-header">📥 PDF报表导出</p>', unsafe_allow_html=True)
    
    conn = sqlite3.connect('performance_system.db')
    
    years = pd.read_sql('SELECT DISTINCT year FROM scores ORDER BY year DESC', conn)['year'].tolist()
    if not years:
        st.info("暂无评分数据")
        conn.close()
        return
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        select_year = st.selectbox("📅 选择导出年度", years)
    with col2:
        export_type = st.selectbox("📄 导出类型", ["完整报表", "机构排名", "指标分析"])
    
    df = pd.read_sql('''
        SELECT i.name, i.region, SUM(s.score) as total_score,
               CASE WHEN SUM(s.score)>=90 THEN "优秀"
                    WHEN SUM(s.score)>=75 THEN "良好"
                    WHEN SUM(s.score)>=60 THEN "合格"
                    ELSE "不合格" END as level
        FROM scores s
        JOIN institutions i ON s.inst_id=i.id
        WHERE s.year=?
        GROUP BY i.id
    ''', conn, params=(select_year,))
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        col_export, col_preview, _ = st.columns([1, 1, 2])
        with col_export:
            if st.button("📥 导出PDF", use_container_width=True):
                with st.spinner("正在生成PDF..."):
                    time.sleep(1)
                    pdf_path = export_pdf(df, f"{select_year}年度绩效报表")
                with open(pdf_path, "rb") as f:
                    st.download_button("⬇️ 下载PDF", f, file_name=pdf_path)
        
        with col_preview:
            if st.button("👁️ 预览报表", use_container_width=True):
                st.info("📄 报表预览功能开发中...")
    
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

def render_institution_dashboard():
    """渲染机构用户控制台"""
    st.markdown('<p class="sub-header">🏢 机构用户控制台</p>', unsafe_allow_html=True)
    
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.markdown("💡 您可以查看本机构的绩效评估结果和审批状态")
    st.markdown('</div>', unsafe_allow_html=True)
    
    check_approval_timeout()
    conn = sqlite3.connect('performance_system.db')
    username = st.session_state.user[1]
    
    # 查找机构
    inst = pd.read_sql('SELECT * FROM institutions WHERE name=?', conn, params=(username,))
    
    if inst.empty:
        st.warning("⚠️ 未找到关联的机构信息")
        conn.close()
        return
    
    inst_id = inst.iloc[0]['id']
    
    # 统计卡片
    col1, col2, col3 = st.columns(3)
    
    with col1:
        avg_score = pd.read_sql(f'''
            SELECT AVG(score) as avg FROM scores WHERE inst_id={inst_id}
        ''', conn)['avg'].iloc[0] or 0
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-number">{avg_score:.1f}</div>
                <div class="stat-label">平均分</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        eval_count = pd.read_sql(f'''
            SELECT COUNT(DISTINCT year) as cnt FROM scores WHERE inst_id={inst_id}
        ''', conn)['cnt'].iloc[0]
        st.markdown(f"""
            <div class="stat-card success">
                <div class="stat-number">{int(eval_count)}</div>
                <div class="stat-label">评估年度</div>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        pending = pd.read_sql(f'''
            SELECT COUNT(*) as cnt FROM materials 
            WHERE inst_id={inst_id} AND status='待审核'
        ''', conn)['cnt'].iloc[0]
        st.markdown(f"""
            <div class="stat-card warning">
                <div class="stat-number">{int(pending)}</div>
                <div class="stat-label">待审批</div>
            </div>
        """, unsafe_allow_html=True)
    
    # 历年成绩
    st.markdown('<div class="card" style="margin-top: 20px;">', unsafe_allow_html=True)
    st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">📊 历年绩效成绩</p>', unsafe_allow_html=True)
    
    df = pd.read_sql('''
        SELECT s.year, 
               SUM(s.score) as total_score,
               AVG(s.score) as avg_score,
               COUNT(s.id) as eval_count
        FROM scores s
        WHERE s.inst_id=?
        GROUP BY s.year
        ORDER BY s.year DESC
    ''', conn, params=(inst_id,))
    
    if not df.empty:
        df['等级'] = df['total_score'].apply(lambda x: get_score_level(x)[0])
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # 趋势图
        fig = px.line(df, x='year', y='total_score', markers=True,
                     labels={'year': '年份', 'total_score': '总分数'})
        fig.update_traces(line_color='#667eea', line_width=3)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("暂无评分数据")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 材料审批状态
    st.markdown('<div class="card" style="margin-top: 20px;">', unsafe_allow_html=True)
    st.markdown('<p style="font-weight: 600; margin-bottom: 15px;">📋 材料审批状态</p>', unsafe_allow_html=True)
    
    materials = pd.read_sql('''
        SELECT file_name, status, submit_time, review_time, review_comment
        FROM materials
        WHERE inst_id=?
        ORDER BY submit_time DESC
    ''', conn, params=(inst_id,))
    
    if not materials.empty:
        st.dataframe(materials, use_container_width=True, hide_index=True)
    else:
        st.info("暂无材料记录")
    
    st.markdown('</div>', unsafe_allow_html=True)
    conn.close()

# -------------------------- 主程序 --------------------------
def main():
    init_db()
    check_approval_timeout()
    
    # 会话状态初始化
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.page = "dashboard"
    
    if not st.session_state.logged_in:
        render_login_page()
    else:
        render_sidebar()
        
        role = st.session_state.user[3]
        
        # 退出登录按钮
        if st.sidebar.button("🚪 退出登录", use_container_width=True):
            add_log(st.session_state.user[1], "用户退出登录")
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
        
        # 角色权限控制
        if role == "管理员":
            render_admin_dashboard()
        elif role == "评估人员":
            render_evaluator_dashboard()
        elif role == "机构用户":
            render_institution_dashboard()

if __name__ == '__main__':
    main()
