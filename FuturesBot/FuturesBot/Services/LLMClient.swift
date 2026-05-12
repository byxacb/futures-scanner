import Foundation

/// LLM 客户端
/// 调用 Anthropic Messages API 兼容协议
class LLMClient: ObservableObject {
    @Published var isLoading = false
    @Published var lastError: String?

    private var baseURL: String {
        // 预配置：小米 MiMo via token-plan 代理
        UserDefaults.standard.string(forKey: "llm_base_url") ?? "https://token-plan-cn.xiaomimimo.com/anthropic"
    }

    private var apiKey: String {
        // 预配置 API Key（从 .env 同步）
        "tp-cn1zy7n31ysdkjk5baapey3dadlpjhtf7xir6pc0cjsdpong"
    }

    private var model: String {
        UserDefaults.standard.string(forKey: "llm_model") ?? "mimo-v2.5-pro"
    }

    /// 发送聊天消息
    func chat(messages: [ChatMessage], systemPrompt: String? = nil) async throws -> String {
        guard !apiKey.isEmpty else {
            throw LLMError.noAPIKey
        }

        var body: [String: Any] = [
            "model": model,
            "max_tokens": 2000,
            "temperature": 0.3,
            "messages": messages.map { ["role": $0.role, "content": $0.content] }
        ]

        if let system = systemPrompt {
            body["system"] = system
        }

        let urlStr = "\(baseURL)/v1/messages"
        guard let url = URL(string: urlStr) else {
            throw LLMError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue(apiKey, forHTTPHeaderField: "x-api-key")
        request.setValue("2023-06-01", forHTTPHeaderField: "anthropic-version")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        request.timeoutInterval = 60

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw LLMError.networkError
        }

        guard httpResponse.statusCode == 200 else {
            let text = String(data: data, encoding: .utf8) ?? "unknown"
            throw LLMError.apiError(statusCode: httpResponse.statusCode, message: text)
        }

        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        let content = json?["content"] as? [[String: Any]]

        // 提取第一个 text block
        for block in content ?? [] {
            if block["type"] as? String == "text",
               let text = block["text"] as? String {
                return text
            }
        }

        throw LLMError.noContent
    }

    /// 流式聊天（返回 AsyncStream）
    func chatStream(messages: [ChatMessage], systemPrompt: String? = nil) -> AsyncStream<String> {
        AsyncStream { continuation in
            Task {
                do {
                    let response = try await chat(messages: messages, systemPrompt: systemPrompt)
                    continuation.yield(response)
                } catch {
                    continuation.yield("❌ 错误: \(error.localizedDescription)")
                }
                continuation.finish()
            }
        }
    }
}

enum LLMError: Error, LocalizedError {
    case noAPIKey
    case invalidURL
    case networkError
    case apiError(statusCode: Int, message: String)
    case noContent

    var errorDescription: String? {
        switch self {
        case .noAPIKey: return "未配置 API Key"
        case .invalidURL: return "URL 无效"
        case .networkError: return "网络错误"
        case .apiError(let code, let msg): return "API 错误 \(code): \(msg.prefix(200))"
        case .noContent: return "API 返回空内容"
        }
    }
}

struct ChatMessage: Identifiable {
    let id = UUID()
    let role: String  // "user" or "assistant"
    let content: String
    let timestamp: Date

    init(role: String, content: String) {
        self.role = role
        self.content = content
        self.timestamp = Date()
    }
}

/// Keychain 读写工具
enum KeychainHelper {
    static func get(key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess, let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    static func set(key: String, value: String) {
        delete(key: key)
        let data = value.data(using: .utf8)!
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data
        ]
        SecItemAdd(query as CFDictionary, nil)
    }

    static func delete(key: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key
        ]
        SecItemDelete(query as CFDictionary)
    }
}
