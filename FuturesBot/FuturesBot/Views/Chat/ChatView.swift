import SwiftUI

struct ChatView: View {
    @StateObject private var llmClient = LLMClient()
    @EnvironmentObject var market: MarketService
    @State private var messages: [ChatMessage] = []
    @State private var inputText = ""
    @State private var isGenerating = false

    private let systemPrompt = """
    你是国贸期货杯·厦门大学模拟期货比赛的 AI 交易助手。

    核心规则：
    - 评分公式：收益率 40% + 最大回撤 20% + 夏普 30% + 波动率 10%（60% 在惩罚风险）
    - 策略：受控激进——基础仓 30-40%、单品种 ≤10%、单笔风险 1%、关键信号叠加 60-70%
    - 绝不建议穿仓、无止损单、马丁加仓
    - 短回答，用中文，给出可执行的建议
    """

    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // 消息列表
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 12) {
                            // 欢迎消息
                            if messages.isEmpty {
                                welcomeCard
                            }

                            ForEach(messages) { message in
                                messageBubble(message)
                                    .id(message.id)
                            }

                            if isGenerating {
                                HStack {
                                    ProgressView()
                                        .padding(8)
                                    Text("思考中...")
                                        .font(.caption)
                                        .foregroundColor(.secondary)
                                }
                            }
                        }
                        .padding()
                    }
                    .onChange(of: messages.count) { _ in
                        withAnimation {
                            proxy.scrollTo(messages.last?.id, anchor: .bottom)
                        }
                    }
                }

                Divider()

                // 输入框
                HStack(spacing: 12) {
                    TextField("问我期货问题...", text: $inputText)
                        .textFieldStyle(.plain)
                        .padding(12)
                        .background(Color(.systemGray6))
                        .cornerRadius(20)
                        .onSubmit { sendMessage() }

                    Button(action: sendMessage) {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.title2)
                            .foregroundColor(inputText.isEmpty ? .gray : .orange)
                    }
                    .disabled(inputText.isEmpty || isGenerating)
                }
                .padding(.horizontal)
                .padding(.vertical, 8)
            }
            .navigationTitle("AI 助手")
        }
    }

    private var welcomeCard: some View {
        VStack(spacing: 16) {
            Image(systemName: "brain.head.profile")
                .font(.system(size: 48))
                .foregroundColor(.orange)

            Text("期货 AI 助手")
                .font(.title2)
                .fontWeight(.bold)

            Text("基于 100 本投资经典 + 主策略文档训练")
                .font(.subheadline)
                .foregroundColor(.secondary)

            // 快捷提问
            VStack(spacing: 8) {
                quickButton("今天 rb 怎么做？")
                quickButton("给我解释一下 ATR 止损")
                quickButton("当前信号质量如何？")
            }
        }
        .padding(24)
    }

    private func quickButton(_ text: String) -> some View {
        Button(action: {
            inputText = text
            sendMessage()
        }) {
            Text(text)
                .font(.subheadline)
                .foregroundColor(.orange)
                .frame(maxWidth: .infinity)
                .padding(10)
                .background(Color.orange.opacity(0.1))
                .cornerRadius(10)
        }
    }

    private func messageBubble(_ message: ChatMessage) -> some View {
        HStack {
            if message.role == "user" { Spacer(minLength: 60) }

            VStack(alignment: message.role == "user" ? .trailing : .leading, spacing: 4) {
                Text(message.content)
                    .padding(12)
                    .background(message.role == "user" ? Color.orange : Color(.systemGray5))
                    .foregroundColor(message.role == "user" ? .white : .primary)
                    .cornerRadius(16)

                Text(message.timestamp.formatted(date: .omitted, time: .shortened))
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }

            if message.role == "assistant" { Spacer(minLength: 60) }
        }
    }

    private func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        let userMessage = ChatMessage(role: "user", content: text)
        messages.append(userMessage)
        inputText = ""
        isGenerating = true

        Task {
            do {
                // 加入当前行情上下文
                let contextMessages = messages.map { ChatMessage(role: $0.role, content: $0.content) }
                let response = try await llmClient.chat(
                    messages: contextMessages,
                    systemPrompt: systemPrompt + "\n\n当前行情快照：\n" + marketSummary()
                )
                let assistantMessage = ChatMessage(role: "assistant", content: response)
                messages.append(assistantMessage)
            } catch {
                let errorMessage = ChatMessage(role: "assistant", content: "❌ 错误: \(error.localizedDescription)\n\n请检查 LLM API Key 配置。")
                messages.append(errorMessage)
            }
            isGenerating = false
        }
    }

    private func marketSummary() -> String {
        var lines = [String]()
        for symbol in market.defaultSymbols {
            if let quote = market.quotes[symbol],
               let signal = market.signals.first(where: { $0.symbol == symbol }) {
                lines.append("- \(quote.name) (\(symbol)): \(Int(quote.price)) | 信号: \(signal.quality.label) \(signal.direction.label)")
            }
        }
        return lines.joined(separator: "\n")
    }
}
