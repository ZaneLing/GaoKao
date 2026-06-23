from .data_utils import (
    DEFAULT_PROVINCE,
    clean_text,
    extract_group_code,
    filter_rows,
    normalize_major_score,
    normalize_plan,
    read_rows,
    subject_matches,
)


SCORE_FILES = {
    2024: "1_最近年份数据/分数线/专业分数-2024-考试院.xlsx",
    2025: "1_最近年份数据/分数线/专业分数-2025.xlsx",
}
PLAN_FILES = {
    2024: "1_最近年份数据/招生计划/招生计划-2024.xlsx",
    2025: "1_最近年份数据/招生计划/招生计划-2025.xlsx",
}


class MajorGroupSkill:
    _score_cache = {}
    _plan_cache = {}
    _score_index_cache = {}
    _plan_index_cache = {}

    @staticmethod
    def _split_keywords(value):
        if not value:
            return []
        if isinstance(value, (list, tuple, set)):
            return [clean_text(item) for item in value if clean_text(item)]
        return [item.strip() for item in str(value).replace("，", ",").split(",") if item.strip()]

    @staticmethod
    def _load_score_data(year=2024, province=DEFAULT_PROVINCE):
        year = int(year)
        cache_key = (year, province)
        if cache_key not in MajorGroupSkill._score_cache:
            file_path = SCORE_FILES.get(year)
            if not file_path:
                MajorGroupSkill._score_cache[cache_key] = []
            else:
                rows = [
                    normalize_major_score(row, source_year=year, province=province)
                    for row in read_rows(file_path)
                ]
                MajorGroupSkill._score_cache[cache_key] = filter_rows(rows, year=year, province=province)
                print(f"  [缓存] 已加载{year}分数数据 {len(MajorGroupSkill._score_cache[cache_key])} 行")
        return MajorGroupSkill._score_cache[cache_key]

    @staticmethod
    def _load_plan_data(year=2024, province=DEFAULT_PROVINCE):
        year = int(year)
        cache_key = (year, province)
        if cache_key not in MajorGroupSkill._plan_cache:
            file_path = PLAN_FILES.get(year)
            if not file_path:
                MajorGroupSkill._plan_cache[cache_key] = []
            else:
                rows = [
                    normalize_plan(row, source_year=year, province=province)
                    for row in read_rows(file_path)
                ]
                MajorGroupSkill._plan_cache[cache_key] = filter_rows(rows, year=year, province=province)
                print(f"  [缓存] 已加载{year}计划数据 {len(MajorGroupSkill._plan_cache[cache_key])} 行")
        return MajorGroupSkill._plan_cache[cache_key]

    @staticmethod
    def _score_index(year=2024, province=DEFAULT_PROVINCE):
        cache_key = (int(year), province)
        if cache_key not in MajorGroupSkill._score_index_cache:
            index = {}
            for row in MajorGroupSkill._load_score_data(year, province=province):
                index.setdefault(row.get("专业组key"), []).append(row)
            MajorGroupSkill._score_index_cache[cache_key] = index
        return MajorGroupSkill._score_index_cache[cache_key]

    @staticmethod
    def _plan_index(year=2024, province=DEFAULT_PROVINCE):
        cache_key = (int(year), province)
        if cache_key not in MajorGroupSkill._plan_index_cache:
            index = {}
            for row in MajorGroupSkill._load_plan_data(year, province=province):
                index.setdefault(row.get("专业组key"), []).append(row)
            MajorGroupSkill._plan_index_cache[cache_key] = index
        return MajorGroupSkill._plan_index_cache[cache_key]

    @staticmethod
    def extract_group_code(group_name):
        return extract_group_code(group_name)

    @staticmethod
    def get_group_number(group_name):
        return extract_group_code(group_name)

    @staticmethod
    def _group_matches(row, major_group=None, major_group_key=None):
        if major_group_key:
            return row.get("专业组key") == major_group_key
        if not major_group:
            return True
        target_group = extract_group_code(major_group)
        row_group = row.get("专业组代码")
        if target_group and row_group and target_group == row_group:
            return True
        text = f"{row.get('专业组名称', '')}{row.get('招生代码', '')}{row.get('专业组key', '')}"
        return clean_text(major_group) in text

    @staticmethod
    def _major_matches(row, major_names):
        keywords = MajorGroupSkill._split_keywords(major_names)
        if not keywords:
            return True
        fields = [
            clean_text(row.get("专业名称")),
            clean_text(row.get("专业全称")),
            clean_text(row.get("专业备注")),
        ]
        haystack = "".join(fields)
        return any(
            keyword in haystack or any(field and field in keyword for field in fields)
            for keyword in keywords
        )

    @staticmethod
    def get_major_group_scores(
        major_group=None,
        school_name=None,
        major_names=None,
        subject=None,
        year=2024,
        major_group_key=None,
    ):
        if major_group_key:
            rows = MajorGroupSkill._score_index(year).get(major_group_key, [])
            rows = filter_rows(rows, subject=subject)
        else:
            rows = filter_rows(MajorGroupSkill._load_score_data(year), subject=subject)
        results = []
        for row in rows:
            if school_name and school_name not in row.get("院校名称", ""):
                continue
            if not MajorGroupSkill._group_matches(row, major_group=major_group, major_group_key=major_group_key):
                continue
            if not MajorGroupSkill._major_matches(row, major_names):
                continue
            results.append(row)
            if len(results) >= 100:
                break
        return results

    @staticmethod
    def get_major_group_plan(
        major_group=None,
        school_name=None,
        year=2024,
        subject=None,
        major_group_key=None,
    ):
        if major_group_key:
            rows = MajorGroupSkill._plan_index(year).get(major_group_key, [])
            rows = filter_rows(rows, subject=subject)
        else:
            rows = filter_rows(MajorGroupSkill._load_plan_data(year), subject=subject)
        results = []
        for row in rows:
            if school_name and school_name not in row.get("学校", ""):
                continue
            if not MajorGroupSkill._group_matches(row, major_group=major_group, major_group_key=major_group_key):
                continue
            results.append(row)
            if len(results) >= 200:
                break
        return results

    @staticmethod
    def _empty_year_metrics():
        return {
            "min_rank": None,
            "max_rank": None,
            "avg_rank": None,
            "min_score": None,
            "max_score": None,
            "avg_score": None,
            "total_plan": 0,
            "group_count": 0,
            "groups": [],
            "data_count": 0,
            "special_plans": [],
            "school_codes": [],
            "total_enroll": None,
            "group_plans": {},
            "majors": [],
        }

    @staticmethod
    def _summarize_scores(scores):
        ranks = [row["最低位次"] for row in scores if isinstance(row.get("最低位次"), int)]
        avg_ranks = [row["平均位次"] for row in scores if isinstance(row.get("平均位次"), int)]
        min_scores = [row["最低分"] for row in scores if isinstance(row.get("最低分"), int)]
        max_scores = [row["最高分"] for row in scores if isinstance(row.get("最高分"), int)]
        avg_scores = [row["平均分"] for row in scores if isinstance(row.get("平均分"), (int, float))]
        enroll_counts = [row["录取人数"] for row in scores if isinstance(row.get("录取人数"), int)]
        majors = sorted({row.get("专业名称") for row in scores if row.get("专业名称")})

        avg_rank_source = avg_ranks or ranks
        avg_score_source = avg_scores or min_scores
        return {
            "min_rank": min(ranks) if ranks else None,
            "max_rank": max(ranks) if ranks else None,
            "avg_rank": round(sum(avg_rank_source) / len(avg_rank_source)) if avg_rank_source else None,
            "min_score": min(min_scores) if min_scores else None,
            "max_score": max(max_scores) if max_scores else None,
            "avg_score": round(sum(avg_score_source) / len(avg_score_source), 1) if avg_score_source else None,
            "total_enroll": sum(enroll_counts) if enroll_counts else None,
            "majors": majors,
        }

    @staticmethod
    def _summarize_plans(plans):
        total_plan = sum(row.get("计划人数") or 0 for row in plans)
        group_plans = {}
        for row in plans:
            group_key = row.get("专业组key") or row.get("专业组代码") or row.get("专业组名称")
            group_plans[group_key] = group_plans.get(group_key, 0) + (row.get("计划人数") or 0)
        return total_plan, group_plans

    @staticmethod
    def _special_plans(rows):
        special_keywords = ["中外合作", "中外合办", "国际班", "地方专项", "国家专项", "定向", "公费", "预科"]
        found = set()
        for row in rows:
            text = f"{row.get('专业名称', '')}{row.get('专业备注', '')}{row.get('备注', '')}{row.get('专业组名称', '')}"
            for keyword in special_keywords:
                if keyword in text:
                    found.add(keyword)
        return sorted(found)

    @staticmethod
    def analyze_school_level_metrics(school_name):
        metrics = {
            "school_name": school_name,
            "2024": MajorGroupSkill._empty_year_metrics(),
            "2025": MajorGroupSkill._empty_year_metrics(),
            "comparison": {},
        }

        for year in [2024, 2025]:
            year_key = str(year)
            scores = MajorGroupSkill.get_major_group_scores(school_name=school_name, year=year)
            plans = MajorGroupSkill.get_major_group_plan(school_name=school_name, year=year)
            score_summary = MajorGroupSkill._summarize_scores(scores)
            total_plan, group_plans = MajorGroupSkill._summarize_plans(plans)
            groups = sorted({row.get("专业组代码") or row.get("专业组名称") for row in scores if row.get("专业组代码") or row.get("专业组名称")})
            plan_groups = sorted({row.get("专业组key") for row in plans if row.get("专业组key")})
            school_codes = sorted(
                {
                    row.get("招生代码") or row.get("院校代码")
                    for row in scores + plans
                    if row.get("招生代码") or row.get("院校代码")
                }
            )
            metrics[year_key].update(score_summary)
            metrics[year_key].update(
                {
                    "total_plan": total_plan,
                    "group_count": len(plan_groups or groups),
                    "groups": (plan_groups or groups)[:10],
                    "data_count": len(scores),
                    "special_plans": MajorGroupSkill._special_plans(scores + plans),
                    "school_codes": school_codes,
                    "group_plans": group_plans,
                }
            )

        if metrics["2024"]["total_plan"] and metrics["2025"]["total_plan"]:
            plan_diff = metrics["2025"]["total_plan"] - metrics["2024"]["total_plan"]
            plan_ratio = plan_diff / metrics["2024"]["total_plan"] * 100
            if plan_ratio > 10:
                metrics["comparison"]["enrollment_change"] = f"扩招 {plan_ratio:.1f}%"
            elif plan_ratio < -10:
                metrics["comparison"]["enrollment_change"] = f"缩招 {abs(plan_ratio):.1f}%"
            else:
                metrics["comparison"]["enrollment_change"] = f"基本持平 ({plan_ratio:.1f}%)"

        groups_2024 = set(metrics["2024"]["groups"])
        groups_2025 = set(metrics["2025"]["groups"])
        if groups_2024 or groups_2025:
            new_groups = groups_2025 - groups_2024
            removed_groups = groups_2024 - groups_2025
            metrics["comparison"]["new_groups"] = sorted(new_groups)[:5]
            metrics["comparison"]["removed_groups"] = sorted(removed_groups)[:5]

        if metrics["2024"]["avg_rank"] and metrics["2025"]["avg_rank"]:
            rank_diff = metrics["2025"]["avg_rank"] - metrics["2024"]["avg_rank"]
            metrics["comparison"]["rank_diff"] = rank_diff
            if rank_diff > 8000:
                metrics["comparison"]["rank_trend"] = "位次大幅后退（明显大小年）"
            elif rank_diff > 3000:
                metrics["comparison"]["rank_trend"] = "位次后退（存在大小年）"
            elif rank_diff > 1000:
                metrics["comparison"]["rank_trend"] = "位次略有后退"
            elif rank_diff < -8000:
                metrics["comparison"]["rank_trend"] = "位次大幅前进（明显大小年）"
            elif rank_diff < -3000:
                metrics["comparison"]["rank_trend"] = "位次前进（存在大小年）"
            elif rank_diff < -1000:
                metrics["comparison"]["rank_trend"] = "位次略有前进"
            else:
                metrics["comparison"]["rank_trend"] = "位次基本稳定"

        special = sorted(set(metrics["2024"]["special_plans"]) | set(metrics["2025"]["special_plans"]))
        if special:
            metrics["comparison"]["special_plans"] = special
            metrics["comparison"]["has_international"] = any("中外" in item or "国际" in item for item in special)
            metrics["comparison"]["has_special_quota"] = any("专项" in item for item in special)
            metrics["comparison"]["has_定向"] = any(item in {"定向", "公费"} for item in special)
        return metrics

    @staticmethod
    def analyze_major_level_metrics(
        school_name,
        major_group,
        major_names=None,
        subject=None,
        major_group_key=None,
        include_historical=True,
    ):
        metrics = {
            "school_name": school_name,
            "major_group": major_group,
            "major_group_key": major_group_key,
            "2024": MajorGroupSkill._empty_year_metrics(),
            "2025": MajorGroupSkill._empty_year_metrics(),
            "comparison": {},
        }

        years = [2024, 2025] if include_historical else [2025]
        for year in years:
            year_key = str(year)
            scores = MajorGroupSkill.get_major_group_scores(
                school_name=school_name,
                major_group=major_group,
                major_names=major_names,
                subject=subject,
                year=year,
                major_group_key=major_group_key if year == 2025 else None,
            )
            plans = MajorGroupSkill.get_major_group_plan(
                school_name=school_name,
                major_group=major_group,
                subject=subject,
                year=year,
                major_group_key=major_group_key if year == 2025 else None,
            )
            score_summary = MajorGroupSkill._summarize_scores(scores)
            total_plan, group_plans = MajorGroupSkill._summarize_plans(plans)
            metrics[year_key].update(score_summary)
            metrics[year_key].update(
                {
                    "total_plan": total_plan,
                    "data_count": len(scores),
                    "group_plans": group_plans,
                    "special_plans": MajorGroupSkill._special_plans(scores + plans),
                }
            )

        if metrics["2024"]["total_plan"] and metrics["2025"]["total_plan"]:
            metrics["comparison"]["plan_change"] = metrics["2025"]["total_plan"] - metrics["2024"]["total_plan"]
        if metrics["2024"]["avg_rank"] and metrics["2025"]["avg_rank"]:
            metrics["comparison"]["rank_diff"] = metrics["2025"]["avg_rank"] - metrics["2024"]["avg_rank"]
        return metrics

    @staticmethod
    def _plan_info(plans):
        if not plans:
            return {}
        first = plans[0]
        all_majors = [row.get("专业名称") for row in plans if row.get("专业名称")]
        total_plan = sum(row.get("计划人数") or 0 for row in plans)
        return {
            "专业组": first.get("专业组名称") or first.get("专业组代码"),
            "专业组代码": first.get("专业组代码"),
            "专业组key": first.get("专业组key"),
            "招生代码": first.get("招生代码"),
            "科目要求": first.get("科类") or "N/A",
            "选科要求": first.get("选科要求") or "N/A",
            "计划总数": total_plan,
            "包含专业": "; ".join(all_majors),
            "学费": first.get("学费") or "N/A",
            "学制": first.get("学制") or "N/A",
        }

    @staticmethod
    def analyze_major_group_admission(
        major_group,
        school_name,
        user_score,
        user_rank=None,
        major_names=None,
        subject=None,
        major_group_key=None,
        include_school_metrics=True,
        include_historical=True,
    ):
        metrics = MajorGroupSkill.analyze_major_level_metrics(
            school_name,
            major_group,
            major_names,
            subject=subject,
            major_group_key=major_group_key,
            include_historical=include_historical,
        )
        plans_2025 = MajorGroupSkill.get_major_group_plan(
            school_name=school_name,
            major_group=major_group,
            year=2025,
            subject=subject,
            major_group_key=major_group_key,
        )
        plan_info = MajorGroupSkill._plan_info(plans_2025)
        if not plan_info:
            plans_2024 = MajorGroupSkill.get_major_group_plan(
                school_name=school_name,
                major_group=major_group,
                year=2024,
                subject=subject,
            )
            plan_info = MajorGroupSkill._plan_info(plans_2024)

        group_ranks = []
        group_scores = []
        for year_key in ["2025", "2024"]:
            year_metrics = metrics[year_key]
            for key in ["avg_rank", "min_rank", "max_rank"]:
                if year_metrics.get(key):
                    group_ranks.append(year_metrics[key])
            for key in ["avg_score", "min_score", "max_score"]:
                if year_metrics.get(key):
                    group_scores.append(year_metrics[key])

        probability = "未知"
        suggestion = "无法评估"
        level = "不推荐"

        if group_ranks and user_rank:
            avg_rank = sum(group_ranks) / len(group_ranks)
            min_rank = min(group_ranks)
            max_rank = max(group_ranks)
            rank_diff = int(user_rank) - avg_rank

            if int(user_rank) <= min_rank:
                probability = "很高 (90%以上)"
                suggestion = "排名优于专业组内较高要求位次，可以作为保的选择"
                level = "保"
            elif rank_diff <= -5000:
                probability = "较高 (70%-90%)"
                suggestion = "排名优于平均位次，可以作为稳的选择"
                level = "稳"
            elif rank_diff <= 0:
                probability = "一般 (40%-70%)"
                suggestion = "排名接近平均位次，需要谨慎考虑"
                level = "冲"
            elif rank_diff <= 5000:
                probability = "较低 (10%-40%)"
                suggestion = "排名略低于平均位次，冲刺选择"
                level = "冲"
            else:
                probability = "很低 (10%以下)"
                suggestion = "排名差距较大，不建议报考"
                level = "不推荐"

            avg_score = sum(group_scores) / len(group_scores) if group_scores else 0
            return {
                "school": school_name,
                "major_group": extract_group_code(major_group) or plan_info.get("专业组代码"),
                "major_group_key": major_group_key or plan_info.get("专业组key"),
                "subject": plan_info.get("科目要求"),
                "user_score": user_score,
                "user_rank": user_rank,
                "group_avg_score": round(avg_score, 1) if avg_score else None,
                "group_min_score": min(group_scores) if group_scores else None,
                "group_max_score": max(group_scores) if group_scores else None,
                "group_avg_rank": round(avg_rank, 0),
                "group_min_rank": int(min_rank),
                "group_max_rank": int(max_rank),
                "rank_diff": round(rank_diff, 0),
                "probability": probability,
                "suggestion": suggestion,
                "level": level,
                "majors": metrics["2025"].get("majors") or metrics["2024"].get("majors") or [],
                "plan_info": plan_info,
                "school_metrics": MajorGroupSkill.analyze_school_level_metrics(school_name) if include_school_metrics else {},
                "major_metrics": metrics,
            }

        if group_scores and user_score:
            avg_score = sum(group_scores) / len(group_scores)
            min_score = min(group_scores)
            max_score = max(group_scores)
            score_diff = int(user_score) - avg_score

            if int(user_score) >= max_score:
                probability = "很高 (90%以上)"
                suggestion = "可以作为稳或保的选择"
                level = "保"
            elif score_diff >= -5:
                probability = "较高 (70%-90%)"
                suggestion = "可以作为稳的选择"
                level = "稳"
            elif score_diff >= -15:
                probability = "一般 (40%-70%)"
                suggestion = "需要谨慎考虑，可作为冲的选择"
                level = "冲"
            elif score_diff >= -25:
                probability = "较低 (10%-40%)"
                suggestion = "冲刺选择，风险较大"
                level = "冲"
            else:
                probability = "很低 (10%以下)"
                suggestion = "不建议报考"
                level = "不推荐"

            return {
                "school": school_name,
                "major_group": extract_group_code(major_group) or plan_info.get("专业组代码"),
                "major_group_key": major_group_key or plan_info.get("专业组key"),
                "subject": plan_info.get("科目要求"),
                "user_score": user_score,
                "user_rank": user_rank,
                "group_avg_score": round(avg_score, 1),
                "group_min_score": min_score,
                "group_max_score": max_score,
                "score_diff": round(score_diff, 1),
                "probability": probability,
                "suggestion": suggestion,
                "level": level,
                "majors": metrics["2025"].get("majors") or metrics["2024"].get("majors") or [],
                "plan_info": plan_info,
                "school_metrics": MajorGroupSkill.analyze_school_level_metrics(school_name) if include_school_metrics else {},
                "major_metrics": metrics,
            }

        return {
            "school": school_name,
            "major_group": extract_group_code(major_group) or plan_info.get("专业组代码"),
            "major_group_key": major_group_key or plan_info.get("专业组key"),
            "error": "无法提取分数数据",
            "plan_info": plan_info,
            "school_metrics": MajorGroupSkill.analyze_school_level_metrics(school_name) if include_school_metrics else {},
            "major_metrics": metrics,
        }

    @staticmethod
    def search_major_groups_by_major(major_name, year=2024, subject=None):
        groups = {}
        for row in filter_rows(MajorGroupSkill._load_plan_data(year), subject=subject):
            if major_name not in row.get("专业名称", ""):
                continue
            group_key = row.get("专业组key")
            if group_key not in groups:
                groups[group_key] = {
                    "school": row.get("学校"),
                    "group": row.get("专业组名称") or row.get("专业组代码"),
                    "group_number": row.get("专业组代码"),
                    "major_group_key": group_key,
                    "majors": [],
                    "subject": row.get("科类") or "N/A",
                    "subject_requirement": row.get("选科要求") or "N/A",
                    "total_plan": 0,
                    "admission_code": row.get("招生代码"),
                }
            groups[group_key]["majors"].append(row.get("专业名称"))
            groups[group_key]["total_plan"] += row.get("计划人数") or 0
        return [(item["school"], item) for item in groups.values()]

    @staticmethod
    def _select_recommendations(recommendations, min_recommendations=15, max_recommendations=45):
        level_order = {"保": 0, "稳": 1, "冲": 2, "不推荐": 3}
        recommendations.sort(
            key=lambda item: (
                level_order.get(item.get("level", "不推荐"), 3),
                item.get("group_avg_rank") or 10**9,
            )
        )

        chong = [r for r in recommendations if r.get("level") == "冲"]
        wen = [r for r in recommendations if r.get("level") == "稳"]
        bao = [r for r in recommendations if r.get("level") == "保"]
        print(f"  原始分布: 冲:{len(chong)} 稳:{len(wen)} 保:{len(bao)}")

        target_chong = min(len(chong), max(5, int(max_recommendations * 0.2)))
        target_wen = min(len(wen), max(10, int(max_recommendations * 0.4)))
        target_bao = min(len(bao), max(10, int(max_recommendations * 0.4)))
        selected = chong[:target_chong] + wen[:target_wen] + bao[:target_bao]

        if len(selected) < min_recommendations:
            for item in recommendations:
                if item not in selected:
                    selected.append(item)
                    if len(selected) >= min_recommendations:
                        break
        return selected[:max_recommendations]

    @staticmethod
    def get_major_groups_by_user_preference(
        user_score=580,
        user_rank=None,
        province=DEFAULT_PROVINCE,
        subject=None,
        score=None,
        rank=None,
        target_majors=None,
    ):
        """根据用户指定的专业获取专业组推荐（严格匹配）"""
        if score and not user_score:
            user_score = score
        if rank and not user_rank:
            user_rank = rank
        if not target_majors:
            print("❌ 错误：必须指定意向专业！")
            return []

        major_keywords = MajorGroupSkill._split_keywords(target_majors)
        print(f"  正在搜索专业组，关键词: {major_keywords}")
        if user_rank:
            print(f"  用户排名: {user_rank}")
        print("  ⚠️  所有推荐将严格包含你选择的专业，并按科类/专业组key隔离")

        all_groups = []
        for keyword in major_keywords:
            groups = MajorGroupSkill.search_major_groups_by_major(keyword, year=2025, subject=subject)
            all_groups.extend(groups)
            print(f"    关键词 '{keyword}' 找到 {len(groups)} 个专业组")

        unique_groups = {}
        for _, info in all_groups:
            unique_groups.setdefault(info["major_group_key"], info)
        print(f"  去重后 {len(unique_groups)} 个专业组")

        rank_hints = {}
        if user_rank:
            for row in filter_rows(MajorGroupSkill._load_score_data(2025), subject=subject):
                text = f"{row.get('专业名称', '')}{row.get('专业全称', '')}{row.get('专业备注', '')}"
                if not any(keyword in text for keyword in major_keywords):
                    continue
                rank_value = row.get("平均位次") or row.get("最低位次")
                if not rank_value:
                    continue
                rank_hints.setdefault(row.get("专业组key"), []).append(rank_value)
            rank_hints = {
                key: sum(values) / len(values)
                for key, values in rank_hints.items()
                if values
            }

        candidate_infos = list(unique_groups.values())
        if user_rank and rank_hints:
            candidate_infos.sort(
                key=lambda info: abs(rank_hints.get(info["major_group_key"], int(user_rank) + 200000) - int(user_rank))
            )
            candidate_infos = candidate_infos[:180]
            print(f"  已按位次相关性预筛，进入详细分析 {len(candidate_infos)} 个专业组")

        recommendations = []
        for info in candidate_infos[:300]:
            analysis = MajorGroupSkill.analyze_major_group_admission(
                info["group_number"],
                info["school"],
                user_score,
                user_rank,
                info["majors"],
                subject=subject,
                major_group_key=info["major_group_key"],
                include_school_metrics=False,
                include_historical=False,
            )
            if "error" not in analysis:
                majors_str = str(info["majors"])
                if any(keyword in majors_str for keyword in major_keywords):
                    recommendations.append(analysis)
                    rank_text = analysis.get("group_avg_rank", analysis.get("group_avg_score"))
                    print(f"    分析完成: {info['school']} - {analysis['level']} - 指标: {rank_text}")

        final_recommendations = MajorGroupSkill._select_recommendations(recommendations)
        print(
            f"  最终推荐: {len(final_recommendations)} 个志愿 "
            f"(冲:{len([r for r in final_recommendations if r.get('level') == '冲'])} "
            f"稳:{len([r for r in final_recommendations if r.get('level') == '稳'])} "
            f"保:{len([r for r in final_recommendations if r.get('level') == '保'])})"
        )
        return final_recommendations

    @staticmethod
    def get_medical_major_groups(
        user_score=580,
        user_rank=None,
        province=DEFAULT_PROVINCE,
        subject=None,
        score=None,
        rank=None,
        target_majors=None,
    ):
        if target_majors:
            keywords = target_majors
        else:
            keywords = "临床医学,口腔医学,中医学,药学,护理,医学,生物医学,针灸推拿,中西医,预防医学,麻醉学,影像学"
        return MajorGroupSkill.get_major_groups_by_user_preference(
            user_score=user_score,
            user_rank=user_rank,
            province=province,
            subject=subject,
            score=score,
            rank=rank,
            target_majors=keywords,
        )[:20]

    @staticmethod
    def compare_major_groups(major_groups, user_score, user_rank=None):
        comparisons = []
        for school, group in major_groups:
            comparisons.append(MajorGroupSkill.analyze_major_group_admission(group, school, user_score, user_rank))
        return MajorGroupSkill._select_recommendations(comparisons, min_recommendations=0)


