import pdfplumber
import pandas as pd
import os

# ===================== 固定路径配置（和你之前的路径完全一致）=====================
PDF_FOLDER      = r"D:\预决算"
OUTPUT_EXCEL    = r"D:\预决算_最终优化版_评分结果.xlsx"

# ===================== 【固定1-32序号】100%匹配你的指标表 =====================
# 严格按你表格的序号、维度、分值、规则排序，绝不乱序
FULL_INDICATORS = [
    # 【及时性维度 10分】1-3号
    {"序号":1, "维度":"及时性", "指标名":"公开时限合规性", "满分":6, "规则":"财政批复后20日内公开，无法判断默认满分"},
    {"序号":2, "维度":"及时性", "指标名":"集中公开情况", "满分":2, "规则":"按要求集中公开，无法判断默认满分"},
    {"序号":3, "维度":"及时性", "指标名":"年度完成时间", "满分":2, "规则":"10月31日前完成，无法判断默认满分"},
    # 【完整性维度 35分】4-13号
    {"序号":4, "维度":"完整性", "指标名":"四本预算公开完整性", "满分":5, "规则":"4本全公开得5分，每缺1本扣1.25分"},
    {"序号":5, "维度":"完整性", "指标名":"收支内容完整性", "满分":5, "规则":"全收支公开得5分，每缺1类扣1分"},
    {"序号":6, "维度":"完整性", "指标名":"所属单位公开覆盖率", "满分":4, "规则":"100%公开得4分，无法判断默认满分"},
    {"序号":7, "维度":"完整性", "指标名":"三公经费公开完整性", "满分":4, "规则":"含“三公”二字即得满分，缺分项扣1分"},
    {"序号":8, "维度":"完整性", "指标名":"机关运行经费公开", "满分":3, "规则":"总额+明细全公开得3分，仅总额得1分，未公开0分"},
    {"序号":9, "维度":"完整性", "指标名":"政府采购信息公开", "满分":3, "规则":"4项全公开得3分，每缺1项扣1分"},
    {"序号":10, "维度":"完整性", "指标名":"国有资产信息公开", "满分":3, "规则":"占用+变动说明全公开得3分，仅总额得1分，未公开0分"},
    {"序号":11, "维度":"完整性", "指标名":"专项资金信息公开", "满分":3, "规则":"3项全公开得3分，每缺1项扣1分"},
    {"序号":12, "维度":"完整性", "指标名":"绩效信息公开", "满分":3, "规则":"3项全公开得3分，每缺1项扣1分"},
    {"序号":13, "维度":"完整性", "指标名":"重点事项说明完整性", "满分":2, "规则":"4项说明全包含得2分，每缺1项扣0.5分"},
    # 【细化程度维度 30分】14-22号
    {"序号":14, "维度":"细化程度", "指标名":"支出功能分类细化程度", "满分":5, "规则":"100%到项级得5分，每低10%扣0.5分"},
    {"序号":15, "维度":"细化程度", "指标名":"基本支出经济分类细化程度", "满分":5, "规则":"100%到款级得5分，每低10%扣0.5分"},
    {"序号":16, "维度":"细化程度", "指标名":"三公经费明细细化程度", "满分":4, "规则":"含“三公”二字即得满分，缺明细扣1分"},
    {"序号":17, "维度":"细化程度", "指标名":"项目支出细化程度", "满分":4, "规则":"100%细化得4分，每低10%扣0.4分"},
    {"序号":18, "维度":"细化程度", "指标名":"绩效指标细化程度", "满分":3, "规则":"全部量化得3分，部分量化得1分，全定性0分"},
    {"序号":19, "维度":"细化程度", "指标名":"收支差异说明细化程度", "满分":3, "规则":"超10%差异全说明得3分，每缺1项扣0.5分"},
    {"序号":20, "维度":"细化程度", "指标名":"三公经费变动说明细化程度", "满分":2, "规则":"含“三公”二字即得满分，说明不完整0分"},
    {"序号":21, "维度":"细化程度", "指标名":"空白项说明完整性", "满分":2, "规则":"空白项全标注得2分，无法判断默认满分"},
    {"序号":22, "维度":"细化程度", "指标名":"民生项目信息细化程度", "满分":2, "规则":"3项全公开得2分，每缺1项扣0.7分"},
    # 【公开规范性维度 25分】23-32号
    {"序号":23, "维度":"规范性", "指标名":"公开位置规范性", "满分":4, "规则":"无法从PDF判断，默认满分"},
    {"序号":24, "维度":"规范性", "指标名":"统一平台同步公开", "满分":3, "规则":"无法从PDF判断，默认满分"},
    {"序号":25, "维度":"规范性", "指标名":"公开格式规范性", "满分":3, "规则":"采用统一模板得3分，无法判断默认满分"},
    {"序号":26, "维度":"规范性", "指标名":"内容可检索性", "满分":2, "规则":"PDF可提取文本即得满分，图片格式0分"},
    {"序号":27, "维度":"规范性", "指标名":"数据一致性", "满分":4, "规则":"无明确不一致即得满分，每1处错误扣1分"},
    {"序号":28, "维度":"规范性", "指标名":"数据勾稽关系正确性", "满分":3, "规则":"无明确矛盾即得满分，每1处错误扣1分"},
    {"序号":29, "维度":"规范性", "指标名":"涉密内容处理规范性", "满分":2, "规则":"无豁免内容即得满分，未说明依据0分"},
    {"序号":30, "维度":"规范性", "指标名":"信息长期留存", "满分":1, "规则":"无法从PDF判断，默认满分"},
    {"序号":31, "维度":"规范性", "指标名":"名称规范性", "满分":2, "规则":"标题含规范名称得2分，无法判断默认满分"},
    {"序号":32, "维度":"规范性", "指标名":"版本一致性", "满分":1, "规则":"无法从PDF判断，默认满分"},
]

