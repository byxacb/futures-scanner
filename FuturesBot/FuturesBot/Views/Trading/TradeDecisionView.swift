import SwiftUI

struct TradeDecisionView: View {
    @EnvironmentObject var market: MarketService
    @EnvironmentObject var notification: NotificationService
    @State private var selectedSignal: TradeSignal?

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 16) {
                    // 今日决策卡
                    let strongSignals = market.signals.filter { $0.quality == .strong }

                    if strongSignals.isEmpty {
                        noSignalCard
                    } else {
                        ForEach(strongSignals) { signal in
                            decisionCard(signal: signal)
                        }
                    }

                    // 红线提醒
                   红线card

                    // 操作指南
                    操作指南card
                }
                .padding()
            }
            .navigationTitle("交易决策")
        }
    }

    private var noSignalCard: some View {
        VStack(spacing: 12) {
            Image(systemName: "pause.circle")
                .font(.system(size: 48))
                .foregroundColor(.gray)
            Text("今日无高确信信号")
                .font(.headline)
            Text("默认操作：空仓观望 / 持有现有头寸")
                .font(.subheadline)
                .foregroundColor(.secondary)
            Text("空仓是免费的最大优势")
                .font(.caption)
                .foregroundColor(.orange)
                .italic()
        }
        .padding(24)
        .frame(maxWidth: .infinity)
        .background(Color(.systemBackground))
        .cornerRadius(12)
    }

    private func decisionCard(signal: TradeSignal) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            // 标题行
            HStack {
                VStack(alignment: .leading) {
                    Text("📋 今日交易计划")
                        .font(.headline)
                    Text(signal.name + " " + signal.symbol.uppercased())
                        .font(.title3)
                        .fontWeight(.bold)
                }
                Spacer()
                VStack(alignment: .trailing) {
                    Text(String(format: "%.0f", signal.quote.price))
                        .font(.title2)
                        .fontWeight(.bold)
                        .monospacedDigit()
                }
            }

            Divider()

            // 交易参数
            if let pos = signal.positionSuggestion {
                decisionRow("合约", signal.symbol.uppercased() + " (主力)")
                decisionRow("方向", signal.direction.label)
                decisionRow("建议手数", "\(pos.maxLots) 手")
                decisionRow("入场价", "限价 ~\(Int(signal.quote.price))")
                decisionRow("止损价", "@\(Int(pos.stopPrice)) (必须挂！)")
                decisionRow("单笔风险", String(format: "%.2f%% 账户 (%.0f 元)", pos.riskPct, pos.riskAmount))
                decisionRow("保证金占用", String(format: "%.1f%% 账户", pos.marginPct))
            }

            // 信号依据
            Divider()
            Text("信号依据:")
                .font(.caption)
                .foregroundColor(.secondary)
            ForEach(signal.conditions, id: \.self) { condition in
                HStack {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)
                        .font(.caption2)
                    Text(condition)
                        .font(.caption)
                }
            }

            // 操作按钮
            HStack {
                Button(action: {
                    // 复制合约号到剪贴板
                    UIPasteboard.general.string = signal.symbol.uppercased()
                    notification.sendAlert(title: "已复制", body: "\(signal.symbol.uppercased()) 已复制到剪贴板")
                }) {
                    Label("复制合约号", systemImage: "doc.on.doc")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)

                Button(action: {
                    // 通知提醒挂止损
                    notification.sendAlert(
                        title: "⚠️ 挂止损",
                        body: "成交后立刻挂止损 @\(Int(signal.positionSuggestion?.stopPrice ?? 0))",
                        isUrgent: true
                    )
                }) {
                    Label("提醒挂止损", systemImage: "exclamationmark.triangle")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(.red)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 5, y: 2)
    }

    private func decisionRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label)
                .font(.subheadline)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .font(.subheadline)
                .fontWeight(.medium)
                .monospacedDigit()
        }
    }

    private var 红线card: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("🚨 红线")
                .font(.headline)
                .foregroundColor(.red)
            红线row("单日浮亏 -3% (¥30,000)", "全平 + 停手")
            红线row("单笔亏损 > 2% 账户 (¥20,000)", "紧急止损")
            红线row("取消/上移止损向不利方向", "绝对禁止")
            红线row("亏损单上加仓（马丁）", "绝对禁止")
        }
        .padding()
        .background(Color.red.opacity(0.05))
        .cornerRadius(12)
    }

    private func 红线row(_ trigger: String, _ action: String) -> some View {
        HStack {
            Image(systemName: "xmark.circle.fill")
                .foregroundColor(.red)
                .font(.caption)
            Text(trigger)
                .font(.caption)
            Spacer()
            Text(action)
                .font(.caption2)
                .fontWeight(.bold)
                .foregroundColor(.red)
        }
    }

    private var 操作指南card: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("💡 操作流程")
                .font(.headline)
            stepRow("1", "打开掘金雷达 → 搜合约号")
            stepRow("2", "选「买入开仓」→ 限价单 → 填手数")
            stepRow("3", "点「买多」→ 截图确认页发给 agent")
            stepRow("4", "成交后立刻去「条件单」→「指定价格止损」→ 挂止损价")
            stepRow("5", "盘中收到 Bark 通知 → 去软件操作 → 截图发 agent")
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(12)
    }

    private func stepRow(_ num: String, _ text: String) -> some View {
        HStack(alignment: .top, spacing: 8) {
            Text(num)
                .font(.caption)
                .fontWeight(.bold)
                .foregroundColor(.orange)
                .frame(width: 16)
            Text(text)
                .font(.caption)
        }
    }
}
