# 圖片功能整合實作計畫

**日期**: 2026-01-25 14:30  
**類型**: 功能整合計畫  
**狀態**: 待審核

---

## 1. 現況分析

### 1.1 已完成的圖片服務元件

| 元件 | 檔案位置 | 功能 | 狀態 |
|------|----------|------|------|
| **PexelsService** | `services/pexels_service.py` | 圖片搜尋、下載、AI 關鍵字生成 | ✅ 完整實作 |
| **ImageCacheService** | `services/image_cache_service.py` | 本地快取管理、TTL 過期處理 | ✅ 完整實作 |
| **SlideImageService** | `services/slide_image_service.py` | 投影片圖片指派（自動/手動） | ✅ 完整實作 |
| **SlideImage Model** | `pptagent_core/presentation/models.py` | 圖片資料結構定義 | ✅ 完整實作 |
| **Pexels API Routes** | `api/routes/pexels.py` | REST 端點 (7個) | ✅ 完整實作 |
| **SlideBuilder._place_images()** | `pptagent_core/roles/slide_builder.py` | PPTX 圖片放置 | ✅ 完整實作 |

### 1.2 關鍵發現

**ContentGenerator 已輸出 `visual_suggestion`！**

```json
{
  "slides": [{
    "slide_number": 1,
    "title": "Introduction to AI",
    "bullet_points": ["Point 1", "Point 2"],
    "visual_suggestion": "A futuristic robot hand touching a human hand",  // ← 已存在
    "speaker_notes": "..."
  }]
}
```

這是 AI 關鍵字生成的最佳來源，可直接用於圖片搜尋。

### 1.3 整合缺口

```
目前四階段流程：
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ TemplateAnalyzer│ →  │ ContentGenerator│ →  │ContentOrganizerV2│ →  │  SlideBuilder   │
│    (0-10%)      │    │   (10-50%)      │    │    (50-80%)     │    │   (80-100%)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                              ↓                        ↓
                       visual_suggestion        ❌ 沒有傳遞
                       (已生成但未使用)         ❌ 沒有圖片處理
```

**問題**: 
1. `visual_suggestion` 在 ContentOrganizerV2 後可能遺失
2. 沒有任何階段調用圖片服務
3. `SlideBuilder.build()` 收到的 `organized_content` 中沒有 `images` 欄位

---

## 2. 整合架構設計

### 2.1 選擇方案：新增 ImageEnricher 階段

經過分析，選擇新增獨立階段的方案：

```
新五階段流程 (含圖片)：
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ TemplateAnalyzer│ →  │ ContentGenerator│ →  │ContentOrganizerV2│
│    (0-10%)      │    │   (10-45%)      │    │    (45-65%)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                      ↓
┌─────────────────┐    ┌─────────────────┐           │
│  SlideBuilder   │ ←  │  ImageEnricher  │ ←─────────┘
│   (85-100%)     │    │   (65-85%)      │  ← 新增！
└─────────────────┘    └─────────────────┘
```

### 2.2 選擇理由

| 考量 | 評估 |
|------|------|
| **單一職責原則** | ✅ ImageEnricher 專注圖片處理 |
| **可測試性** | ✅ 可獨立單元測試 |
| **可選擇性** | ✅ 可透過參數啟用/禁用 |
| **現有程式碼重用** | ✅ 可重用 SlideImageService 邏輯 |
| **Layout Engine 相容** | ✅ 不影響現有文字排版 |

### 2.3 資料流設計

```
                    draft_content
                         │
                         ↓
              ┌─────────────────────┐
              │   ContentGenerator  │
              │  輸出 visual_suggestion │
              └─────────────────────┘
                         │
          ┌──────────────┴──────────────┐
          ↓                              ↓
   organized_content              draft_content
          │                       (保留 visual_suggestion)
          ↓                              │
   ┌─────────────────┐                   │
   │  ImageEnricher  │←──────────────────┘
   │                 │
   │  1. 讀取 visual_suggestion
   │  2. 生成搜尋關鍵字
   │  3. 搜尋 Pexels 圖片
   │  4. 下載並快取圖片
   │  5. 注入 images 欄位
   └─────────────────┘
          │
          ↓
   enriched_content
   (含 images 欄位)
          │
          ↓
   ┌─────────────────┐
   │  SlideBuilder   │
   │                 │
   │  _fill_slide_content() → AutoFitter
   │  _place_images() → 圖片放置
   └─────────────────┘
```

