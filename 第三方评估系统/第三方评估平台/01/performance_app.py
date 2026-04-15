import streamlit as st
import sqlite3
import bcrypt
import pandas as pd
import plotly.express as px
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime, timedelta
import os
import shutil

# ===================== 全局配置 =====================
st.set_page_config(
    page_title="第三方绩效管理平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 文件夹创建
os.makedirs("uploads", exist_ok=True)
os.makedirs("exports", exist_ok=True)
DB_NAME = "performance.db"

# 会话状态初始化
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.org_id = None

# ===================== 数据库初始化（核心） =====================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # 1. 用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  role TEXT NOT NULL,
                  org_id INTEGER,
                  status INTEGER DEFAULT 1,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 2. 机构表
    c.execute('''CREATE TABLE IF NOT EXISTS organizations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  contact TEXT,
                  phone TEXT,
                  address TEXT,
                  performance TEXT,
                  training TEXT,
                  status INTEGER DEFAULT 1,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 3. 主评人表
    c.execute('''CREATE TABLE IF NOT EXISTS evaluators
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  org_id INTEGER NOT NULL,
                  name TEXT NOT NULL,
                  title TEXT,
                  major TEXT,
                  experience TEXT,
                  status INTEGER DEFAULT 1,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 4. 项目表
    c.execute('''CREATE TABLE IF NOT EXISTS projects
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  org_id INTEGER NOT NULL,
                  name TEXT NOT NULL,
                  description TEXT,
                  status TEXT DEFAULT '待上传方案',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 5. 项目阶段表
    c.execute('''CREATE TABLE IF NOT EXISTS project_steps
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  project_id INTEGER NOT NULL,
                  step_name TEXT NOT NULL,
                  file_path TEXT,
                  audit_status TEXT DEFAULT '待审核',
                  audit_remark TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 6. 指标库
    c.execute('''CREATE TABLE IF NOT EXISTS indicator_library
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  type TEXT,
                  content TEXT,
                  status INTEGER DEFAULT 1,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 7. 制度文件
    c.execute('''CREATE TABLE IF NOT EXISTS policy_files
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  category TEXT,
                  file_path TEXT,
                  status INTEGER DEFAULT 1,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 8. 待办任务
    c.execute('''CREATE TABLE IF NOT EXISTS todos
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  org_id INTEGER,
                  title TEXT NOT NULL,
                  deadline DATE,
                  status TEXT DEFAULT '待处理',
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 9. 消息通知
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  org_id INTEGER,
                  content TEXT NOT NULL,
                  is_read INTEGER DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 初始化默认数据
    try:
        # 初始化指标库
        c.execute("SELECT COUNT(*) FROM indicator_library")
        if c.fetchone()[0] == 0:
            indicators = [
                ("服务质量指标", "服务类", "响应时效、服务满意度、问题解决率"),
                ("专业能力指标", "能力类", "专业资质、项目经验、成果质量"),
                ("合规性指标", "合规类", "制度执行、流程规范、资料完备")
            ]
            c.executemany("INSERT INTO indicator_library (name, type, content) VALUES (?,?,?)", indicators)
    except:
        pass

    conn.commit()
    conn.close()

# ===================== 工具函数 =====================
def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def add_todo(org_id, title, days=7):
    deadline = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    conn = get_db_connection()
    conn.execute("INSERT INTO todos (org_id, title, deadline) VALUES (?,?,?)",
                 (org_id, title, deadline))
    conn.commit()
    conn.close()

def add_message(org_id, content):
    conn = get_db_connection()
    conn.execute("INSERT INTO messages (org_id, content) VALUES (?,?)",
                 (org_id, content))
    conn.commit()
    conn.close()

def login_check():
    if not st.session_state.logged_in:
        st.warning("请先登录！")
        st.stop()

def admin_check():
    if st.session_state.role != "admin":
        st.error("无管理员权限！")
        st.stop()

# ===================== 页面模块 =====================
def page_login():
    st.title("🔐 平台登录")
    username = st.text_input("账号")
    password = st.text_input("密码", type="password")
    
    if st.button("登录"):
        if not username or not password:
            st.error("请输入账号密码")
            return
        
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        
        if user and verify_password(password, user['password_hash']):
            st.session_state.logged_in = True
            st.session_state.user_id = user['id']
            st.session_state.username = user['username']
            st.session_state.role = user['role']
            st.session_state.org_id = user['org_id']
            st.success("登录成功！")
            st.rerun()
        else:
            st.error("账号或密码错误")

def page_register():
    st.title("📝 机构注册")
    st.info("仅入围第三方机构可注册")
    
    org_name = st.text_input("机构名称")
    contact = st.text_input("联系人")
    phone = st.text_input("联系电话")
    address = st.text_area("机构地址")
    username = st.text_input("管理员账号")
    password = st.text_input("管理员密码", type="password")
    
    if st.button("注册"):
        if not all([org_name, contact, phone, username, password]):
            st.error("请填写完整信息")
            return
        
        conn = get_db_connection()
        try:
            # 插入机构
            conn.execute("INSERT INTO organizations (name, contact, phone, address) VALUES (?,?,?,?)",
                         (org_name, contact, phone, address))
            org_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            
            # 插入管理员账号
            pwd_hash = hash_password(password)
            conn.execute("INSERT INTO users (username, password_hash, role, org_id) VALUES (?,?,?,?)",
                         (username, pwd_hash, "admin", org_id))
            
            # 初始化待办
            add_todo(org_id, "完善机构基础信息")
            add_message(org_id, "注册成功，欢迎使用绩效管理平台")
            
            conn.commit()
            st.success("注册成功！请登录")
            st.rerun()
        except sqlite3.IntegrityError:
            st.error("账号已存在")
        finally:
            conn.close()

def page_dashboard():
    login_check()
    st.title("📊 工作台")
    
    conn = get_db_connection()
    org_id = st.session_state.org_id
    
    # 项目统计
    projects = conn.execute("SELECT status, COUNT(*) as cnt FROM projects WHERE org_id=? GROUP BY status", (org_id,)).fetchall()
    df_projects = pd.DataFrame(projects)
    
    # 待办任务
    todos = conn.execute("SELECT * FROM todos WHERE org_id=? ORDER BY deadline", (org_id,)).fetchall()
    df_todos = pd.DataFrame(todos)
    
    # 未读消息
    unread = conn.execute("SELECT COUNT(*) FROM messages WHERE org_id=? AND is_read=0", (org_id,)).fetchone()[0]
    conn.close()
    
    # 布局
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("项目状态统计")
        if not df_projects.empty:
            fig = px.pie(df_projects, values="cnt", names="status", title="项目分布")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无项目数据")
    
    with col2:
        st.subheader("待办任务")
        if not df_todos.empty:
            now = datetime.now().date()
            for _, row in df_todos.iterrows():
                deadline = datetime.strptime(row['deadline'], "%Y-%m-%d").date()
                days = (deadline - now).days
                
                if days < 0:
                    st.error(f"🔴 {row['title']} | 逾期 {abs(days)} 天")
                elif days <= 3:
                    st.warning(f"🟡 {row['title']} | 剩余 {days} 天")
                else:
                    st.success(f"🟢 {row['title']} | 剩余 {days} 天")
        else:
            st.success("暂无待办任务")
    
    st.markdown("---")
    st.subheader(f"🔔 未读消息：{unread} 条")

def page_org_manage():
    login_check()
    admin_check()
    st.title("🏢 机构信息管理")
    
    conn = get_db_connection()
    org_id = st.session_state.org_id
    org = conn.execute("SELECT * FROM organizations WHERE id=?", (org_id,)).fetchone()
    
    # 编辑表单
    name = st.text_input("机构名称", value=org['name'])
    contact = st.text_input("联系人", value=org['contact'])
    phone = st.text_input("联系电话", value=org['phone'])
    address = st.text_area("地址", value=org['address'])
    performance = st.text_area("业绩信息", value=org['performance'] if org['performance'] else "")
    training = st.text_area("培训信息", value=org['training'] if org['training'] else "")
    
    if st.button("保存信息"):
        conn.execute('''UPDATE organizations SET
                        name=?, contact=?, phone=?, address=?, performance=?, training=?, updated_at=CURRENT_TIMESTAMP
                        WHERE id=?''',
                     (name, contact, phone, address, performance, training, org_id))
        conn.commit()
        st.success("保存成功")
    
    conn.close()

def page_evaluator_manage():
    login_check()
    admin_check()
    st.title("👨‍💼 主评人管理")
    
    conn = get_db_connection()
    org_id = st.session_state.org_id
    
    # 新增
    with st.expander("➕ 新增主评人"):
        name = st.text_input("姓名")
        title = st.text_input("职称")
        major = st.text_input("专业")
        experience = st.text_area("从业经验")
        if st.button("添加"):
            conn.execute("INSERT INTO evaluators (org_id, name, title, major, experience) VALUES (?,?,?,?,?)",
                         (org_id, name, title, major, experience))
            conn.commit()
            st.success("添加成功")
    
    # 列表
    st.subheader("主评人列表")
    data = conn.execute("SELECT * FROM evaluators WHERE org_id=?", (org_id,)).fetchall()
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    
    # 删除
    del_id = st.number_input("删除ID", min_value=0)
    if st.button("删除") and del_id > 0:
        conn.execute("DELETE FROM evaluators WHERE id=? AND org_id=?", (del_id, org_id))
        conn.commit()
        st.success("删除成功")
        st.rerun()
    
    conn.close()

def page_subuser_manage():
    login_check()
    admin_check()
    st.title("👥 子账号管理")
    
    conn = get_db_connection()
    org_id = st.session_state.org_id
    
    # 创建子账号
    with st.expander("➕ 创建子账号（主评人）"):
        username = st.text_input("子账号")
        password = st.text_input("密码", type="password")
        if st.button("创建"):
            pwd_hash = hash_password(password)
            try:
                conn.execute("INSERT INTO users (username, password_hash, role, org_id) VALUES (?,?,?,?)",
                             (username, pwd_hash, "user", org_id))
                conn.commit()
                st.success("创建成功")
            except:
                st.error("账号已存在")
    
    # 子账号列表
    st.subheader("子账号列表")
    users = conn.execute("SELECT id, username, created_at FROM users WHERE org_id=? AND role='user'", (org_id,)).fetchall()
    df = pd.DataFrame(users)
    st.dataframe(df, use_container_width=True)
    
    # 重置密码/删除
    col1, col2 = st.columns(2)
    with col1:
        uid = st.number_input("用户ID", min_value=0)
        new_pwd = st.text_input("新密码", type="password")
        if st.button("重置密码") and uid > 0 and new_pwd:
            pwd_hash = hash_password(new_pwd)
            conn.execute("UPDATE users SET password_hash=? WHERE id=? AND org_id=?", (pwd_hash, uid, org_id))
            conn.commit()
            st.success("重置成功")
    
    with col2:
        del_uid = st.number_input("删除用户ID", min_value=0)
        if st.button("删除子账号") and del_uid > 0:
            conn.execute("DELETE FROM users WHERE id=? AND org_id=? AND role='user'", (del_uid, org_id))
            conn.commit()
            st.success("删除成功")
            st.rerun()
    
    conn.close()

def page_project_manage():
    login_check()
    st.title("📋 项目全生命周期管理")
    
    conn = get_db_connection()
    org_id = st.session_state.org_id
    
    # 新建项目
    with st.expander("➕ 创建新项目"):
        project_name = st.text_input("项目名称")
        project_desc = st.text_area("项目描述")
        if st.button("创建"):
            conn.execute("INSERT INTO projects (org_id, name, description) VALUES (?,?,?)",
                         (org_id, project_name, project_desc))
            pid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            steps = ["上传评价方案", "录入实施计划", "上传评价成果", "上传评价报告", "项目归档"]
            for step in steps:
                conn.execute("INSERT INTO project_steps (project_id, step_name) VALUES (?,?)", (pid, step))
            add_todo(org_id, f"完成项目【{project_name}】方案上传")
            conn.commit()
            st.success("创建成功")
    
    # 项目列表
    projects = conn.execute("SELECT * FROM projects WHERE org_id=?", (org_id,)).fetchall()
    if not projects:
        st.info("暂无项目")
        return
    
    project_ids = [p['id'] for p in projects]
    select_pid = st.selectbox("选择项目", project_ids, format_func=lambda x: f"项目{x}")
    project = conn.execute("SELECT * FROM projects WHERE id=?", (select_pid,)).fetchone()
    
    st.subheader(f"当前项目：{project['name']}")
    steps = conn.execute("SELECT * FROM project_steps WHERE project_id=? ORDER BY id", (select_pid,)).fetchall()
    
    steps_config = [
        ("上传评价方案", "请上传评价方案文件", "pdf/docx/xlsx"),
        ("录入实施计划", "请上传实施计划文件", "pdf/docx/xlsx"),
        ("上传评价成果", "请上传评价成果文件", "pdf/docx/xlsx"),
        ("上传评价报告", "请上传评价报告文件", "pdf/docx/xlsx"),
        ("项目归档", "请上传合同等归档文件", "pdf/docx/xlsx")
    ]
    
    for i, step in enumerate(steps):
        st.markdown(f"### {i+1}. {step['step_name']}")
        st.write(f"状态：{step['audit_status']}")
        if step['audit_remark']:
            st.write(f"审核意见：{step['audit_remark']}")
        
        # 前置校验
        if i > 0:
            prev_step = steps[i-1]
            if prev_step['audit_status'] != "已通过":
                st.warning("需上一阶段审核通过才可操作")
                continue
        
        # 文件上传
        file = st.file_uploader(steps_config[i][1], type=["pdf","docx","xlsx"], key=f"file_{step['id']}")
        if file and st.button(f"提交{step['step_name']}", key=f"btn_{step['id']}"):
            save_path = f"uploads/{org_id}_{select_pid}_{step['id']}_{file.name}"
            with open(save_path, "wb") as f:
                f.write(file.getbuffer())
            conn.execute('''UPDATE project_steps SET
                            file_path=?, audit_status='待审核', updated_at=CURRENT_TIMESTAMP
                            WHERE id=?''', (save_path, step['id']))
            conn.execute("UPDATE projects SET status=? WHERE id=?", (step['step_name'], select_pid))
            add_message(org_id, f"项目【{project['name']}】{step['step_name']}已提交待审核")
            conn.commit()
            st.success("提交成功")
        
        # 下载
        if step['file_path'] and os.path.exists(step['file_path']):
            with open(step['file_path'], "rb") as f:
                st.download_button("下载文件", f, file_name=os.path.basename(step['file_path']), key=f"dl_{step['id']}")
        
        st.markdown("---")
    
    conn.close()

def page_think_tank():
    login_check()
    st.title("📚 绩效智库")
    
    tab1, tab2 = st.tabs(["评价指标库", "制度文件库"])
    conn = get_db_connection()
    
    with tab1:
        st.subheader("评价指标库")
        data = conn.execute("SELECT * FROM indicator_library").fetchall()
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
    
    with tab2:
        st.subheader("制度文件库")
        files = conn.execute("SELECT * FROM policy_files").fetchall()
        for f in files:
            st.write(f"【{f['category']}】{f['title']}")
            if f['file_path'] and os.path.exists(f['file_path']):
                with open(f['file_path'], "rb") as fp:
                    st.download_button("下载", fp, file_name=os.path.basename(f['file_path']), key=f"p_{f['id']}")
    
    conn.close()

def page_message_todo():
    login_check()
    st.title("🔔 消息与待办")
    
    conn = get_db_connection()
    org_id = st.session_state.org_id
    
    tab1, tab2 = st.tabs(["待办任务", "消息通知"])
    with tab1:
        todos = conn.execute("SELECT * FROM todos WHERE org_id=? ORDER BY deadline", (org_id,)).fetchall()
        df_todo = pd.DataFrame(todos)
        st.dataframe(df_todo, use_container_width=True)
        
        tid = st.number_input("标记完成ID", min_value=0)
        if st.button("标记已完成") and tid > 0:
            conn.execute("UPDATE todos SET status='已完成' WHERE id=? AND org_id=?", (tid, org_id))
            conn.commit()
            st.success("操作成功")
            st.rerun()
    
    with tab2:
        msgs = conn.execute("SELECT * FROM messages WHERE org_id=? ORDER BY created_at DESC", (org_id,)).fetchall()
        for msg in msgs:
            tag = "🔴" if msg['is_read'] == 0 else "🟢"
            st.write(f"{tag} {msg['created_at']} | {msg['content']}")
        
        if st.button("全部已读"):
            conn.execute("UPDATE messages SET is_read=1 WHERE org_id=?", (org_id,))
            conn.commit()
            st.rerun()
    
    conn.close()

def page_profile():
    login_check()
    st.title("👤 个人中心")
    
    old_pwd = st.text_input("原密码", type="password")
    new_pwd = st.text_input("新密码", type="password")
    confirm_pwd = st.text_input("确认新密码", type="password")
    
    if st.button("修改密码"):
        if new_pwd != confirm_pwd:
            st.error("两次密码不一致")
            return
        
        conn = get_db_connection()
        user = conn.execute("SELECT password_hash FROM users WHERE id=?", (st.session_state.user_id,)).fetchone()
        
        if verify_password(old_pwd, user['password_hash']):
            new_hash = hash_password(new_pwd)
            conn.execute("UPDATE users SET password_hash=? WHERE id=?", (new_hash, st.session_state.user_id))
            conn.commit()
            st.success("密码修改成功")
        else:
            st.error("原密码错误")
        conn.close()

def page_export():
    login_check()
    st.title("📤 数据导出与PDF报告")
    org_id = st.session_state.org_id
    conn = get_db_connection()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Excel导出")
        if st.button("导出项目信息"):
            projects = conn.execute("SELECT * FROM projects WHERE org_id=?", (org_id,)).fetchall()
            df = pd.DataFrame(projects)
            path = f"exports/项目信息_{org_id}.xlsx"
            df.to_excel(path, index=False)
            with open(path, "rb") as f:
                st.download_button("下载文件", f, file_name=f"项目信息.xlsx")
        
        if st.button("导出机构信息"):
            org = conn.execute("SELECT * FROM organizations WHERE id=?", (org_id,)).fetchone()
            df = pd.DataFrame([org])
            path = f"exports/机构信息_{org_id}.xlsx"
            df.to_excel(path, index=False)
            with open(path, "rb") as f:
                st.download_button("下载文件", f, file_name=f"机构信息.xlsx")
    
    with col2:
        st.subheader("PDF报告生成")
        project_id = st.number_input("生成项目报告（输入项目ID）", min_value=0)
        if st.button("生成PDF") and project_id > 0:
            project = conn.execute("SELECT * FROM projects WHERE id=? AND org_id=?", (project_id, org_id)).fetchone()
            if not project:
                st.error("项目不存在")
                return
            
            path = f"exports/项目报告_{project_id}.pdf"
            c = canvas.Canvas(path, pagesize=A4)
            c.drawString(100, 800, "第三方绩效评价项目报告")
            c.drawString(100, 780, f"项目名称：{project['name']}")
            c.drawString(100, 760, f"项目状态：{project['status']}")
            c.drawString(100, 740, f"创建时间：{project['created_at']}")
            c.save()
            
            with open(path, "rb") as f:
                st.download_button("下载PDF报告", f, file_name=f"项目报告.pdf")
            st.success("生成成功")
    
    conn.close()

# ===================== 主程序路由 =====================
def main():
    init_db()
    
    if not st.session_state.logged_in:
        menu = ["登录", "注册"]
    else:
        menu = [
            "工作台", "机构信息管理", "主评人管理", "子账号管理",
            "项目管理", "绩效智库", "消息待办", "个人中心", "数据导出"
        ]
    
    choice = st.sidebar.selectbox("菜单导航", menu)
    st.sidebar.markdown("---")
    if st.session_state.logged_in:
        st.sidebar.info(f"欢迎：{st.session_state.username}\n角色：{st.session_state.role}")
        if st.sidebar.button("退出登录"):
            st.session_state.logged_in = False
            st.rerun()
    
    # 路由
    if choice == "登录":
        page_login()
    elif choice == "注册":
        page_register()
    elif choice == "工作台":
        page_dashboard()
    elif choice == "机构信息管理":
        page_org_manage()
    elif choice == "主评人管理":
        page_evaluator_manage()
    elif choice == "子账号管理":
        page_subuser_manage()
    elif choice == "项目管理":
        page_project_manage()
    elif choice == "绩效智库":
        page_think_tank()
    elif choice == "消息待办":
        page_message_todo()
    elif choice == "个人中心":
        page_profile()
    elif choice == "数据导出":
        page_export()

if __name__ == "__main__":
    main()