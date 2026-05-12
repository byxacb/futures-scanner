import SwiftUI

@main
struct FuturesBotApp: App {
    @StateObject private var marketService = MarketService()
    @StateObject private var notificationService = NotificationService()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(marketService)
                .environmentObject(notificationService)
                .onAppear {
                    notificationService.requestPermission()
                    // 注册每日定时通知
                    notificationService.scheduleMorningBriefing(hour: 8, minute: 30)
                    notificationService.scheduleEveningReview(hour: 15, minute: 15)
                    // 启动行情轮询
                    marketService.startPolling()
                    // 首次拉取数据
                    Task { await marketService.refreshAll() }
                }
        }
    }
}
