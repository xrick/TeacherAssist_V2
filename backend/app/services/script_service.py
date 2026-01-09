"""
Teaching Script Service

Generates comprehensive teaching scripts for presentations.
Includes lecture content, teaching tips, Q&A, and transitions.
"""

import logging
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from app.pptagent_core.presentation.models import (
    ContentType,
    LayoutType,
    Presentation,
    SlideContent,
)
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class InteractionQA(BaseModel):
    """Interactive Q&A item"""

    question: str = Field(..., description="Question to ask students")
    expected_answers: list[str] = Field(default_factory=list, description="Expected answers")


class SlideScript(BaseModel):
    """Script for a single slide"""

    slide_index: int = Field(..., description="Slide index (0-based)")
    slide_title: str = Field(..., description="Slide title")
    estimated_minutes: float = Field(default=3.0, description="Estimated time in minutes")

    # Script content
    lecture_content: str = Field(default="", description="Lecture content (conversational style)")
    teaching_tips: list[str] = Field(default_factory=list, description="Teaching tips")
    interaction_qa: list[InteractionQA] = Field(default_factory=list, description="Interactive Q&A")
    transition: str = Field(default="", description="Transition to next slide")


class PresentationScript(BaseModel):
    """Complete script for a presentation"""

    presentation_id: str = Field(..., description="Associated presentation ID")
    title: str = Field(..., description="Presentation title")
    total_minutes: float = Field(default=0.0, description="Total estimated time")
    scripts: list[SlideScript] = Field(default_factory=list, description="Scripts for each slide")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    last_edited_at: datetime = Field(default_factory=datetime.utcnow)

    def update_total_time(self):
        """Recalculate total time from individual slides."""
        self.total_minutes = sum(s.estimated_minutes for s in self.scripts)


class ScriptStyle(str, Enum):
    """Script style options"""

    CONVERSATIONAL = "conversational"  # 口語化
    FORMAL = "formal"  # 正式學術
    CASUAL = "casual"  # 輕鬆隨意


# Time estimation constants (minutes per content type)
TIME_ESTIMATES = {
    LayoutType.TITLE: 1.0,
    LayoutType.SECTION_HEADER: 1.5,
    LayoutType.CONTENT: 3.0,
    LayoutType.TWO_COLUMN: 4.0,
    LayoutType.IMAGE: 2.0,
    LayoutType.IMAGE_TEXT: 3.0,
    LayoutType.QUOTE: 2.0,
    LayoutType.CLOSING: 1.0,
    LayoutType.BLANK: 1.0,
}

# Additional time per content element
ELEMENT_TIME_BONUS = {
    ContentType.BULLET_LIST: 0.5,  # per item roughly
    ContentType.NUMBERED_LIST: 0.5,
    ContentType.CODE_BLOCK: 1.0,
    ContentType.TABLE: 1.5,
    ContentType.QUOTE: 0.5,
}


