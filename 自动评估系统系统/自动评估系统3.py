import pdfplumber
import pandas as pd
import os
import re

# ===================== 固定路径配置 =====================
PDF_FOLDER      = r"D:\预决算"
OUTPUT_EXCEL    = r"D:\预决算_定制规则版_评分结果.xlsx"

# ===================== 固定1-32号指标表 =====================
FULL_INDICATORS = [
    # 【及时性 10分】1-3号
    {"序号":1, "维度":"及时性", "指标名":"公开时限合规性", "满分":6},
    {"序号":2, "维度":"及时性", "指标名":"集中公开情况", "满分":2},
    {"序号":3, "维度":"及时性", "指标名":"年度完成时间", "满分":2},
    # 【完整性 35分】4-13号
    {"序号":4, "维度":"完整性", "指标名":"四本预算公开完整性", "满分":5},
    {"序号":5, "维度":"完整性", "指标名":"收支内容完整性", "满分":5},
    {"序号":6, "维度":"完整性", "指标名":"所属单位公开覆盖率", "满分":4},
    {"序号":7, "维度":"完整性", "指标名":"三公经费公开完整性", "满分":4},
    {"序号":8, "维度":"完整性", "指标名":"机关运行经费公开", "满分":3},
    {"序号":9, "维度":"完整性", "指标名":"政府采购信息公开", "满分":3},
    {"序号":10, "维度":"完整性", "指标名":"国有资产信息公开", "满分":3},
    {"序号":11, "维度":"完整性", "指标名":"专项资金信息公开", "满分":3},
    {"序号":12, "维度":"完整性", "指标名":"绩效信息公开", "满分":3},
    {"序号":13, "维度":"完整性", "指标名":"重点事项说明完整性", "满分":2},
    # 【细化程度 30分】14-22号
    {"序号":14, "维度":"细化程度", "指标名":"支出功能分类细化程度", "满分":5},
    {"序号":15, "维度":"细化程度", "指标名":"基本支出经济分类细化程度", "满分":5},
    {"序号":16, "维度":"细化程度", "指标名":"三公经费明细细化程度", "满分":4},
    {"序号":17, "维度":"细化程度", "指标名":"项目支出细化程度", "满分":4},
    {"序号":18, "维度":"细化程度", "指标名":"绩效指标细化程度", "满分":3},
    {"序号":19, "维度":"细化程度", "指标名":"收支差异说明细化程度", "满分":3},
    {"序号":20, "维度":"细化程度", "指标名":"三公经费变动说明细化程度", "满分":2},
    {"序号":21, "维度":"细化程度", "指标名":"空白项说明完整性", "满分":2},
    {"序号":22, "维度":"细化程度", "指标名":"民生项目信息细化程度", "满分":2},
    # 【规范性 25分】23-32号
    {"序号":23, "维度":"规范性", "指标名":"公开位置规范性", "满分":4},
    {"序号":24, "维度":"规范性", "指标名":"统一平台同步公开", "满分":3},
    {"序号":25, "维度":"规范性", "指标名":"公开格式规范性", "满分":3},
    {"序号":26, "维度":"规范性", "指标名":"内容可检索性", "满分":2},
    {"序号":27, "维度":"规范性", "指标名":"数据一致性", "满分":4},
    {"序号":28, "维度":"规范性", "指标名":"数据勾稽关系正确性", "满分":3},
    {"序号":29, "维度":"规范性", "指标名":"涉密内容处理规范性", "满分":2},
    {"序号":30, "维度":"规范性", "指标名":"信息长期留存", "满分":1},
    {"序号":31, "维度":"规范性", "指标名":"名称规范性", "满分":2},
    {"序号":32, "维度":"规范性", "指标名":"版本一致性", "满分":1},
]

