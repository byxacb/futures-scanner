import Foundation

/// Sina 期货行情 API
/// 解析格式: var hq_str_RB0="螺纹钢,3286.00,3280.00,3286.00,3299.00,3260.00,..."
/// 字段顺序: 品种名,昨收,开盘,最新,最高,最低,买一,卖一,成交量,持仓量,...
enum SinaAPI {

    /// 已知品种的 Sina 代码映射（主连合约）
    static let symbols: [String: (sinaCode: String, name: String)] = [
        "rb": ("RB0", "螺纹钢"),
        "hc": ("HC0", "热卷"),
        "i":  ("I0",  "铁矿石"),
        "j":  ("J0",  "焦炭"),
        "jm": ("JM0", "焦煤"),
        "m":  ("M0",  "豆粕"),
        "y":  ("Y0",  "豆油"),
        "p":  ("P0",  "棕榈油"),
        "c":  ("C0",  "玉米"),
        "cu": ("CU0", "沪铜"),
        "al": ("AL0", "沪铝"),
        "zn": ("ZN0", "沪锌"),
        "ni": ("NI0", "沪镍"),
        "au": ("AU0", "沪金"),
        "ag": ("AG0", "沪银"),
        "sc": ("SC0", "原油"),
        "MA": ("MA0", "甲醇"),
        "FG": ("FG0", "玻璃"),
        "IF": ("IF0", "沪深300"),
        "IH": ("IH0", "上证50"),
        "IC": ("IC0", "中证500"),
        "IM": ("IM0", "中证1000"),
        "T":  ("T0",  "10年国债"),
        "TF": ("TF0", "5年国债"),
        "TS": ("TS0", "2年期国债"),
    ]

    /// 批量拉实时行情
    static func fetchQuotes(symbols: [String]) async throws -> [Quote] {
        let sinaCodes = symbols.compactMap { Self.symbols[$0]?.sinaCode }
        guard !sinaCodes.isEmpty else { return [] }

        let urlStr = "https://hq.sinajs.cn/list=\(sinaCodes.joined(separator: ","))"
        guard let url = URL(string: urlStr) else {
            throw SinaError.invalidURL
        }

        var request = URLRequest(url: url)
        request.setValue("https://finance.sina.com.cn", forHTTPHeaderField: "Referer")
        request.timeoutInterval = 10

        let (data, _) = try await URLSession.shared.data(for: request)

        // Sina 返回 GBK 编码，需要转 UTF-8
        guard let text = String(data: data, encoding: .utf8) ?? String(data: data, encoding: .shiftJIS) else {
            throw SinaError.encodingError
        }

        return parseResponse(text, symbols: symbols)
    }

    /// 拉单个品种的日 K 线（用于指标计算）
    static func fetchDailyKline(sinaCode: String, limit: Int = 120) async throws -> [KlineBar] {
        // Sina K 线 API（前复权）
        let urlStr = "https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20_\(sinaCode)_Daily=/InnerFuturesNewService.getDailyKLine?symbol=\(sinaCode)&type=daily"
        guard let url = URL(string: urlStr) else {
            throw SinaError.invalidURL
        }

        var request = URLRequest(url: url)
        request.setValue("https://finance.sina.com.cn", forHTTPHeaderField: "Referer")
        request.timeoutInterval = 15

        let (data, _) = try await URLSession.shared.data(for: request)
        guard let rawText = String(data: data, encoding: .utf8) else {
            throw SinaError.encodingError
        }

        return parseKlineResponse(rawText, limit: limit)
    }

    // MARK: - Private Parsing

    private static func parseResponse(_ text: String, symbols: [String]) -> [Quote] {
        var results: [Quote] = []
        let lines = text.components(separatedBy: "\n")

        for line in lines {
            // 格式: var hq_str_RB0="螺纹钢,3286,3280,...";
            guard line.contains("=\"") else { continue }

            // 提取 sinaCode
            guard let codeRange = line.range(of: "hq_str_"),
                  let eqRange = line.range(of: "=\"") else { continue }
            let sinaCode = String(line[codeRange.upperBound..<eqRange.lowerBound])

            // 找到对应的用户 symbol
            guard let entry = Self.symbols.first(where: { $0.value.sinaCode == sinaCode }) else { continue }

            // 提取数据部分
            let dataStart = line.index(eqRange.upperBound, offsetBy: 0)
            var dataStr = String(line[dataStart...])
            if dataStr.hasSuffix(";") {
                dataStr = String(dataStr.dropLast())
            }
            if dataStr.hasSuffix("\"") {
                dataStr = String(dataStr.dropLast())
            }

            let fields = dataStr.components(separatedBy: ",")
            guard fields.count >= 10 else { continue }

            let name = fields[0]
            // fields[1]=昨收, [2]=开盘, [3]=最新, [4]=最高, [5]=最低
            // [6]=买一, [7]=卖一, [8]=成交量, [9]=持仓量
            guard let price = Double(fields[3]),
                  let open = Double(fields[2]),
                  let high = Double(fields[4]),
                  let low = Double(fields[5]),
                  let settle = Double(fields[1]),  // 用昨收作为结算参考
                  let volume = Int(fields[8]),
                  let oi = Int(fields[9]) else { continue }

            let quote = Quote(
                symbol: entry.key,
                name: name.isEmpty ? entry.value.name : name,
                price: price,
                open: open,
                high: high,
                low: low,
                settle: settle,
                volume: volume,
                oi: oi,
                timestamp: Date()
            )
            results.append(quote)
        }
        return results
    }

    private static func parseKlineResponse(_ text: String, limit: Int) -> [KlineBar] {
        // Sina K 线返回 JSONP 格式: var _RB0_Daily=[["2025-01-02","3500","3520","3480","3510","123456"],...]
        // 提取 JSON 数组部分
        guard let start = text.firstIndex(of: "["),
              let end = text.lastIndex(of: "]") else { return [] }

        let jsonStr = String(text[start...end])

        guard let jsonData = jsonStr.data(using: .utf8),
              let arr = try? JSONSerialization.jsonObject(with: jsonData) as? [[String]] else { return [] }

        var bars: [KlineBar] = []
        for row in arr.suffix(limit) {
            guard row.count >= 6 else { continue }
            let dateFormatter = DateFormatter()
            dateFormatter.dateFormat = "yyyy-MM-dd"
            guard let date = dateFormatter.date(from: row[0]),
                  let open = Double(row[1]),
                  let high = Double(row[2]),
                  let low = Double(row[3]),
                  let close = Double(row[4]),
                  let volume = Int(row[5]) else { continue }

            bars.append(KlineBar(date: date, open: open, high: high, low: low, close: close, volume: volume))
        }
        return bars
    }
}

struct KlineBar {
    let date: Date
    let open: Double
    let high: Double
    let low: Double
    let close: Double
    let volume: Int
}

enum SinaError: Error, LocalizedError {
    case invalidURL
    case encodingError
    case noData

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "URL 无效"
        case .encodingError: return "编码错误"
        case .noData: return "无数据"
        }
    }
}
