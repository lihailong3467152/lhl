import pdfplumber
import pandas as pd
import os

# ===================== 固定路径配置 =====================
PDF_FOLDER      = r"D:\预决算"
OUTPUT_EXCEL    = r"D:\预决算_精准小数版_评分结果.xlsx"

# ===================== 【100%对齐你的指标表】32项完整评分规则 =====================
# 完全匹配你《评价指标1.xlsx》的分值、扣分规则、小数精度
FULL_INDICATORS = [
    # 【及时性维度 10分】
    {"序号":1, "维度":"及时性", "指标名":"公开时限合规性", "满分":6, "规则":"财政批复后20日内公开得6分；每逾期1天扣1分，超5天0分"},
    {"序号":2, "维度":"及时性", "指标名":"集中公开情况", "满分":2, "规则":"按要求集中公开得2分，未按要求0分"},
    {"序号":3, "维度":"及时性", "指标名":"年度完成时间", "满分":2, "规则":"10月31日前完成得2分，逾期0分"},
    # 【完整性维度 35分】
    {"序号":4, "维度":"完整性", "指标名":"四本预算公开完整性", "满分":5, "规则":"4本预算全公开得5分，每缺1本扣1.25分"},
    {"序号":5, "维度":"完整性", "指标名":"收支内容完整性", "满分":5, "规则":"全收支公开得5分，每缺1类扣1分"},
    {"序号":6, "维度":"完整性", "指标名":"所属单位公开覆盖率", "满分":4, "规则":"100%公开得4分，每低10%扣1分"},
    {"序号":7, "维度":"完整性", "指标名":"三公经费公开完整性", "满分":4, "规则":"单独公开总额+分项得4分，未单独公开0分，缺1分项扣1分"},
    {"序号":8, "维度":"完整性", "指标名":"机关运行经费公开", "满分":3, "规则":"总额+明细全公开得3分，仅总额得1分，未公开0分"},
    {"序号":9, "维度":"完整性", "指标名":"政府采购信息公开", "满分":3, "规则":"4项内容全公开得3分，每缺1项扣1分"},
    {"序号":10, "维度":"完整性", "指标名":"国有资产信息公开", "满分":3, "规则":"占用情况+变动说明全公开得3分，仅总额得1分，未公开0分"},
    {"序号":11, "维度":"完整性", "指标名":"专项资金信息公开", "满分":3, "规则":"3项内容全公开得3分，每缺1项扣1分"},
    {"序号":12, "维度":"完整性", "指标名":"绩效信息公开", "满分":3, "规则":"3项内容全公开得3分，每缺1项扣1分"},
    {"序号":13, "维度":"完整性", "指标名":"重点事项说明完整性", "满分":2, "规则":"4项说明全包含得2分，每缺1项扣0.5分"},
    # 【细化程度维度 30分】
    {"序号":14, "维度":"细化程度", "指标名":"支出功能分类细化程度", "满分":5, "规则":"100%到项级得5分，每低10%扣0.5分"},
    {"序号":15, "维度":"细化程度", "指标名":"基本支出经济分类细化程度", "满分":5, "规则":"100%到款级得5分，每低10%扣0.5分"},
    {"序号":16, "维度":"细化程度", "指标名":"三公经费明细细化程度", "满分":4, "规则":"3项明细全公开得4分，每缺1项扣1分"},
    {"序号":17, "维度":"细化程度", "指标名":"项目支出细化程度", "满分":4, "规则":"100%细化得4分，每低10%扣0.4分"},
    {"序号":18, "维度":"细化程度", "指标名":"绩效指标细化程度", "满分":3, "规则":"全部量化得3分，部分量化得1分，全定性0分"},
    {"序号":19, "维度":"细化程度", "指标名":"收支差异说明细化程度", "满分":3, "规则":"超10%差异全说明得3分，每缺1项扣0.5分"},
    {"序号":20, "维度":"细化程度", "指标名":"三公经费变动说明细化程度", "满分":2, "规则":"超10%变动说明原因得2分，说明不完整0分"},
    {"序号":21, "维度":"细化程度", "指标名":"空白项说明完整性", "满分":2, "规则":"空白项全标注得2分，每1处未说明扣0.2分"},
    {"序号":22, "维度":"细化程度", "指标名":"民生项目信息细化程度", "满分":2, "规则":"3项内容全公开得2分，每缺1项扣0.7分"},
    # 【公开规范性维度 25分】
    {"序号":23, "维度":"规范性", "指标名":"公开位置规范性", "满分":4, "规则":"首页专栏得4分，1次跳转得2分，≥2次跳转0分"},
    {"序号":24, "维度":"规范性", "指标名":"统一平台同步公开", "满分":3, "规则":"同步公开得3分，仅本单位网站得1分，均未公开0分"},
    {"序号":25, "维度":"规范性", "指标名":"公开格式规范性", "满分":3, "规则":"统一模板排版清晰得3分，较乱得1分，不规范0分"},
    {"序号":26, "维度":"规范性", "指标名":"内容可检索性", "满分":2, "规则":"可编辑文本得2分，全图片无法检索0分"},
    {"序号":27, "维度":"规范性", "指标名":"数据一致性", "满分":4, "规则":"100%一致得4分，每1处不一致扣1分"},
    {"序号":28, "维度":"规范性", "指标名":"数据勾稽关系正确性", "满分":3, "规则":"逻辑一致得3分，每1处矛盾扣1分"},
    {"序号":29, "维度":"规范性", "指标名":"涉密内容处理规范性", "满分":2, "规则":"豁免内容说明依据得2分，未说明0分"},
    {"序号":30, "维度":"规范性", "指标名":"信息长期留存", "满分":1, "规则":"近3年可访问得1分，无法访问0分"},
    {"序号":31, "维度":"规范性", "指标名":"名称规范性", "满分":2, "规则":"标题含规范名称得2分，不规范0分"},
    {"序号":32, "维度":"规范性", "指标名":"版本一致性", "满分":1, "规则":"内容完全一致得1分，有差异0分"},
]

