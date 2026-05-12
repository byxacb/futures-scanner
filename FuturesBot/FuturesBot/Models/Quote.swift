import Foundation

/// 实时行情数据
struct Quote: Identifiable, Codable {
    let symbol: String        // 品种代码，如 "RB0"
    let name: String          // 中文名，如 "螺纹钢"
    var price: Double         // 最新价
    let open: Double
    let high: Double
    let low: Double
    let settle: Double        // 结算价
    var volume: Int
    let oi: Int               // 持仓量
    let timestamp: Date

    var changePct: Double {
        guard settle > 0 else { return 0 }
        return (price - settle) / settle * 100
    }

    var id: String { symbol }
}

/// 品种规格
struct SymbolSpec: Codable, Identifiable {
    let code: String          // rb, m, au...
    let name: String          // 螺纹钢、豆粕、沪金
    let multiplier: Int       // 合约乘数
    let marginRate: Double    // 保证金率（比赛：交易所+3%）
    let exchange: String      // SHFE/DCE/CZCE/CFFEX/INE

    var id: String { code }
}

/// 技术指标结果
struct IndicatorResult {
    let atr14: Double
    let ma20: Double
    let ma60: Double
    let rsi14: Double
    let macdDif: Double
    let macdDea: Double
    let macdHist: Double
    let bbUpper: Double
    let bbLower: Double
    let bbWidth: Double
    let dcHigh20: Double      // 唐奇安上轨（前 20 日最高）
    let dcLow20: Double       // 唐奇安下轨（前 20 日最低）
    let adx14: Double

    var trend: String {
        if ma20 > ma60 { return "up" }
        if ma20 < ma60 { return "down" }
        return "sideways"
    }

    var regime: String {
        if adx14 > 25 { return "trend" }
        if adx14 < 20 { return "range" }
        return "transition"
    }
}

/// 交易信号
struct TradeSignal: Identifiable {
    let symbol: String
    let name: String
    let quality: SignalQuality
    let direction: SignalDirection
    let conditions: [String]
    let quote: Quote
    let indicators: IndicatorResult
    let positionSuggestion: PositionSuggestion?

    var id: String { symbol }
}

enum SignalQuality: String, CaseIterable {
    case strong = "strong"
    case medium = "medium"
    case weak = "weak"
    case none = "none"

    var label: String {
        switch self {
        case .strong: return "强"
        case .medium: return "中"
        case .weak: return "弱"
        case .none: return "无"
        }
    }

    var color: String {
        switch self {
        case .strong: return "red"
        case .medium: return "orange"
        case .weak: return "yellow"
        case .none: return "gray"
        }
    }
}

enum SignalDirection: String {
    case long = "long"
    case short = "short"
    case none = "none"

    var label: String {
        switch self {
        case .long: return "做多"
        case .short: return "做空"
        case .none: return "观望"
        }
    }
}

/// 仓位建议
struct PositionSuggestion {
    let maxLots: Int
    let stopDistance: Double
    let stopPrice: Double
    let marginPerLot: Double
    let marginUsed: Double
    let marginPct: Double
    let riskAmount: Double
    let riskPct: Double
}