---

## 3. 詳細實作計畫

### Phase 1: 資料流適配 (影響範圍: 小)

**目標**: 確保 `visual_suggestion` 在流程中被保留

#### 1.1 修改 `ContentOrganizerV2`

**檔案**: `backend/app/pptagent_core/roles/content_organizer_v2.py`

**變更**:
```python
# 在 _build_prompt() 中，確保 visual_suggestion 被傳遞
# 在 _fallback_organize() 中，保留 visual_suggestion

# 新增欄位到輸出
organized_slide = {
    "index": i,
    "layout_index": template_slide.get("layout_index", 1),
    "layout_name": template_slide.get("layout_name", ""),
    "placeholders": [...],
    "speaker_notes": draft_slide.get("speaker_notes", ""),
    "visual_suggestion": draft_slide.get("visual_suggestion", ""),  # ← 新增
    "layout": self._determine_layout_type(template_slide),  # ← 新增
}
```

**新增方法**:
```python
def _determine_layout_type(self, template_slide: dict) -> str:
    """根據 layout_name 判斷 layout 類型"""
    layout_name = template_slide.get("layout_name", "").lower()
    if "title" in layout_name and "content" not in layout_name:
        return "title"
    elif "two" in layout_name or "column" in layout_name:
        return "two_column"
    elif "image" in layout_name:
        return "image_text"
    elif "closing" in layout_name or "end" in layout_name:
        return "closing"
    else:
        return "content"
```

---

### Phase 2: 建立 ImageEnricher Role (核心新增)

**目標**: 建立新的 Role 處理圖片注入

#### 2.1 建立 `ImageEnricher` 類別

**新檔案**: `backend/app/pptagent_core/roles/image_enricher.py`

