import os
import sys
import io
import time
from agent import GaokaoAgent, MultiAgentSystem
from skills import call_skill
from skills.school_analysis_skill import SchoolAnalysisSkill

# 保存输出的文件路径
output_file = None

class Tee:
    """同时输出到屏幕和文件的类"""
    def __init__(self, original, filename):
        self.original = original
        self.filename = filename
        # 清空文件
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('')
    
    def write(self, text):
        if text:  # 避免写入空字符串
            self.original.write(text)
            with open(self.filename, 'a', encoding='utf-8') as f:
                f.write(text)
    
    def flush(self):
        self.original.flush()
    
    def fileno(self):
        return self.original.fileno()
    
    def isatty(self):
        return self.original.isatty()

def log_output(message):
    """同时输出到屏幕和文件"""
    print(message)
    if output_file:
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(message + '\n')

def print_banner():
    banner = """
╔════════════════════════════════════════════════════════════╗
║            🎓 AI辅助高考志愿填报系统 v1.0                  ║
║            安徽高考数据智能分析平台                        ║
╚════════════════════════════════════════════════════════════╝
    """
    print(banner)

def get_user_profile():
    """获取用户个人信息"""
    print("\n📋 请输入你的个人信息（用于精准推荐）：")
    print("⚠️  注意：排名是主要对标往年数据的指标，请务必填写准确排名！")
    
    profile = {}
    
    # 必填项：全省排名（主要对标指标）
    while True:
        ranking = input("1. 全省排名（必填，主要对标往年数据）：").strip()
        if ranking.isdigit():
            profile["全省排名"] = int(ranking)
            break
        print("❌ 排名是必填项！请输入有效的排名数字！")
    
    # 必填项：意向专业
    while True:
        major = input("2. 意向专业（必填，可多选，用逗号分隔，如：数学,计算机,物理）：").strip()
        if major:
            profile["意向专业"] = major
            break
        print("❌ 意向专业是必填项！请输入你感兴趣的专业！")
    
    # 分数（可选，作为辅助参考）
    while True:
        score = input("3. 高考总分（可选，作为辅助参考）：").strip()
        if not score:
            # 根据排名估算分数
            profile["高考总分"] = None
            print("ℹ️  未填写分数，系统将根据排名进行分析")
            break
        if score.isdigit():
            profile["高考总分"] = int(score)
            break
        print("请输入有效的分数！")
    
    while True:
        category = input("4. 科类（理科/文科/历史类/物理类）：").strip()
        if category in ["理科", "文科", "历史类", "物理类"]:
            profile["科类"] = category
            break
        print("请输入有效的科类！")
    
    while True:
        batch = input("5. 目标批次（本科/专科/提前批）：").strip()
        if batch in ["本科", "专科", "提前批"]:
            profile["目标批次"] = batch
            break
        print("请输入有效的批次！")
    
    print("\n🎯 请输入你的择校意向（可选）：")
    profile["意向城市"] = input("6. 意向城市（可多选，用逗号分隔，留空表示不限制）：").strip()
    profile["院校偏好"] = input("7. 院校偏好（如：985/211/双一流/省内高校等）：").strip()
    profile["就业方向"] = input("8. 就业方向期望：").strip()
    
    print("\n✅ 个人信息已录入！")
    print(f"📌 核心指标：排名 {profile['全省排名']} + 意向专业 {profile['意向专业']}")
    print("ℹ️  所有推荐将严格围绕你选择的专业进行筛选")
    return profile

def print_profile(profile):
    """打印用户个人信息"""
    print("\n📊 当前用户信息：")
    print("-" * 40)
    for key, value in profile.items():
        print(f"{key}: {value}")
    print("-" * 40)

