/sc:brainstorm 
在進行計畫前，還有幾項資料，要進行了解，也許要重新產生計畫，若需要請命名為"claudedocs/system_design_blueprints/pptx產生藍圖及計畫_v0.2_202601291409.md"
A. please read the definition of "clean template":
```
1. 清潔版範本架構定義 (The Schema)我們將這個範本定義為 clean_template_v1。它只包含 4 種基礎版型，對應您檔案中的 4 頁：版型名稱 (Key)原始頁碼識別特徵 (Source Content)程式用途COVERSlide 1標題：「教授課程」 副標題：「簡報副標題」 用於簡報的第一頁，填入主題與演講者。AGENDASlide 2標題：「課程大綱」 列表：「第一課...」 用於生成目錄或章節列表。CONTENTSlide 3標題：「第一個技能」 內文：「Lorem ipsum...」 核心版面。用於生成所有詳細內容頁。系統會重複複製此頁。ENDINGSlide 4標題：「感謝您！」 用於簡報結束。
```
我們目前所有的templalte pptx都是clean version template, 在此我們先用"professional_corporate.pptx"來進行測試。
B.接下來我們得定義一個config檔，讓程式能了解它要使用的pptx的結構, 但這個config檔必須有足夠的彈性，因為使用者只會選擇何種template及頁數，因此要定義這樣的template_config.json，我們採用以下的方法：
"""
1. 核心概念：角色化分組 (Role-Based Grouping)
我們不再依賴使用者指定，而是將 8 個版面分為三類：
固定頁 (Fixed)：開頭 (Cover) 和結尾 (Ending) 是一定要有的。
內容池 (Body Pool)：那些適合放文字內容的版面（左圖右文、純文字、三欄式）。程式會從這裡「隨機」或「輪詢」抓取，直到湊滿頁數。
結構頁 (Structural)：如目錄 (Agenda) 或 過場頁 (Section Header)。
---
2. 修改後的 JSON 設定檔 (System-Centric)
這個 JSON 的設計邏輯是告訴程式：「當你需要填充內容頁時，請從 body_pool 裡面挑選版面。」
{
  "template_name": "smart_corporate_8slides",
  "file_path": "professional_corporate_8slides.pptx",
  "total_layouts_in_file": 8,
  
  "structure_rules": {
    "opening": 0,          // Slide 1: 封面 (固定第1頁)
    "agenda": 1,           // Slide 2: 目錄 (固定第2頁)
    "closing": 7,          // Slide 8: 結尾 (固定最後一頁)
    
    "body_pool": [2, 3, 4] // Slide 3, 4, 5: 內容版面池
                           // 系統會自動在這些版面中輪替，填滿中間的頁數
  },

  "advanced_rules": {
     "section_header": 5,  // Slide 6: 過場頁 (可選：每隔 X 頁自動插入)
     "quote": 6            // Slide 7: 引言頁 (可選：隨機插入)
  },

  "placeholders": {
    "standard": { "title": 0, "body": 1 },  // 大部分版面的規則
    "exceptions": {
        "4": { "title": 0, "body": 10 }     // 如果 Slide 5 (Index 4) 的 placeholder 比較特別，在這裡定義
    }
  }
}
---
3. 自動化分配演算法 (The Algorithm)這是後端程式該有的運作邏輯（以 Python 為例）。使用者只要輸入 total_pages = 10，程式就會自己算數學。運作邏輯：扣除固定頁：封面(1) + 目錄(1) + 結尾(1) = 3 頁。計算剩餘空間：使用者要 10 頁，剩餘空間 = $10 - 3 = 7$ 頁。填充內容：程式從 body_pool: [2, 3, 4] 裡面循環抓取，依序填入這 7 頁。Page 3 -> Layout 2Page 4 -> Layout 3Page 5 -> Layout 4Page 6 -> Layout 2 (循環開始)...以此類推。
---
4. 實作程式碼範例
這段程式碼展示了如何「隱藏複雜度」，只接受 target_page_count 作為輸入：
```python
from pptx import Presentation
import itertools # 用來做循環輪替

def generate_smart_presentation(target_page_count, config):
    prs = Presentation(config['file_path'])
    rules = config['structure_rules']
    
    # 1. 建立封面 (固定)
    slide = prs.slides.add_slide(prs.slide_layouts[rules['opening']])
    # fill_cover_content(slide, user_data)...
    
    # 2. 建立目錄 (固定)
    slide = prs.slides.add_slide(prs.slide_layouts[rules['agenda']])
    # fill_agenda_content(slide, user_data)...
    
    # 3. 計算中間需要產生幾頁內容頁
    # 假設固定頁有 Cover, Agenda, Closing 共 3 頁
    fixed_count = 3
    body_count_needed = target_page_count - fixed_count
    
    if body_count_needed < 0:
        body_count_needed = 0 # 防呆
        
    # 4. 準備內容池循環器 (Cycler)
    # 這會產生一個無限迭代器: 2, 3, 4, 2, 3, 4...
    body_pool_indices = rules['body_pool']
    layout_cycler = itertools.cycle(body_pool_indices)
    
    # 5. 自動填充內容頁
    for _ in range(body_count_needed):
        # 從池子裡拿出下一個版型索引
        next_layout_index = next(layout_cycler)
        layout = prs.slide_layouts[next_layout_index]
        
        slide = prs.slides.add_slide(layout)
        # fill_body_content(slide, generated_text_segment)...
        print(f"新增內容頁，使用 Layout Index: {next_layout_index}")

    # 6. 建立結尾 (固定)
    slide = prs.slides.add_slide(prs.slide_layouts[rules['closing']])
    
    prs.save("final_output.pptx")

# 模擬執行
# generate_smart_presentation(10, json_config)
```
"""
請將以上我所描述的，重新與你的方案進行整合
