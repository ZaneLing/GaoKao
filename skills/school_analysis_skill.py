"""
学校综合信息分析技能
从标准化数据层提取并整合学校信息。
"""

from collections import defaultdict
from datetime import datetime

from .data_utils import (
    DEFAULT_PROVINCE,
    clean_text,
    filter_rows,
    normalize_major_score,
    normalize_plan,
    normalize_school_score,
    read_rows,
)


SCHOOL_INFO_FILE = "3_院校信息/院校基础信息.xlsx"
SCHOOL_SCORES_FILE = "1_最近年份数据/分数线/院校分数-2020-2024.xlsx"
MAJOR_SCORE_2024_FILE = "1_最近年份数据/分数线/专业分数-2024-考试院.xlsx"
PLAN_2025_FILE = "1_最近年份数据/招生计划/招生计划-2025.xlsx"


class SchoolAnalysisSkill:
    """学校综合信息分析"""

    @staticmethod
    def _yes_no(value, marker):
        text = clean_text(value)
        return "是" if text in {"是", marker, "1"} else "否"

    @staticmethod
    def _get_school_basic_info(school_name):
        """获取学校基础信息"""
        for info in read_rows(SCHOOL_INFO_FILE):
            if school_name not in clean_text(info.get("学校名称")):
                continue
            return {
                "学校名称": clean_text(info.get("学校名称")),
                "所在省": clean_text(info.get("所在省")),
                "城市": clean_text(info.get("城市")),
                "院校类型": clean_text(info.get("类型")),
                "是否985": SchoolAnalysisSkill._yes_no(info.get("是否985"), "985"),
                "是否211": SchoolAnalysisSkill._yes_no(info.get("是否211"), "211"),
                "是否双一流": "是" if clean_text(info.get("是否双一流")) else "否",
                "是否重点": clean_text(info.get("国重/省重")),
                "公私性质": clean_text(info.get("公私性质")),
                "本科/专科": clean_text(info.get("本科/专科")),
                "保研率": clean_text(info.get("保研率"), "N/A"),
                "国家特色专业": clean_text(info.get("国家特色专业")),
                "省特色专业": clean_text(info.get("省特色专业")),
                "硕士点": info.get("硕士点（个）", "N/A"),
                "博士点": info.get("博士点（个）", "N/A"),
                "学科评估": clean_text(info.get("评估结果")),
                "招办电话": clean_text(info.get("招办电话")),
                "官网": clean_text(info.get("官网")),
            }
        return {}

    @staticmethod
    def _get_school_score_history(school_name):
        """获取学校历年院校投档分数线"""
        rows = [normalize_school_score(row) for row in read_rows(SCHOOL_SCORES_FILE, all_sheets=True)]
        return [row for row in rows if school_name in row.get("学校", "")]

    @staticmethod
    def _major_score_rows_2024(school_name):
        rows = [
            normalize_major_score(row, source_year=2024, province=DEFAULT_PROVINCE)
            for row in read_rows(MAJOR_SCORE_2024_FILE)
        ]
        rows = filter_rows(rows, year=2024, province=DEFAULT_PROVINCE)
        return [row for row in rows if school_name in row.get("院校名称", "")]

    @staticmethod
    def _get_school_major_groups(school_name):
        """按专业组聚合 2024 专业分数线"""
        groups = defaultdict(list)
        for row in SchoolAnalysisSkill._major_score_rows_2024(school_name):
            groups[row.get("专业组key")].append(row)

        results = []
        for group_key, rows in groups.items():
            scores_low = [row.get("最低分") for row in rows if isinstance(row.get("最低分"), int)]
            scores_high = [row.get("最高分") for row in rows if isinstance(row.get("最高分"), int)]
            avg_scores = [row.get("平均分") for row in rows if isinstance(row.get("平均分"), (int, float))]
            ranks = [row.get("最低位次") for row in rows if isinstance(row.get("最低位次"), int)]
            first = rows[0]
            results.append(
                {
                    "年份": 2024,
                    "专业组key": group_key,
                    "专业组代码": first.get("专业组代码"),
                    "专业组名称": first.get("专业组名称"),
                    "科目要求": first.get("科类"),
                    "选科要求": first.get("选科要求"),
                    "最高分": max(scores_high) if scores_high else None,
                    "最低分": min(scores_low) if scores_low else None,
                    "平均分": round(sum(avg_scores) / len(avg_scores), 1) if avg_scores else None,
                    "最低位次": max(ranks) if ranks else None,
                    "包含专业数": len({row.get("专业名称") for row in rows if row.get("专业名称")}),
                }
            )
        return sorted(results, key=lambda item: (item.get("科目要求") or "", item.get("专业组代码") or ""))

    @staticmethod
    def _get_school_enrollment_plan(school_name):
        """获取学校 2025 标准化招生计划"""
        rows = [
            normalize_plan(row, source_year=2025, province=DEFAULT_PROVINCE)
            for row in read_rows(PLAN_2025_FILE)
        ]
        rows = filter_rows(rows, year=2025, province=DEFAULT_PROVINCE)
        return [row for row in rows if school_name in row.get("学校", "")]

    @staticmethod
    def _get_school_majors(school_name):
        """获取学校 2024 专业录取详情"""
        return SchoolAnalysisSkill._major_score_rows_2024(school_name)[:100]

    @staticmethod
    def get_comprehensive_school_analysis(school_name):
        """获取学校综合信息分析"""
        if not school_name:
            return {"error": "请指定学校名称"}

        result = {
            "学校名称": school_name,
            "分析时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "基础信息": SchoolAnalysisSkill._get_school_basic_info(school_name),
            "历年分数线": SchoolAnalysisSkill._get_school_score_history(school_name),
            "专业组信息": SchoolAnalysisSkill._get_school_major_groups(school_name),
            "招生计划": SchoolAnalysisSkill._get_school_enrollment_plan(school_name),
            "专业详情": SchoolAnalysisSkill._get_school_majors(school_name),
            "录取分析": {},
        }
        result["录取分析"] = SchoolAnalysisSkill._analyze_admission(school_name, result)
        return result

    @staticmethod
    def _analyze_admission(school_name, data):
        """生成录取分析"""
        analysis = {
            "总专业组数": len(data.get("专业组信息", [])),
            "总招生专业数": len(data.get("专业详情", [])),
            "近3年分数线": [],
            "招生特点": [],
            "报考建议": [],
        }

        score_history = sorted(
            data.get("历年分数线", []),
            key=lambda item: (item.get("年份") or 0, item.get("科类") or ""),
            reverse=True,
        )
        for record in score_history[:3]:
            analysis["近3年分数线"].append(
                {
                    "年份": record.get("年份", "N/A"),
                    "分数线": record.get("最低分", "N/A"),
                    "最低位次": record.get("最低分位次", "N/A"),
                }
            )

        plan_count = len(data.get("招生计划", []))
        major_count = len(data.get("专业详情", []))
        if plan_count > 0:
            total_plan = sum(row.get("计划人数") or 0 for row in data.get("招生计划", []))
            analysis["招生特点"].append(f"2025年招生计划{plan_count}条，合计计划{total_plan}人")

        basic_info = data.get("基础信息", {})
        if basic_info.get("是否985") == "是":
            analysis["招生特点"].append("985高校，层次较高，竞争激烈")
        if basic_info.get("是否211") == "是":
            analysis["招生特点"].append("211高校，实力雄厚")
        if basic_info.get("是否双一流") == "是":
            analysis["招生特点"].append("双一流建设高校")

        baoyan = clean_text(basic_info.get("保研率"))
        if baoyan:
            try:
                baoyan_rate = float(baoyan.replace("%", ""))
                if baoyan_rate > 20:
                    analysis["报考建议"].append(f"保研率较高({baoyan})，适合有读研意向的考生")
                elif baoyan_rate > 10:
                    analysis["报考建议"].append(f"保研率中等({baoyan})，有一定保研机会")
            except ValueError:
                pass

        if major_count > 30:
            analysis["报考建议"].append("招生专业丰富，选择余地大")
        elif major_count > 10:
            analysis["报考建议"].append("招生专业适中，建议重点关注优势专业")
        else:
            analysis["报考建议"].append("招生专业较少，需仔细研究具体专业")
        return analysis

    @staticmethod
    def format_comprehensive_report(data):
        """格式化综合报告为可读文本"""
        if "error" in data:
            return f"错误: {data['error']}"

        lines = []
        lines.append("=" * 80)
        lines.append(f"🏫 {data['学校名称']} - 综合信息分析报告")
        lines.append("=" * 80)
        lines.append(f"📅 分析时间: {data['分析时间']}")
        lines.append("")

        basic = data.get("基础信息", {})
        if basic:
            lines.append("-" * 80)
            lines.append("📋 【基础信息】")
            lines.append("-" * 80)
            lines.append(f"  院校类型: {basic.get('院校类型', 'N/A')}")
            lines.append(f"  所在地区: {basic.get('所在省', 'N/A')} {basic.get('城市', '')}")
            lines.append(f"  院校层次: 985:{basic.get('是否985')} 211:{basic.get('是否211')} 双一流:{basic.get('是否双一流')}")
            lines.append(f"  公私性质: {basic.get('公私性质', 'N/A')}")
            lines.append(f"  本科/专科: {basic.get('本科/专科', 'N/A')}")
            lines.append(f"  保研率: {basic.get('保研率', 'N/A')}")
            lines.append(f"  硕士点: {basic.get('硕士点', 'N/A')}个")
            lines.append(f"  博士点: {basic.get('博士点', 'N/A')}个")
            lines.append(f"  国家特色专业: {basic.get('国家特色专业', 'N/A') or '无'}")
            lines.append(f"  省特色专业: {basic.get('省特色专业', 'N/A') or '无'}")
            lines.append(f"  招办电话: {basic.get('招办电话', 'N/A')}")
            lines.append(f"  官网: {basic.get('官网', 'N/A')}")
            lines.append("")

        score_history = data.get("历年分数线", [])
        if score_history:
            lines.append("-" * 80)
            lines.append("📈 【历年分数线】")
            lines.append("-" * 80)
            lines.append(f"{'年份':<8} {'科类':<10} {'批次':<12} {'最低分':<10} {'最低位次':<15}")
            lines.append("-" * 70)
            for record in score_history[:10]:
                lines.append(
                    f"{str(record.get('年份', 'N/A')):<8} "
                    f"{str(record.get('科类', 'N/A')):<10} "
                    f"{str(record.get('批次', 'N/A')):<12} "
                    f"{str(record.get('最低分', 'N/A')):<10} "
                    f"{str(record.get('最低分位次', 'N/A')):<15}"
                )
            lines.append("")

        major_groups = data.get("专业组信息", [])
        if major_groups:
            lines.append("-" * 80)
            lines.append("🎯 【专业组信息】（2024年，按专业分数表聚合）")
            lines.append("-" * 80)
            lines.append(f"{'专业组代码':<12} {'科目':<8} {'选科':<10} {'最高分':<10} {'最低分':<10} {'最低位次':<15}")
            lines.append("-" * 80)
            for group in major_groups[:20]:
                lines.append(
                    f"{str(group.get('专业组代码', 'N/A')):<12} "
                    f"{str(group.get('科目要求', 'N/A')):<8} "
                    f"{str(group.get('选科要求', 'N/A')):<10} "
                    f"{str(group.get('最高分', 'N/A')):<10} "
                    f"{str(group.get('最低分', 'N/A')):<10} "
                    f"{str(group.get('最低位次', 'N/A')):<15}"
                )
            lines.append("")

        enrollment = data.get("招生计划", [])
        if enrollment:
            lines.append("-" * 80)
            lines.append("📊 【招生计划】（2025年）")
            lines.append("-" * 80)
            lines.append(f"{'专业组':<12} {'专业':<38} {'计划数':<8} {'选科要求':<10}")
            lines.append("-" * 80)
            for plan in enrollment[:20]:
                lines.append(
                    f"{str(plan.get('专业组代码', 'N/A')):<12} "
                    f"{str(plan.get('专业名称', 'N/A'))[:36]:<38} "
                    f"{str(plan.get('计划人数', 'N/A')):<8} "
                    f"{str(plan.get('选科要求', 'N/A')):<10}"
                )
            lines.append("")

        analysis = data.get("录取分析", {})
        if analysis:
            lines.append("-" * 80)
            lines.append("💡 【录取分析与建议】")
            lines.append("-" * 80)
            if analysis.get("近3年分数线"):
                lines.append("近3年分数线:")
                for score_info in analysis["近3年分数线"]:
                    lines.append(f"  {score_info['年份']}年: {score_info['分数线']}分 (位次: {score_info['最低位次']})")
            if analysis.get("招生特点"):
                lines.append("\n招生特点:")
                for feature in analysis["招生特点"]:
                    lines.append(f"  • {feature}")
            if analysis.get("报考建议"):
                lines.append("\n报考建议:")
                for suggestion in analysis["报考建议"]:
                    lines.append(f"  ✓ {suggestion}")
            lines.append("")

        lines.append("=" * 80)
        lines.append("📝 报告说明:")
        lines.append("  1. 分数线和位次为历史数据，仅供参考")
        lines.append("  2. 专业组信息由标准化专业分数表按专业组聚合生成")
        lines.append("  3. 招生计划为2025年数据，最终以当年官方公布为准")
        lines.append("  4. 建议结合自身排名、选科、调剂风险综合考虑")
        lines.append("=" * 80)
        return "\n".join(lines)


SKILLS_MAP = {
    "get_comprehensive_school_analysis": SchoolAnalysisSkill.get_comprehensive_school_analysis,
    "format_school_report": SchoolAnalysisSkill.format_comprehensive_report,
}

SKILL_DESCRIPTIONS = {
    "get_comprehensive_school_analysis": "获取学校综合信息分析（历年分数线、专业组、招生计划、专业详情等）（参数: school_name）",
    "format_school_report": "格式化学校综合报告为可读文本（参数: data）",
}
