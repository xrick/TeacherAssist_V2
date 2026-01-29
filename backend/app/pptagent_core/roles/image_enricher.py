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

from app.services.image_cache_service import ImageCacheService, get_image_cache_service
from app.services.pexels_service import (
    ImageOrientation,
    PexelsService,
    get_pexels_service,
)

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
        """延遲初始化 Pexels 服務"""
        if self._pexels is None:
            self._pexels = get_pexels_service()
        return self._pexels

    @property
    def cache(self) -> ImageCacheService:
        """延遲初始化快取服務"""
        if self._cache is None:
            self._cache = get_image_cache_service()
        return self._cache

    async def enrich(
        self,
        organized_content: dict[str, Any],
        draft_content: dict[str, Any],
        presentation_title: str,
        images_per_slide: int = 1,
        max_images: int | None = None,
    ) -> dict[str, Any]:
        """
        為投影片注入圖片

        Args:
            organized_content: ContentOrganizerV2 的輸出
            draft_content: ContentGenerator 的輸出
            presentation_title: 簡報標題（用於 AI 關鍵字生成）
            images_per_slide: 每張投影片的圖片數量
            max_images: 最大總圖片數量（None = 不限制）

        Returns:
            enriched_content: 含 images 欄位的內容
        """
        slides = organized_content.get("slides", [])
        logger.info(f"開始圖片注入: {len(slides)} 張投影片, max_images={max_images}")

        # 建立 draft slides 的 visual_suggestion 對照表
        visual_suggestions = self._build_visual_suggestions_map(draft_content)

        # 處理每張投影片
        enriched_slides = []
        total_images_added = 0

        for slide in slides:
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

            # v0.3: 檢查是否已達到最大圖片數量
            if max_images is not None and total_images_added >= max_images:
                logger.debug(f"Slide {slide_idx}: 已達最大圖片數量 ({max_images})")
                enriched_slide["images"] = []
                enriched_slides.append(enriched_slide)
                continue

            # 取得 visual_suggestion
            vs_data = visual_suggestions.get(slide_idx, {})
            visual_suggestion = slide.get("visual_suggestion", "") or vs_data.get("suggestion", "")
            slide_title = vs_data.get("title", "") or self._extract_title_from_placeholders(slide)

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
                total_images_added += len(images)

                if images:
                    logger.info(f"Slide {slide_idx}: 加入 {len(images)} 張圖片")
                else:
                    logger.debug(f"Slide {slide_idx}: 無可用圖片")

            except Exception as e:
                logger.warning(f"Slide {slide_idx} 圖片處理失敗: {e}")
                enriched_slide["images"] = []

            enriched_slides.append(enriched_slide)

        # 組合輸出
        enriched_content = dict(organized_content)
        enriched_content["slides"] = enriched_slides

        logger.info(f"圖片注入完成: 共 {total_images_added} 張圖片")

        return enriched_content

    def _build_visual_suggestions_map(
        self, draft_content: dict[str, Any]
    ) -> dict[int, dict[str, str]]:
        """
        建立 visual_suggestion 對照表

        Args:
            draft_content: ContentGenerator 的輸出

        Returns:
            {slide_index: {"suggestion": "...", "title": "..."}}
        """
        result = {}
        for draft_slide in draft_content.get("slides", []):
            # slide_number 是 1-based，轉換為 0-based index
            slide_number = draft_slide.get("slide_number", 0)
            idx = slide_number - 1 if slide_number > 0 else 0

            result[idx] = {
                "suggestion": draft_slide.get("visual_suggestion", ""),
                "title": draft_slide.get("title", ""),
            }
        return result

    def _extract_title_from_placeholders(self, slide: dict[str, Any]) -> str:
        """從 placeholders 中提取標題"""
        for ph in slide.get("placeholders", []):
            if ph.get("type") in ("TITLE", "CENTER_TITLE"):
                content = ph.get("content", "")
                if isinstance(content, str):
                    return content
        return ""

    async def _get_images_for_slide(
        self,
        visual_suggestion: str,
        slide_title: str,
        presentation_title: str,
        layout: str,
        count: int,
    ) -> list[dict[str, Any]]:
        """
        取得單張投影片的圖片

        Args:
            visual_suggestion: 視覺建議
            slide_title: 投影片標題
            presentation_title: 簡報標題
            layout: 版面類型
            count: 需要的圖片數量

        Returns:
            圖片資訊列表（dict 格式，供 SlideBuilder 使用）
        """
        # 1. 決定搜尋關鍵字
        primary_keyword, fallback_keywords = await self._generate_keywords(
            visual_suggestion=visual_suggestion,
            slide_title=slide_title,
            presentation_title=presentation_title,
        )

        # 2. 檢查快取
        cached = await self.cache.get_cached_images_by_keyword(primary_keyword)
        if cached:
            logger.debug(f"快取命中: {primary_keyword} ({len(cached)} 張)")
            return [self._cache_to_dict(c) for c in cached[:count]]

        # 3. 搜尋 Pexels
        orientation = self._get_orientation(layout)
        images = await self._search_and_cache_images(
            primary_keyword=primary_keyword,
            fallback_keywords=fallback_keywords,
            orientation=orientation,
            count=count,
        )

        return images

    async def _generate_keywords(
        self,
        visual_suggestion: str,
        slide_title: str,
        presentation_title: str,
    ) -> tuple[str, list[str]]:
        """
        生成搜尋關鍵字

        Returns:
            (primary_keyword, fallback_keywords)
        """
        if visual_suggestion:
            try:
                # 使用 AI 優化關鍵字
                keywords_result = await self.pexels.generate_search_keywords(
                    course_title=presentation_title,
                    slide_title=slide_title,
                    slide_content=visual_suggestion,
                    max_keywords=3,
                )
                return keywords_result.primary_keyword, keywords_result.keywords[1:]
            except Exception as e:
                logger.warning(f"AI 關鍵字生成失敗: {e}")

        # Fallback: 使用 slide_title
        return slide_title or presentation_title, []

    async def _search_and_cache_images(
        self,
        primary_keyword: str,
        fallback_keywords: list[str],
        orientation: ImageOrientation | None,
        count: int,
    ) -> list[dict[str, Any]]:
        """搜尋並快取圖片"""
        # 搜尋 Pexels
        search_result = await self.pexels.search_images(
            keyword=primary_keyword,
            per_page=count + 2,  # 多取幾張備用
            orientation=orientation,
        )

        # 若無結果，嘗試 fallback
        effective_keyword = primary_keyword
        if not search_result.photos and fallback_keywords:
            for fallback in fallback_keywords:
                search_result = await self.pexels.search_images(
                    keyword=fallback,
                    per_page=count + 2,
                    orientation=orientation,
                )
                if search_result.photos:
                    effective_keyword = fallback
                    logger.debug(f"使用 fallback 關鍵字: {fallback}")
                    break

        if not search_result.photos:
            logger.warning(f"找不到圖片: {primary_keyword}")
            return []

        # 下載並快取
        images = []
        for photo in search_result.photos[:count]:
            try:
                image_data = await self.pexels.download_image(photo.src.large)
                cached_info = await self.cache.save_to_cache(
                    keyword=effective_keyword,
                    image=photo,
                    image_data=image_data,
                )
                images.append(
                    {
                        "image_id": photo.id,
                        "file_path": cached_info.file_path,
                        "keyword": effective_keyword,
                        "photographer": photo.photographer,
                        "pexels_url": photo.url,
                        "alt_text": photo.alt,
                        "position": "auto",
                    }
                )
            except Exception as e:
                logger.warning(f"圖片下載失敗 {photo.id}: {e}")
                continue

        return images

    def _cache_to_dict(self, cached: Any) -> dict[str, Any]:
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
