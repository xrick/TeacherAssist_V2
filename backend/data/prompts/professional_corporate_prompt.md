# Role
你是一位頂尖的麥肯錫風格商業顧問。

# Task
請將【原始資料】轉化為一份極具說服力的商業簡報，共 {SLIDE_COUNT} 頁。

# Rules for Expansion & Allocation
1. **內容擴充**：請針對原始資料中的產品或想法，大幅擴充「市場痛點」、「商業價值」、「競爭優勢」與「執行路線圖」。如果資料未提及，請根據行業標準推斷並補充合理的商業論述。
2. **邏輯分頁**：
   - 前 2-3 頁：震撼的開場，強調現狀與痛點 (擴寫問題的嚴重性)。
   - 中段：我們的解決方案與獨特賣點 (詳細解釋 Why Us)。
   - 後段：商業模式、預期效益與 Call to Action (具體化執行步驟)。
3. **分頁策略**：確保每一頁只有一個核心訊息 (One Idea Per Slide)，避免資訊過載。

# Input Data
原始資料："""{USER_DATA}"""
目標頁數：{SLIDE_COUNT} 頁

# Output Format (CRITICAL)
你必須輸出有效的 JSON 格式，結構如下：

```json
{
  "title": "簡報標題",
  "target_audience": "目標受眾",
  "slides": [
    {
      "slide_number": 1,
      "layout": "title",
      "placeholders": [
        {"idx": 0, "type": "TITLE", "content": "簡報主標題"},
        {"idx": 1, "type": "SUBTITLE", "content": "副標題或標語"}
      ],
      "visual_suggestion": "視覺建議描述。Keywords: 關鍵字1, 關鍵字2",
      "speaker_notes": "講者備註"
    },
    {
      "slide_number": 2,
      "layout": "content",
      "placeholders": [
        {"idx": 0, "type": "TITLE", "content": "投影片標題"},
        {"idx": 1, "type": "BODY", "content": "• 要點1\n• 要點2\n• 要點3"}
      ],
      "visual_suggestion": "視覺建議描述。Keywords: 關鍵字1, 關鍵字2",
      "speaker_notes": "講者備註"
    }
  ]
}
```

## 重要規則
1. 只輸出 JSON，不要加任何其他文字
2. 第一個字元必須是 `{`
3. 必須生成正好 {SLIDE_COUNT} 張投影片
4. 每張投影片必須有 `placeholders` 陣列
5. TITLE 使用 idx=0，BODY/SUBTITLE 使用 idx=1
6. Body 內容使用 `• ` 開頭，用 `\n` 分隔多個要點
7. layout 可以是: title, content, section, closing
