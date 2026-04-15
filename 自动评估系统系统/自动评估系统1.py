import pdfplumber
import pandas as pd
import os

# ===================== 核心配置（已适配你的路径和新指标表）=====================
# 1. PDF文件存放路径（你的预决算文件夹）
PDF_FOLDER = r"D:\预决算"
# 2. 新评价指标表路径（请将《评价指标1.xlsx》放在此路径，或修改为你的实际路径）
INDICATOR_FILE = r"D:\评价指标\评价指标1.xlsx"
# 3. 最终输出结果路径
OUTPUT_EXCEL = r"D:\预决算评分结果_新指标版.xlsx"

# ===================== 步骤1：读取新评价指标表 =====================
def load_new_indicators():
    """读取《评价指标1.xlsx》，获取维度、评分指标、分值、评分标准"""
    try:
        df_indicators = pd.read_excel(INDICATOR_FILE)
        # 按新指标表格式整理列名（适配常见Excel表头，可根据实际表调整）
        if "维度" not in df_indicators.columns or "评分指标" not in df_indicators.columns:
            raise ValueError("评价指标表格式错误，需包含'维度'和'评分指标'列")
        
        # 提取核心指标信息（去重，保留有效行）
        indicator_list = []
        for _, row in df_indicators.iterrows():
            if pd.notna(row["评分指标"]):  # 跳过空指标行
                indicator_list.append({
                    "维度": row["维度"] if pd.notna(row["维度"]) else "未分类",
                    "评分指标": str(row["评分指标"]).strip(),
                    "分值": float(row["分值"]) if pd.notna(row["分值"]) else 0.0,
                    "评分标准": str(row["评分标准"]) if pd.notna(row["评分标准"]) else "无"
                })
        return indicator_list
    except Exception as e:
        print(f"❌ 读取评价指标表失败：{str(e)}")
        exit()

# ===================== 步骤2：单个PDF自动评分（按新指标）=====================
def score_pdf_by_new_indicator(pdf_path, indicator_list):
    """按新指标表逐项评分，未评判指标默认0分，记录问题"""
    # 1. 提取PDF文本（用于判断指标是否达标）
    pdf_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pdf_text += page_text.lower()  # 转小写，避免大小写问题
    except Exception as e:
        return f"读取失败_{os.path.basename(pdf_path)}", [], f"PDF读取错误：{str(e)}"

    # 2. 识别单位名称（优先从文件名提取，其次从文本提取）
    file_name = os.path.basename(pdf_path).replace(".pdf", "")
    unit_name = file_name  # 默认用文件名作为单位名
    # 文本中提取更精准的单位名（适配江西各厅局格式）
    if "江西省" in pdf_text and ("厅" in pdf_text or "局" in pdf_text or "委员会" in pdf_text):
        for keyword in ["财政厅", "教育厅", "发改委", "水利厅", "农业农村厅", "卫健委"]:
            if keyword in pdf_text:
                unit_name = f"江西省{keyword}"
                break

    # 3. 按新指标表逐项评分（未评判/不达标默认0分）
    score_results = []
    total_problems = []

    for indicator in indicator_list:
        indicator_name = indicator["评分指标"]
        full_score = indicator["分值"]
        standard = indicator["评分标准"]
        score = 0.0  # 未评判/不达标默认0分
        problem = ""

        # ---------------- 指标判断逻辑（按新指标表常见指标适配，可扩展）----------------
        # （1）及时性相关指标
        if "公开时限" in indicator_name:
            if "20日内" in standard and "批复后" in standard:
                if "20日内" in pdf_text or "及时公开" in pdf_text:
                    score = full_score
                else:
                    problem = "未在规定时限内公开"
        elif "年度完成时间" in indicator_name:
            if "10月31日" in standard:
                if "10月31日" in pdf_text or "10月底前" in pdf_text:
                    score = full_score
                else:
                    problem = "未在10月31日前完成公开"
        
        # （2）完整性相关指标
        elif "四本预算" in indicator_name:
            if "一般公共预算" in standard and "政府性基金" in standard:
                required_budgets = ["一般公共预算", "政府性基金", "国有资本经营", "社会保险基金"]
                missing = [b for b in required_budgets if b.lower() not in pdf_text]
                if not missing:
                    score = full_score
                else:
                    problem = f"缺{','.join(missing)}预算"
        elif "三公经费" in indicator_name and "完整性" in indicator_name:
            if "因公出国" in standard and "公务用车" in standard:
                if all(x.lower() in pdf_text for x in ["因公出国", "公务用车", "公务接待"]):
                    score = full_score
                else:
                    problem = "三公经费缺分项公开"
        
        # （3）细化程度相关指标
        elif "支出功能分类" in indicator_name:
            if "项级" in standard:
                if "项级" in pdf_text or "类款项" in pdf_text:
                    score = full_score
                else:
                    problem = "支出功能分类未细化到项级"
        elif "绩效指标" in indicator_name and "细化" in indicator_name:
            if "量化" in standard:
                if "量化" in pdf_text or "具体数值" in pdf_text:
                    score = full_score
                else:
                    problem = "绩效指标未量化"
        
        # （4）规范性相关指标
        elif "内容可检索性" in indicator_name:
            if "不可检索" in standard or "PDF图片" in standard:
                if "图片" not in pdf_text and "不可复制" not in pdf_text:
                    score = full_score
                else:
                    problem = "内容为图片格式，不可检索"
        elif "数据一致性" in indicator_name:
            if "无矛盾" in standard:
                if "不一致" not in pdf_text and "矛盾" not in pdf_text:
                    score = full_score
                else:
                    problem = "存在数据不一致情况"

        # 记录当前指标评分结果
        score_results.append({
            "单位名称": unit_name,
            "维度": indicator["维度"],
            "评分指标": indicator_name,
            "分值": full_score,
            "评分标准": standard,
            "评分结果": score,
            "问题记录": problem if problem else "无"
        })

        # 汇总问题（仅记录有问题的指标）
        if problem:
            total_problems.append(f"{indicator_name}：{problem}")

    return unit_name, score_results, " | ".join(total_problems) if total_problems else "无"

