import SwiftUI

struct ContentView: View {
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            DashboardView()
                .tabItem {
                    Label("简报", systemImage: "chart.bar.doc.horizontal")
                }
                .tag(0)

            MonitorView()
                .tabItem {
                    Label("行情", systemImage: "chart.line.uptrend.xyaxis")
                }
                .tag(1)

            TradeDecisionView()
                .tabItem {
                    Label("交易", systemImage: "arrow.triangle.2.circlepath")
                }
                .tag(2)

            ChatView()
                .tabItem {
                    Label("AI 助手", systemImage: "bubble.left.and.bubble.right")
                }
                .tag(3)

            SettingsView()
                .tabItem {
                    Label("设置", systemImage: "gearshape")
                }
                .tag(4)
        }
        .tint(.orange)
    }
}
