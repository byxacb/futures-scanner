import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var notification: NotificationService
    @AppStorage("llm_base_url") private var baseURL = "https://token-plan-cn.xiaomimimo.com/anthropic"
    @AppStorage("llm_model") private var model = "mimo-v2.5-pro"
    @AppStorage("account_equity") private var accountEquity = 1_000_000.0
    @AppStorage("bark_url") private var barkURL = ""
    @State private var apiKey = ""
    @State private var showAPIKey = false
    @State private var saved = false

    var body: some View {
        NavigationView {
            Form {
                Section("LLM API") {
                    HStack {
                        Label("API Key", systemImage: "key")
                        Spacer()
                        if showAPIKey {
                            TextField("sk-...", text: $apiKey)
                                .textFieldStyle(.plain)
                                .monospaced()
                        } else {
                            SecureField("sk-...", text: $apiKey)
                                .textFieldStyle(.plain)
                        }
                        Button(action: { showAPIKey.toggle() }) {
                            Image(systemName: showAPIKey ? "eye.slash" : "eye")
                                .foregroundColor(.secondary)
                        }
                    }

                    HStack {
                        Label("Base URL", systemImage: "link")
                        TextField("https://...", text: $baseURL)
                            .textFieldStyle(.plain)
                            .monospaced()
                    }

                    HStack {
                        Label("模型", systemImage: "cpu")
                        TextField("mimo-v2.5-pro", text: $model)
                            .textFieldStyle(.plain)
                    }
                }

                Section("Bark 推送") {
                    HStack {
                        Label("Bark URL", systemImage: "bell")
                        TextField("https://api.day.app/...", text: $barkURL)
                            .textFieldStyle(.plain)
                    }
                }

                Section("账户") {
                    HStack {
                        Label("初始资金", systemImage: "banknote")
                        TextField("1000000", value: $accountEquity, format: .number)
                            .textFieldStyle(.plain)
                            .keyboardType(.decimalPad)
                    }
                }

                Section("通知") {
                    HStack {
                        Label("盘前简报", systemImage: "sun.max")
                        Spacer()
                        Text("08:30")
                            .foregroundColor(.secondary)
                    }
                    .onTapGesture {
                        notification.scheduleMorningBriefing()
                    }

                    HStack {
                        Label("盘后复盘", systemImage: "moon")
                        Spacer()
                        Text("15:15")
                            .foregroundColor(.secondary)
                    }
                    .onTapGesture {
                        notification.scheduleEveningReview()
                    }

                    Button("测试通知") {
                        notification.sendAlert(
                            title: "🎉 通知测试",
                            body: "如果你看到这条通知，说明推送工作正常！"
                        )
                    }
                }

                Section("关于") {
                    HStack {
                        Text("版本")
                        Spacer()
                        Text("1.0.0")
                            .foregroundColor(.secondary)
                    }
                    HStack {
                        Text("品种数")
                        Spacer()
                        Text("28")
                            .foregroundColor(.secondary)
                    }
                    HStack {
                        Text("知识库")
                        Spacer()
                        Text("100 本书 + 15 品种手册")
                            .foregroundColor(.secondary)
                    }
                }
            }
            .navigationTitle("设置")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("保存") {
                        // 保存 API Key 到 Keychain
                        if !apiKey.isEmpty {
                            KeychainHelper.set(key: "llm_api_key", value: apiKey)
                        }
                        saved = true
                        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                            saved = false
                        }
                    }
                }
            }
            .overlay {
                if saved {
                    VStack {
                        Text("✅ 已保存")
                            .font(.headline)
                            .padding()
                            .background(.ultraThinMaterial)
                            .cornerRadius(12)
                    }
                    .transition(.opacity)
                }
            }
            .onAppear {
                // 从 Keychain 加载（预配置）
                apiKey = KeychainHelper.get(key: "llm_api_key") ?? "tp-cn1zy7n31ysdkjk5baapey3dadlpjhtf7xir6pc0cjsdpong"
                barkURL = UserDefaults.standard.string(forKey: "bark_url") ?? "https://api.day.app/S3QnU9QTHddi3XB8Pc8E8o"
            }
            .onChange(of: barkURL) { newValue in
                UserDefaults.standard.set(newValue, forKey: "bark_url")
            }
        }
    }
}
