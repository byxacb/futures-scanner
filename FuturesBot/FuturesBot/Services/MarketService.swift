import Foundation
import SwiftUI
import UserNotifications

/// 行情服务：管理行情拉取、信号计算、自动分析+推送
@MainActor
class MarketService: ObservableObject {
    @Published var quotes: [String: Quote] = [:]
    @Published var signals: [TradeSignal] = []
    @Published var klineCache: [String: [KlineBar]] = [:]
    @Published var lastUpdate: Date?
    @Published var isLoading = false
    @Published var dailyBriefing: String = ""

    /// 默认监控品种
    let defaultSymbols = ["rb", "m", "au", "IF", "sc"]

    /// 账户净值
    var accountEquity: Double {
        UserDefaults.standard.double(forKey: "account_equity") == 0
            ? 1_000_000
            : UserDefaults.standard.double(forKey: "account_equity")
    }

    /// 上次信号快照（用于检测变化）
    private var lastSignalSnapshot: [String: SignalQuality] = [:]

    /// 定时轮询
    private var pollTimer: Timer?
    private var analysisTimer: Timer?

    func startPolling() {
        // 立即拉一次
        Task { await refreshAll() }

        // 每 30 秒拉一次行情（仅交易时段）
        pollTimer = Timer.scheduledTimer(withTimeInterval: 30, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            Task { @MainActor in
                if self.isMarketHours() {
                    await self.refreshQuotes()
                    // 每 5 分钟重算信号（节省 K 线请求）
                    if Int(Date().timeIntervalSince1970) % 300 < 30 {
                        await self.refreshSignals()
                        self.checkSignalChanges()
                    }
                }
            }
        }

        // 每 5 分钟生成一次简报摘要
        analysisTimer = Timer.scheduledTimer(withTimeInterval: 300, repeats: true) { [weak self] _ in
            guard let self = self else { return }
            Task { @MainActor in
                if self.isMarketHours() {
                    self.generateBriefing()
                }
            }
        }
    }

    func stopPolling() {
        pollTimer?.invalidate()
        pollTimer = nil
        analysisTimer?.invalidate()
        analysisTimer = nil
    }

    /// 刷新所有数据（行情 + K 线 + 信号）
    func refreshAll() async {
        isLoading = true
        defer { isLoading = false }

        await refreshQuotes()
        await refreshSignals()
        lastUpdate = Date()
        generateBriefing()
    }

    /// 仅刷新行情
    func refreshQuotes() async {
        do {
            let newQuotes = try await SinaAPI.fetchQuotes(symbols: defaultSymbols)
            for q in newQuotes {
                quotes[q.symbol] = q
            }
        } catch {
            print("行情拉取失败: \(error)")
        }
    }

    /// 重新计算所有信号
    func refreshSignals() async {
        var newSignals: [TradeSignal] = []

        for symbol in defaultSymbols {
            guard let name = SinaAPI.symbols[symbol]?.name else { continue }

            do {
                guard let sinaCode = SinaAPI.symbols[symbol]?.sinaCode else { continue }
                let bars = try await SinaAPI.fetchDailyKline(sinaCode: sinaCode, limit: 120)
                guard bars.count >= 60 else { continue }

                klineCache[symbol] = bars

                if let summary = IndicatorEngine.signalSummary(bars: bars) {
                    let signal = SignalEngine.evaluate(
                        symbol: symbol,
                        name: name,
                        summary: summary,
                        accountEquity: accountEquity
                    )
                    newSignals.append(signal)
                }
            } catch {
                print("信号计算失败 \(symbol): \(error)")
            }
        }

        signals = newSignals.sorted { a, b in
            let order: [SignalQuality] = [.strong, .medium, .weak, .none]
            return order.firstIndex(of: a.quality)! < order.firstIndex(of: b.quality)!
        }
    }

