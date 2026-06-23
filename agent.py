import os
import json
import requests
import time
from dotenv import load_dotenv
from skills import SKILL_DESCRIPTIONS, SKILL_CATEGORIES, call_skill

load_dotenv()

class GaokaoAgent:
    def __init__(self, agent_name="通用Agent"):
        self.agent_name = agent_name
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.api_base_url = os.getenv("OPENROUTER_API_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")
        self.conversation_history = []
        self.user_profile = {}
        self.step_count = 0
        self.output_dir = None
        self.raw_data_store = {}
        self.log_lines = []
    
    def set_output_dir(self, output_dir):
        """设置输出目录"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'raw_data'), exist_ok=True)
        print(f"📁 输出目录已设置: {output_dir}")
    
    def log(self, message):
        """记录日志"""
        self.log_lines.append(message)
        print(message)
    
    def save_output(self):
        """保存输出到文件"""
        if not self.output_dir:
            return
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        full_text = "\n".join(self.log_lines)
        text_file = os.path.join(self.output_dir, f"result_{timestamp}.txt")
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(full_text)
        print(f"\n📄 完整文本已保存: {text_file}")
        
        raw_data_file = os.path.join(self.output_dir, 'raw_data', f"raw_data_{timestamp}.json")
        with open(raw_data_file, 'w', encoding='utf-8') as f:
            json.dump(self.raw_data_store, f, ensure_ascii=False, indent=2)
        print(f"📊 原始数据已保存: {raw_data_file}")
    
    def set_user_profile(self, profile):
        """设置用户个人信息"""
        self.user_profile = profile
    
    def print_step(self, step_name, content=""):
        """打印步骤信息"""
        self.step_count += 1
        step_str = f"\n{'='*60}"
        self.log(step_str)
        step_str = f"📍 步骤 {self.step_count}: {step_name}"
        self.log(step_str)
        step_str = f"🤖 当前Agent: {self.agent_name}"
        self.log(step_str)
        step_str = f"{'='*60}"
        self.log(step_str)
        if content:
            self.log(content)
    
    def format_table(self, data):
        """格式化表格数据为文本"""
        if not data:
            return "无数据"
        if isinstance(data[0], dict):
            headers = list(data[0].keys())
            rows = [[item.get(header, "") for header in headers] for item in data]
        else:
            headers = data[0]
            rows = data[1:]
        
        col_widths = []
        for i in range(len(headers)):
            max_len = len(str(headers[i]))
            for row in rows:
                if isinstance(row, (list, tuple)) and i < len(row):
                    max_len = max(max_len, len(str(row[i])))
            col_widths.append(max_len + 2)
        
        result = "| " + " | ".join(str(h).ljust(w-2) for h, w in zip(headers, col_widths)) + " |\n"
        result += "|-" + "-|-".join("-"*(w-2) for w in col_widths) + "-|\n"
        
        for row in rows:
            if isinstance(row, (list, tuple)):
                row_str = []
                for i, w in enumerate(col_widths):
                    val = str(row[i]) if i < len(row) else ""
                    row_str.append(val.ljust(w-2))
                result += "| " + " | ".join(row_str) + " |\n"
        
        return result
    
    def build_system_prompt(self):
        """构建系统提示词"""
        profile_str = "\n".join(f"- {k}: {v}" for k, v in self.user_profile.items())
        
        skills_str = ""
        for category, skills in SKILL_CATEGORIES.items():
            skills_str += f"\n【{category}】\n"
            for skill_name in skills:
                skills_str += f"- {skill_name}: {SKILL_DESCRIPTIONS[skill_name]}\n"
        
        system_prompt = f"""你是一个专业的安徽高考志愿填报AI助手。

【用户个人信息】
{profile_str}

【可用技能列表】
{skills_str}

【重要说明】
现在高考志愿填报采用"学校+专业组"模式，推荐时必须推荐具体的"学校+专业组"组合，而不仅仅是学校。

