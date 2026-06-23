from .data_utils import DEFAULT_PROVINCE, filter_rows, normalize_plan, read_rows, subject_matches


PLAN_FILES = {
    2021: "1_最近年份数据/招生计划/招生计划-2021.xlsx",
    2022: "1_最近年份数据/招生计划/招生计划-2022.xlsx",
    2023: "1_最近年份数据/招生计划/招生计划-2023-本科.xlsx",
    2024: "1_最近年份数据/招生计划/招生计划-2024.xlsx",
    2025: "1_最近年份数据/招生计划/招生计划-2025.xlsx",
}


class EnrollmentPlanSkill:
    @staticmethod
    def _plan_rows(year, province=DEFAULT_PROVINCE):
        file_path = PLAN_FILES.get(int(year))
        if not file_path:
            return []
        rows = [normalize_plan(row, source_year=int(year), province=province) for row in read_rows(file_path)]
        return filter_rows(rows, year=int(year), province=province)

    @staticmethod
    def get_plan_by_year(year, province=DEFAULT_PROVINCE, subject=None, batch=None):
        """按年份获取标准化招生计划"""
        rows = filter_rows(
            EnrollmentPlanSkill._plan_rows(int(year), province=province),
            province=province,
            subject=subject,
            batch=batch,
        )
        return rows[:50]

    @staticmethod
    def get_plan_trend(school_name=None, major_name=None, years=None, province=DEFAULT_PROVINCE, subject=None):
        """获取招生计划多年趋势"""
        if years is None:
            years = [2022, 2023, 2024, 2025]

        trend_data = {}
        for year in years:
            plan_data = EnrollmentPlanSkill._plan_rows(int(year), province=province)
            filtered = []
            for row in plan_data:
                if school_name and school_name not in row.get("学校", ""):
                    continue
                if major_name and major_name not in row.get("专业名称", ""):
                    continue
                if subject and not subject_matches(row.get("科类"), subject):
                    continue
                filtered.append(row)
            trend_data[int(year)] = filtered[:30]
        return trend_data

    @staticmethod
    def analyze_plan_change(school_name, major_name=None):
        """分析招生计划变化趋势"""
        trend_data = EnrollmentPlanSkill.get_plan_trend(school_name=school_name, major_name=major_name)

        if not trend_data:
            return {"school": school_name, "error": "未找到招生计划数据"}

        plan_counts = {}
        for year, data in trend_data.items():
            plan_counts[year] = sum(row.get("计划人数") or 0 for row in data)

        non_empty_counts = {year: count for year, count in plan_counts.items() if count > 0}
        if non_empty_counts:
            years = sorted(non_empty_counts.keys())
            first_year = years[0]
            last_year = years[-1]

            total_change = non_empty_counts[last_year] - non_empty_counts[first_year]
            change_rate = (
                total_change / non_empty_counts[first_year] * 100
                if non_empty_counts[first_year] > 0
                else 0
            )

            return {
                "school": school_name,
                "major": major_name if major_name else "全部专业",
                "plan_by_year": non_empty_counts,
                "total_change": total_change,
                "change_rate": round(change_rate, 1),
                "trend": "扩招" if total_change > 0 else "缩招" if total_change < 0 else "稳定",
                "years_covered": len(years),
            }

        return {"school": school_name, "error": "无法提取计划数据"}

    @staticmethod
    def get_school_plan_detail(school_name, year=2024, subject=None, batch=None):
        """获取某院校某年度详细招生计划"""
        rows = filter_rows(
            EnrollmentPlanSkill._plan_rows(int(year)),
            subject=subject,
            batch=batch,
        )
        result = [row for row in rows if school_name in row.get("学校", "")]
        return result[:50]

    @staticmethod
    def compare_plan_between_schools(schools, year=2024):
        """对比多所院校的招生计划"""
        plan_data = EnrollmentPlanSkill._plan_rows(int(year))

        comparison = {}
        for school in schools:
            school_plans = [row for row in plan_data if school in row.get("学校", "")]
            comparison[school] = school_plans[:10]
        return comparison

    @staticmethod
    def analyze_major_plan_distribution(year=2024):
        """分析各专业招生计划分布"""
        plan_data = EnrollmentPlanSkill._plan_rows(int(year))

        major_dist = {}
        for row in plan_data:
            major_name = row.get("专业名称")
            count = row.get("计划人数") or 0
            if not major_name or major_name in ["合计", "总计", "小计"]:
                continue
            major_dist[major_name] = major_dist.get(major_name, 0) + count

        sorted_dist = sorted(major_dist.items(), key=lambda x: x[1], reverse=True)
        return sorted_dist[:20]

    @staticmethod
    def get_plan_by_major(major_name, year=2024, subject=None, batch=None):
        """按专业查询招生计划"""
        rows = filter_rows(
            EnrollmentPlanSkill._plan_rows(int(year)),
            subject=subject,
            batch=batch,
        )
        result = [row for row in rows if major_name in row.get("专业名称", "")]
        return result[:50]


SKILLS_MAP = {
    "get_plan_by_year": EnrollmentPlanSkill.get_plan_by_year,
    "get_plan_trend": EnrollmentPlanSkill.get_plan_trend,
    "analyze_plan_change": EnrollmentPlanSkill.analyze_plan_change,
    "get_school_plan_detail": EnrollmentPlanSkill.get_school_plan_detail,
    "compare_plan_between_schools": EnrollmentPlanSkill.compare_plan_between_schools,
    "analyze_major_plan_distribution": EnrollmentPlanSkill.analyze_major_plan_distribution,
    "get_plan_by_major": EnrollmentPlanSkill.get_plan_by_major,
}

SKILL_DESCRIPTIONS = {
    "get_plan_by_year": "按年份获取标准化招生计划",
    "get_plan_trend": "获取招生计划多年趋势",
    "analyze_plan_change": "分析招生计划变化趋势（扩招/缩招）",
    "get_school_plan_detail": "获取某院校某年度详细招生计划",
    "compare_plan_between_schools": "对比多所院校的招生计划",
    "analyze_major_plan_distribution": "分析各专业招生计划分布",
    "get_plan_by_major": "按专业查询招生计划",
}