def main():
    global output_file
    
    print_banner()
    
    print("欢迎使用AI辅助高考志愿填报系统！")
    print("本系统提供两大核心功能：")
    print("")
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │  1️⃣  了解学校 - 分析指定学校的综合信息（历年分数线、  │")
    print("  │                      招生计划、专业详情等）           │")
    print("  │                                                         │")
    print("  │  2️⃣  志愿推荐 - 根据您的分数/排名，制定冲稳保志愿方案  │")
    print("  │                      并生成最终填报表格                 │")
    print("  └─────────────────────────────────────────────────────────┘")
    print("")
    
    while True:
        choice = input("请选择功能（输入 1 或 2，输入 exit 退出）：").strip()
        if choice.lower() == 'exit':
            print("\n👋 感谢使用AI辅助高考志愿填报系统！祝你高考顺利！")
            return
        if choice in ["1", "2"]:
            break
        print("❌ 请输入有效的选项（1 或 2）！")
    
    # 创建输出目录
    output_dir = os.path.join('/Users/lingziyang/Desktop/Gaokao', 'output', time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, 'result.txt')
    
    # 重定向 stdout 到文件，同时保持屏幕输出
    old_stdout = sys.stdout
    sys.stdout = Tee(old_stdout, output_file)
    
    if choice == "1":
        # 功能1：了解学校
        print("\n" + "🎯"*30)
        print("🎯 已选择：了解学校")
        print("🎯"*30)
        
        while True:
            school_name = input("\n请输入要查询的学校名称（输入 exit 返回主菜单）：").strip()
            if school_name.lower() == 'exit':
                print("\n已返回主菜单")
                sys.stdout = old_stdout
                main()  # 重新启动主菜单
                return
            
            if not school_name:
                print("❌ 请输入学校名称！")
                continue
            
            print(f"\n🏫 正在分析: {school_name}")
            print("⏳ 正在从多个数据源提取学校信息...")
            
            try:
                from skills.school_analysis_skill import SchoolAnalysisSkill
                school_data = SchoolAnalysisSkill.get_comprehensive_school_analysis(school_name)
                
                if not school_data.get('基础信息') and not school_data.get('历年分数线'):
                    print(f"❌ 未找到学校: {school_name}，请检查学校名称是否正确")
                    continue
                
                report = SchoolAnalysisSkill.format_comprehensive_report(school_data)
                print("\n" + "="*80)
                print(f"🏫 {school_name} - 综合信息分析报告")
                print("="*80)
                print(report)
                print("="*80)
                print(f"\n📄 报告已保存到: {output_file}")
                print(f"📁 输出目录: {output_dir}")
                
            except Exception as e:
                print(f"❌ 分析失败: {e}")
        
    else:
        # 功能2：志愿推荐
        print("\n" + "📝"*30)
        print("📝 已选择：志愿推荐")
        print("📝"*30)
        
        profile = get_user_profile()
        
        print("\n请选择使用模式：")
        print("1. 单Agent模式（快速问答）")
        print("2. 多Agent模式（全面分析）")
        
        while True:
            mode = input("请输入选择（1/2）：").strip()
            if mode in ["1", "2"]:
                break
            print("请输入有效的选项！")
        
        if mode == "1":
            agent = GaokaoAgent()
            agent.set_user_profile(profile)
            print("\n🚀 已启动单Agent模式")
        else:
            agent = MultiAgentSystem()
            agent.set_user_profile(profile)
            agent.set_output_dir(output_dir)
            print("\n🚀 已启动多Agent模式")
        
        print("\n" + "=" * 60)
        print("💡 提示：你可以提出关于志愿填报的任何问题，例如：")
        print("   - 我的分数能上哪些大学？")
        print("   - 推荐一些计算机专业的高校")
        print("   - 帮我制定冲稳保志愿方案")
        print("=" * 60)
        
        while True:
            print("\n" + "-" * 40)
            question = input("请输入你的问题（输入 exit 返回主菜单，输入 menu 返回功能选择）：").strip()
            
            if question.lower() == "exit":
                print("\n👋 感谢使用AI辅助高考志愿填报系统！")
                print("祝你高考顺利，金榜题名！")
                print(f"\n📄 完整输出已保存到: {output_file}")
                sys.stdout = old_stdout
                return
            
            if question.lower() == "menu":
                print("\n已返回功能选择菜单")
                sys.stdout = old_stdout
                main()  # 重新启动主菜单
                return
            
            if not question:
                print("请输入问题！")
                continue
            
            print("\n⏳ 正在分析你的问题...")
            
            try:
                if mode == "1":
                    result = agent.run(question)
                    print("\n" + "=" * 60)
                    print("🎓 AI分析结果：")
                    print("=" * 60)
                    print(result)
                else:
                    results = agent.run_multi_agent(question)
                    print("\n" + "=" * 60)
                    print("🎓 多Agent综合分析结果：")
                    print("=" * 60)
                    
                    for name, result in results:
                        print(f"\n--- {name} ---")
                        print(result)
                    
                    # 检查是否有志愿方案表格
                    table = agent._generate_table_summary()
                    if table:
                        print("\n" + table)
                    
                    print("\n" + "=" * 60)
                    print("🎉 分析完成！")
                    print("=" * 60)
            
            except Exception as e:
                print(f"\n❌ 发生错误：{e}")
                print("请检查网络连接或API配置后重试。")

if __name__ == "__main__":
    main()