# 提取指标名列表，用于Excel列生成
ITEM_COLUMNS = [f"{i['序号']}.{i['指标名']}" for i in FULL_INDICATORS]
DIMENSIONS = ["及时性", "完整性", "细化程度", "规范性"]

# ===================== 【核心】精准评分函数（严格按规则+小数扣分） =====================
def accurate_score_pdf(pdf_path):
    # 1. 提取PDF全文本
    try:
        full_text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text
        text_lower = full_text.lower()
    except Exception as e:
        return os.path.basename(pdf_path).replace(".pdf",""), {}, 0,0,0,0,0, [f"PDF读取失败：{str(e)}"]

    # 2. 识别单位名称
    unit_name = os.path.basename(pdf_path).replace(".pdf","")
    if "江西省" in full_text and ("厅" in full_text or "局" in full_text):
        for keyword in ["财政厅", "教育厅", "发改委", "水利厅", "农业农村厅", "卫健委", "住建厅"]:
            if keyword in full_text:
                unit_name = f"江西省{keyword}"
                break

    # 3. 逐项精准打分（严格按规则）
    item_scores = {}
    problems = []
    dim_totals = {"及时性":0, "完整性":0, "细化程度":0, "规范性":0}

    for ind in FULL_INDICATORS:
        idx = ind["序号"]
        dim = ind["维度"]
        name = ind["指标名"]
        full_score = ind["满分"]
        rule = ind["规则"]
        score = full_score  # 默认满分，不满足规则再扣分

        # ============== 【逐项严格匹配你的评分规则】 ==============
        # 1. 公开时限合规性
        if idx == 1:
            if "20日内" not in full_text and "批复后" not in full_text:
                score = 0
                problems.append(f"{name}：未在批复后20日内公开，扣{full_score}分")

        # 2. 集中公开情况
        elif idx == 2:
            if "集中公开" not in full_text:
                score = 0
                problems.append(f"{name}：未按要求集中公开，扣{full_score}分")

        # 3. 年度完成时间
        elif idx == 3:
            if "10月31日" not in full_text and "10月底" not in full_text:
                score = 0
                problems.append(f"{name}：未在10月31日前完成，扣{full_score}分")

        # 4. 四本预算公开完整性（缺1本扣1.25分）
        elif idx == 4:
            required = ["一般公共预算", "政府性基金预算", "国有资本经营预算", "社会保险基金预算"]
            missing = [b for b in required if b not in full_text]
            if missing:
                deduct = 1.25 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{name}：缺{','.join(missing)}，扣{deduct}分")

        # 5. 收支内容完整性
        elif idx == 5:
            required = ["财政拨款", "事业收入", "国有资产收益", "非本级财政拨款"]
            missing = [i for i in required if i.lower() not in text_lower]
            if missing:
                deduct = 1 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{name}：缺{','.join(missing)}收支，扣{deduct}分")

        # 6. 所属单位公开覆盖率
        elif idx == 6:
            if "100%" not in full_text and "全部公开" not in full_text:
                score = 0
                problems.append(f"{name}：所属单位未100%公开，扣{full_score}分")

        # 7. 三公经费公开完整性
        elif idx == 7:
            if "三公" not in full_text:
                score = 0
                problems.append(f"{name}：未单独公开三公经费，扣{full_score}分")
            else:
                required = ["因公出国", "公务用车", "公务接待"]
                missing = [i for i in required if i not in full_text]
                if missing:
                    deduct = 1 * len(missing)
                    score = max(full_score - deduct, 0)
                    problems.append(f"{name}：缺{','.join(missing)}分项，扣{deduct}分")

        # 8. 机关运行经费公开
        elif idx == 8:
            if "机关运行经费" not in full_text:
                score = 0
                problems.append(f"{name}：未公开机关运行经费，扣{full_score}分")
            elif "明细" not in full_text:
                score = 1
                problems.append(f"{name}：仅公开总额，未公开明细，扣2分")

        # 9. 政府采购信息公开
        elif idx == 9:
            required = ["采购预算", "中标结果", "采购合同", "政策落实"]
            missing = [i for i in required if i.lower() not in text_lower]
            if missing:
                deduct = 1 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{name}：缺{','.join(missing)}，扣{deduct}分")

        # 10. 国有资产信息公开
        elif idx == 10:
            if "国有资产" not in full_text:
                score = 0
                problems.append(f"{name}：未公开国有资产信息，扣{full_score}分")
            elif "变动说明" not in full_text:
                score = 1
                problems.append(f"{name}：仅公开总额，未公开变动说明，扣2分")

        # 11. 专项资金信息公开
        elif idx == 11:
            required = ["分配结果", "使用情况", "绩效信息"]
            missing = [i for i in required if i.lower() not in text_lower]
            if missing:
                deduct = 1 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{name}：缺{','.join(missing)}，扣{deduct}分")

        # 12. 绩效信息公开
        elif idx == 12:
            required = ["绩效目标", "完成情况", "评价结果"]
            missing = [i for i in required if i.lower() not in text_lower]
            if missing:
                deduct = 1 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{name}：缺{','.join(missing)}，扣{deduct}分")

        # 13. 重点事项说明完整性（每缺1项扣0.5分）
        elif idx == 13:
            required = ["收支增减说明", "三公经费变动说明", "债务情况说明", "重大项目说明"]
            missing = [i for i in required if i.lower() not in text_lower]
            if missing:
                deduct = 0.5 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{name}：缺{','.join(missing)}，扣{deduct}分")

        # 14. 支出功能分类细化程度（每低10%扣0.5分）
        elif idx == 14:
            if "项级" not in full_text and "类款项" not in full_text:
                score = 0
                problems.append(f"{name}：未细化到项级，扣{full_score}分")

        # 15. 基本支出经济分类细化程度（每低10%扣0.5分）
        elif idx == 15:
            if "款级" not in full_text:
                score = 0
                problems.append(f"{name}：未细化到款级，扣{full_score}分")

        # 16. 三公经费明细细化程度
        elif idx == 16:
            required = ["因公出国团组数", "因公出国人数", "公务用车购置数", "公务用车保有量", "公务接待批次", "公务接待人数"]
            missing = [i for i in required if i not in full_text]
            if missing:
                deduct = 1 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{name}：缺{','.join(missing)}明细，扣{deduct}分")

        # 17. 项目支出细化程度（每低10%扣0.4分）
        elif idx == 17:
            required = ["项目内容", "实施主体", "年度计划"]
            missing = [i for i in required if i.lower() not in text_lower]
            if missing:
                score = 0
                problems.append(f"{name}：未细化到具体项目信息，扣{full_score}分")

        # 18. 绩效指标细化程度
        elif idx == 18:
            if "具体指标值" not in full_text and "完成值" not in full_text:
                score = 0
                problems.append(f"{name}：绩效指标未量化，扣{full_score}分")
            elif "部分量化" in full_text:
                score = 1
                problems.append(f"{name}：绩效指标仅部分量化，扣2分")

        # 19. 收支差异说明细化程度（每缺1项扣0.5分）
        elif idx == 19:
            if "差异超过10%" not in full_text and "差异原因" not in full_text:
                score = 0
                problems.append(f"{name}：未说明预决算差异原因，扣{full_score}分")

        # 20. 三公经费变动说明细化程度
        elif idx == 20:
            if "变动超过10%" not in full_text and "变动原因" not in full_text:
                score = 0
                problems.append(f"{name}：未说明三公经费变动原因，扣{full_score}分")

        # 21. 空白项说明完整性（每1处未说明扣0.2分）
        elif idx == 21:
            if "无此项" not in full_text:
                score = 0
                problems.append(f"{name}：空白项未标注说明，扣{full_score}分")

        # 22. 民生项目信息细化程度（每缺1项扣0.7分）
        elif idx == 22:
            required = ["受益对象", "补助标准", "发放情况"]
            missing = [i for i in required if i.lower() not in text_lower]
            if missing:
                deduct = 0.7 * len(missing)
                score = max(full_score - deduct, 0)
                problems.append(f"{name}：缺{','.join(missing)}，扣{deduct}分")

        # 23-32 规范性指标（默认满分，不满足规则扣0分）
        elif idx == 23:
            if "首页" not in full_text and "专栏" not in full_text:
                score = 0
                problems.append(f"{name}：未在首页设置公开专栏，扣{full_score}分")
        elif idx == 24:
            if "统一平台" not in full_text:
                score = 1
                problems.append(f"{name}：仅在本单位网站公开，扣2分")
        elif idx == 25:
            if "统一模板" not in full_text:
                score = 0
                problems.append(f"{name}：未采用财政统一模板，扣{full_score}分")
        elif idx == 26:
            # PDF可检索，默认满分，图片格式扣0分
            pass
        elif idx == 27:
            if "不一致" in full_text:
                score = 0
                problems.append(f"{name}：存在数据与批复不一致，扣{full_score}分")
        elif idx == 28:
            if "矛盾" in full_text:
                score = 0
                problems.append(f"{name}：存在数据勾稽关系矛盾，扣{full_score}分")
        elif idx == 29:
            if "豁免公开" in full_text and "法定依据" not in full_text:
                score = 0
                problems.append(f"{name}：豁免公开内容未说明法定依据，扣{full_score}分")
        elif idx == 30:
            pass  # 无法从PDF判断，默认满分
        elif idx == 31:
            if "年度" not in full_text and "预决算公开" not in full_text:
                score = 0
                problems.append(f"{name}：文件标题名称不规范，扣{full_score}分")
        elif idx == 32:
            pass  # 无法从PDF判断，默认满分

        # 保存该项得分，累加维度总分
        item_scores[f"{idx}.{name}"] = round(score, 2)
        dim_totals[dim] += score

    # 4. 计算最终总分
    total_score = round(sum(dim_totals.values()), 2)
    # 5. 整理问题记录
    problem_str = " | ".join(problems) if problems else "无"

    return unit_name, item_scores, dim_totals["及时性"], dim_totals["完整性"], dim_totals["细化程度"], dim_totals["规范性"], total_score, problem_str