```python
"""
Image Enricher Role

Stage 3.5: Enriches slides with images based on visual suggestions

功能：
- 讀取 ContentGenerator 輸出的 visual_suggestion
- 使用 AI 生成最佳搜尋關鍵字
- 搜尋、下載、快取 Pexels 圖片
- 注入 images 欄位到 organized_content
"""

import logging
from typing import Any

from app.services.pexels_service import PexelsService, get_pexels_service, ImageOrientation
from app.services.image_cache_service import ImageCacheService, get_image_cache_service

logger = logging.getLogger(__name__)


# 不加入圖片的 Layout 類型
SKIP_IMAGE_LAYOUTS = {"title", "closing", "section_header"}


class ImageEnricher:
    """
    Stage 3.5: 為投影片注入圖片
    
    輸入：
    - organized_content: ContentOrganizerV2 的輸出
    - draft_content: ContentGenerator 的輸出（含 visual_suggestion）
    
    輸出：enriched_content（含 images 欄位）
    """
    
    def __init__(
        self,
        pexels_service: PexelsService | None = None,
        cache_service: ImageCacheService | None = None,
    ):
        self._pexels = pexels_service
        self._cache = cache_service
    
    @property
    def pexels(self) -> PexelsService:
        if self._pexels is None:
            self._pexels = get_pexels_service()
        return self._pexels
    
    @property
    def cache(self) -> ImageCacheService:
        if self._cache is None:
            self._cache = get_image_cache_service()
        return self._cache
    
    async def enrich(
        self,
        organized_content: dict[str, Any],
        draft_content: dict[str, Any],
        presentation_title: str,
        images_per_slide: int = 1,
    ) -> dict[str, Any]:
        """
        為投影片注入圖片
        
        Args:
            organized_content: ContentOrganizerV2 的輸出
            draft_content: ContentGenerator 的輸出
            presentation_title: 簡報標題（用於 AI 關鍵字生成）
            images_per_slide: 每張投影片的圖片數量
            
        Returns:
            enriched_content: 含 images 欄位的內容
        """
        logger.info(f"開始圖片注入: {len(organized_content.get('slides', []))} 張投影片")
        
        # 建立 draft slides 的 visual_suggestion 對照表
        visual_suggestions = {}
        for draft_slide in draft_content.get("slides", []):
            idx = draft_slide.get("slide_number", 0) - 1  # 1-based to 0-based
            visual_suggestions[idx] = {
                "suggestion": draft_slide.get("visual_suggestion", ""),
                "title": draft_slide.get("title", ""),
            }
        
        # 處理每張投影片
        enriched_slides = []
        for slide in organized_content.get("slides", []):
            slide_idx = slide.get("index", 0)
            layout = slide.get("layout", "content")
            
            # 複製 slide 資料
            enriched_slide = dict(slide)
            
            # 判斷是否需要圖片
            if layout in SKIP_IMAGE_LAYOUTS:
                logger.debug(f"Slide {slide_idx}: 跳過圖片 (layout={layout})")
                enriched_slide["images"] = []
                enriched_slides.append(enriched_slide)
                continue
            
            # 取得 visual_suggestion
            vs_data = visual_suggestions.get(slide_idx, {})
            visual_suggestion = vs_data.get("suggestion", "")
            slide_title = vs_data.get("title", "") or slide.get("placeholders", [{}])[0].get("content", "")
            
            # 搜尋並加入圖片
            try:
                images = await self._get_images_for_slide(
                    visual_suggestion=visual_suggestion,
                    slide_title=slide_title,
                    presentation_title=presentation_title,
                    layout=layout,
                    count=images_per_slide,
                )
                enriched_slide["images"] = images
                logger.info(f"Slide {slide_idx}: 加入 {len(images)} 張圖片")
            except Exception as e:
                logger.warning(f"Slide {slide_idx} 圖片處理失敗: {e}")
                enriched_slide["images"] = []
            
            enriched_slides.append(enriched_slide)
        
        # 組合輸出
        enriched_content = dict(organized_content)
        enriched_content["slides"] = enriched_slides
        
        total_images = sum(len(s.get("images", [])) for s in enriched_slides)
        logger.info(f"圖片注入完成: 共 {total_images} 張圖片")
        
        return enriched_content
    
    async def _get_images_for_slide(
        self,
        visual_suggestion: str,
        slide_title: str,
        presentation_title: str,
        layout: str,
        count: int,
    ) -> list[dict]:
        """取得單張投影片的圖片"""
        
        # 1. 決定搜尋關鍵字
        if visual_suggestion:
            # 使用 AI 優化關鍵字
            keywords_result = await self.pexels.generate_search_keywords(
                course_title=presentation_title,
                slide_title=slide_title,
                slide_content=visual_suggestion,
                max_keywords=3,
            )
            primary_keyword = keywords_result.primary_keyword
            fallback_keywords = keywords_result.keywords[1:]
        else:
            # 直接使用 slide_title
            primary_keyword = slide_title
            fallback_keywords = []
        
        # 2. 檢查快取
        cached = await self.cache.get_cached_images_by_keyword(primary_keyword)
        if cached:
            return [self._cache_to_dict(c) for c in cached[:count]]
        
        # 3. 搜尋 Pexels
        orientation = self._get_orientation(layout)
        search_result = await self.pexels.search_images(
            keyword=primary_keyword,
            per_page=count + 2,  # 多取幾張備用
            orientation=orientation,
        )
        
        # 4. 若無結果，嘗試 fallback
        if not search_result.photos and fallback_keywords:
            for fallback in fallback_keywords:
                search_result = await self.pexels.search_images(
                    keyword=fallback,
                    per_page=count + 2,
                    orientation=orientation,
                )
                if search_result.photos:
                    primary_keyword = fallback
                    break
        
        if not search_result.photos:
            logger.warning(f"找不到圖片: {primary_keyword}")
            return []
        
        # 5. 下載並快取
        images = []
        for photo in search_result.photos[:count]:
            try:
                image_data = await self.pexels.download_image(photo.src.large)
                cached_info = await self.cache.save_to_cache(
                    keyword=primary_keyword,
                    image=photo,
                    image_data=image_data,
                )
                images.append({
                    "image_id": photo.id,
                    "file_path": cached_info.file_path,
                    "keyword": primary_keyword,
                    "photographer": photo.photographer,
                    "pexels_url": photo.url,
                    "alt_text": photo.alt,
                    "position": "auto",
                })
            except Exception as e:
                logger.warning(f"圖片下載失敗 {photo.id}: {e}")
                continue
        
        return images
    
    def _cache_to_dict(self, cached) -> dict:
        """將 CachedImageInfo 轉換為 dict"""
        return {
            "image_id": cached.image_id,
            "file_path": cached.file_path,
            "keyword": cached.keyword,
            "photographer": cached.photographer,
            "pexels_url": cached.pexels_url,
            "alt_text": cached.alt_text,
            "position": "auto",
        }
    
    def _get_orientation(self, layout: str) -> ImageOrientation | None:
        """根據 layout 決定圖片方向"""
        if layout in ("content", "image"):
            return ImageOrientation.LANDSCAPE
        elif layout == "image_text":
            return ImageOrientation.PORTRAIT
        return None
```

