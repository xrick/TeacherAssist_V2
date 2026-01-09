"""
Content Generator Role

Stage 2: Uses LLM to expand and structure user input into presentation content

功能：
- 接收使用者的 markdown/text 輸入
- 使用 LLM 擴展、分析、結構化內容
- 輸出詳細的投影片草稿（含標題、要點、視覺建議、講者備註）
"""

import json
import logging
from typing import Any

from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


# System Prompt for Content Generation
CONTENT_GENERATOR_SYSTEM = """<system-instruction>
You are an experienced and skilled Presentation Specialist (PPTX Expert). You excel at structuring complex information into clear, compelling narratives suitable for professional slides.
</system-instruction>

<Task>
1. **Analyze & Expand:** Deepen the user's input by adding relevant details, examples, or data to ensure the content is comprehensive.
2. **Structure:** Organize the content into a logical flow (e.g., Introduction, Problem, Solution, Conclusion).
3. **Draft Slides:** Break the content down into specific slides. For each slide, provide:
    * **Slide Title:** Catchy and relevant.
    * **Bullet Points:** Concise key takeaways (avoid walls of text).
    * **Visual Suggestion:** A brief description of an image, chart, or icon to support the point.
    * **Speaker Notes:** A short script or elaboration for the presenter.
</Task>

<Constraints>
* Keep the language professional yet accessible (easy to understand).
* Ensure the tone is engaging and persuasive.
* Prioritize clarity and brevity in the bullet points.
* Each bullet point should be under 15 words.
* Preserve technical terms in their original language (e.g., Machine Learning, API, GPU).
</Constraints>

<OutputFormat>
Return a JSON object with the following structure:
{
  "title": "Presentation Title",
  "target_audience": "Who this presentation is for",
  "slides": [
    {
      "slide_number": 1,
      "slide_type": "title|content|section|closing",
      "title": "Slide Title",
      "bullet_points": ["Point 1", "Point 2", "Point 3"],
      "visual_suggestion": "Description of recommended visual",
      "speaker_notes": "What the presenter should say"
    }
  ]
}
</OutputFormat>

Return ONLY valid JSON, no additional text or explanation."""


class ContentGenerator:
    """
    Stage 2: 使用 LLM 擴展使用者輸入

    輸入：使用者的 markdown/text 內容
    輸出：結構化的投影片草稿（含標題、要點、視覺建議、講者備註）
    """

    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    async def generate(
        self,
        user_input: str,
        slide_count: int | None = None,
        audience: str | None = None,
        language: str = "zh-TW",
    ) -> dict[str, Any]:
        """
        從使用者輸入生成投影片內容

        Args:
            user_input: 使用者的 markdown/text 輸入
            slide_count: 建議的投影片數量（可選）
            audience: 目標受眾（可選）
            language: 輸出語言

        Returns:
            結構化的投影片內容
        """
        logger.info(f"生成內容: {len(user_input)} 字元輸入")

        # 建立 User Prompt
        user_prompt = self._build_prompt(user_input, slide_count, audience, language)

        # 呼叫 LLM
        try:
            response = await self.llm.generate(
                prompt=user_prompt,
                system_prompt=CONTENT_GENERATOR_SYSTEM,
                temperature=0.7,
                max_tokens=8000,
            )

            logger.info(
                f"內容生成完成: {response.usage.total_tokens} tokens, "
                f"${response.usage.cost_usd:.4f}"
            )

            # 解析 JSON
            content = self._parse_json_response(response.content)

            # 驗證結構
            self._validate_content(content)

            logger.info(f"生成 {len(content.get('slides', []))} 張投影片草稿")
            return content

        except Exception as e:
            logger.error(f"內容生成失敗: {e}", exc_info=True)
            raise

    def _build_prompt(
        self,
        user_input: str,
        slide_count: int | None,
        audience: str | None,
        language: str,
    ) -> str:
        """建立 User Prompt"""
        parts = []

        # 額外指示
        if slide_count:
            parts.append(f"Target slide count: approximately {slide_count} slides")

        if audience:
            parts.append(f"Target audience: {audience}")

        parts.append(f"Output language: {language}")

        # 使用者輸入
        parts.append(f"""
<user_input>
{user_input}
</user_input>

Please analyze and expand this content into a professional presentation structure.""")

        return "\n\n".join(parts)

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """解析 LLM 回應中的 JSON"""
        import re

        def clean_json(text: str) -> str:
            """清理 JSON 中的常見問題"""
            text = re.sub(r",\s*([}\]])", r"\1", text)
            return text

        def fix_missing_brackets(text: str) -> str:
            """修復缺少的括號"""
            text = re.sub(r"(\})\s*\},\s*\{", r"\1]\n    }, {", text)
            return text

        def try_parse(text: str) -> dict[str, Any] | None:
            """嘗試多種修復方式解析 JSON"""
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

        # 直接解析
        result = try_parse(content)
        if result:
            return result

        # 從 code block 提取
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

        # 找 JSON 物件
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            result = try_parse(content[start:end])
            if result:
                return result

        raise json.JSONDecodeError("No valid JSON found", content, 0)

    def _validate_content(self, content: dict[str, Any]) -> None:
        """驗證生成的內容結構"""
        if "slides" not in content:
            raise ValueError("內容缺少 'slides' 欄位")

        if not content["slides"]:
            raise ValueError("slides 陣列為空")

        for i, slide in enumerate(content["slides"]):
            if "title" not in slide:
                logger.warning(f"Slide {i} 缺少 title")
            if "bullet_points" not in slide:
                logger.warning(f"Slide {i} 缺少 bullet_points")

        logger.debug("內容驗證通過")