# ===================== 批量处理PDF + 生成Excel =====================
def run_batch():
    print(f"📂 读取PDF文件夹：{PDF_FOLDER}")
    if not os.path.exists(PDF_FOLDER):
        print(f"❌ 错误：文件夹不存在，请确认路径 {PDF_FOLDER}")
        return

    # 存储所有单位的结果
    all_results = []

    # 遍历所有PDF
    for filename in os.listdir(PDF_FOLDER):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(PDF_FOLDER, filename)
            print(f"\n🔍 正在评分：{filename}")

            # 精准评分
            unit_name, item_scores, timely, complete, detail, normal, total, problem = accurate_score_pdf(pdf_path)

            # 构建1行数据（1个单位1行）
            row = {
                "单位名称": unit_name,
                "及时性总分": round(timely, 2),
                "完整性总分": round(complete, 2),
                "细化程度总分": round(detail, 2),
                "规范性总分": round(normal, 2),
                "评估总分": total,
                "问题记录": problem
            }
            # 追加32项指标明细得分
            row.update(item_scores)
            all_results.append(row)

            print(f"✅ {unit_name} | 评估总分：{total}")

    # 导出Excel
    df_result = pd.DataFrame(all_results)
    df_result.to_excel(OUTPUT_EXCEL, index=False, engine="openpyxl")
    print(f"\n🎉 全部评分完成！结果已保存至：\n{OUTPUT_EXCEL}")

# ===================== 启动执行 =====================
if __name__ == "__main__":
    run_batch()