#### 2.2 更新 `roles/__init__.py`

**檔案**: `backend/app/pptagent_core/roles/__init__.py`

```python
# 新增 import
from app.pptagent_core.roles.image_enricher import ImageEnricher

__all__ = [
    # 新四階段流程 (含圖片)
    "TemplateAnalyzer",
    "ContentGenerator",
    "ContentOrganizerV2",
    "ImageEnricher",  # ← 新增
    "SlideBuilder",
    # 舊流程...
]
```

---

### Phase 3: 整合到 PPTServiceV2 (核心修改)

**目標**: 將 ImageEnricher 整合到生成流程

#### 3.1 修改 `PPTServiceV2`

**檔案**: `backend/app/services/ppt_service_v2.py`

**主要變更**:

```python
# 新增 import
from app.pptagent_core.roles.image_enricher import ImageEnricher

class PPTServiceV2:
    """
    五階段 PPT 生成服務（含圖片）
    
    工作流程：
    1. TemplateAnalyzer → Template 結構
    2. ContentGenerator → 草稿內容 (含 visual_suggestion)
    3. ContentOrganizerV2 → 組織內容
    4. ImageEnricher → 注入圖片  ← 新增
    5. SlideBuilder → PPTX
    """
    
    async def generate(
        self,
        user_input: str,
        template: str | None = None,
        slide_count: int = 10,
        audience: str | None = None,
        language: str = "zh-TW",
        add_images: bool = True,  # ← 新增參數
        images_per_slide: int = 1,  # ← 新增參數
    ) -> bytes:
        """
        從使用者輸入生成簡報
        
        Args:
            user_input: 使用者的 markdown/text 輸入
            template: Template 檔案名稱
            slide_count: 目標投影片數量
            audience: 目標受眾
            language: 輸出語言
            add_images: 是否自動加入圖片
            images_per_slide: 每張投影片的圖片數量
        """
        # ... Stage 1-3 保持不變 ...
        
        # Stage 4: 圖片注入（新增）
        if add_images:
            logger.info("[4/5] 注入圖片...")
            enricher = ImageEnricher()
            enriched_content = await enricher.enrich(
                organized_content=organized_content,
                draft_content=draft_content,
                presentation_title=draft_content.get("title", "Presentation"),
                images_per_slide=images_per_slide,
            )
        else:
            enriched_content = organized_content
        
        # Stage 5: 建構 PPTX
        logger.info("[5/5] 建構 PPTX 檔案..." if add_images else "[4/4] 建構 PPTX 檔案...")
        builder = SlideBuilder(template_path)
        pptx_bytes = builder.build(enriched_content)
        
        return pptx_bytes
```

#### 3.2 更新 `generate_stream()` 方法

