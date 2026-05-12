import Foundation

/// 技术指标计算引擎
/// 从 Python tools/indicators/compute.py 移植
enum IndicatorEngine {

    // MARK: - ATR (Average True Range)

    static func atr(bars: [KlineBar], period: Int = 14) -> [Double] {
        let tr = trueRange(bars: bars)
        return wilderSmooth(values: tr, period: period)
    }

    static func trueRange(bars: [KlineBar]) -> [Double] {
        guard bars.count > 1 else { return Array(repeating: 0, count: bars.count) }
        var result = [0.0]
        for i in 1..<bars.count {
            let hl = bars[i].high - bars[i].low
            let hpc = abs(bars[i].high - bars[i-1].close)
            let lpc = abs(bars[i].low - bars[i-1].close)
            result.append(max(hl, hpc, lpc))
        }
        return result
    }

    // MARK: - Moving Average

    static func sma(values: [Double], period: Int) -> [Double] {
        var result = [Double](repeating: 0, count: values.count)
        guard values.count >= period else { return result }
        var sum = values.prefix(period).reduce(0, +)
        result[period - 1] = sum / Double(period)
        for i in period..<values.count {
            sum += values[i] - values[i - period]
            result[i] = sum / Double(period)
        }
        return result
    }

    static func ema(values: [Double], period: Int) -> [Double] {
        var result = [Double](repeating: 0, count: values.count)
        guard !values.isEmpty else { return result }
        let alpha = 2.0 / Double(period + 1)
        result[0] = values[0]
        for i in 1..<values.count {
            result[i] = alpha * values[i] + (1 - alpha) * result[i - 1]
        }
        return result
    }

    // MARK: - MACD

    struct MACDResult {
        let dif: [Double]
        let dea: [Double]
        let hist: [Double]
    }

    static func macd(bars: [KlineBar], fast: Int = 12, slow: Int = 26, signal: Int = 9) -> MACDResult {
        let closes = bars.map { $0.close }
        let emaFast = ema(values: closes, period: fast)
        let emaSlow = ema(values: closes, period: slow)
        let dif = zip(emaFast, emaSlow).map { $0 - $1 }
        let dea = ema(values: dif, period: signal)
        let hist = zip(dif, dea).map { ($0 - $1) * 2 }
        return MACDResult(dif: dif, dea: dea, hist: hist)
    }

    // MARK: - RSI

    static func rsi(bars: [KlineBar], period: Int = 14) -> [Double] {
        let closes = bars.map { $0.close }
        guard closes.count > period else { return Array(repeating: 50, count: closes.count) }

        var deltas = [Double]()
        deltas.append(0)
        for i in 1..<closes.count {
            deltas.append(closes[i] - closes[i-1])
        }

        let gains = deltas.map { max($0, 0) }
        let losses = deltas.map { max(-$0, 0) }

        let avgGain = wilderSmooth(values: gains, period: period)
        let avgLoss = wilderSmooth(values: losses, period: period)

        var result = [Double](repeating: 50, count: avgGain.count)
        for i in 0..<avgGain.count {
            let g = avgGain[i]
            let l = avgLoss[i]
            result[i] = l == 0 ? 100 : 100 - 100 / (1 + g / l)
        }
        return result
    }

    // MARK: - Bollinger Bands

    struct BollingerResult {
        let upper: [Double]
        let mid: [Double]
        let lower: [Double]
        let width: [Double]
    }

    static func bollinger(bars: [KlineBar], period: Int = 20, multiplier: Double = 2.0) -> BollingerResult {
        let closes = bars.map { $0.close }
        let mid = sma(values: closes, period: period)

        var upper = [Double](repeating: 0, count: closes.count)
        var lower = [Double](repeating: 0, count: closes.count)
        var width = [Double](repeating: 0, count: closes.count)

        for i in (period-1)..<closes.count {
            let slice = Array(closes[(i - period + 1)...i])
            let mean = mid[i]
            let variance = slice.reduce(0) { $0 + ($1 - mean) * ($1 - mean) } / Double(period)
            let sd = sqrt(variance)
            upper[i] = mean + multiplier * sd
            lower[i] = mean - multiplier * sd
            width[i] = mean > 0 ? (2 * multiplier * sd) / mean : 0
        }

        return BollingerResult(upper: upper, mid: mid, lower: lower, width: width)
    }

    // MARK: - Donchian Channel

    struct DonchianResult {
        let high: [Double]
        let low: [Double]
        let mid: [Double]
    }

    static func donchian(bars: [KlineBar], period: Int = 20) -> DonchianResult {
        var high = [Double](repeating: 0, count: bars.count)
        var low = [Double](repeating: Double.infinity, count: bars.count)
        var mid = [Double](repeating: 0, count: bars.count)

        for i in (period-1)..<bars.count {
            let slice = Array(bars[(i - period + 1)...i])
            high[i] = slice.map(\.high).max() ?? 0
            low[i] = slice.map(\.low).min() ?? 0
            mid[i] = (high[i] + low[i]) / 2
        }

        return DonchianResult(high: high, low: low, mid: mid)
    }

    // MARK: - ADX