    /// 检测信号变化并推送通知
    private func checkSignalChanges() {
        let newSnapshot = Dictionary(uniqueKeysWithValues: signals.map { ($0.symbol, $0.quality) })

        for (symbol, newQuality) in newSnapshot {
            let oldQuality = lastSignalSnapshot[symbol]

            // 新出现强信号 → 推送
            if newQuality == .strong && oldQuality != .strong {
                if let signal = signals.first(where: { $0.symbol == symbol }) {
                    let direction = signal.direction == .long ? "做多" : "做空"
                    let pos = signal.positionSuggestion
                    let lotsText = pos != nil ? "建议 \(pos!.maxLots) 手" : ""
                    let stopText = pos != nil ? "止损 @\(Int(pos!.stopPrice))" : ""

                    let content = """
                    \(signal.name) (\(symbol.uppercased())) → \(direction)
                    信号质量: 强
                    \(lotsText) \(stopText)
                    依据: \(signal.conditions.joined(separator: " + "))
                    """

                    // 本地通知
                    let notification = UNMutableNotificationContent()
                    notification.title = "🔥 强信号: \(signal.name) \(direction)"
                    notification.body = content
                    notification.sound = .default
                    UNUserNotificationCenter.current().add(
                        UNNotificationRequest(identifier: "signal-\(symbol)", content: notification, trigger: nil)
                    )

                    // Bark 推送
                    sendBarkNotification(title: "🔥 \(signal.name) \(direction)", body: content, level: "urgent")
                }
            }

            // 强信号消失 → 提醒
            if newQuality != .strong && oldQuality == .strong {
                let content = UNMutableNotificationContent()
                content.title = "⚠️ \(symbol.uppercased()) 信号减弱"
                content.body = "原强信号已变为 \(newQuality.label)，注意风险"
                content.sound = .default
                UNUserNotificationCenter.current().add(
                    UNNotificationRequest(identifier: "signal-fade-\(symbol)", content: content, trigger: nil)
                )
            }
        }

        lastSignalSnapshot = newSnapshot
    }

    /// 生成每日简报摘要
    func generateBriefing() {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd HH:mm"
        let now = formatter.string(from: Date())

        var lines = ["📊 \(now) 行情速览\n"]

        for symbol in defaultSymbols {
            guard let quote = quotes[symbol],
                  let signal = signals.first(where: { $0.symbol == symbol }) else { continue }

            let emoji = signal.quality == .strong ? "🔥" : signal.quality == .medium ? "🔶" : "⚪"
            let dir = signal.direction == .long ? "多" : signal.direction == .short ? "空" : "观望"

            lines.append("\(emoji) \(quote.name) \(Int(quote.price)) (\(String(format: "%+.1f%%", quote.changePct))) → \(signal.quality.label) \(dir)")

            if let pos = signal.positionSuggestion, signal.quality != .none && signal.quality != .weak {
                lines.append("   建议 \(pos.maxLots) 手 | 止损 @\(Int(pos.stopPrice)) | 保证金 \(String(format: "%.1f%%", pos.marginPct))")
            }
        }

        // 高确信信号汇总
        let strong = signals.filter { $0.quality == .strong }
        if !strong.isEmpty {
            lines.append("\n⭐ 高确信信号:")
            for s in strong {
                let dir = s.direction == .long ? "做多" : "做空"
                lines.append("  \(s.name) \(dir) — \(s.conditions.joined(separator: " + "))")
            }
        } else {
            lines.append("\n今日无高确信信号 — 空仓观望")
        }

        dailyBriefing = lines.joined(separator: "\n")
    }

    /// 获取指定品种的 K 线
    func getKline(symbol: String) -> [KlineBar] {
        return klineCache[symbol] ?? []
    }

    // MARK: - Bark Push

    private func sendBarkNotification(title: String, body: String, level: String) {
        let barkURL = UserDefaults.standard.string(forKey: "bark_url") ?? "https://api.day.app/S3QnU9QTHddi3XB8Pc8E8o"
        guard let url = URL(string: "\(barkURL)/push") else { return }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let payload: [String: Any] = [
            "title": title,
            "body": String(body.prefix(1000)),
            "sound": level == "urgent" ? "anticipate" : "minuet",
            "group": "期货比赛",
            "level": level == "urgent" ? "timeSensitive" : "active"
        ]
        request.httpBody = try? JSONSerialization.data(withJSONObject: payload)
        URLSession.shared.dataTask(with: request).resume()
    }

    // MARK: - Helpers

    private func isMarketHours() -> Bool {
        let calendar = Calendar.current
        let hour = calendar.component(.hour, from: Date())
        let minute = calendar.component(.minute, from: Date())
        let weekday = calendar.component(.weekday, from: Date())
        guard weekday >= 2 && weekday <= 6 else { return false }
        let time = hour * 60 + minute
        return (time >= 8 * 60 + 30 && time <= 15 * 60 + 30)
    }
}