class ScriptService:
    """
    Service for generating and managing teaching scripts.

    Features:
    - AI-powered script generation from slide content
    - Conversational/oral style content
    - Teaching tips and interaction suggestions
    - Time estimation with user adjustment
    """

    def __init__(self):
        """Initialize script service."""
        self._llm_service = None

    @property
    def llm_service(self):
        """Get LLM service (lazy initialization)."""
        if self._llm_service is None:
            self._llm_service = get_llm_service()
        return self._llm_service

    async def generate_presentation_script(
        self,
        presentation: Presentation,
        presentation_id: str,
        style: ScriptStyle = ScriptStyle.CONVERSATIONAL,
        target_total_minutes: float | None = None,
    ) -> PresentationScript:
        """
        Generate complete teaching script for a presentation.

        Args:
            presentation: Presentation model
            presentation_id: Presentation ID for reference
            style: Script style (conversational, formal, casual)
            target_total_minutes: Optional target total duration

        Returns:
            PresentationScript with all slide scripts
        """
        logger.info(f"Generating script for: {presentation.metadata.title}")

        scripts: list[SlideScript] = []

        for idx, slide in enumerate(presentation.slides):
            try:
                script = await self._generate_slide_script(
                    slide=slide,
                    slide_index=idx,
                    presentation_title=presentation.metadata.title,
                    style=style,
                    is_first=(idx == 0),
                    is_last=(idx == len(presentation.slides) - 1),
                )
                scripts.append(script)
                logger.debug(f"Generated script for slide {idx + 1}")
            except Exception as e:
                logger.warning(f"Failed to generate script for slide {idx + 1}: {e}")
                # Create minimal fallback script
                scripts.append(self._create_fallback_script(slide, idx))

        # Create presentation script
        pres_script = PresentationScript(
            presentation_id=presentation_id,
            title=presentation.metadata.title,
            scripts=scripts,
            generated_at=datetime.utcnow(),
            last_edited_at=datetime.utcnow(),
        )
        pres_script.update_total_time()

        # Adjust times if target specified
        if target_total_minutes and pres_script.total_minutes > 0:
            self._adjust_time_allocation(pres_script, target_total_minutes)

        logger.info(
            f"Script generated: {len(scripts)} slides, "
            f"{pres_script.total_minutes:.1f} minutes total"
        )

        return pres_script

    async def _generate_slide_script(
        self,
        slide: SlideContent,
        slide_index: int,
        presentation_title: str,
        style: ScriptStyle,
        is_first: bool,
        is_last: bool,
    ) -> SlideScript:
        """Generate script for a single slide."""

        # Estimate time based on layout and content
        estimated_time = self._estimate_slide_time(slide)

        # Build context for LLM
        slide_content = self._extract_slide_content(slide)

        # Generate script using LLM
        system_prompt = self._build_system_prompt(style)
        user_prompt = self._build_user_prompt(
            slide_title=slide.title,
            slide_content=slide_content,
            presentation_title=presentation_title,
            slide_index=slide_index,
            is_first=is_first,
            is_last=is_last,
            estimated_minutes=estimated_time,
        )

        response = await self.llm_service.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=1500,
        )

        # Parse response
        script = self._parse_script_response(
            response.content,
            slide_index=slide_index,
            slide_title=slide.title,
            estimated_minutes=estimated_time,
        )

        return script

    def _build_system_prompt(self, style: ScriptStyle) -> str:
        """Build system prompt for script generation."""

        style_instructions = {
            ScriptStyle.CONVERSATIONAL: """
Use a friendly, conversational tone as if speaking directly to students.
- Use "各位同學" or "大家" to address students
- Include natural speech patterns and transitions
- Add verbal cues like "好，接下來..." or "那麼..."
- Make complex concepts accessible through analogies""",
            ScriptStyle.FORMAL: """
Use a formal academic tone appropriate for university lectures.
- Maintain professional language throughout
- Use precise terminology with clear definitions
- Structure explanations logically""",
            ScriptStyle.CASUAL: """
Use a relaxed, approachable tone.
- Be friendly and encouraging
- Use simple language and everyday examples
- Feel free to add humor where appropriate""",
        }

        return f"""You are an expert educational content developer creating teaching scripts for university professors.
Your task is to generate comprehensive lecture scripts in Traditional Chinese (繁體中文).

{style_instructions.get(style, style_instructions[ScriptStyle.CONVERSATIONAL])}

For each slide, provide:
1. 📖 講解內容 (Lecture Content): A complete, word-for-word script the professor can follow
2. 💡 教學提示 (Teaching Tips): 2-3 practical tips for effective delivery
3. ❓ 互動問答 (Interactive Q&A): 1-2 questions to engage students, with expected answers
4. 🔗 過場銜接 (Transition): A smooth transition to the next topic

Format your response EXACTLY as:
===講解內容===
[lecture content here]

===教學提示===
- [tip 1]
- [tip 2]

===互動問答===
Q: [question]
A: [expected answers, comma separated]

===過場銜接===
[transition text]"""

    def _build_user_prompt(
        self,
        slide_title: str,
        slide_content: str,
        presentation_title: str,
        slide_index: int,
        is_first: bool,
        is_last: bool,
        estimated_minutes: float,
    ) -> str:
        """Build user prompt for script generation."""

        position_context = ""
        if is_first:
            position_context = "這是簡報的開場投影片，請包含適當的開場白和課程介紹。"
        elif is_last:
            position_context = "這是簡報的結尾投影片，請包含總結和結語。"

        return f"""請為以下投影片生成教學腳本：

課程標題：{presentation_title}
投影片 {slide_index + 1}：{slide_title}
預計時間：{estimated_minutes:.1f} 分鐘

投影片內容：
{slide_content}

{position_context}

請生成完整的教學腳本，包含講解內容、教學提示、互動問答和過場銜接。"""

    def _parse_script_response(
        self,
        response: str,
        slide_index: int,
        slide_title: str,
        estimated_minutes: float,
    ) -> SlideScript:
        """Parse LLM response into SlideScript."""

        lecture_content = ""
        teaching_tips: list[str] = []
        interaction_qa: list[InteractionQA] = []
        transition = ""

        # Parse sections
        sections = response.split("===")

        current_section = None
        current_content: list[str] = []

        for section in sections:
            section = section.strip()
            if not section:
                continue

            if "講解內容" in section:
                current_section = "lecture"
                # Get content after the header
                lines = section.split("\n", 1)
                if len(lines) > 1:
                    current_content = [lines[1].strip()]
            elif "教學提示" in section:
                # Save previous section
                if current_section == "lecture":
                    lecture_content = "\n".join(current_content).strip()
                current_section = "tips"
                lines = section.split("\n", 1)
                if len(lines) > 1:
                    current_content = [lines[1].strip()]
            elif "互動問答" in section:
                if current_section == "tips":
                    teaching_tips = self._parse_tips(current_content)
                current_section = "qa"
                lines = section.split("\n", 1)
                if len(lines) > 1:
                    current_content = [lines[1].strip()]
            elif "過場銜接" in section:
                if current_section == "qa":
                    interaction_qa = self._parse_qa(current_content)
                current_section = "transition"
                lines = section.split("\n", 1)
                if len(lines) > 1:
                    current_content = [lines[1].strip()]
            else:
                current_content.append(section)

        # Handle last section
        if current_section == "transition":
            transition = "\n".join(current_content).strip()
        elif current_section == "qa":
            interaction_qa = self._parse_qa(current_content)
        elif current_section == "tips":
            teaching_tips = self._parse_tips(current_content)
        elif current_section == "lecture":
            lecture_content = "\n".join(current_content).strip()

        # Fallback if parsing failed
        if not lecture_content:
            lecture_content = response.strip()

        return SlideScript(
            slide_index=slide_index,
            slide_title=slide_title,
            estimated_minutes=estimated_minutes,
            lecture_content=lecture_content,
            teaching_tips=teaching_tips,
            interaction_qa=interaction_qa,
            transition=transition,
        )

    def _parse_tips(self, content: list[str]) -> list[str]:
        """Parse teaching tips from content."""
        tips = []
        text = "\n".join(content)
        for line in text.split("\n"):
            line = line.strip()
            if line and line.startswith(("-", "•", "*", "·")):
                tips.append(line.lstrip("-•*· ").strip())
            elif line and not line.startswith("="):
                tips.append(line)
        return tips[:5]  # Limit to 5 tips

    def _parse_qa(self, content: list[str]) -> list[InteractionQA]:
        """Parse Q&A from content."""
        qa_list = []
        text = "\n".join(content)

        current_q = None
        current_a: list[str] = []

        for line in text.split("\n"):
            line = line.strip()
            if line.upper().startswith("Q:") or line.startswith("問:") or line.startswith("問題:"):
                if current_q:
                    qa_list.append(
                        InteractionQA(
                            question=current_q,
                            expected_answers=current_a,
                        )
                    )
                current_q = line.split(":", 1)[1].strip() if ":" in line else line
                current_a = []
            elif (
                line.upper().startswith("A:")
                or line.startswith("答:")
                or line.startswith("預期答案:")
            ):
                answer_text = line.split(":", 1)[1].strip() if ":" in line else line
                current_a = [a.strip() for a in answer_text.split(",") if a.strip()]

        if current_q:
            qa_list.append(
                InteractionQA(
                    question=current_q,
                    expected_answers=current_a,
                )
            )

        return qa_list[:3]  # Limit to 3 Q&A pairs

    def _estimate_slide_time(self, slide: SlideContent) -> float:
        """Estimate time needed for a slide."""
        # Base time from layout
        base_time = TIME_ESTIMATES.get(slide.layout, 3.0)

        # Add time for content elements
        bonus_time = 0.0
        for element in slide.elements:
            element_bonus = ELEMENT_TIME_BONUS.get(element.type, 0.0)
            # For lists, estimate based on content lines
            if element.type in (ContentType.BULLET_LIST, ContentType.NUMBERED_LIST):
                lines = len([l for l in element.content.split("\n") if l.strip()])
                bonus_time += element_bonus * min(lines, 8)
            else:
                bonus_time += element_bonus

        return min(base_time + bonus_time, 10.0)  # Cap at 10 minutes per slide

    def _extract_slide_content(self, slide: SlideContent) -> str:
        """Extract text content from slide for prompt."""
        parts = [f"標題：{slide.title}"]

        for element in slide.elements:
            if element.type == ContentType.BULLET_LIST:
                parts.append(f"要點：\n{element.content}")
            elif element.type == ContentType.NUMBERED_LIST:
                parts.append(f"列表：\n{element.content}")
            elif element.type == ContentType.CODE_BLOCK:
                parts.append(f"程式碼：\n{element.content[:300]}")
            elif element.type == ContentType.TABLE:
                parts.append(f"表格：\n{element.content[:300]}")
            elif element.type == ContentType.QUOTE:
                parts.append(f"引言：{element.content}")
            else:
                parts.append(element.content)

        return "\n\n".join(parts)[:1500]  # Limit context size

    def _create_fallback_script(self, slide: SlideContent, slide_index: int) -> SlideScript:
        """Create minimal fallback script when generation fails."""
        return SlideScript(
            slide_index=slide_index,
            slide_title=slide.title,
            estimated_minutes=self._estimate_slide_time(slide),
            lecture_content=f"（請針對「{slide.title}」進行講解）",
            teaching_tips=["確保學生理解核心概念", "適時詢問學生是否有問題"],
            interaction_qa=[],
            transition="接下來，讓我們繼續看下一個主題。",
        )

    def _adjust_time_allocation(
        self,
        script: PresentationScript,
        target_minutes: float,
    ):
        """Adjust time allocation to match target total time."""
        if script.total_minutes <= 0:
            return

        ratio = target_minutes / script.total_minutes

        for slide_script in script.scripts:
            slide_script.estimated_minutes = round(slide_script.estimated_minutes * ratio, 1)

        script.update_total_time()
        logger.debug(f"Adjusted total time to {script.total_minutes:.1f} minutes")

    async def regenerate_slide_script(
        self,
        presentation: Presentation,
        slide_index: int,
        style: ScriptStyle = ScriptStyle.CONVERSATIONAL,
    ) -> SlideScript:
        """Regenerate script for a single slide."""
        if slide_index < 0 or slide_index >= len(presentation.slides):
            raise ValueError(f"Invalid slide index: {slide_index}")

        slide = presentation.slides[slide_index]
        is_first = slide_index == 0
        is_last = slide_index == len(presentation.slides) - 1

        return await self._generate_slide_script(
            slide=slide,
            slide_index=slide_index,
            presentation_title=presentation.metadata.title,
            style=style,
            is_first=is_first,
            is_last=is_last,
        )


# Global instance
_script_service: ScriptService | None = None


def get_script_service() -> ScriptService:
    """Get or create global script service instance."""
    global _script_service
    if _script_service is None:
        _script_service = ScriptService()
    return _script_service