【专业硬性筛选规则】
如果用户指定了目标专业（如医学、计算机、师范等），必须严格筛选，只推荐包含该专业的专业组，不得推荐无关专业组。
医学相关关键词：临床医学、口腔医学、中医学、药学、护理、医学、生物医学、针灸推拿、中西医、预防医学、麻醉学、影像学
计算机相关关键词：计算机、软件工程、人工智能、大数据、信息安全
师范相关关键词：师范、教育、小学教育、学前教育

【任务说明】
用户会提出关于高考志愿填报的问题，你需要：
1. 分析用户问题，判断需要调用哪些技能获取数据
2. 使用<call>标签调用技能，格式：<call>skill_name(param1=value1, param2=value2)</call>
3. 获取数据后，对数据进行分析和整理
4. 给出详细的志愿填报建议和推荐，必须包含"学校+专业组"组合

【输出格式】
- 如果需要调用技能，直接输出<call>标签
- 如果已经获取数据并完成分析，输出最终回答
- 回答中需要包含表格数据和分析结论
- 推荐必须包含具体的"学校+专业组"组合

【注意事项】
- 必须根据用户分数、排名、选科等信息进行精准推荐
- 推荐时要考虑冲稳保策略
- 可以多轮调用技能获取不同类别的数据
- 用中文回答，语气友好专业
- 推荐格式：学校名称(专业组名称) - 录取概率 - 推荐理由
"""
        return system_prompt
    
    def call_llm(self, messages):
        """调用LLM API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 4000
        }
        
        response = requests.post(f"{self.api_base_url}/chat/completions", headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    def extract_tool_calls(self, text):
        """从文本中提取tool_call"""
        tool_calls = []
        import re
        pattern = r"<call>(.+?)</call>"
        matches = re.findall(pattern, text, re.DOTALL)
        
        for match in matches:
            match = match.strip()
            if "(" in match and ")" in match:
                skill_name = match[:match.index("(")].strip()
                params_str = match[match.index("(")+1:match.index(")")]
                params = {}
                for param in params_str.split(","):
                    param = param.strip()
                    if "=" in param:
                        key, value = param.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip("'\"")
                        try:
                            params[key] = int(value)
                        except ValueError:
                            params[key] = value
                tool_calls.append({"skill": skill_name, "params": params})
        
        return tool_calls
    
    def run(self, user_question):
        """运行Agent处理用户问题"""
        self.log(f"\n{'='*80}")
        self.log("🎯 高考志愿填报AI系统启动")
        self.log(f"{'='*80}")
        
        self.print_step(f"开始处理问题: {user_question}")
        
        messages = [
            {"role": "system", "content": self.build_system_prompt()},
            {"role": "user", "content": user_question}
        ]
        
        max_rounds = 5
        for round_num in range(max_rounds):
            self.print_step(f"第 {round_num + 1} 轮对话")
            
            response = self.call_llm(messages)
            self.log(f"\n📝 LLM响应: {response[:500]}..." if len(response) > 500 else f"\n📝 LLM响应: {response}")
            
            tool_calls = self.extract_tool_calls(response)
            
            if not tool_calls:
                self.log("\n✅ 直接给出回答")
                self.log(f"\n{'='*80}")
                self.log("📊 最终分析结果")
                self.log(f"{'='*80}")
                self.log(response)
                self.save_output()
                return response
            
            self.log(f"\n🔧 检测到 {len(tool_calls)} 个技能调用")
            
            tool_results = []
            for tool_call in tool_calls:
                skill_name = tool_call["skill"]
                params = tool_call["params"]
                
                self.print_step(f"调用技能: {skill_name}", f"参数: {params}")
                result = call_skill(skill_name, **params)
                
                self.raw_data_store[f"{skill_name}_{len(self.raw_data_store)}"] = {
                    'skill_name': skill_name,
                    'params': params,
                    'result': result
                }
                if (
                    isinstance(result, list)
                    and any(isinstance(item, dict) and item.get('level') in ['冲', '稳', '保'] for item in result)
                ):
                    self.raw_data_store['recommendations'] = result
                
                if isinstance(result, list) and len(result) > 0:
                    formatted_result = self.format_table(result)
                    tool_results.append(f"【{skill_name}调用结果】\n{formatted_result}")
                else:
                    tool_results.append(f"【{skill_name}调用结果】\n{result}")
            
            tool_results_str = "\n\n".join(tool_results)
            
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"技能调用结果如下，请根据这些数据进行分析并给出最终回答：\n\n{tool_results_str}"})
        
        self.save_output()
        return "已达到最大对话轮数，请精简问题后重试。"


