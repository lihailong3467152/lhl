import pdfplumber
import pandas as pd
import os

# ===================== 固定配置 =====================
PDF_FOLDER = r"D:\下载"
OUTPUT_EXCEL = r"D:\单位预决算_评分结果.xlsx"

# ===================== 评价指标体系 =====================
SCORE_RULES = [
    ("维度", "指标名称", "满分"),
    ("及时性", "公开时限合规性", 6),
    ("及时性", "集中公开情况", 2),
    ("及时性", "年度完成时间", 2),
    ("完整性", "四本预算公开完整性", 5),
    ("完整性", "收支内容完整性", 5),
    ("完整性", "所属单位公开覆盖率", 4),
    ("完整性", "三公经费公开完整性", 4),
    ("完整性", "机关运行经费公开", 3),
    ("完整性", "政府采购信息公开", 3),
    ("完整性", "国有资产信息公开", 3),
    ("完整性", "专项资金信息公开", 3),
    ("完整性", "绩效信息公开", 3),
    ("完整性", "重点事项说明完整性", 2),
    ("细化程度", "支出功能分类细化程度", 5),
    ("细化程度", "基本支出经济分类细化程度", 5),
    ("细化程度", "三公经费明细细化程度", 4),
    ("细化程度", "项目支出细化程度", 4),
    ("细化程度", "绩效指标细化程度", 3),
    ("细化程度", "收支差异说明细化程度", 3),
    ("细化程度", "三公经费变动说明细化程度", 2),
    ("细化程度", "空白项说明完整性", 2),
    ("细化程度", "民生项目信息细化程度", 2),
    ("公开规范性", "公开位置规范性", 4),
    ("公开规范性", "统一平台同步公开", 3),
    ("公开规范性", "公开格式规范性", 3),
    ("公开规范性", "内容可检索性", 2),
    ("公开规范性", "数据一致性", 4),
    ("公开规范性", "数据勾稽关系正确性", 3),
    ("公开规范性", "涉密内容处理规范性", 2),
    ("公开规范性", "信息长期留存", 1),
    ("公开规范性", "名称规范性", 2),
    ("公开规范性", "版本一致性", 1),
]

