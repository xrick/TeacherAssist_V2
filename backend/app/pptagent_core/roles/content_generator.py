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

CRITICAL RULES:
1. Your response MUST be ONLY a valid JSON object.
2. Do NOT include any text, explanation, or markdown code blocks.
3. Start your response directly with { and end with }.
4. Do NOT wrap JSON in ```json``` or any markdown formatting.
5. Ensure all strings are properly escaped and all brackets are closed."""


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
        max_json_retries: int = 2,
    ) -> dict[str, Any]:
        """
        從使用者輸入生成投影片內容

        Args:
            user_input: 使用者的 markdown/text 輸入
            slide_count: 建議的投影片數量（可選）
            audience: 目標受眾（可選）
            language: 輸出語言
            max_json_retries: JSON 解析失敗時的最大重試次數

        Returns:
            結構化的投影片內容
        """
        logger.info(f"生成內容: {len(user_input)} 字元輸入")

        # 建立 User Prompt
        user_prompt = self._build_prompt(user_input, slide_count, audience, language)

        last_error = None
        for attempt in range(1 + max_json_retries):
            # 第一次用原始 prompt，重試時加入更強的 JSON 約束
            if attempt == 0:
                prompt = user_prompt
                system = CONTENT_GENERATOR_SYSTEM
                temp = 0.3
            else:
                logger.warning(
                    f"JSON 解析失敗，第 {attempt} 次重試（降低 temperature，強化 prompt）"
                )
                prompt = (
                    user_prompt + "\n\nIMPORTANT: You MUST respond with ONLY a valid JSON object. "
                    "Do NOT include any text, explanation, or markdown formatting before or after the JSON. "
                    "Start your response with { and end with }."
                )
                system = CONTENT_GENERATOR_SYSTEM
                temp = 0.1

            # 呼叫 LLM
            try:
                response = await self.llm.generate(
                    prompt=prompt,
                    system_prompt=system,
                    temperature=temp,
                    max_tokens=8000,
                )

                logger.info(
                    f"內容生成完成 (attempt {attempt + 1}): "
                    f"{response.usage.total_tokens} tokens, "
                    f"${response.usage.cost_usd:.4f}"
                )

                # 解析 JSON
                content = self._parse_json_response(response.content)

                # 驗證結構
                self._validate_content(content)

                logger.info(f"生成 {len(content.get('slides', []))} 張投影片草稿")
                return content

            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"JSON 解析失敗 (attempt {attempt + 1}/{1 + max_json_retries}): {e}")
                continue
            except Exception as e:
                logger.error(f"內容生成失敗: {e}", exc_info=True)
                raise

        # 所有重試都失敗
        logger.error(f"JSON 解析在 {1 + max_json_retries} 次嘗試後仍然失敗")
        raise last_error  # type: ignore[misc]

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

        # Debug: 記錄原始回應以便排查
        logger.debug(f"LLM 原始回應 (前 500 字元): {content[:500]!r}")

        # 空值檢查
        if not content or not content.strip():
            raise json.JSONDecodeError("LLM 回傳空內容，無法解析 JSON", content or "", 0)

        def clean_json(text: str) -> str:
            """清理 JSON 中的常見問題"""
            # 移除 trailing commas
            text = re.sub(r",\s*([}\]])", r"\1", text)
            # 移除控制字元（保留換行和 tab）
            text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
            return text

        def fix_missing_brackets(text: str) -> str:
            """修復缺少的括號"""
            text = re.sub(r"(\})\s*\},\s*\{", r"\1]\n    }, {", text)
            return text

        def fix_truncated_json(text: str) -> str:
            """嘗試修復被截斷的 JSON"""
            # 計算未關閉的括號
            open_braces = text.count("{") - text.count("}")
            open_brackets = text.count("[") - text.count("]")

            if open_braces > 0 or open_brackets > 0:
                # 移除最後一個不完整的元素
                # 找到最後一個完整的 }, 或 ] 後截斷
                last_complete = max(
                    text.rfind("},"),
                    text.rfind("],"),
                    text.rfind("}]"),
                )
                if last_complete > 0:
                    text = text[: last_complete + 1]
                    # 如果結尾是 }, 移除逗號
                    text = text.rstrip().rstrip(",")

                # 補上缺少的括號
                text += "]" * open_brackets + "}" * open_braces

            return text

        def try_parse(text: str) -> dict[str, Any] | None:
            """嘗試多種修復方式解析 JSON"""
            attempts = [
                text,
                clean_json(text),
                fix_missing_brackets(text),
                fix_truncated_json(text),
                fix_truncated_json(clean_json(text)),
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

        # 記錄完整回應內容供除錯
        logger.error(f"無法解析 JSON，LLM 完整回應:\n{content}")
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
