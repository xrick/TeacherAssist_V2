"""
Content Organizer V2 Role

Stage 3: Organizes generated content into template structure

功能：
- 接收 ContentGenerator 的輸出（投影片草稿）
- 接收 TemplateAnalyzer 的輸出（Template 結構）
- 將草稿內容對應到 Template 的 Placeholder 結構
- 使用 LLM 進行精煉和適配
"""

import json
import logging
from typing import Any

from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


# System Prompt for Content Organization
CONTENT_ORGANIZER_SYSTEM = """你是一位專業的簡報內容編排專家。你的任務是將簡報草稿內容精確地對應到 PowerPoint 模板的 Placeholder 結構中。

## 任務

1. **對應內容**：將每張投影片的內容對應到對應的 Placeholder
2. **精煉文字**：
   - TITLE: 5-10 字，直接點題
   - SUBTITLE: 10-20 字，補充說明
   - CONTENT/BODY: 每個要點 15 字以內
3. **保留重點**：確保關鍵訊息完整傳達
4. **格式適配**：根據 Placeholder 類型調整內容格式

## 極簡原則

- 簡約清晰：避免冗詞贅字
- 一目瞭然：使用具體數據或例子
- 專業術語：保留英文專業術語原文

## 輸出格式

返回 JSON，結構必須與 template_structure 完全一致，只填入 content 欄位：
{
  "slides": [
    {
      "index": 0,
      "layout_index": 1,
      "layout_name": "Title Slide",
      "placeholders": [
        {"idx": 0, "type": "TITLE", "content": "填入的標題"},
        {"idx": 1, "type": "SUBTITLE", "content": "填入的副標題"}
      ],
      "speaker_notes": "講者備註（來自草稿）",
      "visual_suggestion": "視覺建議（來自草稿）"
    }
  ]
}

只返回 JSON，不要加任何說明。"""