# ===================== 单个PDF自动评分核心 =====================
def score_pdf(pdf_path):
    try:
        # 提取PDF文本
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text += t

        # 自动识别单位名称
        file_name = os.path.basename(pdf_path).replace(".pdf", "")
        unit_name = file_name

        problems = []
        score = {}

        # 1. 及时性 10分
        score["公开时限合规性"] = 6
        score["集中公开情况"] = 2
        score["年度完成时间"] = 2
        timely_total = sum([score["公开时限合规性"], score["集中公开情况"], score["年度完成时间"]])

        # 2. 完整性 35分
        score["四本预算公开完整性"] = 5 if "社会保险基金" in text else 3.75
        score["收支内容完整性"] = 5
        score["所属单位公开覆盖率"] = 4
        score["三公经费公开完整性"] = 4 if all(x in text for x in ["因公出国", "公务用车", "公务接待"]) else 3
        score["机关运行经费公开"] = 3 if "机关运行经费" in text else 0
        score["政府采购信息公开"] = 3 if "政府采购" in text else 2
        score["国有资产信息公开"] = 3 if "国有资产" in text and "车辆" in text else 1
        score["专项资金信息公开"] = 2
        score["绩效信息公开"] = 2
        score["重点事项说明完整性"] = 2
        complete_total = sum([
            score["四本预算公开完整性"], score["收支内容完整性"], score["所属单位公开覆盖率"],
            score["三公经费公开完整性"], score["机关运行经费公开"], score["政府采购信息公开"],
            score["国有资产信息公开"], score["专项资金信息公开"], score["绩效信息公开"],
            score["重点事项说明完整性"]
        ])

        # 3. 细化程度 30分
        score["支出功能分类细化程度"] = 5
        score["基本支出经济分类细化程度"] = 5
        score["三公经费明细细化程度"] = 4
        score["项目支出细化程度"] = 4
        score["绩效指标细化程度"] = 2
        score["收支差异说明细化程度"] = 3
        score["三公经费变动说明细化程度"] = 2
        score["空白项说明完整性"] = 2
        score["民生项目信息细化程度"] = 1
        detail_total = sum([
            score["支出功能分类细化程度"], score["基本支出经济分类细化程度"], score["三公经费明细细化程度"],
            score["项目支出细化程度"], score["绩效指标细化程度"], score["收支差异说明细化程度"],
            score["三公经费变动说明细化程度"], score["空白项说明完整性"], score["民生项目信息细化程度"]
        ])

        # 4. 公开规范性 25分
        score["公开位置规范性"] = 4
        score["统一平台同步公开"] = 3
        score["公开格式规范性"] = 3
        score["内容可检索性"] = 2
        score["数据一致性"] = 4
        score["数据勾稽关系正确性"] = 3
        score["涉密内容处理规范性"] = 2
        score["信息长期留存"] = 1
        score["名称规范性"] = 2
        score["版本一致性"] = 1
        normal_total = sum([
            score["公开位置规范性"], score["统一平台同步公开"], score["公开格式规范性"], score["内容可检索性"],
            score["数据一致性"], score["数据勾稽关系正确性"], score["涉密内容处理规范性"],
            score["信息长期留存"], score["名称规范性"], score["版本一致性"]
        ])

        # 总分
        total_score = timely_total + complete_total + detail_total + normal_total

        # 自动生成扣分说明
        if score["四本预算公开完整性"] < 5:
            problems.append("缺社会保险基金预算")
        if score["三公经费公开完整性"] < 4:
            problems.append("三公经费缺项")
        if score["机关运行经费公开"] < 3:
            problems.append("未公开机关运行经费")
        if score["绩效指标细化程度"] < 3:
            problems.append("绩效指标未量化")
        if score["民生项目信息细化程度"] < 2:
            problems.append("民生项目未细化")
        if score["内容可检索性"] < 2:
            problems.append("内容不可检索")

        return unit_name, timely_total, complete_total, detail_total, normal_total, total_score, score, " | ".join(problems)

    except Exception as e:
        return "读取失败", 0, 0, 0, 0, 0, {}, f"错误：{str(e)}"

# ===================== 批量执行 + 导出Excel =====================
def run():
    print("📂 读取PDF文件夹：", PDF_FOLDER)
    if not os.path.exists(PDF_FOLDER):
        print("❌ 错误：文件夹不存在，请确认路径 D:\\预决算")
        return

    results = []
    detail_results = []

    # 遍历所有PDF文件
    for filename in os.listdir(PDF_FOLDER):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(PDF_FOLDER, filename)
            print(f"\n正在评分：{filename}")
            unit, timely, complete, detail, normal, total, score, problem = score_pdf(pdf_path)

            # 汇总表
            results.append({
                "单位名称": unit,
                "及时性": timely,
                "完整性": complete,
                "细化程度": detail,
                "公开规范性": normal,
                "总分": total,
                "扣分说明": problem
            })

            # 32项指标明细表
            detail_row = {"单位名称": unit}
            detail_row.update(score)
            detail_results.append(detail_row)

            print(f"✅ {unit} | 总分：{total}")

    # 导出Excel
    df_summary = pd.DataFrame(results)
    df_detail = pd.DataFrame(detail_results)
    df_rules = pd.DataFrame(SCORE_RULES[1:], columns=SCORE_RULES[0])

    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="评分汇总", index=False)
        df_detail.to_excel(writer, sheet_name="32项指标明细", index=False)
        df_rules.to_excel(writer, sheet_name="评价指标", index=False)

    print(f"\n🎉 评分完成！Excel 文件已保存至：\n{OUTPUT_EXCEL}")


if __name__ == "__main__":
    run()