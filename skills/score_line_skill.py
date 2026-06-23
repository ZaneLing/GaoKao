from .data_utils import (
    DEFAULT_PROVINCE,
    filter_rows,
    normalize_batch_line,
    normalize_major_score,
    normalize_school_score,
    normalize_score_segment,
    read_rows,
    subject_matches,
)


BATCH_LINES_FILE = "1_最近年份数据/分数线/批次线-2021-2024.xlsx"
SCORE_SEGMENT_FILE = "1_最近年份数据/分数线/一分一段-2017-2024.xlsx"
SCHOOL_SCORES_FILE = "1_最近年份数据/分数线/院校分数-2020-2024.xlsx"
MAJOR_SCORE_FILES = {
    2024: "1_最近年份数据/分数线/专业分数-2024-考试院.xlsx",
    2025: "1_最近年份数据/分数线/专业分数-2025.xlsx",
}


class ScoreLineSkill:
    @staticmethod
    def _batch_line_rows():
        return [normalize_batch_line(row) for row in read_rows(BATCH_LINES_FILE)]

    @staticmethod
    def _score_segment_rows(province=DEFAULT_PROVINCE):
        rows = read_rows(SCORE_SEGMENT_FILE, province_sheet=province)
        return [
            normalize_score_segment(row, province=province)
            for row in rows
            if row.get("省份") == province
        ]

    @staticmethod
    def _school_score_rows(years=None):
        raw_rows = read_rows(SCHOOL_SCORES_FILE, all_sheets=True)
        normalized = [normalize_school_score(row) for row in raw_rows]
        if years:
            year_set = {int(year) for year in years}
            normalized = [row for row in normalized if row.get("年份") in year_set]
        return normalized

    @staticmethod
    def _major_score_rows(years=None):
        if years is None:
            years = [2024]
        rows = []
        for year in years:
            file_path = MAJOR_SCORE_FILES.get(int(year))
            if not file_path:
                continue
            rows.extend(normalize_major_score(row, source_year=int(year)) for row in read_rows(file_path))
        return rows

    @staticmethod
    def get_batch_lines_trend(years=None, category=None, province=DEFAULT_PROVINCE, subject=None, batch=None):
        """获取多年份批次线趋势数据"""
        if years is None:
            years = [2021, 2022, 2023, 2024]
        target_subject = subject or category
        rows = filter_rows(
            ScoreLineSkill._batch_line_rows(),
            province=province,
            subject=target_subject,
            batch=batch,
        )
        year_set = {int(year) for year in years}

        trend_data = {}
        for row in rows:
            if row.get("年份") not in year_set:
                continue
            trend_data.setdefault(row["年份"], []).append(
                {
                    "批次": row["批次"],
                    "科类": row["科类"],
                    "分数线": row["控制分数线"],
                    "位次": row["压分线"],
                    "省份": row["省份"],
                }
            )
        return trend_data

    @staticmethod
    def analyze_batch_trend(category="理科", province=DEFAULT_PROVINCE, subject=None, batch=None):
        """分析批次线多年趋势"""
        trend_data = ScoreLineSkill.get_batch_lines_trend(
            category=category, province=province, subject=subject, batch=batch
        )
        analysis = []
        for year in sorted(trend_data.keys()):
            for item in trend_data[year]:
                analysis.append([year, item["批次"], item["科类"], item["分数线"], item["位次"]])
        return analysis

    @staticmethod
    def get_rank_by_score(score, year=2024, subject=None, province=DEFAULT_PROVINCE):
        """根据分数查询全省排名"""
        target_score = int(score)
        rows = filter_rows(
            ScoreLineSkill._score_segment_rows(province=province),
            year=year,
            province=province,
            subject=subject,
        )
        for row in rows:
            min_score = row.get("最小分数")
            max_score = row.get("最大分数")
            if min_score is None or max_score is None:
                continue
            if min_score <= target_score <= max_score:
                return {
                    "省份": row["省份"],
                    "年份": row["年份"],
                    "科目": row["科类"],
                    "分数": target_score,
                    "分数区间": row["分数区间"],
                    "最高位次": row["最高位次"],
                    "最低位次": row["最低位次"],
                    "位次": row["最低位次"],
                    "同分人数": row["同分人数"],
                }
        return None

    @staticmethod
    def get_score_by_rank(rank, year=2024, subject=None, province=DEFAULT_PROVINCE):
        """根据排名查询对应分数"""
        target_rank = int(rank)
        rows = filter_rows(
            ScoreLineSkill._score_segment_rows(province=province),
            year=year,
            province=province,
            subject=subject,
        )
        for row in rows:
            high_rank = row.get("最高位次")
            low_rank = row.get("最低位次")
            if high_rank is None or low_rank is None:
                continue
            if high_rank <= target_rank <= low_rank:
                min_score = row.get("最小分数")
                max_score = row.get("最大分数")
                score = min_score if min_score == max_score else f"{min_score}~{max_score}"
                return {
                    "省份": row["省份"],
                    "年份": row["年份"],
                    "科目": row["科类"],
                    "分数": score,
                    "分数区间": row["分数区间"],
                    "最高位次": high_rank,
                    "最低位次": low_rank,
                    "位次": target_rank,
                    "同分人数": row["同分人数"],
                }
        return None

    @staticmethod
    def get_school_scores_trend(school_name=None, years=None, subject=None, batch=None):
        """获取院校多年份分数线趋势"""
        if years is None:
            years = [2020, 2021, 2022, 2023, 2024]
        rows = ScoreLineSkill._school_score_rows(years=years)
        result = []
        for row in rows:
            if school_name and school_name not in row.get("学校", ""):
                continue
            if subject and not subject_matches(row.get("科类"), subject):
                continue
            if batch and batch not in row.get("批次", ""):
                continue
            result.append(row)
        return result[:30]

    @staticmethod
    def analyze_school_score_trend(school_name):
        """分析院校分数线趋势"""
        raw_data = ScoreLineSkill.get_school_scores_trend(school_name=school_name)

        if not raw_data:
            return {"school": school_name, "error": "未找到院校数据"}

        sorted_data = sorted(raw_data, key=lambda item: (item.get("年份") or 0, item.get("科类") or ""))
        scores = [row["最低分"] for row in sorted_data if isinstance(row.get("最低分"), int)]

        if scores:
            avg_score = sum(scores) / len(scores)
            min_score = min(scores)
            max_score = max(scores)
            volatility = (max_score - min_score) / avg_score * 100 if avg_score else 0

            return {
                "school": school_name,
                "years": len({row.get("年份") for row in sorted_data}),
                "avg_score": round(avg_score, 1),
                "min_score": min_score,
                "max_score": max_score,
                "volatility": round(volatility, 1),
                "trend": "上升" if scores[-1] > scores[0] else "下降" if scores[-1] < scores[0] else "稳定",
                "samples": sorted_data[:5],
            }
        return {"school": school_name, "error": "无法提取分数数据"}

    @staticmethod
    def get_major_scores(major_name=None, school_name=None, years=None, year=None, subject=None, province=DEFAULT_PROVINCE):
        """获取专业分数线"""
        if year and not years:
            years = [int(year)]
        if years is None:
            years = [2024]

        rows = filter_rows(
            ScoreLineSkill._major_score_rows(years=years),
            province=province,
            subject=subject,
        )
        data = []
        for row in rows:
            if school_name and school_name not in row.get("院校名称", ""):
                continue
            if major_name and major_name not in f"{row.get('专业名称', '')}{row.get('专业全称', '')}":
                continue
            data.append(row)
            if len(data) >= 50:
                break
        return data

    @staticmethod
    def analyze_major_score_comparison(major_name, schools=None):
        """对比分析多所院校的同一专业分数线"""
        data = ScoreLineSkill.get_major_scores(major_name=major_name)

        comparison = []
        for row in data:
            school = row.get("院校名称", "")
            if schools and school not in schools:
                continue

            scores = [
                value
                for value in [row.get("最高分"), row.get("平均分"), row.get("最低分")]
                if isinstance(value, (int, float)) and value > 0
            ]
            if scores:
                comparison.append(
                    {
                        "school": school,
                        "major": row.get("专业名称") or major_name,
                        "avg_score": round(sum(scores) / len(scores), 1),
                        "min_score": min(scores),
                        "max_score": max(scores),
                        "专业组key": row.get("专业组key"),
                        "data": row,
                    }
                )

        comparison.sort(key=lambda x: x["avg_score"], reverse=True)
        return comparison[:10]

    @staticmethod
    def predict_admission_score(school_name=None, user_score=None, score=None, rank=None, subject=None):
        """预测录取可能性"""
        if score and not user_score:
            user_score = score

        if not school_name:
            return {"error": "请提供学校名称"}

        if not user_score:
            return {"error": "请提供分数"}

        analysis = ScoreLineSkill.analyze_school_score_trend(school_name)

        if "error" in analysis:
            return {"school": school_name, "error": analysis["error"]}

        avg_score = analysis["avg_score"]
        min_score = analysis["min_score"]
        max_score = analysis["max_score"]

        if user_score >= max_score:
            probability = "很高 (90%以上)"
            suggestion = "可以作为稳或保的选择"
        elif user_score >= avg_score:
            probability = "较高 (70%-90%)"
            suggestion = "可以作为稳的选择"
        elif user_score >= min_score:
            probability = "一般 (40%-70%)"
            suggestion = "需要谨慎考虑，可作为冲的选择"
        elif user_score >= min_score - 10:
            probability = "较低 (10%-40%)"
            suggestion = "冲刺选择，风险较大"
        else:
            probability = "很低 (10%以下)"
            suggestion = "不建议报考"

        return {
            "school": school_name,
            "user_score": user_score,
            "user_rank": rank,
            "subject": subject,
            "school_avg_score": avg_score,
            "school_min_score": min_score,
            "school_max_score": max_score,
            "probability": probability,
            "suggestion": suggestion,
        }