```python
async def generate_stream(
    self,
    user_input: str,
    template: str | None = None,
    slide_count: int = 10,
    audience: str | None = None,
    language: str = "zh-TW",
    add_images: bool = True,
    images_per_slide: int = 1,
) -> AsyncGenerator[dict[str, Any], None]:
    """生成簡報（帶進度串流）"""
    
    # 調整進度百分比
    # Stage 1: 0-10%
    # Stage 2: 10-45%
    # Stage 3: 45-65%
    # Stage 4 (圖片): 65-85%
    # Stage 5: 85-100%
    
    # ... Stage 1-3 ...
    
    # Stage 4: 圖片注入
    if add_images:
        yield {
            "stage": "image_enrichment",
            "progress": 65,
            "message": "搜尋並注入圖片...",
        }
        
        enricher = ImageEnricher()
        enriched_content = await enricher.enrich(
            organized_content=organized_content,
            draft_content=draft_content,
            presentation_title=draft_content.get("title", "Presentation"),
            images_per_slide=images_per_slide,
        )
        
        total_images = sum(len(s.get("images", [])) for s in enriched_content.get("slides", []))
        yield {
            "stage": "image_enrichment",
            "progress": 85,
            "message": f"圖片注入完成: {total_images} 張圖片",
        }
    else:
        enriched_content = organized_content
    
    # Stage 5: 建構 PPTX (85-100%)
    yield {
        "stage": "pptx_building",
        "progress": 85,
        "message": "建構 PPTX 檔案...",
    }
    # ...
```

---

### Phase 4: Layout Engine 協調 (微調)

**目標**: 確保 SlideBuilder 正確處理圖片放置

#### 4.1 檢查 SlideBuilder

**檔案**: `backend/app/pptagent_core/roles/slide_builder.py`

**現有程式碼已支援**，確認以下邏輯正確：

```python
# 確保 layout 欄位被正確讀取
layout_type = slide_data.get("layout", "content")

# 確保 images 欄位被處理
images = slide_data.get("images", [])
if images:
    self._place_images(slide, images, layout_type)
```

#### 4.2 增強 `_place_images()` (可選優化)

```python
def _place_images(self, slide, images: list, layout_type: str):
    """動態配置圖片位置"""
    if not images:
        return
    
    # 支援多張圖片（未來擴展）
    for idx, image_data in enumerate(images):
        if idx >= 1:  # 目前只處理第一張
            break
        
        img_path = image_data.get("file_path")
        position = image_data.get("position", "auto")  # 支援手動指定位置
        
        if not img_path or not Path(img_path).exists():
            logger.warning(f"Image not found: {img_path}")
            continue
        
        # 根據 position 決定放置位置
        if position != "auto":
            left, top, width, height = self._get_position_by_type(position)
        else:
            left, top, width, height = self._get_position_by_layout(layout_type)
        
        try:
            slide.shapes.add_picture(str(img_path), left, top, width=width, height=height)
        except Exception as e:
            logger.error(f"Failed to add image: {e}")
```

---

### Phase 5: API 擴展 (可選)

**目標**: 提供 API 控制圖片功能

#### 5.1 修改 Generation API Schema

**檔案**: `backend/app/api/schemas/generation.py`

```python
class GenerationRequest(BaseModel):
    content: str
    template: str | None = None
    slide_count: int = 10
    audience: str | None = None
    language: str = "zh-TW"
    add_images: bool = True  # ← 新增
    images_per_slide: int = Field(default=1, ge=0, le=3)  # ← 新增
```

#### 5.2 修改 Generation Route

**檔案**: `backend/app/api/routes/generation.py`

```python
# 更新為使用 PPTServiceV2 並傳遞圖片參數
from app.services.ppt_service_v2 import get_ppt_service_v2

@router.post("/generate")
async def generate_presentation(request: GenerationRequest):
    service = get_ppt_service_v2()
    result = await service.generate(
        user_input=request.content,
        template=request.template,
        slide_count=request.slide_count,
        audience=request.audience,
        language=request.language,
        add_images=request.add_images,
        images_per_slide=request.images_per_slide,
    )
    # ...
```

---

### Phase 6: 測試計畫

#### 6.1 單元測試