# 固定列顺序（严格按要求，总分放最后）
ITEM_COLUMNS = [f"{i['序号']}.{i['指标名']}" for i in FULL_INDICATORS]
FINAL_HEADER = [
    "单位名称", "及时性总分", "完整性总分", "细化程度总分", "规范性总分"
] + ITEM_COLUMNS + ["问题记录", "评估总分"]

# ===================== 辅助函数：统计项目数量 =====================
# 统计项目支出表的项目数量
def count_project_items(full_text):
    """匹配支出预算表/项目支出表的项目名称，统计数量"""
    # 适配江西预决算PDF的项目行格式：科目编码+项目名称、项目支出明细行
    project_patterns = [
        r"\d{6}\s+[\u4e00-\u9fa5]+",  # 6位科目编码+中文项目名
        r"项目名称\s*[:：]\s*[\u4e00-\u9fa5]+",
        r"[2][0][1]\d\s+[\u4e00-\u9fa5]+支出",
        r"[项级科目|功能科目]\s*[:：]\s*[\u4e00-\u9fa5]+"
    ]
    project_count = 0
    for pattern in project_patterns:
        matches = re.findall(pattern, full_text)
        project_count += len(matches)
    # 去重+保底，避免重复统计
    project_count = min(max(project_count, 0), 20)
    return project_count

# 统计绩效表的项目数量
def count_perf_projects(full_text):
    """匹配绩效目标表/项目绩效表的项目名称，统计数量"""
    perf_patterns = [
        r"项目名称\s*[:：]\s*[\u4e00-\u9fa5]+",
        r"绩效目标表\s*[\u4e00-\u9fa5]+项目",
        r"项目支出绩效\s*[:：]\s*[\u4e00-\u9fa5]+"
    ]
    perf_count = 0
    for pattern in perf_patterns:
        matches = re.findall(pattern, full_text)
        perf_count += len(matches)
    perf_count = min(max(perf_count, 0), 20)
    return perf_count

# 统计绩效项目的说明完整度
def count_perf_note(full_text, perf_total):
    """统计有目标/原因说明的绩效项目数量"""
    note_patterns = [
        r"项目目标\s*[:：]\s*[\u4e00-\u9fa5]+",
        r"差异原因\s*[:：]\s*[\u4e00-\u9fa5]+",
        r"完成情况说明\s*[:：]\s*[\u4e00-\u9fa5]+"
    ]
    note_count = 0
    for pattern in note_patterns:
        matches = re.findall(pattern, full_text)
        note_count += len(matches)
    # 说明数量不超过项目总数
    note_count = min(note_count, perf_total)
    return note_count

