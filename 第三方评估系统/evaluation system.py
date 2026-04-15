import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime

# ---------------------------
# 数据库初始化
# ---------------------------
def init_db():
    conn = sqlite3.connect('performance.db')
    c = conn.cursor()

    # 用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE,
                  password TEXT,
                  name TEXT,
                  role TEXT)''')

    # 机构表
    c.execute('''CREATE TABLE IF NOT EXISTS organizations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  contact TEXT,
                  phone TEXT,
                  address TEXT,
                  remark TEXT)''')

    # 指标表
    c.execute('''CREATE TABLE IF NOT EXISTS indicators
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT,
                  full_score INTEGER,
                  sort INTEGER)''')

    # 评分表
    c.execute('''CREATE TABLE IF NOT EXISTS scores
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  org_id INTEGER,
                  indicator_id INTEGER,
                  score REAL,
                  comment TEXT,
                  year TEXT,
                  evaluator TEXT,
                  create_time TEXT)''')

    # 初始化默认账号
    try:
        c.execute("INSERT OR IGNORE INTO users (username,password,name,role) VALUES (?,?,?,?)",
                  ('admin', hashlib.md5(b'123456').hexdigest(), '系统管理员', '管理员'))
        c.execute("INSERT OR IGNORE INTO users (username,password,name,role) VALUES (?,?,?,?)",
                  ('user', hashlib.md5(b'123456').hexdigest(), '评估员', '评估人员'))
    except:
        pass

    conn.commit()
    conn.close()

# ---------------------------
# 密码加密 & 登录校验
# ---------------------------
def md5(s):
    return hashlib.md5(s.encode()).hexdigest()

def check_login(username, password):
    conn = sqlite3.connect('performance.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username=? AND password=?",
              (username, md5(password)))
    user = c.fetchone()
    conn.close()
    return user

# ---------------------------
# 页面控制
# ---------------------------
def main():
    init_db()
    st.set_page_config(page_title="第三方机构绩效评估系统", layout="wide")
    st.title("📊 第三方机构绩效评估系统")

    if 'user' not in st.session_state:
        st.session_state.user = None

    user = st.session_state.user

    # 登录页面
    if not user:
        with st.form("登录"):
            username = st.text_input("账号")
            password = st.text_input("密码", type="password")
            submit = st.form_submit_button("登录")
            if submit:
                u = check_login(username, password)
                if u:
                    st.session_state.user = {
                        'id': u[0],
                        'username': u[1],
                        'name': u[3],
                        'role': u[4]
                    }
                    st.success("登录成功！")
                    st.rerun()
                else:
                    st.error("账号或密码错误")
        return

    # 已登录
    st.sidebar.info(f"欢迎：{user['name']}（{user['role']}）")
    if st.sidebar.button("退出登录"):
        st.session_state.user = None
        st.rerun()

    menu = []
    if user['role'] == "管理员":
        menu = ["机构管理", "指标管理", "绩效评分", "报表查看", "用户管理", "导入导出"]
    elif user['role'] == "评估人员":
        menu = ["机构管理", "绩效评分", "报表查看", "导入导出"]
    else:
        menu = ["我的绩效"]

    tab = st.sidebar.radio("菜单", menu)

    # ------------------------
    # 1. 机构管理
    # ------------------------
    if tab == "机构管理":
        st.subheader("🏢 第三方机构管理")
        conn = sqlite3.connect('performance.db')
        mode = st.radio("操作", ["查看列表", "新增机构"], horizontal=True)

        if mode == "新增机构":
            with st.form("add_org"):
                name = st.text_input("机构名称")
                contact = st.text_input("联系人")
                phone = st.text_input("联系电话")
                address = st.text_area("地址")
                remark = st.text_area("备注")
                if st.form_submit_button("保存"):
                    try:
                        c = conn.cursor()
                        c.execute('''INSERT INTO organizations 
                                     (name,contact,phone,address,remark)
                                     VALUES (?,?,?,?,?)''',
                                  (name, contact, phone, address, remark))
                        conn.commit()
                        st.success("添加成功！")
                    except:
                        st.error("机构名称已存在")

        df = pd.read_sql("SELECT * FROM organizations", conn)
        st.dataframe(df, use_container_width=True)
        conn.close()

    # ------------------------
    # 2. 指标管理
    # ------------------------
    elif tab == "指标管理" and user['role'] == "管理员":
        st.subheader("📋 评估指标管理")
        conn = sqlite3.connect('performance.db')

        with st.form("add_ind"):
            name = st.text_input("指标名称")
            full_score = st.number_input("满分", min_value=1, value=100)
            sort = st.number_input("排序号", min_value=0, value=0)
            if st.form_submit_button("添加指标"):
                c = conn.cursor()
                c.execute('''INSERT INTO indicators (name,full_score,sort)
                             VALUES (?,?,?)''', (name, full_score, sort))
                conn.commit()
                st.success("添加成功")

        df = pd.read_sql("SELECT * FROM indicators ORDER BY sort", conn)
        st.dataframe(df, use_container_width=True)
        conn.close()

    # ------------------------
    # 3. 绩效评分
    # ------------------------
    elif tab == "绩效评分":
        st.subheader("✏️ 绩效评分")
        conn = sqlite3.connect('performance.db')

        # 选择机构
        orgs = pd.read_sql("SELECT id,name FROM organizations", conn)
        if orgs.empty:
            st.warning("请先添加机构")
            conn.close()
            return
        org = st.selectbox("选择机构", orgs['name'])
        org_id = orgs[orgs['name'] == org]['id'].iloc[0]
        year = st.selectbox("年度", ["2025", "2026", "2027"])

        # 指标
        inds = pd.read_sql("SELECT * FROM indicators ORDER BY sort", conn)
        if inds.empty:
            st.warning("请先添加指标")
            conn.close()
            return

        scores = []
        comments = []
        total = 0
        max_total = inds['full_score'].sum()

        with st.form("score_form"):
            st.markdown(f"**总分：{max_total} 分**")
            for i, row in inds.iterrows():
                sc = st.slider(f"{row['name']}（{row['full_score']}分）",
                               0.0, float(row['full_score']), 0.0)
                cmt = st.text_input(f"评语：{row['name']}", key=f"cmt_{i}")
                scores.append(sc)
                comments.append(cmt)
                total += sc

            st.markdown(f"### 本次得分：**{total}/{max_total}**")
            if max_total > 0:
                rate = total / max_total
                if rate >= 0.9:
                    level = "优秀"
                elif rate >= 0.8:
                    level = "良好"
                elif rate >= 0.7:
                    level = "合格"
                else:
                    level = "不合格"
                st.success(f"**等级：{level}**")

            if st.form_submit_button("提交评分"):
                c = conn.cursor()
                # 先清空同机构同年数据
                c.execute("DELETE FROM scores WHERE org_id=? AND year=?",
                          (org_id, year))
                for i, row in inds.iterrows():
                    c.execute('''INSERT INTO scores
                                 (org_id,indicator_id,score,comment,year,evaluator,create_time)
                                 VALUES (?,?,?,?,?,?,?)''',
                              (org_id, row['id'], scores[i], comments[i],
                               year, user['name'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                conn.commit()
                st.success("评分提交成功！")
        conn.close()

    # ------------------------
    # 4. 报表查看
    # ------------------------
    elif tab == "报表查看":
        st.subheader("📈 绩效报表与排名")
        conn = sqlite3.connect('performance.db')
        year = st.selectbox("选择年度", ["2025", "2026", "2027"], index=1)

        # 总分统计
        sql = '''
            SELECT o.name org_name, SUM(s.score) total_score,
                   (SELECT SUM(full_score) FROM indicators) max_score
            FROM scores s
            JOIN organizations o ON s.org_id = o.id
            WHERE s.year=?
            GROUP BY o.id
            ORDER BY total_score DESC
        '''
        df = pd.read_sql(sql, conn, params=(year,))
        if not df.empty:
            df['得分率'] = (df['total_score'] / df['max_score'] * 100).round(2).astype(str) + "%"
            st.dataframe(df, use_container_width=True)
            st.bar_chart(df, x="org_name", y="total_score")
        else:
            st.info("暂无评分数据")
        conn.close()

    # ------------------------
    # 5. 导入导出
    # ------------------------
    elif tab == "导入导出":
        st.subheader("Excel 导入/导出")
        conn = sqlite3.connect('performance.db')
        op = st.radio("功能", ["导出机构", "导出评分", "导入机构"], horizontal=True)

        if op == "导出机构":
            df = pd.read_sql("SELECT * FROM organizations", conn)
            st.dataframe(df)
            st.download_button("下载机构Excel",
                               df.to_csv(index=False, encoding="utf-8-sig"),
                               file_name="机构.csv")

        elif op == "导出评分":
            year = st.selectbox("年度", ["2025", "2026", "2027"])
            sql = '''
                SELECT o.name org_name, i.name ind_name,
                       s.score, s.comment, s.year, s.evaluator
                FROM scores s
                JOIN organizations o ON s.org_id=o.id
                JOIN indicators i ON s.indicator_id=i.id
                WHERE s.year=?
            '''
            df = pd.read_sql(sql, conn, params=(year,))
            st.dataframe(df)
            st.download_button("下载评分数据",
                               df.to_csv(index=False, encoding="utf-8-sig"),
                               file_name="评分.csv")

        elif op == "导入机构":
            f = st.file_uploader("上传机构Excel（必须有name,contact,phone,address,remark列）")
            if f:
                try:
                    df_upload = pd.read_csv(f)
                    for _, row in df_upload.iterrows():
                        try:
                            c = conn.cursor()
                            c.execute('''INSERT OR IGNORE INTO organizations
                                         (name,contact,phone,address,remark)
                                         VALUES (?,?,?,?,?)''',
                                      (str(row['name']),
                                       str(row.get('contact','')),
                                       str(row.get('phone','')),
                                       str(row.get('address','')),
                                       str(row.get('remark',''))))
                            conn.commit()
                        except:
                            continue
                    st.success("导入完成！")
                except:
                    st.error("格式错误")
        conn.close()

    # ------------------------
    # 6. 用户管理（仅管理员）
    # ------------------------
    elif tab == "用户管理" and user['role'] == "管理员":
        st.subheader("👥 用户管理")
        conn = sqlite3.connect('performance.db')
        with st.form("add_user"):
            new_user = st.text_input("账号")
            new_pwd = st.text_input("密码", value="123456")
            new_name = st.text_input("姓名")
            new_role = st.selectbox("角色", ["管理员", "评估人员"])
            if st.form_submit_button("添加用户"):
                c = conn.cursor()
                c.execute("INSERT INTO users (username,password,name,role) VALUES (?,?,?,?)",
                          (new_user, md5(new_pwd), new_name, new_role))
                conn.commit()
                st.success("添加成功")
        df = pd.read_sql("SELECT id,username,name,role FROM users", conn)
        st.dataframe(df, use_container_width=True)
        conn.close()

if __name__ == '__main__':
    main()