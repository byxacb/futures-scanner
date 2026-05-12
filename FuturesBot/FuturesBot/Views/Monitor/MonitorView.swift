import SwiftUI

struct MonitorView: View {
    @EnvironmentObject var market: MarketService
    @State private var selectedSymbol = "rb"

    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // 品种选择器
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 12) {
                        ForEach(market.defaultSymbols, id: \.self) { symbol in
                            Button(action: { selectedSymbol = symbol }) {
                                Text(symbol.uppercased())
                                    .font(.subheadline)
                                    .fontWeight(selectedSymbol == symbol ? .bold : .regular)
                                    .padding(.horizontal, 16)
                                    .padding(.vertical, 8)
                                    .background(selectedSymbol == symbol ? Color.orange : Color(.systemGray5))
                                    .foregroundColor(selectedSymbol == symbol ? .white : .primary)
                                    .cornerRadius(20)
                            }
                        }
                    }
                    .padding(.horizontal)
                    .padding(.vertical, 8)
                }

                Divider()

                // 行情详情
                if let quote = market.quotes[selectedSymbol] {
                    quoteDetail(quote)
                } else {
                    VStack {
                        ProgressView()
                        Text("加载中...")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
            .navigationTitle("行情监控")
        }
    }

    private func quoteDetail(_ quote: Quote) -> some View {
        ScrollView {
            VStack(spacing: 16) {
                // 价格头部
                VStack(spacing: 4) {
                    Text(quote.name)
                        .font(.title3)
                    Text(String(format: "%.0f", quote.price))
                        .font(.system(size: 48, weight: .bold, design: .rounded))
                    Text(String(format: "%+.2f%%  ¥%.0f", quote.changePct, quote.changePct * quote.price / 100))
                        .foregroundColor(quote.changePct >= 0 ? .red : .green)
                }
                .padding()

                // 详情网格
                LazyVGrid(columns: [
                    GridItem(.flexible()),
                    GridItem(.flexible())
                ], spacing: 12) {
                    detailRow("开盘", String(format: "%.0f", quote.open))
                    detailRow("最高", String(format: "%.0f", quote.high))
                    detailRow("最低", String(format: "%.0f", quote.low))
                    detailRow("结算", String(format: "%.0f", quote.settle))
                    detailRow("成交量", "\(quote.volume)")
                    detailRow("持仓量", "\(quote.oi)")
                }
                .padding(.horizontal)

                // 信号信息
                if let signal = market.signals.first(where: { $0.symbol == selectedSymbol }) {
                    signalInfo(signal)
                }

                // 技术指标
                if let signal = market.signals.first(where: { $0.symbol == selectedSymbol }) {
                    indicatorInfo(signal)
                }
            }
        }
    }

    private func signalInfo(_ signal: TradeSignal) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("信号分析")
                .font(.headline)

            HStack {
                Label(signal.quality.label, systemImage: signal.quality == .strong ? "bolt.fill" : "minus.circle")
                    .foregroundColor(signal.quality == .strong ? .red : .orange)
                Spacer()
                Label(signal.direction.label, systemImage: signal.direction == .long ? "arrow.up.circle" : "arrow.down.circle")
                    .foregroundColor(signal.direction == .long ? .red : .green)
            }

            ForEach(signal.conditions, id: \.self) { condition in
                HStack {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundColor(.green)
                        .font(.caption)
                    Text(condition)
                        .font(.caption)
                }
            }

            if let pos = signal.positionSuggestion {
                Divider()
                HStack {
                    Text("建议手数: \(pos.maxLots)")
                    Spacer()
                    Text("止损: @\(Int(pos.stopPrice))")
                        .foregroundColor(.red)
                }
                .font(.subheadline)

                HStack {
                    Text("保证金: \(String(format: "%.1f%%", pos.marginPct))")
                    Spacer()
                    Text("风险: \(String(format: "%.2f%%", pos.riskPct))")
                }
                .font(.caption)
                .foregroundColor(.secondary)
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
    }

    private func indicatorInfo(_ signal: TradeSignal) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("技术指标")
                .font(.headline)

            gridRow("ATR(14)", String(format: "%.1f", signal.indicators.atr14))
            gridRow("MA20", String(format: "%.0f", signal.indicators.ma20))
            gridRow("MA60", String(format: "%.0f", signal.indicators.ma60))
            gridRow("RSI(14)", String(format: "%.1f", signal.indicators.rsi14))
            gridRow("MACD 柱", String(format: "%.2f", signal.indicators.macdHist))
            gridRow("ADX(14)", String(format: "%.1f", signal.indicators.adx14))
            gridRow("布林宽度", String(format: "%.2f%%", signal.indicators.bbWidth * 100))
            gridRow("唐奇安上轨", String(format: "%.0f", signal.indicators.dcHigh20))
            gridRow("唐奇安下轨", String(format: "%.0f", signal.indicators.dcLow20))
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
    }

    private func gridRow(_ label: String, _ value: String) -> some View {
        HStack {
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
            Spacer()
            Text(value)
                .font(.caption)
                .monospacedDigit()
        }
    }

    private func detailRow(_ label: String, _ value: String) -> some View {
        VStack {
            Text(label)
                .font(.caption)
                .foregroundColor(.secondary)
            Text(value)
                .font(.subheadline)
                .monospacedDigit()
        }
        .frame(maxWidth: .infinity)
        .padding(8)
        .background(Color(.systemGray6))
        .cornerRadius(8)
    }
}
