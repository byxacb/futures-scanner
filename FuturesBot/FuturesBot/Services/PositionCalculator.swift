import Foundation

/// 仓位计算器
/// 从 Python tools/risk/position_calc.py 移植
enum PositionCalculator {

    /// 28 个品种的合约规格（和 position_calc.py 的 SPECS 同步）
    static let specs: [String: SymbolSpec] = [
        "rb": SymbolSpec(code: "rb", name: "螺纹钢", multiplier: 10, marginRate: 0.12, exchange: "SHFE"),
        "hc": SymbolSpec(code: "hc", name: "热卷", multiplier: 10, marginRate: 0.12, exchange: "SHFE"),
        "i":  SymbolSpec(code: "i",  name: "铁矿石", multiplier: 100, marginRate: 0.13, exchange: "DCE"),
        "j":  SymbolSpec(code: "j",  name: "焦炭", multiplier: 100, marginRate: 0.15, exchange: "DCE"),
        "jm": SymbolSpec(code: "jm", name: "焦煤", multiplier: 60, marginRate: 0.15, exchange: "DCE"),
        "m":  SymbolSpec(code: "m",  name: "豆粕", multiplier: 10, marginRate: 0.11, exchange: "DCE"),
        "y":  SymbolSpec(code: "y",  name: "豆油", multiplier: 10, marginRate: 0.12, exchange: "DCE"),
        "p":  SymbolSpec(code: "p",  name: "棕榈油", multiplier: 10, marginRate: 0.12, exchange: "DCE"),
        "c":  SymbolSpec(code: "c",  name: "玉米", multiplier: 10, marginRate: 0.10, exchange: "DCE"),
        "cu": SymbolSpec(code: "cu", name: "沪铜", multiplier: 5, marginRate: 0.12, exchange: "SHFE"),
        "al": SymbolSpec(code: "al", name: "沪铝", multiplier: 5, marginRate: 0.12, exchange: "SHFE"),
        "zn": SymbolSpec(code: "zn", name: "沪锌", multiplier: 5, marginRate: 0.13, exchange: "SHFE"),
        "ni": SymbolSpec(code: "ni", name: "沪镍", multiplier: 1, marginRate: 0.16, exchange: "SHFE"),
        "au": SymbolSpec(code: "au", name: "沪金", multiplier: 1000, marginRate: 0.12, exchange: "SHFE"),
        "ag": SymbolSpec(code: "ag", name: "沪银", multiplier: 15, marginRate: 0.12, exchange: "SHFE"),
        "sc": SymbolSpec(code: "sc", name: "原油", multiplier: 1000, marginRate: 0.13, exchange: "INE"),
        "MA": SymbolSpec(code: "MA", name: "甲醇", multiplier: 10, marginRate: 0.11, exchange: "CZCE"),
        "FG": SymbolSpec(code: "FG", name: "玻璃", multiplier: 20, marginRate: 0.12, exchange: "CZCE"),
        "IF": SymbolSpec(code: "IF", name: "沪深300", multiplier: 300, marginRate: 0.15, exchange: "CFFEX"),
        "IH": SymbolSpec(code: "IH", name: "上证50", multiplier: 300, marginRate: 0.15, exchange: "CFFEX"),
        "IC": SymbolSpec(code: "IC", name: "中证500", multiplier: 200, marginRate: 0.15, exchange: "CFFEX"),
        "IM": SymbolSpec(code: "IM", name: "中证1000", multiplier: 200, marginRate: 0.15, exchange: "CFFEX"),
        "TS": SymbolSpec(code: "TS", name: "2年期国债", multiplier: 20000, marginRate: 0.03, exchange: "CFFEX"),
        "TF": SymbolSpec(code: "TF", name: "5年期国债", multiplier: 10000, marginRate: 0.04, exchange: "CFFEX"),
        "T":  SymbolSpec(code: "T",  name: "10年期国债", multiplier: 10000, marginRate: 0.05, exchange: "CFFEX"),
    ]

    /// 高相关组合（同向加和受限）
    static let correlationGroups: [String: [String]] = [
        "black": ["rb", "hc", "i", "j", "jm"],
        "ag_oil": ["m", "y", "p"],
        "nonferrous": ["cu", "al", "zn", "ni"],
        "precious": ["au", "ag"],
        "equity_idx": ["IF", "IH", "IC", "IM"],
        "bond": ["TS", "TF", "T"],
    ]

    /// 计算最大手数
    static func calcPosition(
        symbol: String,
        direction: String,
        accountEquity: Double,
        entryPrice: Double,
        atr: Double,
        riskPct: Double = 0.01,
        atrMultiplier: Double = 2.0,
        highConfidence: Bool = false,
        singleSymbolCap: Double = 0.10
    ) -> PositionSuggestion? {
        guard let spec = specs[symbol] else { return nil }

        let actualRiskPct = highConfidence ? riskPct * 1.5 : riskPct
        let riskAmount = accountEquity * actualRiskPct
        let stopDistance = atrMultiplier * atr
        let lossPerLot = stopDistance * Double(spec.multiplier)

        guard lossPerLot > 0 else { return nil }

        let marginPerLot = entryPrice * Double(spec.multiplier) * spec.marginRate
        let singleSymbolMaxLots = marginPerLot > 0 ? Int((accountEquity * singleSymbolCap) / marginPerLot) : 0
        let rawMax = Int(riskAmount / lossPerLot)
        let maxLots = min(rawMax, singleSymbolMaxLots)

        guard maxLots > 0 else { return nil }

        let marginUsed = Double(maxLots) * marginPerLot
        let marginPct = marginUsed / accountEquity
        let actualRisk = Double(maxLots) * lossPerLot
        let actualRiskPctVal = actualRisk / accountEquity

        let stopPrice = direction == "long"
            ? entryPrice - stopDistance
            : entryPrice + stopDistance

        return PositionSuggestion(
            maxLots: maxLots,
            stopDistance: stopDistance,
            stopPrice: stopPrice,
            marginPerLot: marginPerLot,
            marginUsed: marginUsed,
            marginPct: marginPct * 100,
            riskAmount: actualRisk,
            riskPct: actualRiskPctVal * 100
        )
    }
}