SKILLS_MAP = {
    "get_major_group_scores": MajorGroupSkill.get_major_group_scores,
    "get_major_group_plan": MajorGroupSkill.get_major_group_plan,
    "analyze_major_group_admission": MajorGroupSkill.analyze_major_group_admission,
    "search_major_groups_by_major": MajorGroupSkill.search_major_groups_by_major,
    "get_medical_major_groups": MajorGroupSkill.get_medical_major_groups,
    "get_major_groups_by_user_preference": MajorGroupSkill.get_major_groups_by_user_preference,
    "compare_major_groups": MajorGroupSkill.compare_major_groups,
    "analyze_school_level_metrics": MajorGroupSkill.analyze_school_level_metrics,
    "analyze_major_level_metrics": MajorGroupSkill.analyze_major_level_metrics,
}

SKILL_DESCRIPTIONS = {
    "get_major_group_scores": "获取标准化专业组分数线(参数: school_name, major_group, major_names, year, subject, major_group_key)",
    "get_major_group_plan": "获取标准化专业组招生计划(参数: school_name, major_group, year, subject, major_group_key)",
    "analyze_major_group_admission": "分析专业组录取可能性(参数: major_group, school_name, user_score, user_rank, major_names, subject, major_group_key)",
    "search_major_groups_by_major": "根据专业名称搜索专业组(参数: major_name, year, subject)",
    "get_medical_major_groups": "获取医学相关专业组推荐(参数: user_score, user_rank, province, subject, score, rank, target_majors)",
    "get_major_groups_by_user_preference": "根据用户指定专业获取专业组推荐（严格匹配，15-45个）(参数: user_score, user_rank, province, subject, score, rank, target_majors)",
    "compare_major_groups": "对比多个专业组(参数: groups_info)",
    "analyze_school_level_metrics": "分析院校层面指标（位次、计划、扩招等）(参数: school_name)",
    "analyze_major_level_metrics": "分析专业层面指标（位次、计划、冷热程度等）(参数: school_name, major_group, major_names, subject, major_group_key)",
}
