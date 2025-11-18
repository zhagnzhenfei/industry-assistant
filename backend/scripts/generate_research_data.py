"""
生成研报演示数据
用于Text2SQL智能体测试
"""
import asyncio
import asyncpg
import random
from datetime import datetime, timedelta
import os


# 配置
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
    'database': 'research_reports_db'
}

# 研报标题模板
REPORT_TITLE_TEMPLATES = [
    "{company}：{event}，{conclusion}",
    "{company}：{aspect}{trend}，{rating}",
    "{company}{period}业绩{performance}，{outlook}",
    "{company}：{product}表现{result}",
    "{company}调研纪要：{insight}",
]

# 事件
EVENTS = [
    "新产品发布",
    "业绩超预期",
    "战略转型加速",
    "海外市场突破",
    "并购重组",
    "管理层变动",
    "分拆上市",
    "回购计划公布",
]

# 结论
CONCLUSIONS = [
    "维持买入评级",
    "上调目标价",
    "业绩拐点确立",
    "长期增长逻辑不变",
    "估值优势显著",
    "下调盈利预测",
]

# 方面
ASPECTS = [
    "核心业务",
    "新兴业务",
    "盈利能力",
    "市场份额",
    "产品创新",
    "运营效率",
]

# 趋势
TRENDS = [
    "持续改善",
    "超预期增长",
    "增速放缓",
    "稳健发展",
    "快速扩张",
]

# 展望
OUTLOOKS = [
    "全年目标可期",
    "增长动能充足",
    "关注政策变化",
    "静待基本面改善",
    "长期看好",
]

# 业绩表现
PERFORMANCES = [
    "超预期",
    "符合预期",
    "略低于预期",
    "大幅增长",
    "稳健增长",
]

# 产品
PRODUCTS = [
    "新品",
    "核心产品",
    "旗舰机型",
    "创新业务",
]

# 结果
RESULTS = [
    "亮眼",
    "不及预期",
    "稳健",
    "强劲",
]

# 洞察
INSIGHTS = [
    "管理层信心十足",
    "产能扩张计划明确",
    "新品即将发布",
    "市场竞争加剧",
    "成本控制良好",
]

# 报告类型
REPORT_TYPES = ['深度报告', '快评', '调研纪要', '行业报告', '季度报告', '月度报告']

# 评级及其概率
RATINGS = ['买入', '增持', '中性', '减持', '卖出']
RATING_WEIGHTS = [0.40, 0.30, 0.20, 0.08, 0.02]  # 买入40%，卖出2%

# 主题标签库
TOPICS = [
    '云计算', '人工智能', '大数据', '物联网', '5G', '元宇宙',
    '电动车', '自动驾驶', '动力电池', '充电桩',
    '芯片', '半导体', '国产替代',
    '医疗器械', '创新药', '生物医药',
    '白酒', '消费升级', '下沉市场',
    '金融科技', '数字货币', '区块链',
    'ESG', '碳中和', '绿色能源',
    '跨境电商', '直播电商', '社区团购',
]


def generate_report_title(company_name):
    """生成研报标题"""
    template = random.choice(REPORT_TITLE_TEMPLATES)
    
    # 随机选择时期
    periods = ['Q1', 'Q2', 'Q3', 'Q4', '半年度', '年度', '一季度']
    
    title = template.format(
        company=company_name.replace('股份有限公司', '').replace('有限公司', ''),
        event=random.choice(EVENTS),
        conclusion=random.choice(CONCLUSIONS),
        aspect=random.choice(ASPECTS),
        trend=random.choice(TRENDS),
        rating=random.choice(['维持买入', '维持增持', '上调至买入', '下调至中性']),
        period=random.choice(periods),
        performance=random.choice(PERFORMANCES),
        outlook=random.choice(OUTLOOKS),
        product=random.choice(PRODUCTS),
        result=random.choice(RESULTS),
        insight=random.choice(INSIGHTS)
    )
    
    return title


def generate_abstract(company_name, rating):
    """生成研报摘要"""
    templates = [
        f"公司{random.choice(['核心业务', '主营业务', '传统业务'])}{random.choice(['稳健增长', '快速扩张', '持续改善'])}，"
        f"{random.choice(['新兴业务', '创新业务', '海外业务'])}{random.choice(['表现亮眼', '超预期', '增长强劲'])}。"
        f"预计{random.choice(['今年', '明年', '未来三年'])}{random.choice(['营收', '净利润', '毛利率'])}将"
        f"{random.choice(['增长', '提升', '改善'])}约{random.randint(10, 50)}%。",
        
        f"公司在{random.choice(['产品创新', '技术研发', '市场拓展', '成本控制'])}方面取得显著进展。"
        f"{random.choice(['市场份额', '品牌影响力', '客户粘性'])}{random.choice(['持续提升', '稳步增长', '优势明显']}。"
        f"维持{rating}评级。",
        
        f"{random.choice(['受益于', '得益于', '基于'])}{random.choice(['行业景气度提升', '政策支持', '需求旺盛', '竞争格局改善'])}，"
        f"公司{random.choice(['业绩', '收入', '利润'])}表现{random.choice(['强劲', '稳健', '超预期'])}。"
        f"预计{random.choice(['短期', '中期', '长期'])}增长{random.choice(['动能充足', '逻辑清晰', '确定性高'])}。"
    ]
    
    return random.choice(templates)


def generate_random_date(start_year=2020, end_year=2024):
    """生成随机日期"""
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randint(0, days_between)
    
    return start_date + timedelta(days=random_days)


