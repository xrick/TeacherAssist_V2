/sc:analyze --c7 --seq --focus architecture
請再分析以下二個專案，它們產生pptx的流程、文字排版、適當的圖片產生或搜尋、圖片如何放到正確位置
- refData/Codes/presentation-ai-main
- refData/Codes/GenSlide-main.zip
分析過後，重新產生最佳的流程。我有個想法，你可以參考看看：
採用json把
整個PPTX結構,
每一頁的文字內容,
文字排版,
每頁的圖片儲存路徑,
每頁的圖片如何插入到合適的位置,
其它需要考慮的issues.
記錄下來。
大致的結構會是：
{
"pptx架構":......,
"title":.....,
"outline":...,
"第一頁":{
    "subtitle":....,
    "content":....,
    "text_layout":...,
    "images":[],
    "images_positions":[]
    }
.....
}
這是我的個人想法，你可以思考看看，不見得要依這個格式，但先產生json就像是蓋大樓，先有藍圖，才能按圖來進行建造，道理是一樣的。
**very important**:請逐步思考，產生可行的、結果正確的計畫及流程。