# ===================== 步骤3：批量评分+生成最终Excel =====================
def batch_score():
    # 1. 加载新评价指标表
    indicator_list = load_new_indicators()
    print(f"✅ 成功加载新评价指标：共{len(indicator_list)}项")

    # 2. 检查PDF文件夹是否存在
    if not os.path.exists(PDF_FOLDER):
        print(f"❌ PDF文件夹不存在：{PDF_FOLDER}")
        return

    # 3. 遍历所有PDF文件，批量评分
    all_score_results = []  # 存储所有单位的指标级评分结果
    summary_results = []    # 存储单位级总分汇总

    for filename in os.listdir(PDF_FOLDER):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(PDF_FOLDER, filename)
            print(f"\n🔍 正在处理：{filename}")
            
            # 单个PDF评分
            unit_name, unit_score_results, problems = score_pdf_by_new_indicator(pdf_path, indicator_list)
            
            # 记录指标级结果
            all_score_results.extend(unit_score_results)
            
            # 计算单位总分（所有指标得分之和）
            unit_total = sum([res["评分结果"] for res in unit_score_results])
            # 记录单位级汇总
            summary_results.append({
                "单位名称": unit_name,
                "总分": round(unit_total, 2),
                "问题记录": problems,
                "PDF文件名": filename
            })
            
            print(f"✅ {unit_name} 评分完成 | 总分：{unit_total} | 问题：{problems}")

    # 4. 生成最终Excel（包含2张表：指标级明细、单位级汇总）
    # 表1：指标级明细（你要求的格式）
    df_detail = pd.DataFrame(all_score_results)
    # 表2：单位级汇总（方便快速查看总分）
    df_summary = pd.DataFrame(summary_results)

    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        df_detail.to_excel(writer, sheet_name="指标级评分明细", index=False)
        df_summary.to_excel(writer, sheet_name="单位级总分汇总", index=False)
        # 同时写入原始评价指标表，方便对照
        pd.read_excel(INDICATOR_FILE).to_excel(writer, sheet_name="原始评价指标", index=False)

    print(f"\n🎉 全部处理完成！结果已保存至：\n{OUTPUT_EXCEL}")
    print(f"📊 统计：共处理{len(summary_results)}个单位，{len(indicator_list)}项指标")

# ===================== 启动批量评分 =====================
if __name__ == "__main__":
    batch_score()