SKILLS_MAP = {
    "get_batch_lines_trend": ScoreLineSkill.get_batch_lines_trend,
    "analyze_batch_trend": ScoreLineSkill.analyze_batch_trend,
    "get_rank_by_score": ScoreLineSkill.get_rank_by_score,
    "get_score_by_rank": ScoreLineSkill.get_score_by_rank,
    "get_school_scores_trend": ScoreLineSkill.get_school_scores_trend,
    "analyze_school_score_trend": ScoreLineSkill.analyze_school_score_trend,
    "get_major_scores": ScoreLineSkill.get_major_scores,
    "analyze_major_score_comparison": ScoreLineSkill.analyze_major_score_comparison,
    "predict_admission_score": ScoreLineSkill.predict_admission_score,
}

SKILL_DESCRIPTIONS = {
    "get_batch_lines_trend": "获取多年份批次线趋势数据(参数: years, category, province, subject, batch)",
    "analyze_batch_trend": "分析批次线多年变化趋势(参数: category, province, subject, batch)",
    "get_rank_by_score": "根据分数查询全省排名(参数: score, year, subject, province)",
    "get_score_by_rank": "根据排名查询对应分数(参数: rank, year, subject, province)",
    "get_school_scores_trend": "获取院校多年份分数线数据(参数: school_name, years, subject, batch)",
    "analyze_school_score_trend": "分析院校分数线趋势（平均分、波动、走向）(参数: school_name)",
    "get_major_scores": "获取专业分数线(参数: major_name, school_name, year, years, subject)",
    "analyze_major_score_comparison": "对比分析多所院校的同一专业分数线(参数: major_name, school_names)",
    "predict_admission_score": "根据用户分数预测录取可能性(参数: school_name, user_score, score, rank, subject)",
}
