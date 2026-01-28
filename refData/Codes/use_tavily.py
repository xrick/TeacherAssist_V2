from tavily import TavilyClient

# 1. 初始化 (你需要去 tavily.com 申請一個免費 API Key)
# 實務上請將 Key 放在環境變數 (.env) 中
tavily_client = TavilyClient(api_key="tvly-YOUR_API_KEY_HERE")


def search_google_for_rag(query):
    """
    使用 Tavily 搜尋 Google 並回傳整合後的文本內容
    """
    print(f"正在網路上搜尋：{query} ...")

    # 2. 執行搜尋
    # search_depth="advanced" 會爬得比較深，內容比較豐富
    # max_results=3 表示只抓最相關的 3 篇文章
    response = tavily_client.search(query=query, search_depth="advanced", max_results=3)

    # 3. 整理搜尋結果
    # Tavily 會回傳一個 list，裡面包含 'content' (內文)
    combined_content = ""
    for result in response["results"]:
        title = result["title"]
        url = result["url"]
        content = result["content"]  # 這是它已經幫你爬下來的內文

        combined_content += f"=== 來源：{title} ({url}) ===\n{content}\n\n"

    return combined_content


# --- 測試 ---
user_query = "介紹最新的 AI Agent 發展趨勢"
rag_context = search_google_for_rag(user_query)

print("\n--- 準備餵給 LLM 的 RAG 資料 ---")
print(rag_context[:500])  # 只印出前 500 字給你看
