import pdfplumber
import pandas as pd
import os

# ===================== 路径配置 =====================
PDF_FOLDER = r"D:\预决算"
INDICATOR_FILE = r"D:\评价指标\评价指标.xlsx"  # 你的评价指标表
OUTPUT_EXCEL = r"D:\预决算评分结果_完整版.xlsx"

# ===================== 读取评价指标 =====================
def load_indicators():
    df = pd.read_excel(INDICATOR_FILE)
    df = df.dropna(subset=["评分指标"])
    return df.to_dict("records")

# ===================== 单个PDF评分 =====================
def score_pdf(pdf_path, indicators):
    try:
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t
        text = text.lower()
    except:
        return "读取失败", [], 0

    # 单位名称
    unit_name = os.path.basename(pdf_path).replace(".pdf", "")

    # 逐项评分
    results = []
    total_score = 0

    for ind in indicators:
        dim = ind["维度"]
        name = ind["评分指标"]
        full = float(ind["分值"])
        standard = ind["评分标准"]
        score = 0.0
        problem = ""

        # ============== 自动判断规则 ==============
        # 及时性
        if "公开时限" in name:
            score = full
        elif "年度完成时间" in name:
            score = full

        # 完整性
        elif "四本预算" in name:
            req = ["一般公共预算", "政府性基金", "国有资本经营", "社会保险基金"]
            if all(k.lower() in text for k in req):
                score = full
            else:
                problem = "缺部分预算"

        elif "三公经费" in name and "完整性" in name:
            if all(k in text for k in ["因公出国", "公务用车", "公务接待"]):
                score = full
            else:
                problem = "三公经费缺项"

        elif "机关运行经费" in name:
            score = full if "机关运行经费" in text else 0
            if score == 0: problem = "未公开机关运行经费"

        elif "政府采购" in name:
            score = full if "政府采购" in text else 0

        elif "国有资产" in name:
            score = full if "国有资产" in text else 0

        elif "专项资金" in name:
            score = full if "专项" in text else 0

        elif "绩效信息" in name:
            score = full if "绩效" in text else 0

        # 细化程度
        elif "功能分类" in name:
            score = full if "项级" in text else 0

        elif "经济分类" in name:
            score = full if "款级" in text else 0

        elif "绩效指标" in name:
            score = full if "量化" in text else 0

        # 规范性
        elif "可检索" in name:
            score = full  # PDF可检索

        # 不识别的指标 → 默认0分
        else:
            score = 0.0
            problem = "无法自动评判，按0分计"

        total_score += score
        results.append([unit_name, dim, name, full, standard, score, problem])

    return unit_name, results, round(total_score, 2)

# ===================== 批量执行 =====================
def run():
    indicators = load_indicators()
    all_rows = []

    for file in os.listdir(PDF_FOLDER):
        if file.lower().endswith(".pdf"):
            path = os.path.join(PDF_FOLDER, file)
            unit, rows, total = score_pdf(path, indicators)

            for r in rows:
                r.append(total)  # 加入【评估总分】
                all_rows.append(r)
            print(f"✅ {unit} | 评估总分：{total}")

    # 输出最终格式
    df_out = pd.DataFrame(all_rows, columns=[
        "单位名称", "维度", "评分指标", "分值", "评分标准", "评分结果", "问题记录", "评估总分"
    ])
    df_out.to_excel(OUTPUT_EXCEL, index=False)
    print(f"\n🎉 全部完成！文件已保存到：{OUTPUT_EXCEL}")

if __name__ == "__main__":
    run()