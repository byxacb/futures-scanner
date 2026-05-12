import SwiftUI

struct DashboardView: View {
    @EnvironmentObject var market: MarketService
    @State private var showingDetail = false

    var body: some View {
        NavigationView {
            ScrollView {
                VStack(spacing: 16) {
                    // 账户概览
                    accountCard

                    // 每日简报摘要
                    if !market.dailyBriefing.isEmpty {
                        briefingCard
                    }

                    // 高确信信号
                    let strongSignals = market.signals.filter { $0.quality == .strong }
                    if !strongSignals.isEmpty {
                        signalSection(title: "⭐ 高确信信号", signals: strongSignals)
                    }

                    // 中等信号
                    let mediumSignals = market.signals.filter { $0.quality == .medium }
                    if !mediumSignals.isEmpty {
                        signalSection(title: "🔶 中等信号", signals: mediumSignals)
                    }

                    // 所有品种状态
                    signalSection(title: "📊 全部品种", signals: market.signals)

                    // 行情速览
                    quoteCards
                }
                .padding()
            }
            .navigationTitle("FuturesBot")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button(action: {
                        Task { await market.refreshAll() }
                    }) {
                        if market.isLoading {
                            ProgressView()
                        } else {
                            Image(systemName: "arrow.clockwise")
                        }
                    }
                }
            }
            .refreshable {
                await market.refreshAll()
            }
        }
    }

    // MARK: - Briefing Card

    private var briefingCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("📋 实时简报")
                    .font(.headline)
                Spacer()
                Text("自动更新")
                    .font(.caption2)
                    .foregroundColor(.green)
            }
            Text(market.dailyBriefing)
                .font(.caption)
                .monospaced()
                .foregroundColor(.primary)
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 5, y: 2)
    }

    // MARK: - Account Card

    private var accountCard: some View {
        VStack(spacing: 8) {
            HStack {
                Text("账户净值")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                Spacer()
                if let lastUpdate = market.lastUpdate {
                    Text("更新于 \(lastUpdate.formatted(date: .omitted, time: .shortened))")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }
            }
            Text(String(format: "¥%.0f", market.accountEquity))
                .font(.system(size: 32, weight: .bold, design: .rounded))
                .foregroundColor(.primary)

            HStack(spacing: 20) {
                VStack {
                    Text("活跃信号")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("\(market.signals.filter { $0.quality != .none }.count)")
                        .font(.title3)
                        .fontWeight(.semibold)
                }
                VStack {
                    Text("强信号")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("\(market.signals.filter { $0.quality == .strong }.count)")
                        .font(.title3)
                        .fontWeight(.semibold)
                        .foregroundColor(.red)
                }
                VStack {
                    Text("品种数")
                        .font(.caption)
                        .foregroundColor(.secondary)
                    Text("\(market.quotes.count)")
                        .font(.title3)
                        .fontWeight(.semibold)
                }
            }
        }
        .padding()
        .background(Color(.systemBackground))
        .cornerRadius(12)
        .shadow(color: .black.opacity(0.05), radius: 5, y: 2)
    }

    // MARK: - Signal Section

    private func signalSection(title: String, signals: [TradeSignal]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)

            if signals.isEmpty {
                Text("暂无信号")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding()
            }

            ForEach(signals) { signal in
                SignalCard(signal: signal)
            }
        }
    }

    // MARK: - Quote Cards

    private var quoteCards: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("📈 行情速览")
                .font(.headline)

            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: 8) {
                ForEach(market.defaultSymbols, id: \.self) { symbol in
                    if let quote = market.quotes[symbol] {
                        MiniQuoteCard(quote: quote)
                    }
                }
            }
        }
    }
}

// MARK: - Signal Card

struct SignalCard: View {
    let signal: TradeSignal

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(signal.name)
                        .font(.headline)
                    Text(signal.symbol.uppercased())
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                HStack(spacing: 8) {
                    qualityBadge
                    directionBadge

                    if let pos = signal.positionSuggestion {
                        Text("\(pos.maxLots) 手")
                            .font(.caption)
                            .foregroundColor(.blue)
                    }
                }

                if !signal.conditions.isEmpty {
                    Text(signal.conditions.joined(separator: " + "))
                        .font(.caption2)
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                }
            }

            Spacer()

            VStack(alignment: .trailing) {
                Text(String(format: "%.0f", signal.quote.price))
                    .font(.headline)
                    .monospacedDigit()

                if let pos = signal.positionSuggestion {
                    Text("止损 @\(Int(pos.stopPrice))")
                        .font(.caption2)
                        .foregroundColor(.red)
                }
            }
        }
        .padding(12)
        .background(Color(.systemBackground))
        .cornerRadius(10)
        .shadow(color: .black.opacity(0.03), radius: 3, y: 1)
    }

    private var qualityBadge: some View {
        Text(signal.quality.label)
            .font(.caption2)
            .fontWeight(.bold)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(qualityColor.opacity(0.15))
            .foregroundColor(qualityColor)
            .cornerRadius(4)
    }

    private var directionBadge: some View {
        Text(signal.direction.label)
            .font(.caption2)
            .fontWeight(.bold)
            .padding(.horizontal, 6)
            .padding(.vertical, 2)
            .background(directionColor.opacity(0.15))
            .foregroundColor(directionColor)
            .cornerRadius(4)
    }

    private var qualityColor: Color {
        switch signal.quality {
        case .strong: return .red
        case .medium: return .orange
        case .weak: return .yellow
        case .none: return .gray
        }
    }

    private var directionColor: Color {
        switch signal.direction {
        case .long: return .red
        case .short: return .green
        case .none: return .gray
        }
    }
}

// MARK: - Mini Quote Card

struct MiniQuoteCard: View {
    let quote: Quote

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(quote.name)
                    .font(.caption)
                    .foregroundColor(.secondary)
                Spacer()
            }

            Text(String(format: "%.0f", quote.price))
                .font(.headline)
                .monospacedDigit()

            HStack {
                Text(String(format: "%+.2f%%", quote.changePct))
                    .font(.caption2)
                    .foregroundColor(quote.changePct >= 0 ? .red : .green)
                Spacer()
                Text("量 \(quote.volume)")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }
        }
        .padding(10)
        .background(Color(.systemBackground))
        .cornerRadius(8)
        .shadow(color: .black.opacity(0.03), radius: 2, y: 1)
    }
}