# ===================== 核心评分函数 =====================
def score_pdf(pdf_path):
    # 1. 提取PDF文本
    try:
        full_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text
        text_lower = full_text.lower()
        is_searchable = len(full_text.strip()) > 100
    except Exception as e:
        return os.path.basename(pdf_path).replace(".pdf",""), {}, 0,0,0,0,0, [f"PDF读取失败：{str(e)}"]

    # 2. 识别单位名称
    unit_name = os.path.basename(pdf_path).replace(".pdf","")
    if "江西省" in full_text and ("厅" in full_text or "局" in full_text):
        for keyword in ["财政厅", "教育厅", "发改委", "水利厅", "农业农村厅", "卫健委", "住建厅"]:
            if keyword in full_text:
                unit_name = f"江西省{keyword}"
                break

    # 3. 预统计核心数据（用于17/18/19号指标）
    project_count = count_project_items(full_text)       # 17号用：项目支出数量
    perf_count = count_perf_projects(full_text)          # 18号用：绩效项目数量
    perf_note_count = count_perf_note(full_text, perf_count) # 19号用：有说明的绩效项目数

    # 4. 初始化：默认满分，仅违规扣分
    item_scores = {}
    problems = []
    dim_totals = {"及时性":0, "完整性":0, "细化程度":0, "规范性":0}

    for ind in FULL_INDICATORS:
        idx = ind["序号"]
        dim = ind["维度"]
        name = ind["指标名"]
        full_score = ind["满分"]
        score = full_score

        # ============== 逐项精准评分 ==============
        # 1-3号：及时性，无法判断默认满分
        if idx in [1,2,3]:
            pass

        # 4号：四本预算完整性
        elif idx == 4:
            required = ["一般公共预算", "政府性基金预算", "国有资本经营预算", "社会保险基金预算"]
            missing = [b for b in required if b not in full_text]
            if missing:
                deduct = 1.25 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：缺{','.join(missing)}，扣{deduct}分")

        # 5号：收支内容完整性
        elif idx == 5:
            required = ["财政拨款", "事业收入", "国有资产收益", "非本级财政拨款"]
            missing = [i for i in required if i.lower() not in text_lower]
            if missing:
                deduct = 1 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：缺{','.join(missing)}收支，扣{deduct}分")

        # 6号：所属单位覆盖率
        elif idx == 6:
            if "未全部公开" in full_text:
                score = 0
                problems.append(f"{idx}.{name}：所属单位未100%公开，扣{full_score}分")

        # 7/16/20号：三公相关，含“三公”即满分
        elif idx in [7,16,20]:
            if "三公" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：未提及三公经费，扣{full_score}分")

        # 8号：机关运行经费
        elif idx == 8:
            if "机关运行经费" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：未公开机关运行经费，扣{full_score}分")
            elif "明细" not in full_text:
                score = 1
                problems.append(f"{idx}.{name}：仅公开总额，扣2分")

        # 9号：政府采购
        elif idx == 9:
            required = ["采购预算", "中标结果", "采购合同", "政策落实"]
            missing = [i for i in required if i.lower() not in text_lower]
            if missing:
                deduct = 1 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：缺{','.join(missing)}，扣{deduct}分")

        # 10号：国有资产
        elif idx == 10:
            if "国有资产" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：未公开国有资产信息，扣{full_score}分")
            elif "变动说明" not in full_text:
                score = 1
                problems.append(f"{idx}.{name}：仅公开总额，扣2分")

        # 11号：专项资金
        elif idx == 11:
            required = ["分配结果", "使用情况", "绩效信息"]
            missing = [i for i in required if i.lower() not in text_lower]
            if missing:
                deduct = 1 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：缺{','.join(missing)}，扣{deduct}分")

        # 12号：绩效信息
        elif idx == 12:
            required = ["绩效目标", "完成情况", "评价结果"]
            missing = [i for i in required if i.lower() not in text_lower]
            if missing:
                deduct = 1 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：缺{','.join(missing)}，扣{deduct}分")

        # 13号：重点事项说明
        elif idx == 13:
            required = ["收支增减", "三公经费变动", "债务情况", "重大项目"]
            missing = [i for i in required if i.lower() not in text_lower]
            if missing:
                deduct = 0.5 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：缺{','.join(missing)}说明，扣{deduct}分")

        # 14号：功能分类细化
        elif idx == 14:
            if "项级" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：未细化到项级，扣{full_score}分")

        # 15号：经济分类细化
        elif idx == 15:
            if "款级" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：未细化到款级，扣{full_score}分")

        # 17号：项目支出细化程度（定制规则）
        elif idx == 17:
            if project_count >= 10:
                score = full_score
            else:
                deduct_rate = (10 - project_count) * 0.1
                deduct = full_score * deduct_rate
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：项目数量{project_count}个，不足10个，扣{deduct_rate*100}%，扣{round(deduct,2)}分")

        # 18号：绩效指标细化程度（定制规则）
        elif idx == 18:
            if perf_count >= 10:
                score = full_score
            else:
                deduct_rate = (10 - perf_count) * 0.1
                deduct = full_score * deduct_rate
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：绩效项目数量{perf_count}个，不足10个，扣{deduct_rate*100}%，扣{round(deduct,2)}分")

        # 19号：收支差异说明细化程度（定制规则）
        elif idx == 19:
            if perf_count == 0:
                score = 0
                problems.append(f"{idx}.{name}：未找到绩效项目，扣{full_score}分")
            else:
                missing_count = perf_count - perf_note_count
                if missing_count > 0:
                    deduct = missing_count * 0.5
                    score = max(full_score - deduct, 0)
                    problems.append(f"{idx}.{name}：共{perf_count}个项目，{missing_count}个未说明原因，扣{round(deduct,2)}分")

        # 21号：空白项说明
        elif idx == 21:
            if "无此项" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：空白项未标注说明，扣{full_score}分")

        # 22号：民生项目细化
        elif idx == 22:
            required = ["受益对象", "补助标准", "发放情况"]
            missing = [i for i in required if i.lower() not in text_lower]
            if missing:
                deduct = 0.7 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{idx}.{name}：缺{','.join(missing)}，扣{deduct}分")

        # 26号：内容可检索性
        elif idx == 26:
            if not is_searchable:
                score = 0
                problems.append(f"{idx}.{name}：内容不可检索，扣{full_score}分")

        # 27号：数据一致性
        elif idx == 27:
            if "与批复不符" in full_text:
                score = 0
                problems.append(f"{idx}.{name}：数据与批复不一致，扣{full_score}分")

        # 28号：勾稽关系
        elif idx == 28:
            if "数据矛盾" in full_text:
                score = 0
                problems.append(f"{idx}.{name}：数据勾稽关系矛盾，扣{full_score}分")

        # 29号：涉密处理
        elif idx == 29:
            if "豁免公开" in full_text and "法定依据" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：豁免内容未说明依据，扣{full_score}分")

        # 31号：名称规范性
        elif idx == 31:
            if "预决算公开" not in full_text:
                score = 0
                problems.append(f"{idx}.{name}：文件名称不规范，扣{full_score}分")

        # 23/24/25/30/32号：无法从PDF判断，默认满分
        else:
            pass

        # 保存得分，累加维度总分
        item_scores[f"{idx}.{name}"] = round(score, 2)
        dim_totals[dim] += score

    # 5. 计算最终总分
    total_score = round(sum(dim_totals.values()), 2)
    problem_str = " | ".join(problems) if problems else "无"

    return unit_name, item_scores, round(dim_totals["及时性"],2), round(dim_totals["完整性"],2), round(dim_totals["细化程度"],2), round(dim_totals["规范性"],2), total_score, problem_str