async def generate_more_reports(conn, count=100):
    """生成更多研报数据"""
    print(f"开始生成{count}条研报数据...")
    
    # 获取所有公司
    companies = await conn.fetch("SELECT id, name FROM companies")
    # 获取所有分析师
    analysts = await conn.fetch("SELECT id FROM analysts")
    
    if not companies or not analysts:
        print("错误：数据库中没有公司或分析师数据")
        return
    
    reports_data = []
    topics_data = []
    
    for i in range(count):
        company = random.choice(companies)
        analyst_id = random.choice(analysts)['id']
        
        # 生成基础信息
        title = generate_report_title(company['name'])
        report_type = random.choice(REPORT_TYPES)
        publish_date = generate_random_date()
        rating = random.choices(RATINGS, weights=RATING_WEIGHTS)[0]
        
        # 生成价格（目标价高于当前价）
        current_price = round(random.uniform(10, 500), 2)
        price_change = random.uniform(0.05, 0.35) if rating in ['买入', '增持'] else random.uniform(-0.15, 0.10)
        target_price = round(current_price * (1 + price_change), 2)
        
        # 生成摘要
        abstract = generate_abstract(company['name'], rating)
        
        # 其他信息
        page_count = random.randint(15, 60)
        views = random.randint(50, 5000)
        downloads = random.randint(10, 500)
        
        reports_data.append((
            title, company['id'], analyst_id, report_type,
            publish_date, rating, target_price, current_price,
            abstract, page_count, views, downloads
        ))
        
        if (i + 1) % 20 == 0:
            print(f"已生成 {i + 1}/{count} 条研报")
    
    # 批量插入研报
    await conn.executemany(
        """
        INSERT INTO research_reports 
        (title, company_id, analyst_id, report_type, publish_date, 
         rating, target_price, current_price, abstract, page_count, views, downloads)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """,
        reports_data
    )
    
    print(f"✅ 成功插入 {count} 条研报数据")
    
    # 为每篇研报生成2-4个主题标签
    print("开始生成主题标签...")
    report_ids = await conn.fetch(
        "SELECT id FROM research_reports WHERE id > 20 ORDER BY id"
    )
    
    for report in report_ids:
        topic_count = random.randint(2, 4)
        selected_topics = random.sample(TOPICS, topic_count)
        
        for topic in selected_topics:
            relevance = round(random.uniform(0.70, 1.00), 2)
            topics_data.append((report['id'], topic, relevance))
    
    # 批量插入主题标签
    await conn.executemany(
        """
        INSERT INTO report_topics (report_id, topic, relevance)
        VALUES ($1, $2, $3)
        """,
        topics_data
    )
    
    print(f"✅ 成功插入 {len(topics_data)} 条主题标签")


async def update_statistics(conn):
    """更新统计信息"""
    print("\n更新统计信息...")
    
    # 统计各表数据量
    companies_count = await conn.fetchval("SELECT COUNT(*) FROM companies")
    analysts_count = await conn.fetchval("SELECT COUNT(*) FROM analysts")
    reports_count = await conn.fetchval("SELECT COUNT(*) FROM research_reports")
    industries_count = await conn.fetchval("SELECT COUNT(*) FROM industries")
    topics_count = await conn.fetchval("SELECT COUNT(*) FROM report_topics")
    
    # 统计评级分布
    rating_dist = await conn.fetch(
        """
        SELECT rating, COUNT(*) as count 
        FROM research_reports 
        GROUP BY rating 
        ORDER BY count DESC
        """
    )
    
    # 统计最活跃的分析师
    top_analysts = await conn.fetch(
        """
        SELECT a.name, a.institution, COUNT(r.id) as report_count
        FROM analysts a
        LEFT JOIN research_reports r ON a.id = r.analyst_id
        GROUP BY a.id, a.name, a.institution
        ORDER BY report_count DESC
        LIMIT 5
        """
    )
    
    # 打印统计信息
    print("\n" + "="*70)
    print("📊 数据库统计信息")
    print("="*70)
    print(f"公司数量: {companies_count}")
    print(f"分析师数量: {analysts_count}")
    print(f"研报数量: {reports_count}")
    print(f"行业数量: {industries_count}")
    print(f"主题标签数: {topics_count}")
    
    print("\n评级分布:")
    for row in rating_dist:
        percentage = (row['count'] / reports_count * 100)
        print(f"  {row['rating']}: {row['count']} ({percentage:.1f}%)")
    
    print("\n最活跃分析师 (Top 5):")
    for i, analyst in enumerate(top_analysts, 1):
        print(f"  {i}. {analyst['name']} ({analyst['institution']}): {analyst['report_count']}篇")
    
    print("="*70)


async def main():
    """主函数"""
    print("="*70)
    print("🚀 研报数据生成脚本")
    print("="*70)
    print(f"数据库: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print()
    
    try:
        # 连接数据库
        print("正在连接数据库...")
        conn = await asyncpg.connect(**DB_CONFIG)
        print("✅ 数据库连接成功")
        
        # 检查基础数据是否存在
        companies_count = await conn.fetchval("SELECT COUNT(*) FROM companies")
        if companies_count == 0:
            print("\n⚠️  警告：数据库中没有公司数据！")
            print("请先运行 setup_research_reports_db.sql 初始化数据库。")
            return
        
        # 生成更多研报
        print()
        await generate_more_reports(conn, count=100)
        
        # 更新统计信息
        await update_statistics(conn)
        
        print("\n✅ 所有数据生成完成！")
        print("\n💡 提示：")
        print("   - 可以使用只读用户 research_readonly 连接数据库")
        print("   - Text2SQL智能体将使用这些数据进行演示")
        print("   - 数据包含多种查询场景：聚合、JOIN、时间过滤等")
        
        await conn.close()
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

