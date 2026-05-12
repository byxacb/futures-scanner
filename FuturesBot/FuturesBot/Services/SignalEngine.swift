import Foundation

/// 信号引擎
/// 从 strategy/master_playbook.md 的入场规则移植
enum SignalEngine {

    /// 评估单个品种的信号质量
    static func evaluate(
        symbol: String,
        name: String,
        summary: SignalSummary,
        accountEquity: Double = 1_000_000
    ) -> TradeSignal {
        let sig = summary.signals
        var longScore = 0
        var shortScore = 0
        var longConditions = [String]()
        var shortConditions = [String]()

        // 多头条件评分
        if sig.breakoutUp20d { longScore += 2; longConditions.append("突破 20 日新高") }
        if summary.trend == "up" { longScore += 1; longConditions.append("MA20>MA60 上升趋势") }
        if sig.volumeConfirmed && (sig.breakoutUp20d || sig.macdCrossUp) { longScore += 1; longConditions.append("成交量放大") }
        if sig.macdCrossUp { longScore += 1; longConditions.append("MACD 金叉") }
        if summary.regime == "trend" { longScore += 1; longConditions.append("ADX>25 趋势市") }

        // 空头条件评分
        if sig.breakoutDn20d { shortScore += 2; shortConditions.append("突破 20 日新低") }
        if summary.trend == "down" { shortScore += 1; shortConditions.append("MA20<MA60 下降趋势") }
        if sig.volumeConfirmed && (sig.breakoutDn20d || sig.macdCrossDn) { shortScore += 1; shortConditions.append("成交量放大") }
        if sig.macdCrossDn { shortScore += 1; shortConditions.append("MACD 死叉") }
        if summary.regime == "trend" { shortScore += 1; shortConditions.append("ADX>25 趋势市") }

        // 决定方向
        let quality: SignalQuality
        let direction: SignalDirection
        let conditions: [String]

        if longScore >= shortScore {
            direction = .long
            conditions = longConditions
            quality = qualityFromScore(longScore)
        } else {
            direction = .short
            conditions = shortConditions
            quality = qualityFromScore(shortScore)
        }

        // 仓位建议
        var positionSuggestion: PositionSuggestion? = nil
        if direction != .none && quality != .none && quality != .weak {
            positionSuggestion = PositionCalculator.calcPosition(
                symbol: symbol,
                direction: direction.rawValue,
                accountEquity: accountEquity,
                entryPrice: summary.close,
                atr: summary.atr14,
                highConfidence: quality == .strong
            )
        }

        // 构造 Quote（从 summary 取近似值）
        let quote = Quote(
            symbol: symbol,
            name: name,
            price: summary.close,
            open: summary.close,
            high: summary.close,
            low: summary.close,
            settle: summary.close,
            volume: 0,
            oi: 0,
            timestamp: Date()
        )

        return TradeSignal(
            symbol: symbol,
            name: name,
            quality: quality,
            direction: direction,
            conditions: conditions,
            quote: quote,
            indicators: IndicatorResult(
                atr14: summary.atr14,
                ma20: summary.ma20,
                ma60: summary.ma60,
                rsi14: summary.rsi14,
                macdDif: 0,
                macdDea: 0,
                macdHist: summary.macdHist,
                bbUpper: summary.bbUpper,
                bbLower: summary.bbLower,
                bbWidth: summary.bbWidth,
                dcHigh20: summary.dcHigh20,
                dcLow20: summary.dcLow20,
                adx14: summary.adx14
            ),
            positionSuggestion: positionSuggestion
        )
    }

    /// 分数转质量等级
    private static func qualityFromScore(_ score: Int) -> SignalQuality {
        switch score {
        case 5...: return .strong
        case 3...4: return .medium
        case 1...2: return .weak
        default: return .none
        }
    }
}