# 固定1-32号指标的列名，确保顺序完全不乱
ITEM_COLUMNS = [f"{i['序号']}.{i['指标名']}" for i in FULL_INDICATORS]
# 固定Excel表头顺序（严格按你的要求）
FINAL_HEADER = [
    "单位名称", "及时性总分", "完整性总分", "细化程度总分", "规范性总分"
] + ITEM_COLUMNS + ["问题记录", "评估总分"]

# ===================== 【核心优化】精准评分函数（贴合指标深意+默认满分）=====================
def accurate_score_pdf(pdf_path):
    # 1. 提取PDF全文本，判断是否可检索
    try:
        full_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text
        text_lower = full_text.lower()
        # 可检索性判断：能提取到文本即为可检索
        is_searchable = len(full_text.strip()) > 100
    except Exception as e:
        return os.path.basename(pdf_path).replace(".pdf",""), {}, 0,0,0,0,0, [f"PDF读取失败：{str(e)}"]

    # 2. 识别单位名称（优先从文本提取，兜底用文件名）
    unit_name = os.path.basename(pdf_path).replace(".pdf","")
    if "江西省" in full_text and ("厅" in full_text or "局" in full_text or "委员会" in full_text):
        for keyword in ["财政厅", "教育厅", "发改委", "水利厅", "农业农村厅", "卫健委", "住建厅", "交通厅", "审计厅"]:
            if keyword in full_text:
                unit_name = f"江西省{keyword}"
                break

    # 3. 初始化：所有指标默认满分，仅违规才扣分
    item_scores = {}
    problems = []
    dim_totals = {"及时性":0, "完整性":0, "细化程度":0, "规范性":0}

    for ind in FULL_INDICATORS:
        idx = ind["序号"]
        dim = ind["维度"]
        name = ind["指标名"]
        full_score = ind["满分"]
        score = full_score  # 核心优化：默认满分，仅实锤违规才扣分

        # ============== 【逐项贴合指标深意 精准判断】 ==============
        # 1-3号：及时性指标，无法判断直接给满分，绝不扣分
        if idx in [1,2,3]:
            pass  # 直接保留满分，无实锤逾期不扣分

        # 4号：四本预算公开完整性（缺1本扣1.25分，最低0分）
        elif idx == 4:
            required_budgets = ["一般公共预算", "政府性基金预算", "国有资本经营预算", "社会保险基金预算"]
            missing = [b for b in required_budgets if b not in full_text]
            if missing:
                deduct = 1.25 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：缺{','.join(missing)}，扣{deduct}分")

        # 5号：收支内容完整性（缺1类扣1分）
        elif idx == 5:
            required_income = ["财政拨款", "事业收入", "国有资产收益", "非本级财政拨款"]
            missing = [i for i in required_income if i.lower() not in text_lower]
            if missing:
                deduct = 1 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：缺{','.join(missing)}收支，扣{deduct}分")

        # 6号：所属单位公开覆盖率（无法判断默认满分）
        elif idx == 6:
            if "未全部公开" in full_text or "覆盖率不足" in full_text:
                score = 0
                problems.append(f"{idx}.{name}：所属单位未100%公开，扣{full_score}分")

        # 7/16/20号：三公相关指标，含“三公”二字直接给满分
        elif idx in [7,16,20]:
            if "三公" not in full_text and "三公" not in text_lower:
                score = 0
                problems.append(f"{idx}.{name}：未提及三公经费相关内容，扣{full_score}分")

        # 8号：机关运行经费公开
        elif idx == 8:
            if "机关运行经费" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：未公开机关运行经费，扣{full_score}分")
            elif "明细" not in full_text:
                score = 1
                problems.append(f"{idx}.{name}：仅公开总额，未公开明细，扣2分")

        # 9号：政府采购信息公开
        elif idx == 9:
            required_procure = ["采购预算", "中标结果", "采购合同", "政策落实"]
            missing = [i for i in required_procure if i.lower() not in text_lower]
            if missing:
                deduct = 1 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：缺{','.join(missing)}，扣{deduct}分")

        # 10号：国有资产信息公开
        elif idx == 10:
            if "国有资产" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：未公开国有资产信息，扣{full_score}分")
            elif "变动说明" not in full_text:
                score = 1
                problems.append(f"{idx}.{name}：仅公开总额，未公开变动说明，扣2分")

        # 11号：专项资金信息公开
        elif idx == 11:
            required_fund = ["分配结果", "使用情况", "绩效信息"]
            missing = [i for i in required_fund if i.lower() not in text_lower]
            if missing:
                deduct = 1 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：缺{','.join(missing)}，扣{deduct}分")

        # 12号：绩效信息公开
        elif idx == 12:
            required_perf = ["绩效目标", "完成情况", "评价结果"]
            missing = [i for i in required_perf if i.lower() not in text_lower]
            if missing:
                deduct = 1 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：缺{','.join(missing)}，扣{deduct}分")

        # 13号：重点事项说明完整性（每缺1项扣0.5分）
        elif idx == 13:
            required_note = ["收支增减", "三公经费变动", "债务情况", "重大项目"]
            missing = [i for i in required_note if i.lower() not in text_lower]
            if missing:
                deduct = 0.5 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：缺{','.join(missing)}说明，扣{deduct}分")

        # 14号：支出功能分类细化程度
        elif idx == 14:
            if "项级" not in full_text and "类款项" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：未明确细化到功能分类项级，扣{full_score}分")

        # 15号：基本支出经济分类细化程度
        elif idx == 15:
            if "款级" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：未明确细化到经济分类款级，扣{full_score}分")

        # 17号：项目支出细化程度
        elif idx == 17:
            required_project = ["项目内容", "实施主体", "年度计划"]
            missing = [i for i in required_project if i.lower() not in text_lower]
            if missing:
                score = 0
                problems.append(f"{idx}.{name}：未细化到具体项目信息，扣{full_score}分")

        # 18号：绩效指标细化程度
        elif idx == 18:
            if "具体指标值" not in full_text and "完成值" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：绩效指标未量化，扣{full_score}分")
            elif "部分量化" in full_text:
                score = 1
                problems.append(f"{idx}.{name}：绩效指标仅部分量化，扣2分")

        # 19号：收支差异说明细化程度
        elif idx == 19:
            if "差异超过10%" not in full_text and "差异原因" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：未说明预决算差异原因，扣{full_score}分")

        # 21号：空白项说明完整性（无明确违规默认满分）
        elif idx == 21:
            if "空白项未说明" in full_text:
                score = 0
                problems.append(f"{idx}.{name}：空白项未标注说明，扣{full_score}分")

        # 22号：民生项目信息细化程度（每缺1项扣0.7分）
        elif idx == 22:
            required_people = ["受益对象", "补助标准", "发放情况"]
            missing = [i for i in required_people if i.lower() not in text_lower]
            if missing:
                deduct = 0.7 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：缺{','.join(missing)}，扣{deduct}分")

        # 26号：内容可检索性
        elif idx == 26:
            if not is_searchable:
                score = 0
                problems.append(f"{idx}.{name}：内容为图片格式，无法检索，扣{full_score}分")

        # 27号：数据一致性
        elif idx == 27:
            if "数据不一致" in full_text or "与批复不符" in full_text:
                score = 0
                problems.append(f"{idx}.{name}：存在数据与批复不一致，扣{full_score}分")

        # 28号：数据勾稽关系正确性
        elif idx == 28:
            if "数据矛盾" in full_text or "勾稽不符" in full_text:
                score = 0
                problems.append(f"{idx}.{name}：存在数据勾稽关系矛盾，扣{full_score}分")

        # 29号：涉密内容处理规范性
        elif idx == 29:
            if "豁免公开" in full_text and "法定依据" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：豁免公开内容未说明法定依据，扣{full_score}分")

        # 31号：名称规范性
        elif idx == 31:
            if "年度" not in full_text and "预决算公开" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：文件标题名称不规范，扣{full_score}分")

        # 23/24/25/30/32号：无法从PDF判断的指标，默认满分，不做处理

        # 保存得分，累加维度总分
        item_scores[f"{idx}.{name}"] = round(score, 2)
        dim_totals[dim] += score

    # 4. 计算最终总分（4个维度之和）
    total_score = round(sum(dim_totals.values()), 2)
    # 5. 整理问题记录
    problem_str = " | ".join(problems) if problems else "无"

    return unit_name, item_scores, round(dim_totals["及时性"],2), round(dim_totals["完整性"],2), round(dim_totals["细化程度"],2), round(dim_totals["规范性"],2), total_score, problem_str

