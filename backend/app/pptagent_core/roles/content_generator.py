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

from app.pptagent_core.roles.input_classifier import InputMode
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


# System Prompt for Content Generation
CONTENT_GENERATOR_SYSTEM = """<system-instruction>
You are an experienced and skilled Presentation Specialist (PPTX Expert). You excel at structuring complex information into clear, compelling narratives suitable for professional slides.
</system-instruction>

<Input_Data>
  <User_Topic>
  {{USER_TOPIC_HERE}}
  </User_Topic>

  <Target_Slide_Count>
  {{SLIDE_COUNT}}
  </Target_Slide_Count>

  <Retrieved_Context>
  {{RAG_DOCUMENTS_HERE}}
  </Retrieved_Context>
</Input_Data>

<Task>
1. **Synthesize & Ground:** Analyze the <User_Topic> and enrich it using *only* the information provided in <Retrieved_Context>.
2. **Structure:** Plan the presentation to fit exactly **{{SLIDE_COUNT}} slides**. Distribute the content evenly across these slides (e.g., if 5 slides: 1 Title, 1 Intro, 2 Details, 1 Conclusion).
3. **Draft Slides:** Break the content down into specific slides. For each slide, provide:
    * **Slide Title:** Catchy and relevant.
    * **Bullet Points:** Concise key takeaways (under 15 words each).
    * **Visual Suggestion:** A concrete description + 2 keywords.
    * **Speaker Notes:** Script for the presenter.
</Task>

<Constraints>
* **Quantity Control:** You must generate exactly {{SLIDE_COUNT}} slides. No more, no less.
* **Source Truth:** Do not hallucinate. Use only the <Retrieved_Context>.
* **Language & Tone:** Professional, engaging, accessible.
* **JSON Safety:** Ensure all strings are properly escaped to prevent JSON parsing errors.
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
      "visual_suggestion": "Image description. Keywords: tag1, tag2",
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
        input_mode: InputMode = InputMode.DIRECT,
        max_json_retries: int = 2,
    ) -> dict[str, Any]:
        """
        從使用者輸入生成投影片內容

        Args:
            user_input: 使用者的 markdown/text 輸入
            slide_count: 建議的投影片數量（可選）
            audience: 目標受眾（可選）
            language: 輸出語言
            input_mode: 輸入模式（SEARCH=短題目, DIRECT=長文章）
            max_json_retries: JSON 解析失敗時的最大重試次數

        Returns:
            結構化的投影片內容
        """
        logger.info(f"生成內容: {len(user_input)} 字元輸入, 模式={input_mode.value}")

        # 建立 User Prompt（根據輸入模式調整策略）
        user_prompt = self._build_prompt(user_input, slide_count, audience, language, input_mode)

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
        input_mode: InputMode = InputMode.DIRECT,
    ) -> str:
        """
        建立 User Prompt

        根據 input_mode 調整指令策略：
        - SEARCH: 短題目 → 要求 LLM 從零生成完整內容
        - DIRECT: 長文章 → 要求 LLM 結構化已有內容
        """
        parts = []

        # 額外指示
        if slide_count:
            parts.append(f"Target slide count: approximately {slide_count} slides")

        if audience:
            parts.append(f"Target audience: {audience}")

        parts.append(f"Output language: {language}")

        # 根據模式調整指令
        if input_mode == InputMode.SEARCH:
            # 短題目模式：LLM 需要自行生成完整內容
            parts.append(f"""
<user_topic>
{user_input}
</user_topic>

The user has provided a short topic or keyword. You must:
1. Generate comprehensive, detailed content about this topic from your knowledge.
2. Cover multiple aspects and sub-topics to fill the target slide count.
3. Include relevant examples, data points, and key concepts.
4. Structure everything into a professional presentation.""")
        else:
            # 長文章模式：LLM 結構化已有內容
            parts.append(f"""
<user_input>
{user_input}
</user_input>

The user has provided detailed content. You must:
1. Analyze and organize this existing content into slides.
2. Preserve the key information and main arguments.
3. Condense and restructure for clarity and visual impact.
4. Do NOT add information beyond what the user provided.""")

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
