import Foundation
import UserNotifications

/// 通知服务：本地通知 + Bark 推送
class NotificationService: ObservableObject {
    @Published var isAuthorized = false

    func requestPermission() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
            DispatchQueue.main.async {
                self.isAuthorized = granted
            }
        }
    }

    // MARK: - 本地定时通知

    /// 注册每日盘前简报提醒
    func scheduleMorningBriefing(hour: Int = 8, minute: Int = 30) {
        let content = UNMutableNotificationContent()
        content.title = "📊 盘前简报已生成"
        content.body = "打开 FuturesBot 查看今日交易建议"
        content.sound = .default

        var dateComponents = DateComponents()
        dateComponents.hour = hour
        dateComponents.minute = minute

        let trigger = UNCalendarNotificationTrigger(dateMatching: dateComponents, repeats: true)
        let request = UNNotificationRequest(
            identifier: "morning-briefing",
            content: content,
            trigger: trigger
        )
        UNUserNotificationCenter.current().add(request)
    }

    /// 注册每日盘后复盘提醒
    func scheduleEveningReview(hour: Int = 15, minute: Int = 15) {
        let content = UNMutableNotificationContent()
        content.title = "📉 盘后复盘"
        content.body = "打开 FuturesBot 填写今日复盘"
        content.sound = .default

        var dateComponents = DateComponents()
        dateComponents.hour = hour
        dateComponents.minute = minute

        let trigger = UNCalendarNotificationTrigger(dateMatching: dateComponents, repeats: true)
        let request = UNNotificationRequest(
            identifier: "evening-review",
            content: content,
            trigger: trigger
        )
        UNUserNotificationCenter.current().add(request)
    }

    // MARK: - 即时通知

    /// 发送止损/突破告警
    func sendAlert(title: String, body: String, isUrgent: Bool = false) {
        // 1. 本地通知
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = isUrgent ? .defaultCritical : .default

        let request = UNNotificationRequest(
            identifier: UUID().uuidString,
            content: content,
            trigger: nil  // 立即
        )
        UNUserNotificationCenter.current().add(request)

        // 2. Bark 推送（如果配了）
        sendBark(title: title, body: body, level: isUrgent ? "urgent" : "info")
    }

    // MARK: - Bark

    private func sendBark(title: String, body: String, level: String) {
        // 预配置 Bark URL
        let barkURL = UserDefaults.standard.string(forKey: "bark_url") ?? "https://api.day.app/S3QnU9QTHddi3XB8Pc8E8o"
        guard !barkURL.isEmpty else { return }

        let urlStr = "\(barkURL)/push"
        guard let url = URL(string: urlStr) else { return }

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
}
