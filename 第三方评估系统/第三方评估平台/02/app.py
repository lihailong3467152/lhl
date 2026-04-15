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

# -------------------------- 页面配置（美化）--------------------------
st.set_page_config(
    page_title="第三方机构绩效评估系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
html, body, [class*="css"]  {
    font-family: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
}
.main-header {
    font-size: 34px;
    color: #0b3559;
    text-align: center;
    font-weight: 700;
    margin-bottom: 18px;
}
.sub-header {
    font-size: 20px;
    color: #1464a6;
    margin: 12px 0 8px 0;
    font-weight: 600;
}
.card {
    background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
    border: 1px solid #e6eef8;
    border-radius: 10px;
    padding: 16px;
    box-shadow: 0 2px 6px rgba(14,30,37,0.06);
}
.muted {
    color: #6b7280;
}
.btn-primary {
    background-color: #0b66b2 !important;
    color: white !important;
    border-radius: 6px !important;
}
.sidebar .sidebar-content {
    background-color: #f6f9fc;
    padding: 12px;
}
.logo {
    display:block; margin:auto; width:72px; height:72px; border-radius:12px;
}
.small-note {font-size:12px;color:#64748b}
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
                  role TEXT NOT NULL)''')
    
    # 机构表
    c.execute('''CREATE TABLE IF NOT EXISTS institutions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  region TEXT,
                  contact TEXT,
                  phone TEXT,
                  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 绩效指标表
    c.execute('''CREATE TABLE IF NOT EXISTS indicators
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  full_score INTEGER NOT NULL,
                  sort INTEGER DEFAULT 0)''')
    
    # 绩效评分表
    c.execute('''CREATE TABLE IF NOT EXISTS scores
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  inst_id INTEGER NOT NULL,
                  year INTEGER NOT NULL,
                  indicator_id INTEGER NOT NULL,
                  score INTEGER NOT NULL,
                  evaluator TEXT NOT NULL,
                  evaluate_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 提交材料审批表
    c.execute('''CREATE TABLE IF NOT EXISTS materials
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  inst_id INTEGER NOT NULL,
                  year INTEGER NOT NULL,
                  file_content BLOB,
                  file_name TEXT,
                  status TEXT DEFAULT '待审核',
                  reviewer TEXT,
                  submit_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  review_time TIMESTAMP)''')
    
    # 操作日志表
    c.execute('''CREATE TABLE IF NOT EXISTS logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT NOT NULL,
                  operation TEXT NOT NULL,
                  create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # 插入默认账号
    default_users = [
        ('admin', hashlib.md5('123456'.encode()).hexdigest(), '管理员'),
        ('user', hashlib.md5('123456'.encode()).hexdigest(), '评估人员')
    ]
    for user in default_users:
        try:
            c.execute('INSERT INTO users (username, password, role) VALUES (?,?,?)', user)
        except sqlite3.IntegrityError:
            pass
    
    conn.commit()
    conn.close()

# -------------------------- 通用工具函数 --------------------------
def md5_hash(text):
    return hashlib.md5(text.encode()).hexdigest()

def login_user(username, password):
    conn = sqlite3.connect('performance_system.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username=? AND password=?', 
              (username, md5_hash(password)))
    user = c.fetchone()
    conn.close()
    return user

def add_log(username, operation):
    """记录操作日志"""
    conn = sqlite3.connect('performance_system.db')
    c = conn.cursor()
    c.execute('INSERT INTO logs (username, operation) VALUES (?,?)', 
              (username, operation))
    conn.commit()
    conn.close()

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
    """提示词工程管道：AI自动评估文档"""
    # 模拟AI接口（真实使用时替换为OpenAI/通义千问等API）
    prompt = f"""
    文档内容：{content}
    评估规则：{rule}
    请返回严格的JSON格式：
    {{"score": 分数(0-100), "reason": "评估原因", "suggestions": ["建议1","建议2"]}}
    """
    
    # 模拟AI返回结果
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

# -------------------------- 功能模块 --------------------------
def login_page():
    st.markdown('<p class="main-header">📊 第三方机构绩效评估系统</p>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form(key='login_form'):
            st.image('https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/FluentIcons_72.png', width=72)
            username = st.text_input("用户名", placeholder="请输入用户名")
            password = st.text_input("密码", type="password", placeholder="请输入密码")
            submitted = st.form_submit_button("登录")
            if submitted:
                user = login_user(username, password)
                if user:
                    st.session_state.user = user
                    st.session_state.logged_in = True
                    add_log(username, "用户登录系统")
                    st.success("登录成功！")
                    st.experimental_rerun()
                else:
                    st.error("用户名或密码错误，请重试。")

def admin_dashboard():
    st.markdown('<p class="sub-header">管理员控制台</p>', unsafe_allow_html=True)
    # 简要统计卡片
    conn = sqlite3.connect('performance_system.db')
    user_cnt = pd.read_sql('SELECT COUNT(*) as cnt FROM users', conn)['cnt'].iloc[0]
    inst_cnt = pd.read_sql('SELECT COUNT(*) as cnt FROM institutions', conn)['cnt'].iloc[0]
    score_cnt = pd.read_sql('SELECT COUNT(*) as cnt FROM scores', conn)['cnt'].iloc[0]
    conn.close()
    c1, c2, c3 = st.columns(3)
    c1.metric("用户数", int(user_cnt))
    c2.metric("机构数", int(inst_cnt))
    c3.metric("评分记录", int(score_cnt))
    menu = ["用户管理", "机构管理", "指标管理", "审批管理", "统计分析", "日志管理", "AI文档评估"]
    choice = st.sidebar.selectbox("功能菜单", menu)
    
    if choice == "用户管理":
        st.subheader("用户管理")
        conn = sqlite3.connect('performance_system.db')
        df = pd.read_sql('SELECT id,username,role FROM users', conn)
        conn.close()
        st.dataframe(df)
        
        new_user = st.text_input("新用户名")
        new_pwd = st.text_input("密码", type="password")
        new_role = st.selectbox("角色", ["管理员", "评估人员", "机构用户"])
        if st.button("添加用户"):
            try:
                conn = sqlite3.connect('performance_system.db')
                c = conn.cursor()
                c.execute('INSERT INTO users (username,password,role) VALUES (?,?,?)',
                          (new_user, md5_hash(new_pwd), new_role))
                conn.commit()
                conn.close()
                add_log(st.session_state.user[1], f"添加用户：{new_user}")
                st.success("添加成功")
                st.rerun()
            except:
                st.error("用户名已存在")
    
    elif choice == "机构管理":
        st.subheader("机构信息管理")
        conn = sqlite3.connect('performance_system.db')
        df = pd.read_sql('SELECT * FROM institutions', conn)
        st.dataframe(df)
        
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("机构名称")
            region = st.text_input("地区")
        with col2:
            contact = st.text_input("联系人")
            phone = st.text_input("联系电话")
        
        if st.button("添加机构"):
            c = conn.cursor()
            c.execute('INSERT INTO institutions (name,region,contact,phone) VALUES (?,?,?,?)',
                      (name, region, contact, phone))
            conn.commit()
            add_log(st.session_state.user[1], f"添加机构：{name}")
            st.success("添加成功")
            st.rerun()
        conn.close()
    
    elif choice == "指标管理":
        st.subheader("绩效指标管理")
        conn = sqlite3.connect('performance_system.db')
        df = pd.read_sql('SELECT * FROM indicators ORDER BY sort', conn)
        st.dataframe(df)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            ind_name = st.text_input("指标名称")
        with col2:
            full_score = st.number_input("满分值", min_value=1, max_value=100)
        with col3:
            sort = st.number_input("排序号", min_value=0)
        
        if st.button("添加指标"):
            c = conn.cursor()
            c.execute('INSERT INTO indicators (name,full_score,sort) VALUES (?,?,?)',
                      (ind_name, full_score, sort))
            conn.commit()
            add_log(st.session_state.user[1], f"添加指标：{ind_name}")
            st.success("添加成功")
            st.rerun()
        conn.close()
    
    elif choice == "审批管理":
        st.subheader("材料审批管理")
        check_approval_timeout()
        conn = sqlite3.connect('performance_system.db')
        df = pd.read_sql('''SELECT m.*,i.name as inst_name 
                            FROM materials m 
                            JOIN institutions i ON m.inst_id=i.id''', conn)
        st.dataframe(df)
        
        if not df.empty:
            material_id = st.selectbox("选择审批材料", df['id'].tolist())
            status = st.selectbox("审批状态", ["通过", "驳回"])
            if st.button("确认审批"):
                c = conn.cursor()
                c.execute('''UPDATE materials 
                             SET status=?, reviewer=?, review_time=?
                             WHERE id=?''',
                          (status, st.session_state.user[1], 
                           datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                           material_id))
                conn.commit()
                add_log(st.session_state.user[1], f"审批材料ID：{material_id}")
                st.success("审批完成")
                st.rerun()
        conn.close()
    
    elif choice == "统计分析":
        st.subheader("数据统计分析")
        conn = sqlite3.connect('performance_system.db')
        
        # 年度统计
        years = pd.read_sql('SELECT DISTINCT year FROM scores', conn)['year'].tolist()
        if years:
            select_year = st.selectbox("选择年度", years)
            # 总分统计
            total_df = pd.read_sql('''
                SELECT i.name, SUM(s.score) as total_score
                FROM scores s
                JOIN institutions i ON s.inst_id=i.id
                WHERE s.year=?
                GROUP BY i.name
                ORDER BY total_score DESC
            ''', conn, params=(select_year,))
            st.dataframe(total_df)
            
            # 图表展示
            st.bar_chart(total_df, x='name', y='total_score')
            
            # 地区统计
            region_df = pd.read_sql('''
                SELECT i.region, AVG(s.score) as avg_score
                FROM scores s
                JOIN institutions i ON s.inst_id=i.id
                WHERE s.year=?
                GROUP BY i.region
            ''', conn, params=(select_year,))
            st.subheader("地区平均分")
            st.dataframe(region_df)
    
    elif choice == "日志管理":
        st.subheader("系统操作日志")
        conn = sqlite3.connect('performance_system.db')
        df = pd.read_sql('SELECT * FROM logs ORDER BY create_time DESC', conn)
        conn.close()
        st.dataframe(df, use_container_width=True)
    
    elif choice == "AI文档评估":
        st.subheader("AI智能文档评估")
        uploaded_file = st.file_uploader("上传评估文档", type=['txt', 'docx'])
        rule = st.text_area("评估规则", "检查是否包含年度财务数据、人员配置信息")
        
        if uploaded_file and rule:
            content = uploaded_file.read().decode('utf-8', errors='ignore')
            if st.button("开始AI评估"):
                result = ai_evaluate_document(content, rule)
                st.json(result)
                add_log(st.session_state.user[1], "使用AI文档评估功能")

def user_dashboard():
    st.markdown('<p class="sub-header">评估人员控制台</p>', unsafe_allow_html=True)
    menu = ["机构评分", "查看报表", "材料提交", "导出PDF"]
    choice = st.sidebar.selectbox("功能菜单", menu)
    
    if choice == "机构评分":
        st.subheader("绩效评分")
        conn = sqlite3.connect('performance_system.db')
        # 选择机构
        insts = pd.read_sql('SELECT id,name FROM institutions', conn)
        inst_id = st.selectbox("选择机构", insts['id'].tolist(), 
                              format_func=lambda x: insts[insts['id']==x]['name'].iloc[0])
        year = st.number_input("评估年度", min_value=2020, max_value=2030)
        
        # 加载指标
        indicators = pd.read_sql('SELECT * FROM indicators ORDER BY sort', conn)
        total_score = 0
        scores_map = {}

        for _, ind in indicators.iterrows():
            s = st.slider(f"{ind['name']} (满分{ind['full_score']})", 
                         0, int(ind['full_score']), 0)
            scores_map[int(ind['id'])] = int(s)
            total_score += int(s)

        if st.button("提交评分"):
            c = conn.cursor()
            for ind_id, s in scores_map.items():
                c.execute('INSERT INTO scores (inst_id,year,indicator_id,score,evaluator) VALUES (?,?,?,?,?)',
                          (inst_id, year, ind_id, s, st.session_state.user[1]))
            conn.commit()
            add_log(st.session_state.user[1], f"为机构{inst_id}提交评分")
            st.success(f"评分提交成功！总分：{total_score}")
        conn.close()
    
    elif choice == "查看报表":
        st.subheader("绩效报表")
        conn = sqlite3.connect('performance_system.db')
        years = pd.read_sql('SELECT DISTINCT year FROM scores', conn)['year'].tolist()
        if years:
            select_year = st.selectbox("选择年度", years)
            df = pd.read_sql('''
                SELECT i.name, SUM(s.score) as total_score,
                CASE WHEN SUM(s.score)>=90 THEN "优秀"
                     WHEN SUM(s.score)>=75 THEN "良好"
                     WHEN SUM(s.score)>=60 THEN "合格"
                     ELSE "不合格" END as level
                FROM scores s
                JOIN institutions i ON s.inst_id=i.id
                WHERE s.year=?
                GROUP BY i.name
                ORDER BY total_score DESC
            ''', conn, params=(select_year,))
            st.dataframe(df)
            st.bar_chart(df, x='name', y='total_score')
        conn.close()
    
    elif choice == "材料提交":
        st.subheader("评估材料提交")
        conn = sqlite3.connect('performance_system.db')
        insts = pd.read_sql('SELECT id,name FROM institutions', conn)
        inst_id = st.selectbox("选择机构", insts['id'].tolist(),
                              format_func=lambda x: insts[insts['id']==x]['name'].iloc[0])
        year = st.number_input("年度", 2020, 2030)
        uploaded_file = st.file_uploader("上传材料", type=['xlsx', 'pdf', 'docx'])
        
        if uploaded_file and st.button("提交材料"):
            c = conn.cursor()
            c.execute('INSERT INTO materials (inst_id,year,file_content,file_name) VALUES (?,?,?,?)',
                      (inst_id, year, uploaded_file.read(), uploaded_file.name))
            conn.commit()
            add_log(st.session_state.user[1], f"提交机构{inst_id}材料")
            st.success("材料提交成功，等待审核")
        conn.close()
    
    elif choice == "导出PDF":
        st.subheader("PDF报表导出")
        conn = sqlite3.connect('performance_system.db')
        years = pd.read_sql('SELECT DISTINCT year FROM scores', conn)['year'].tolist()
        if years:
            select_year = st.selectbox("选择导出年度", years)
            df = pd.read_sql('''
                SELECT i.name, SUM(s.score) as total_score,
                CASE WHEN SUM(s.score)>=90 THEN "优秀"
                     WHEN SUM(s.score)>=75 THEN "良好"
                     WHEN SUM(s.score)>=60 THEN "合格"
                     ELSE "不合格" END as level
                FROM scores s
                JOIN institutions i ON s.inst_id=i.id
                WHERE s.year=?
                GROUP BY i.name
            ''', conn, params=(select_year,))
            st.dataframe(df)
            if st.button("导出PDF"):
                pdf_path = export_pdf(df, f"{select_year}年度绩效报表")
                with open(pdf_path, "rb") as f:
                    st.download_button("下载PDF", f, file_name=pdf_path)
        conn.close()

def inst_dashboard():
    st.markdown('<p class="sub-header">机构用户控制台</p>', unsafe_allow_html=True)
    st.info("您可以查看本机构的绩效评估结果和审批状态")
    check_approval_timeout()
    conn = sqlite3.connect('performance_system.db')
    username = st.session_state.user[1]
    
    # 简单关联：机构用户名=机构名
    df = pd.read_sql('''
        SELECT i.name, SUM(s.score) as total_score, s.year,
        CASE WHEN SUM(s.score)>=90 THEN "优秀"
             WHEN SUM(s.score)>=75 THEN "良好"
             WHEN SUM(s.score)>=60 THEN "合格"
             ELSE "不合格" END as level
        FROM scores s
        JOIN institutions i ON s.inst_id=i.id
        WHERE i.name=?
        GROUP BY i.name, s.year
    ''', conn, params=(username,))
    st.dataframe(df)
    conn.close()

# -------------------------- 主程序 --------------------------
def main():
    init_db()
    check_approval_timeout()
    
    # 会话状态初始化
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user = None
    
    if not st.session_state.logged_in:
        login_page()
    else:
        role = st.session_state.user[3]
        st.sidebar.markdown(f"**当前用户：{st.session_state.user[1]}**")
        st.sidebar.markdown(f"**角色：{role}**")
        if st.sidebar.button("退出登录"):
            add_log(st.session_state.user[1], "用户退出登录")
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
        
        # 角色权限控制
        if role == "管理员":
            admin_dashboard()
        elif role == "评估人员":
            user_dashboard()
        elif role == "机构用户":
            inst_dashboard()

if __name__ == '__main__':
    main()