class MultiAgentSystem:
    def __init__(self):
        self.agents = {
            "score_agent": GaokaoAgent("分数线分析Agent"),
            "school_agent": GaokaoAgent("院校信息Agent"),
            "major_group_agent": GaokaoAgent("专业组分析Agent"),
            "strategy_agent": GaokaoAgent("策略推荐Agent")
        }
        self.step_count = 0
        self.output_dir = None
        self.all_log_lines = []
        self.all_raw_data = {}
    
    def set_output_dir(self, output_dir):
        """设置输出目录"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'raw_data'), exist_ok=True)
        for agent in self.agents.values():
            agent.set_output_dir(output_dir)
        print(f"📁 输出目录已设置: {output_dir}")
    
    def log(self, message):
        """记录日志"""
        self.all_log_lines.append(message)
        print(message)
    
    def save_output(self):
        """保存输出到文件"""
        if not self.output_dir:
            return
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # 生成表格汇总（如果有推荐结果）
        table_summary = self._generate_table_summary()
        if table_summary:
            # 在日志开头插入表格汇总
            self.all_log_lines.insert(0, table_summary)
        
        # 保存完整文本
        full_text = "\n".join(self.all_log_lines)
        text_file = os.path.join(self.output_dir, f"multi_agent_result_{timestamp}.txt")
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(full_text)
        print(f"\n📄 完整文本已保存: {text_file}")
        
        # 保存原始数据为JSON（保留原有格式）
        raw_data_file = os.path.join(self.output_dir, 'raw_data', f"multi_agent_raw_data_{timestamp}.json")
        with open(raw_data_file, 'w', encoding='utf-8') as f:
            json.dump(self.all_raw_data, f, ensure_ascii=False, indent=2)
        print(f"📊 原始数据已保存: {raw_data_file}")
        
        # 新增：分门别类保存为txt文件
        raw_data_dir = os.path.join(self.output_dir, 'raw_data')
        
        # 按学校分类保存
        school_data = {}
        for key, value in self.all_raw_data.items():
            if isinstance(value, dict) and 'school' in value:
                school_name = value['school']
                if school_name not in school_data:
                    school_data[school_name] = {}
                school_data[school_name][key] = value
        
        for school_name, data in school_data.items():
            school_file = os.path.join(raw_data_dir, f"{school_name}_{timestamp}.txt")
            with open(school_file, 'w', encoding='utf-8') as f:
                f.write(f"{'='*80}\n")
                f.write(f"🏛️ 院校: {school_name}\n")
                f.write(f"{'='*80}\n\n")
                for key, value in data.items():
                    f.write(f"【{key}】\n")
                    if isinstance(value, dict):
                        for k, v in value.items():
                            f.write(f"  {k}: {v}\n")
                    else:
                        f.write(f"  {value}\n")
                    f.write("\n")
            print(f"📁 院校数据已保存: {school_file}")
        
        # 按志愿分类保存（如果有推荐结果）
        if 'recommendations' in self.all_raw_data:
            recommendations = self.all_raw_data['recommendations']
            if isinstance(recommendations, list):
                for i, rec in enumerate(recommendations, 1):
                    if isinstance(rec, dict) and 'school' in rec:
                        school_name = rec['school']
                        group_name = rec.get('major_group', rec.get('group', ''))
                        volunteer_file = os.path.join(raw_data_dir, f"志愿{i}_{school_name}_{group_name}_{timestamp}.txt")
                        with open(volunteer_file, 'w', encoding='utf-8') as f:
                            f.write(f"{'='*80}\n")
                            f.write(f"📋 志愿 #{i}: {school_name}({group_name})\n")
                            f.write(f"{'='*80}\n\n")
                            for key, value in rec.items():
                                f.write(f"【{key}】\n")
                                if isinstance(value, dict):
                                    for k, v in value.items():
                                        f.write(f"  {k}: {v}\n")
                                else:
                                    f.write(f"  {value}\n")
                                f.write("\n")
                        print(f"📁 志愿数据已保存: {volunteer_file}")
    
    def _generate_table_summary(self):
        """生成志愿方案最终填报表格（15-45个推荐）"""
        # 从all_raw_data中获取recommendations
        recommendations = []
        
        # 直接查找recommendations
        if 'recommendations' in self.all_raw_data:
            recommendations = self.all_raw_data['recommendations']
        else:
            # 从all_raw_data中搜索包含level信息的记录
            for key, value in self.all_raw_data.items():
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict) and item.get('level') in ['冲', '稳', '保']:
                            recommendations.append(item)
                elif isinstance(value, dict) and isinstance(value.get('result'), list):
                    for item in value['result']:
                        if isinstance(item, dict) and item.get('level') in ['冲', '稳', '保']:
                            recommendations.append(item)
        
        if not isinstance(recommendations, list) or len(recommendations) == 0:
            return None
        
        # 按冲稳保分类
        chong = [r for r in recommendations if r.get('level') == '冲']
        wen = [r for r in recommendations if r.get('level') == '稳']
        bao = [r for r in recommendations if r.get('level') == '保']
        
        # 按比例选取：冲5个 + 稳15个 + 保25个 = 45个（上限）
        selected_chong = chong[:min(5, len(chong))]
        selected_wen = wen[:min(15, len(wen))]
        selected_bao = bao[:min(25, len(bao))]
        selected = selected_chong + selected_wen + selected_bao
        
        # 如果总数不足15个，从剩余中补充
        if len(selected) < 15:
            for r in recommendations:
                if r not in selected:
                    selected.append(r)
                    if len(selected) >= 15:
                        break
        
        # 限制最多45个
        selected = selected[:45]
        
        summary_lines = []
        summary_lines.append("="*120)
        summary_lines.append("🎯 志愿方案最终填报表格")
        summary_lines.append("="*120)
        summary_lines.append("")
        
        # 表头（符合高考志愿填报格式）
        summary_lines.append("┌──────┬────────────────────────────────┬────────────┬──────────┬──────────────┬────────────┬────────────┬────────────┐")
        summary_lines.append("│ 志愿 │ 学校名称                      │ 专业组代码 │ 科目要求 │ 包含专业     │ 录取概率   │ 平均位次   │ 计划人数   │")
        summary_lines.append("├──────┼────────────────────────────────┼────────────┼──────────┼──────────────┼────────────┼────────────┼────────────┤")
        
        # 填写志愿（按冲稳保顺序）
        for i, rec in enumerate(selected, 1):
            school = rec.get('school', 'N/A')[:28]
            group = rec.get('major_group', rec.get('group', 'N/A'))[:10]
            subject = rec.get('subject', 'N/A')[:8]
            majors = rec.get('majors', [])
            majors_str = '; '.join(majors[:3]) if isinstance(majors, list) else str(rec.get('majors', 'N/A'))[:20]
            prob = rec.get('probability', 'N/A')[:10]
            avg_rank = rec.get('group_avg_rank', rec.get('avg_rank', 'N/A'))
            plan = rec.get('plan_info', {}).get('计划总数', rec.get('plan', 'N/A'))
            
            summary_lines.append(f"│ {i:4d} │ {school:28s} │ {group:10s} │ {subject:8s} │ {majors_str:20s} │ {prob:10s} │ {str(avg_rank):10s} │ {str(plan):10s} │")
        
        summary_lines.append("└──────┴────────────────────────────────┴────────────┴──────────┴──────────────┴────────────┴────────────┴────────────┘")
        summary_lines.append("")
        
        # 统计信息
        final_chong = len([r for r in selected if r.get('level') == '冲'])
        final_wen = len([r for r in selected if r.get('level') == '稳'])
        final_bao = len([r for r in selected if r.get('level') == '保'])
        
        summary_lines.append(f"📊 填报统计：")
        summary_lines.append(f"  总计: {len(selected)} 个志愿")
        summary_lines.append(f"  冲一冲: {final_chong} 个（录取概率较低，尝试冲击更高层次院校）")
        summary_lines.append(f"  稳一稳: {final_wen} 个（录取概率较高，匹配自身分数段）")
        summary_lines.append(f"  保一保: {final_bao} 个（录取概率很高，确保有学可上）")
        summary_lines.append("")
        summary_lines.append(f"备选库: 共 {len(recommendations)} 个专业组可选择")
        summary_lines.append("")
        summary_lines.append("="*120)
        summary_lines.append("")
        
        return "\n".join(summary_lines)
    
    def set_user_profile(self, profile):
        """设置用户信息到所有Agent"""
        for agent in self.agents.values():
            agent.set_user_profile(profile)
    
    def print_system_step(self, step_name, content=""):
        """打印系统步骤信息"""
        self.step_count += 1
        step_str = f"\n{'='*60}"
        self.log(step_str)
        step_str = f"📍 系统步骤 {self.step_count}: {step_name}"
        self.log(step_str)
        step_str = f"{'='*60}"
        self.log(step_str)
        if content:
            self.log(content)
    
    def run_multi_agent(self, user_question):
        """多Agent协作处理"""
        self.log(f"\n{'='*80}")
        self.log("🎯 多Agent高考志愿分析系统启动")
        self.log(f"{'='*80}")
        
        self.print_system_step("启动多Agent高考志愿分析系统")
        
        analysis_results = []
        
        # 保存完整log的文件路径
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        if self.output_dir:
            self.full_log_file = os.path.join(self.output_dir, f"full_log_{timestamp}.txt")
            # 清空文件
            with open(self.full_log_file, 'w', encoding='utf-8') as f:
                f.write('')
        else:
            self.full_log_file = None
        
        def log_and_save(message):
            """同时输出和保存完整log"""
            self.log(message)
            if self.full_log_file:
                with open(self.full_log_file, 'a', encoding='utf-8') as f:
                    f.write(message + '\n')
        
        # ========== Agent 1: 分数线分析 ==========
        self.log("\n" + "🎓"*30)
        self.log("📊 分数线分析Agent开始工作")
        self.log("🎓"*30)
        if self.full_log_file:
            with open(self.full_log_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "="*80 + "\n")
                f.write("📊 Agent 1: 分数线分析\n")
                f.write("="*80 + "\n")
        
        score_question = f"用户问题：{user_question}。请分析分数线相关数据，包括批次线、院校分数线、专业组分数线等。"
        score_result = self.agents["score_agent"].run(score_question)
        analysis_results.append(("分数线分析", score_result))
        self.all_raw_data.update(self.agents["score_agent"].raw_data_store)
        self.all_log_lines.extend(self.agents["score_agent"].log_lines)
        
        # 保存分数线分析Agent的完整输出
        if self.output_dir:
            score_agent_file = os.path.join(self.output_dir, 'agent_outputs', f"01_score_agent_{timestamp}.txt")
            os.makedirs(os.path.dirname(score_agent_file), exist_ok=True)
            with open(score_agent_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("📊 Agent 1: 分数线分析\n")
                f.write("="*80 + "\n\n")
                f.write("【Agent分析过程】\n")
                f.write("\n".join(self.agents["score_agent"].log_lines))
                f.write("\n\n【最终分析结果】\n")
                f.write(score_result)
            print(f"📄 Agent 1 输出已保存: {score_agent_file}")
        
        # ========== Agent 2: 院校信息 ==========
        self.log("\n" + "🏫"*30)
        self.log("🏫 院校信息Agent开始工作")
        self.log("🏫"*30)
        if self.full_log_file:
            with open(self.full_log_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "="*80 + "\n")
                f.write("🏫 Agent 2: 院校信息\n")
                f.write("="*80 + "\n")
        
        school_question = f"用户问题：{user_question}。请分析院校信息，包括院校排名、学科评估、院校基础信息等。"
        school_result = self.agents["school_agent"].run(school_question)
        analysis_results.append(("院校分析", school_result))
        self.all_raw_data.update(self.agents["school_agent"].raw_data_store)
        self.all_log_lines.extend(self.agents["school_agent"].log_lines)
        
        # 保存院校信息Agent的完整输出
        if self.output_dir:
            school_agent_file = os.path.join(self.output_dir, 'agent_outputs', f"02_school_agent_{timestamp}.txt")
            with open(school_agent_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("🏫 Agent 2: 院校信息\n")
                f.write("="*80 + "\n\n")
                f.write("【Agent分析过程】\n")
                f.write("\n".join(self.agents["school_agent"].log_lines))
                f.write("\n\n【最终分析结果】\n")
                f.write(school_result)
            print(f"📄 Agent 2 输出已保存: {school_agent_file}")
        
        # ========== Agent 3: 专业组分析 ==========
        self.log("\n" + "🎯"*30)
        self.log("🎯 专业组分析Agent开始工作")
        self.log("🎯"*30)
        if self.full_log_file:
            with open(self.full_log_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "="*80 + "\n")
                f.write("🎯 Agent 3: 专业组分析\n")
                f.write("="*80 + "\n")
        
        major_group_question = f"用户问题：{user_question}。请重点分析专业组信息，包括专业组分数线、招生计划、录取可能性等。"
        major_group_result = self.agents["major_group_agent"].run(major_group_question)
        analysis_results.append(("专业组分析", major_group_result))
        self.all_raw_data.update(self.agents["major_group_agent"].raw_data_store)
        self.all_log_lines.extend(self.agents["major_group_agent"].log_lines)
        
        # 保存专业组分析Agent的完整输出
        if self.output_dir:
            major_agent_file = os.path.join(self.output_dir, 'agent_outputs', f"03_major_group_agent_{timestamp}.txt")
            with open(major_agent_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("🎯 Agent 3: 专业组分析\n")
                f.write("="*80 + "\n\n")
                f.write("【Agent分析过程】\n")
                f.write("\n".join(self.agents["major_group_agent"].log_lines))
                f.write("\n\n【最终分析结果】\n")
                f.write(major_group_result)
            print(f"📄 Agent 3 输出已保存: {major_agent_file}")
        
        # ========== Agent 4: 策略推荐 ==========
        self.log("\n" + "💡"*30)
        self.log("💡 策略推荐Agent开始工作")
        self.log("💡"*30)
        if self.full_log_file:
            with open(self.full_log_file, 'a', encoding='utf-8') as f:
                f.write("\n" + "="*80 + "\n")
                f.write("💡 Agent 4: 策略推荐\n")
                f.write("="*80 + "\n")
        
        strategy_question = f"综合以下分析结果，请给出最终的志愿填报推荐方案（冲稳保策略），必须包含具体的'学校+专业组'组合：\n\n"
        for name, result in analysis_results:
            strategy_question += f"【{name}】\n{result}\n\n"
        
        strategy_result = self.agents["strategy_agent"].run(strategy_question)
        analysis_results.append(("策略推荐", strategy_result))
        self.all_raw_data.update(self.agents["strategy_agent"].raw_data_store)
        self.all_log_lines.extend(self.agents["strategy_agent"].log_lines)
        
        # 保存策略推荐Agent的完整输出
        if self.output_dir:
            strategy_agent_file = os.path.join(self.output_dir, 'agent_outputs', f"04_strategy_agent_{timestamp}.txt")
            with open(strategy_agent_file, 'w', encoding='utf-8') as f:
                f.write("="*80 + "\n")
                f.write("💡 Agent 4: 策略推荐\n")
                f.write("="*80 + "\n\n")
                f.write("【Agent分析过程】\n")
                f.write("\n".join(self.agents["strategy_agent"].log_lines))
                f.write("\n\n【最终分析结果】\n")
                f.write(strategy_result)
            print(f"📄 Agent 4 输出已保存: {strategy_agent_file}")
        
        self.print_system_step("多Agent分析完成")
        
        # 保存完整命令行log
        if self.full_log_file:
            print(f"📄 完整命令行log已保存: {self.full_log_file}")
        
        self.save_output()
        
        return analysis_results
