import SwiftUI

struct KnowledgeView: View {
    @State private var searchText = ""
    @State private var selectedTab = 0

    var body: some View {
        NavigationView {
            VStack {
                // Tab 选择器
                Picker("", selection: $selectedTab) {
                    Text("铁律").tag(0)
                    Text("策略").tag(1)
                    Text("品种").tag(2)
                    Text("书籍").tag(3)
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)

                // 内容
                List {
                    switch selectedTab {
                    case 0: consensusList
                    case 1: strategyList
                    case 2: productsList
                    case 3: booksList
                    default: EmptyView()
                    }
                }
                .listStyle(.plain)
            }
            .navigationTitle("知识库")
            .searchable(text: $searchText, prompt: "搜索规则、品种、书籍...")
        }
    }

    // MARK: - 20 条铁律

    private var consensusList: some View {
        Section("100 本书共识的 20 条铁律") {
            ForEach(Array(consensusRules.enumerated()), id: \.offset) { index, rule in
                VStack(alignment: .leading, spacing: 4) {
                    Text("\(index + 1). \(rule.title)")
                        .font(.headline)
                    Text(rule.summary)
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .padding(.vertical, 4)
            }
        }
    }

    // MARK: - 策略

    private var strategyList: some View {
        Section("主策略：受控激进") {
            strategyRow("品种池", "rb + m + au + IF + sc（5 个低相关）")
            strategyRow("入场信号", "20 日唐奇安突破 + MA20/60 + 量增 + ADX>25")
            strategyRow("仓位", "基础 30-40%，高确信叠加 60-70%")
            strategyRow("止损", "2×ATR 硬止损，移动止盈")
            strategyRow("加仓", "浮盈 1×ATR 加 1 单位，最多 4 单位")
            strategyRow("红线", "单日 -3% 全平停手 / 周 -6% 休战")
            strategyRow("决策树", "趋势市 → 突破 → 过滤 → 无事件 → 计算仓位 → Kovner 三问 → 执行")
        }
    }

    private func strategyRow(_ label: String, _ detail: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(.headline)
            Text(detail)
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }

    // MARK: - 品种

    private var productsList: some View {
        Group {
            Section("主力品种池") {
                productRow("rb", "螺纹钢", "SHFE", "趋势性强，流动性最佳，库存驱动")
                productRow("m", "豆粕", "DCE", "USDA + 养殖需求，低相关分散")
                productRow("au", "沪金", "SHFE", "宏观对冲，和商品负相关")
                productRow("IF", "沪深300", "CFFEX", "A 股大盘，合约面值大不易做")
                productRow("sc", "原油", "INE", "全球宏观，和其它品种相关性最低")
            }
            Section("候补品种") {
                productRow("hc", "热卷", "SHFE", "和 rb 高度相关，卷螺差套利")
                productRow("i", "铁矿石", "DCE", "进口依赖，波动大")
                productRow("cu", "沪铜", "SHFE", "全球宏观+美元")
                productRow("FG", "玻璃", "CZCE", "地产竣工周期")
                productRow("MA", "甲醇", "CZCE", "煤化工+伊朗供应")
            }
        }
    }

    private func productRow(_ code: String, _ name: String, _ exchange: String, _ note: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            HStack {
                Text("\(name) (\(code.uppercased()))")
                    .font(.headline)
                Text(exchange)
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
            Text(note)
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }

    // MARK: - 书籍

    private var booksList: some View {
        Group {
            Section("必读 S 档") {
                bookRow("股票作手回忆录", "Lefèvre", "趋势跟踪+仓位+心态")
                bookRow("海龟交易法则", "Faith", "系统化趋势+ATR 仓位")
                bookRow("金融怪杰 1-4", "Schwager", "顶级交易员访谈")
                bookRow("期货市场技术分析", "Murphy", "期货 TA 圣经")
                bookRow("通向金融王国的自由之路", "Tharp", "R-multiple/期望值")
                bookRow("新概念技术交易系统", "Wilder", "RSI/ATR 原作")
                bookRow("趋势跟踪", "Covel", "CTA 历史业绩证据")
            }
            Section("核心 A 档") {
                bookRow("思考快与慢", "Kahneman", "行为偏差源头")
                bookRow("黑天鹅/反脆弱/随机漫步", "Taleb", "尾部风险+凸性")
                bookRow("原则", "Dalio", "系统化决策")
                bookRow("金融炼金术", "Soros", "反身性")
                bookRow("穷查理宝典", "Munger", "多元思维模型")
            }
        }
    }

    private func bookRow(_ title: String, _ author: String, _ core: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("\(title)")
                .font(.headline)
            HStack {
                Text(author)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Text("·")
                    .foregroundColor(.secondary)
                Text(core)
                    .font(.caption)
                    .foregroundColor(.orange)
            }
        }
    }

    // MARK: - Data

    private let consensusRules = [
        (title: "截短亏损让利润奔跑", summary: "单笔亏损 ≤ 2% 账户、止盈用移动止损"),
        (title: "风险管理 > 选股 > 入场", summary: "每个决定先问「亏多少」再问「赚多少」"),
        (title: "仓位是不可逆变量", summary: "单笔风险率 1%，单品种 ≤10%"),
        (title: "不在亏损头寸上加仓", summary: "金字塔加仓——只在浮盈 1×ATR 后才加"),
        (title: "永远挂实盘止损单", summary: "开仓后 30 秒内必须挂止损单"),
        (title: "顺势而为不预测顶底", summary: "日线 MA20/60 + 唐奇安通道作为基础信号"),
        (title: "突破伴量价配合", summary: "突破日成交量 ≥ 20 日均量×1.2"),
        (title: "大周期定方向小周期找点位", summary: "日线判断趋势，4 小时/1 小时找入场"),
        (title: "系统化 > 个人判断", summary: "master_playbook 写下来后严格执行"),
        (title: "接受连续亏损是常态", summary: "胜率 30-40% 的趋势策略连亏 5-7 单是统计正常"),
        (title: "不报复性交易", summary: "单日 -3% 强制全平 + 停手一天"),
        (title: "大部分时间什么都不做", summary: "空仓是免费的最大优势"),
        (title: "复盘是少数人能做的事", summary: "每日复盘 + 周日总复盘"),
        (title: "盈亏比比胜率重要", summary: "单笔目标盈亏比 ≥ 2:1"),
        (title: "凯利公式简化版用 1/4", summary: "实际用 5% = 1/4 凯利"),
        (title: "80% 利润来自 5% 的交易", summary: "不能因为怕错而不开仓"),
        (title: "库存+持仓量+基差是三大信号", summary: "每周四钢联数据看库存方向"),
        (title: "重大事件前减仓", summary: "FOMC/CPI/非农前 24h 现有持仓减半"),
        (title: "综合得分 > 绝对收益", summary: "60% 权重惩罚风险——稳健 > 满仓"),
        (title: "持仓天数硬约束", summary: "必须 ≥10 个交易日有效"),
    ]
}
