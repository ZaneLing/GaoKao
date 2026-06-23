from .score_line_skill import SKILLS_MAP as score_line_skills, SKILL_DESCRIPTIONS as score_line_descriptions
from .enrollment_plan_skill import SKILLS_MAP as enrollment_plan_skills, SKILL_DESCRIPTIONS as enrollment_plan_descriptions
from .school_info_skill import SKILLS_MAP as school_info_skills, SKILL_DESCRIPTIONS as school_info_descriptions
from .major_info_skill import SKILLS_MAP as major_info_skills, SKILL_DESCRIPTIONS as major_info_descriptions
from .reference_data_skill import SKILLS_MAP as reference_data_skills, SKILL_DESCRIPTIONS as reference_data_descriptions
from .major_group_skill import SKILLS_MAP as major_group_skills, SKILL_DESCRIPTIONS as major_group_descriptions
from .school_analysis_skill import SKILLS_MAP as school_analysis_skills, SKILL_DESCRIPTIONS as school_analysis_descriptions

SKILLS_MAP = {}
SKILL_DESCRIPTIONS = {}

SKILLS_MAP.update(score_line_skills)
SKILL_DESCRIPTIONS.update(score_line_descriptions)

SKILLS_MAP.update(enrollment_plan_skills)
SKILL_DESCRIPTIONS.update(enrollment_plan_descriptions)

SKILLS_MAP.update(school_info_skills)
SKILL_DESCRIPTIONS.update(school_info_descriptions)

SKILLS_MAP.update(major_info_skills)
SKILL_DESCRIPTIONS.update(major_info_descriptions)

SKILLS_MAP.update(reference_data_skills)
SKILL_DESCRIPTIONS.update(reference_data_descriptions)

SKILLS_MAP.update(major_group_skills)
SKILL_DESCRIPTIONS.update(major_group_descriptions)

SKILLS_MAP.update(school_analysis_skills)
SKILL_DESCRIPTIONS.update(school_analysis_descriptions)

SKILL_CATEGORIES = {
    '分数线分析': list(score_line_descriptions.keys()),
    '招生计划': list(enrollment_plan_descriptions.keys()),
    '院校信息': list(school_info_descriptions.keys()),
    '专业信息': list(major_info_descriptions.keys()),
    '专业组分析': list(major_group_descriptions.keys()),
    '学校综合分析': list(school_analysis_descriptions.keys()),
    '参考数据': list(reference_data_descriptions.keys()),
}

def call_skill(skill_name, **kwargs):
    if skill_name not in SKILLS_MAP:
        return f"错误：未知的skill: {skill_name}"
    
    print(f"🔍 正在调用技能: {skill_name} ({SKILL_DESCRIPTIONS[skill_name]})")
    print(f"   参数: {kwargs}")
    
    try:
        result = SKILLS_MAP[skill_name](**kwargs)
        print(f"✅ 技能调用成功，返回数据")
        return result
    except Exception as e:
        print(f"❌ 技能调用失败: {e}")
        return f"错误: {e}"