**檔案**: `backend/tests/test_image_enricher.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.pptagent_core.roles.image_enricher import ImageEnricher

@pytest.fixture
def mock_pexels():
    service = MagicMock()
    service.generate_search_keywords = AsyncMock(return_value=MagicMock(
        primary_keyword="education",
        keywords=["education", "learning", "school"]
    ))
    service.search_images = AsyncMock(return_value=MagicMock(photos=[]))
    return service

@pytest.fixture
def mock_cache():
    service = MagicMock()
    service.get_cached_images_by_keyword = AsyncMock(return_value=[])
    return service

class TestImageEnricher:
    async def test_skip_title_slide(self, mock_pexels, mock_cache):
        enricher = ImageEnricher(mock_pexels, mock_cache)
        
        organized = {
            "slides": [{"index": 0, "layout": "title", "placeholders": []}]
        }
        draft = {"slides": [{"slide_number": 1, "visual_suggestion": "test"}]}
        
        result = await enricher.enrich(organized, draft, "Test", 1)
        
        assert result["slides"][0]["images"] == []
    
    async def test_add_images_to_content_slide(self, mock_pexels, mock_cache):
        # ...測試內容投影片是否正確加入圖片
        pass
```

#### 6.2 整合測試

```python
class TestPPTServiceV2WithImages:
    async def test_generate_with_images(self):
        service = PPTServiceV2()
        result = await service.generate(
            user_input="# Python Introduction\n- Easy to learn\n- Powerful",
            add_images=True,
            images_per_slide=1,
        )
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    async def test_generate_without_images(self):
        service = PPTServiceV2()
        result = await service.generate(
            user_input="# Test",
            add_images=False,
        )
        assert isinstance(result, bytes)
```

---

## 4. 實作優先順序

| 優先級 | Phase | 任務 | 預估工作量 |
|--------|-------|------|-----------|
| P0 | Phase 2 | 建立 ImageEnricher | 中 |
| P0 | Phase 3 | 整合到 PPTServiceV2 | 中 |
| P1 | Phase 1 | 修改 ContentOrganizerV2 保留 visual_suggestion | 小 |
| P2 | Phase 4 | Layout Engine 微調 | 小 |
| P2 | Phase 5 | API 擴展 | 小 |
| P3 | Phase 6 | 測試 | 中 |

---

## 5. 風險與緩解

| 風險 | 影響 | 緩解策略 |
|------|------|---------|
| Pexels API 限流 | 圖片搜尋失敗 | 實作重試機制、增加快取命中率 |
| 圖片下載超時 | 生成流程卡住 | 設定合理 timeout、跳過失敗的圖片 |
| 快取空間不足 | 磁碟滿載 | 實作自動清理、設定容量上限 |
| visual_suggestion 品質差 | 搜尋結果不相關 | 提供 fallback 關鍵字、允許手動替換 |

---

## 6. 檔案變更清單

| 操作 | 檔案 | 說明 |
|------|------|------|
| **新增** | `pptagent_core/roles/image_enricher.py` | 新 Role |
| **修改** | `pptagent_core/roles/__init__.py` | 匯出 ImageEnricher |
| **修改** | `pptagent_core/roles/content_organizer_v2.py` | 保留 visual_suggestion |
| **修改** | `services/ppt_service_v2.py` | 整合 ImageEnricher |
| **修改** | `api/schemas/generation.py` | 新增圖片參數 |
| **修改** | `api/routes/generation.py` | 切換到 V2 服務 |
| **新增** | `tests/test_image_enricher.py` | 單元測試 |

---

## 7. 總結

本計畫將六項圖片功能整合為一個完整的工作流程：

```
使用者輸入 → ContentGenerator (生成 visual_suggestion)
          → ContentOrganizerV2 (保留 visual_suggestion)
          → ImageEnricher (AI 關鍵字 → Pexels 搜尋 → 快取 → 注入)
          → SlideBuilder (Layout Engine + 圖片放置)
          → PPTX 輸出
```

**核心設計原則**:
1. **單一職責**: ImageEnricher 專注圖片處理
2. **可選啟用**: `add_images` 參數控制
3. **快取優先**: 減少 API 呼叫
4. **優雅降級**: 圖片失敗不影響整體生成
5. **Layout 相容**: 與現有 Layout Engine 無縫整合

**待您確認後即可開始實作。**