class ContentOrganizerV2:
    """
    Stage 3: 將生成的內容組織到 Template 結構

    輸入：
    - draft_content: ContentGenerator 的輸出（投影片草稿）
    - template_structure: TemplateAnalyzer 的輸出（Template 結構）

    輸出：填入內容的 Template 結構（供 SlideBuilder 使用）
    """

    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def organize(
        self,
        draft_content: dict[str, Any],
        template_structure: dict[str, Any],
    ) -> dict[str, Any]:
        """
        將草稿內容組織到 Template 結構

        Args:
            draft_content: ContentGenerator 的輸出
            template_structure: TemplateAnalyzer 的輸出

        Returns:
            填入內容的結構，可直接傳給 SlideBuilder
        """
        draft_slides = draft_content.get("slides", [])
        template_slides = template_structure.get("slides", [])

        logger.info(f"組織內容: {len(draft_slides)} 張草稿 → {len(template_slides)} 張模板投影片")

        # 建立 User Prompt
        user_prompt = self._build_prompt(draft_content, template_structure)

        try:
            response = await self.llm.generate(
                prompt=user_prompt,
                system_prompt=CONTENT_ORGANIZER_SYSTEM,
                temperature=0.3,  # 低溫度確保結構一致
                max_tokens=6000,
            )

            logger.info(
                f"內容組織完成: {response.usage.total_tokens} tokens, "
                f"${response.usage.cost_usd:.4f}"
            )

            # 解析 JSON
            organized = self._parse_json_response(response.content)

            # 驗證並補全結構
            organized = self._validate_and_complete(organized, template_structure)

            return organized

        except Exception as e:
            logger.error(f"內容組織失敗: {e}", exc_info=True)
            # 如果 LLM 失敗，嘗試直接對應
            return self._fallback_organize(draft_content, template_structure)

    def _build_prompt(
        self,
        draft_content: dict[str, Any],
        template_structure: dict[str, Any],
    ) -> str:
        """建立 User Prompt"""
        # 簡化草稿內容
        simplified_draft = {"title": draft_content.get("title", ""), "slides": []}

        for slide in draft_content.get("slides", []):
            simplified_draft["slides"].append(
                {
                    "slide_number": slide.get("slide_number"),
                    "slide_type": slide.get("slide_type"),
                    "title": slide.get("title", ""),
                    "bullet_points": slide.get("bullet_points", []),
                    "speaker_notes": slide.get("speaker_notes", ""),
                    "visual_suggestion": slide.get("visual_suggestion", ""),
                }
            )

        return f"""## 簡報草稿內容

```json
{json.dumps(simplified_draft, ensure_ascii=False, indent=2)}
```

## Template 結構（需要填入的結構）

```json
{json.dumps(template_structure, ensure_ascii=False, indent=2)}
```

## 任務

請將草稿內容精煉後填入 Template 結構的 placeholder content 欄位。
- 草稿的 slide_number 對應 Template 的 index
- 草稿的 title 對應 TITLE placeholder
- 草稿的 bullet_points 對應 CONTENT/BODY placeholder（格式為列表）
- 草稿的 subtitle 或第一個 bullet point 可對應 SUBTITLE placeholder

返回完整的 Template 結構 JSON，確保 slides 陣列長度與 Template 一致。"""

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """解析 LLM 回應中的 JSON"""
        import re

        def clean_json(text: str) -> str:
            text = re.sub(r",\s*([}\]])", r"\1", text)
            return text

        def fix_missing_brackets(text: str) -> str:
            text = re.sub(r"(\})\s*\},\s*\{", r"\1]\n    }, {", text)
            return text

        def try_parse(text: str) -> dict[str, Any] | None:
            attempts = [
                text,
                clean_json(text),
                fix_missing_brackets(text),
                fix_missing_brackets(clean_json(text)),
                clean_json(fix_missing_brackets(text)),
            ]
            for attempt in attempts:
                try:
                    return json.loads(attempt)
                except json.JSONDecodeError:
                    continue
            return None

        result = try_parse(content)
        if result:
            return result

        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end > start:
                result = try_parse(content[start:end].strip())
                if result:
                    return result

        if "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            if end > start:
                result = try_parse(content[start:end].strip())
                if result:
                    return result

        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            result = try_parse(content[start:end])
            if result:
                return result

        raise json.JSONDecodeError("No valid JSON found", content, 0)

    def _validate_and_complete(
        self,
        organized: dict[str, Any],
        template_structure: dict[str, Any],
    ) -> dict[str, Any]:
        """驗證並補全結構"""
        if "slides" not in organized:
            organized["slides"] = []

        template_slides = template_structure.get("slides", [])
        organized_slides = organized.get("slides", [])

        # 確保投影片數量一致
        while len(organized_slides) < len(template_slides):
            idx = len(organized_slides)
            template_slide = template_slides[idx]
            organized_slides.append(
                {
                    "index": idx,
                    "layout_index": template_slide.get("layout_index", 1),
                    "layout_name": template_slide.get("layout_name", ""),
                    "placeholders": [
                        {**ph, "content": "" if ph.get("format") != "bullet_list" else []}
                        for ph in template_slide.get("placeholders", [])
                    ],
                }
            )

        # 確保每個 slide 都有必要欄位
        for i, slide in enumerate(organized_slides):
            if i < len(template_slides):
                template_slide = template_slides[i]
                slide["layout_index"] = template_slide.get(
                    "layout_index", slide.get("layout_index", 1)
                )
                slide["layout_name"] = template_slide.get(
                    "layout_name", slide.get("layout_name", "")
                )
                # 新增：確保 layout 類型欄位存在（供 ImageEnricher 和 SlideBuilder 使用）
                if "layout" not in slide:
                    slide["layout"] = self._determine_layout_type(template_slide)

        organized["slides"] = organized_slides
        organized["template"] = template_structure.get("template", "")
        organized["slide_count"] = len(organized_slides)

        return organized

    def _determine_layout_type(self, template_slide: dict[str, Any]) -> str:
        """
        根據 layout_name 和 placeholders 判斷 layout 類型

        Args:
            template_slide: 模板投影片結構

        Returns:
            layout 類型字串: title, content, two_column, image_text, closing
        """
        layout_name = template_slide.get("layout_name", "").lower()
        layout_index = template_slide.get("layout_index", 1)
        placeholders = template_slide.get("placeholders", [])

        # 檢查是否有 PICTURE placeholder
        has_picture = any(ph.get("type") == "PICTURE" for ph in placeholders)

        # 根據 layout_name 判斷
        if "title" in layout_name and "content" not in layout_name:
            return "title"
        elif "two" in layout_name or "column" in layout_name:
            return "two_column"
        elif "image" in layout_name or has_picture:
            return "image_text"  # 有 PICTURE placeholder 就是 image_text
        elif "closing" in layout_name or "end" in layout_name or "thank" in layout_name:
            return "closing"
        elif "section" in layout_name or "header" in layout_name:
            return "section_header"

        # 根據 layout_index 判斷（v0.2: 配合 config 的 body_pool）
        if layout_index == 0:
            return "title"
        elif layout_index in (8, 9):
            # Layout 8, 9 有 PICTURE placeholder
            return "image_text"
        elif layout_index == 1 or layout_index == 2:
            return "content"

        return "content"

    def _fallback_organize(
        self,
        draft_content: dict[str, Any],
        template_structure: dict[str, Any],
    ) -> dict[str, Any]:
        """當 LLM 失敗時的降級處理：直接對應"""
        logger.warning("使用降級處理：直接對應草稿到模板")

        result = {
            "template": template_structure.get("template", ""),
            "slide_count": template_structure.get("slide_count", 0),
            "slides": [],
        }

        draft_slides = draft_content.get("slides", [])
        template_slides = template_structure.get("slides", [])

        for i, template_slide in enumerate(template_slides):
            # 取得對應的草稿（如果有）
            draft_slide = draft_slides[i] if i < len(draft_slides) else {}

            organized_slide = {
                "index": i,
                "layout_index": template_slide.get("layout_index", 1),
                "layout_name": template_slide.get("layout_name", ""),
                "layout": self._determine_layout_type(template_slide),
                "placeholders": [],
                "speaker_notes": draft_slide.get("speaker_notes", ""),
                "visual_suggestion": draft_slide.get("visual_suggestion", ""),
            }

            # 對應 placeholder
            for ph in template_slide.get("placeholders", []):
                ph_type = ph.get("type", "")
                content = ""

                if ph_type == "TITLE":
                    content = draft_slide.get("title", "")
                elif ph_type == "SUBTITLE":
                    # 用第一個 bullet point 作為 subtitle
                    bullets = draft_slide.get("bullet_points", [])
                    content = bullets[0] if bullets else ""
                elif ph_type in ("CONTENT", "BODY"):
                    content = draft_slide.get("bullet_points", [])

                organized_slide["placeholders"].append(
                    {
                        "idx": ph.get("idx", 0),
                        "type": ph_type,
                        "content": content,
                        **({"format": "bullet_list"} if ph.get("format") == "bullet_list" else {}),
                    }
                )

            result["slides"].append(organized_slide)

        return result