    static func adx(bars: [KlineBar], period: Int = 14) -> [Double] {
        guard bars.count > period + 1 else { return Array(repeating: 0, count: bars.count) }

        var plusDM = [Double](repeating: 0, count: bars.count)
        var minusDM = [Double](repeating: 0, count: bars.count)

        for i in 1..<bars.count {
            let upMove = bars[i].high - bars[i-1].high
            let downMove = bars[i-1].low - bars[i].low
            if upMove > downMove && upMove > 0 {
                plusDM[i] = upMove
            }
            if downMove > upMove && downMove > 0 {
                minusDM[i] = downMove
            }
        }

        let tr = trueRange(bars: bars)
        let smoothTR = wilderSmooth(values: tr, period: period)
        let smoothPlusDM = wilderSmooth(values: plusDM, period: period)
        let smoothMinusDM = wilderSmooth(values: minusDM, period: period)

        var plusDI = [Double](repeating: 0, count: bars.count)
        var minusDI = [Double](repeating: 0, count: bars.count)
        for i in 0..<bars.count {
            if smoothTR[i] > 0 {
                plusDI[i] = 100 * smoothPlusDM[i] / smoothTR[i]
                minusDI[i] = 100 * smoothMinusDM[i] / smoothTR[i]
            }
        }

        var dx = [Double](repeating: 0, count: bars.count)
        for i in 0..<bars.count {
            let sum = plusDI[i] + minusDI[i]
            dx[i] = sum > 0 ? 100 * abs(plusDI[i] - minusDI[i]) / sum : 0
        }

        return wilderSmooth(values: dx, period: period)
    }

    // MARK: - Full Signal Summary

    static func signalSummary(bars: [KlineBar]) -> SignalSummary? {
        guard bars.count >= 60 else { return nil }

        let closes = bars.map(\.close)
        let atrValues = atr(bars: bars, period: 14)
        let ma20Values = sma(values: closes, period: 20)
        let ma60Values = sma(values: closes, period: 60)
        let rsiValues = rsi(bars: bars, period: 14)
        let macdResult = macd(bars: bars)
        let bbResult = bollinger(bars: bars)
        let dcResult = donchian(bars: bars, period: 20)
        let adxValues = adx(bars: bars, period: 14)

        let last = bars.count - 1
        let prev = last - 1

        let lastClose = closes[last]
        let lastATR = atrValues[last]
        let lastMA20 = ma20Values[last]
        let lastMA60 = ma60Values[last]
        let lastRSI = rsiValues[last]
        let lastHist = macdResult.hist[last]
        let lastBBUpper = bbResult.upper[last]
        let lastBBLower = bbResult.lower[last]
        let lastBBWidth = bbResult.width[last]
        let lastDCHigh = dcResult.high[prev]  // 前 20 日最高
        let lastDCLow = dcResult.low[prev]
        let lastADX = adxValues[last]

        // 信号判定
        let breakoutUp = lastClose >= lastDCHigh
        let breakoutDn = lastClose <= lastDCLow

        let last20AvgVol = Double(bars.suffix(20).dropLast().map(\.volume).reduce(0, +)) / 19.0
        let volumeUp = Double(bars[last].volume) > last20AvgVol * 1.2

        let macdCrossUp = macdResult.dea[prev] >= macdResult.dif[prev] && macdResult.dif[last] > macdResult.dea[last]
        let macdCrossDn = macdResult.dea[prev] <= macdResult.dif[prev] && macdResult.dif[last] < macdResult.dea[last]

        let trend: String = {
            if lastMA20 > lastMA60 { return "up" }
            if lastMA20 < lastMA60 { return "down" }
            return "sideways"
        }()

        let regime: String = {
            if lastADX > 25 { return "trend" }
            if lastADX < 20 { return "range" }
            return "transition"
        }()

        return SignalSummary(
            close: lastClose,
            atr14: lastATR,
            ma20: lastMA20,
            ma60: lastMA60,
            rsi14: lastRSI,
            macdHist: lastHist,
            bbUpper: lastBBUpper,
            bbLower: lastBBLower,
            bbWidth: lastBBWidth,
            dcHigh20: lastDCHigh,
            dcLow20: lastDCLow,
            adx14: lastADX,
            trend: trend,
            regime: regime,
            signals: SignalFlags(
                breakoutUp20d: breakoutUp,
                breakoutDn20d: breakoutDn,
                volumeConfirmed: volumeUp,
                macdCrossUp: macdCrossUp,
                macdCrossDn: macdCrossDn,
                rsiOverbought: lastRSI > 70,
                rsiOversold: lastRSI < 30
            )
        )
    }

    // MARK: - Helper

    private static func wilderSmooth(values: [Double], period: Int) -> [Double] {
        guard values.count >= period else { return Array(repeating: 0, count: values.count) }
        var result = [Double](repeating: 0, count: values.count)
        let initial = Array(values.prefix(period)).reduce(0, +) / Double(period)
        result[period - 1] = initial
        for i in period..<values.count {
            result[i] = (result[i - 1] * Double(period - 1) + values[i]) / Double(period)
        }
        return result
    }
}

/// signalSummary 返回的结果
struct SignalSummary {
    let close: Double
    let atr14: Double
    let ma20: Double
    let ma60: Double
    let rsi14: Double
    let macdHist: Double
    let bbUpper: Double
    let bbLower: Double
    let bbWidth: Double
    let dcHigh20: Double
    let dcLow20: Double
    let adx14: Double
    let trend: String
    let regime: String
    let signals: SignalFlags
}

struct SignalFlags {
    let breakoutUp20d: Bool
    let breakoutDn20d: Bool
    let volumeConfirmed: Bool
    let macdCrossUp: Bool
    let macdCrossDn: Bool
    let rsiOverbought: Bool
    let rsiOversold: Bool
}