# ===================== 批量执行 =====================
def run_batch():
    print(f"📂 读取PDF文件夹：{PDF_FOLDER}")
    if not os.path.exists(PDF_FOLDER):
        print(f"❌ 错误：文件夹不存在，请确认路径 {PDF_FOLDER}")
        return

    all_results = []
    for filename in os.listdir(PDF_FOLDER):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(PDF_FOLDER, filename)
            print(f"\n🔍 正在评分：{filename}")

            unit_name, item_scores, timely, complete, detail, normal, total, problem = score_pdf(pdf_path)
            # 构建固定顺序的行
            row = {
                "单位名称": unit_name,
                "及时性总分": timely,
                "完整性总分": complete,
                "细化程度总分": detail,
                "规范性总分": normal
            }
            row.update(item_scores)
            row["问题记录"] = problem
            row["评估总分"] = total

            all_results.append(row)
            print(f"✅ {unit_name} | 评估总分：{total}")

    # 导出Excel，强制固定列顺序
    df_result = pd.DataFrame(all_results)
    df_result = df_result[FINAL_HEADER]
    df_result.to_excel(OUTPUT_EXCEL, index=False, engine="openpyxl")
    print(f"\n🎉 全部评分完成！结果已保存至：\n{OUTPUT_EXCEL}")

# 一键启动
if __name__ == "__main__":
    run_batch()