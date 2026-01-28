# 模板 UI 文字追蹤報告

> 日期：2026-01-28 11:00

## 目標

追蹤使用者介面上模板選擇畫廊（Template Gallery）中每個模板卡片的名稱、描述、標籤文字的定義位置。

## 截圖參考

`refData/images/ppt_template.png` — 顯示 7 個模板卡片，包含名稱、描述文字與標籤。

## 資料流向總覽

```
backend/data/templates/*.json        ← 描述與標籤在此定義
  ↓
TemplateService._create_metadata()   ← 讀取 JSON，名稱從 PPTX 檔名自動生成
  (backend/app/services/template_service.py)
  ↓
GET /api/v1/templates                ← API 回傳 TemplateListResponse
  (backend/app/api/routes/templates.py)
  ↓
frontend/src/api/client.ts           ← templateAPI.list() 呼叫 API
  ↓
TemplateGallery.tsx                  ← 前端渲染 name / description / tags
  (frontend/src/components/template/TemplateGallery.tsx)
```

## 各層級關鍵檔案

| 層級 | 檔案 | 角色 |
|------|------|------|
| 資料定義 | `backend/data/templates/*.json` | 模板描述、標籤、預覽圖路徑 |
| 資料定義 | `backend/data/templates/*.pptx` | 模板名稱來源（檔名自動轉換） |
| 後端服務 | `backend/app/services/template_service.py` | `_scan_templates()` 掃描檔案、`_create_metadata()` 組裝 metadata |
| 後端路由 | `backend/app/api/routes/templates.py` | `list_templates()` 處理 GET /api/v1/templates |
| 後端 Schema | `backend/app/api/schemas/templates.py` | `TemplateResponse` Pydantic model |
| 前端 API | `frontend/src/api/client.ts` | `templateAPI.list()` 呼叫後端 |
| 前端型別 | `frontend/src/types/api.ts` | `Template` interface 定義 |
| 前端元件 | `frontend/src/components/template/TemplateGallery.tsx` | 渲染模板卡片 |

## 模板 JSON 定義檔案對照

所有 JSON 檔案位於 `backend/data/templates/`：

| 模板名稱 | JSON 檔案 | PPTX 檔案 |
|----------|-----------|-----------|
| Professional Corporate | `professional_corporate.json` | `professional_corporate.pptx` |
| Education Basic | `education_basic.json` | `education_basic.pptx` |
| Nature Artistic | `nature_artistic.json` | `nature_artistic.pptx` |
| Industrial Tech | `industrial_tech.json` | `industrial_tech.pptx` |
| Modern Clean | `modern_clean.json` | `modern_clean.pptx` |
| Pastoral Style | `pastoral_style.json` | `pastoral_style.pptx` |
| Creative Colorful | `creative_colorful.json` | `creative_colorful.pptx` |

## 各模板 JSON 內容

### professional_corporate.json
```json
{
  "description": "專為企業商務場合設計的專業風格模板，採用深藍與金色搭配，展現穩重權威與專業形象，適合正式會議、商業提案及高階主管簡報使用",
  "tags": ["專業", "企業", "商務", "正式", "權威"],
  "preview_image": "/api/v1/static/templates/previews/professional_corporate.png"
}
```

### education_basic.json
```json
{
  "description": "適合教學使用的基礎教育模板，清晰易讀的藍色系設計",
  "tags": ["教育", "教學", "基礎", "專業"],
  "preview_image": "/api/v1/static/templates/previews/education_basic.png"
}
```

### nature_artistic.json
```json
{
  "description": "以自然元素為靈感的藝術風格，適合環境、生態或輕鬆氛圍的主題",
  "tags": ["自然", "藝術", "綠色", "環保"],
  "preview_image": "/api/v1/static/templates/previews/nature_artistic.png"
}
```

### industrial_tech.json
```json
{
  "description": "融合工業美學與科技感的現代風格模板，採用深灰、橙色與金屬質感元素，展現創新力與執行力，適合製造業、工程技術、科技產品發表及技術研討會使用",
  "tags": ["工業", "科技", "製造", "技術", "創新"],
  "preview_image": "/api/v1/static/templates/previews/industrial_tech.png"
}
```

### modern_clean.json
```json
{
  "description": "適合商業簡報的現代簡約風格，簡潔大方的灰白色系設計",
  "tags": ["商業", "簡約", "現代", "專業"],
  "preview_image": "/api/v1/static/templates/previews/modern_clean.png"
}
```

### pastoral_style.json
```json
{
  "description": "以田園風光為靈感的溫馨風格模板，採用柔和的大地色系與自然元素，營造寧靜舒適的視覺氛圍，適合農業、園藝、生態旅遊、鄉村文化及休閒生活主題的簡報使用",
  "tags": ["田園", "自然", "溫馨", "鄉村", "生態"],
  "preview_image": "/api/v1/static/templates/previews/pastoral_style.png"
}
```

### creative_colorful.json
```json
{
  "description": "充滿活力的創意設計，鮮豔多彩適合創意提案和展示",
  "tags": ["創意", "活潑", "多彩", "設計"],
  "preview_image": "/api/v1/static/templates/previews/creative_colorful.png"
}
```

## 名稱生成邏輯

模板名稱**不在 JSON 中定義**，而是由 `TemplateService._create_metadata()` 從 PPTX 檔名自動生成：

- 檔名 `professional_corporate.pptx` → 取 stem `professional_corporate` → title case → `Professional Corporate`
- 檔名 `education_basic.pptx` → `Education Basic`

## 前端 UI 文字（靜態）

除了來自 API 的動態資料外，`TemplateGallery.tsx` 中還有以下靜態文字：

| 文字 | 用途 |
|------|------|
| `載入模板中...` | 載入狀態提示 |
| `選擇模板` | 畫廊標題 |
| `{n} 個可用模板` | 模板數量顯示 |
| `尚無可用模板` | 空狀態提示 |

## 修改指引

- 修改模板描述或標籤：編輯 `backend/data/templates/<template_name>.json`
- 修改模板名稱：重新命名對應的 `.pptx` 和 `.json` 檔案
- 修改 UI 靜態文字：編輯 `frontend/src/components/template/TemplateGallery.tsx`