# ===================== 批量处理PDF + 生成规范Excel =====================
def run_batch():
    print(f"📂 读取PDF文件夹：{PDF_FOLDER}")
    if not os.path.exists(PDF_FOLDER):
        print(f"❌ 错误：文件夹不存在，请确认路径 {PDF_FOLDER}")
        return

    all_results = []
    # 遍历所有PDF文件
    for filename in os.listdir(PDF_FOLDER):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(PDF_FOLDER, filename)
            print(f"\n🔍 正在评分：{filename}")

            # 执行精准评分
            unit_name, item_scores, timely, complete, detail, normal, total, problem = accurate_score_pdf(pdf_path)

            # 严格按固定表头构建行数据
            row = {
                "单位名称": unit_name,
                "及时性总分": timely,
                "完整性总分": complete,
                "细化程度总分": detail,
                "规范性总分": normal
            }
            # 追加1-32号指标得分（顺序完全固定）
            row.update(item_scores)
            # 追加问题记录和评估总分（总分放最后一列）
            row["问题记录"] = problem
            row["评估总分"] = total

            all_results.append(row)
            print(f"✅ {unit_name} | 评估总分：{total}")

    # 导出Excel，严格按固定表头顺序
    df_result = pd.DataFrame(all_results)
    df_result = df_result[FINAL_HEADER]  # 强制锁定列顺序，绝不乱序
    df_result.to_excel(OUTPUT_EXCEL, index=False, engine="openpyxl")
    print(f"\n🎉 全部评分完成！结果已保存至：\n{OUTPUT_EXCEL}")

# ===================== 一键启动 =====================
if __name__ == "__main__":
    run_batch()