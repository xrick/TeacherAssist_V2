"""
PPT Generation Service V2

四階段流程：
1. TemplateAnalyzer - 分析 Template 結構
2. ContentGenerator - LLM 擴展使用者輸入
3. ContentOrganizerV2 - 組織內容到 Template 結構
4. SlideBuilder - 建構最終 PPTX

核心原則：使用者輸入 → LLM 擴展 → 結構化組織 → PPTX 輸出
"""

import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.pptagent_core.roles.content_generator import ContentGenerator
from app.pptagent_core.roles.content_organizer_v2 import ContentOrganizerV2
from app.pptagent_core.roles.slide_builder import SlideBuilder
from app.pptagent_core.roles.template_analyzer import TemplateAnalyzer
from app.services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)


class PPTServiceV2:
    """
    四階段 PPT 生成服務

    工作流程：
    User Input → ContentGenerator → Draft Content
                                          ↓
    Template → TemplateAnalyzer → Structure → ContentOrganizerV2 → Organized Content
                                                                          ↓
                                                              SlideBuilder → PPTX
    """

    def __init__(
        self,
        llm_service: LLMService | None = None,
        templates_path: Path | None = None,
    ):
        self.llm = llm_service or get_llm_service()
        self.templates_path = templates_path or settings.template_storage_path

    def _get_template_path(self, template: str | None) -> Path:
        """取得 Template 檔案路徑"""
        if template is None:
            template = "modern_clean.pptx"

        if not template.endswith(".pptx"):
            template = f"{template}.pptx"

        template_path = self.templates_path / template

        if not template_path.exists():
            logger.warning(f"Template 不存在: {template_path}, 使用預設")
            available = list(self.templates_path.glob("*.pptx"))
            if available:
                template_path = available[0]
                logger.info(f"使用替代 Template: {template_path.name}")
            else:
                raise FileNotFoundError(f"找不到任何 PPTX Template: {self.templates_path}")

        return template_path

    async def generate(
        self,
        user_input: str,
        template: str | None = None,
        slide_count: int = 10,
        audience: str | None = None,
        language: str = "zh-TW",
    ) -> bytes:
        """
        從使用者輸入生成簡報

        Args:
            user_input: 使用者的 markdown/text 輸入
            template: Template 檔案名稱
            slide_count: 目標投影片數量
            audience: 目標受眾
            language: 輸出語言

        Returns:
            PPTX 檔案的 bytes
        """
        start_time = datetime.now()
        logger.info(f"開始生成簡報: {len(user_input)} 字元輸入")

        try:
            # 取得 Template 路徑
            template_path = self._get_template_path(template)

            # Stage 1: 分析 Template
            logger.info("[1/4] 分析 Template 結構...")
            analyzer = TemplateAnalyzer(template_path)
            template_structure = analyzer.analyze(
                slide_count=slide_count,
                include_title=True,
                include_closing=True,
            )

            # Stage 2: 生成內容草稿
            logger.info("[2/4] LLM 擴展使用者輸入...")
            generator = ContentGenerator(self.llm)
            draft_content = await generator.generate(
                user_input=user_input,
                slide_count=slide_count,
                audience=audience,
                language=language,
            )

            # Stage 3: 組織內容到 Template 結構
            logger.info("[3/4] 組織內容到 Template...")
            organizer = ContentOrganizerV2(self.llm)
            organized_content = await organizer.organize(
                draft_content=draft_content,
                template_structure=template_structure,
            )

            # Stage 4: 建構 PPTX
            logger.info("[4/4] 建構 PPTX 檔案...")
            builder = SlideBuilder(template_path)
            pptx_bytes = builder.build(organized_content)

            # 完成
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"簡報生成完成: "
                f"{len(organized_content.get('slides', []))} 張投影片, "
                f"{duration:.2f}s"
            )

            return pptx_bytes

        except Exception as e:
            logger.error(f"簡報生成失敗: {e}", exc_info=True)
            raise

    async def generate_stream(
        self,
        user_input: str,
        template: str | None = None,
        slide_count: int = 10,
        audience: str | None = None,
        language: str = "zh-TW",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        生成簡報（帶進度串流）

        Yields:
            進度更新，包含 stage, progress, message
            最後一則包含 result (PPTX bytes)
        """
        start_time = datetime.now()

        try:
            template_path = self._get_template_path(template)

            # Stage 1: 分析 Template (0-10%)
            yield {
                "stage": "template_analysis",
                "progress": 0,
                "message": f"分析 Template: {template_path.name}",
            }

            analyzer = TemplateAnalyzer(template_path)
            template_structure = analyzer.analyze(
                slide_count=slide_count,
                include_title=True,
                include_closing=True,
            )

            yield {
                "stage": "template_analysis",
                "progress": 10,
                "message": f"Template 分析完成: {template_structure['slide_count']} 張投影片結構",
            }

            # Stage 2: 生成內容草稿 (10-50%)
            yield {
                "stage": "content_generation",
                "progress": 10,
                "message": "LLM 正在擴展和結構化內容...",
            }

            generator = ContentGenerator(self.llm)
            draft_content = await generator.generate(
                user_input=user_input,
                slide_count=slide_count,
                audience=audience,
                language=language,
            )

            yield {
                "stage": "content_generation",
                "progress": 50,
                "message": f"內容草稿完成: {len(draft_content.get('slides', []))} 張投影片",
            }

            # Stage 3: 組織內容 (50-80%)
            yield {
                "stage": "content_organization",
                "progress": 50,
                "message": "組織內容到 Template 結構...",
            }

            organizer = ContentOrganizerV2(self.llm)
            organized_content = await organizer.organize(
                draft_content=draft_content,
                template_structure=template_structure,
            )

            yield {
                "stage": "content_organization",
                "progress": 80,
                "message": "內容組織完成",
            }

            # Stage 4: 建構 PPTX (80-100%)
            yield {
                "stage": "pptx_building",
                "progress": 80,
                "message": "建構 PPTX 檔案...",
            }

            builder = SlideBuilder(template_path)
            pptx_bytes = builder.build(organized_content)

            duration = (datetime.now() - start_time).total_seconds()

            yield {
                "stage": "completed",
                "progress": 100,
                "message": f"完成: {duration:.2f}s",
                "result": pptx_bytes,
                "stats": {
                    "template": template_path.name,
                    "slide_count": len(organized_content.get("slides", [])),
                    "duration_seconds": duration,
                    "file_size": len(pptx_bytes),
                },
                "draft_content": draft_content,  # 可選：返回草稿供除錯
            }

        except Exception as e:
            logger.error(f"簡報生成失敗: {e}", exc_info=True)
            yield {
                "stage": "error",
                "progress": 0,
                "message": f"失敗: {str(e)}",
                "error": str(e),
            }
            raise

    async def generate_to_file(
        self,
        user_input: str,
        output_path: Path,
        template: str | None = None,
        slide_count: int = 10,
        audience: str | None = None,
        language: str = "zh-TW",
    ) -> Path:
        """
        生成簡報並存檔
        """
        pptx_bytes = await self.generate(
            user_input=user_input,
            template=template,
            slide_count=slide_count,
            audience=audience,
            language=language,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(pptx_bytes)

        logger.info(f"已儲存到: {output_path}")
        return output_path


# Singleton
_ppt_service_v2: PPTServiceV2 | None = None


def get_ppt_service_v2() -> PPTServiceV2:
    """取得 PPTServiceV2 singleton"""
    global _ppt_service_v2
    if _ppt_service_v2 is None:
        _ppt_service_v2 = PPTServiceV2()
    return _ppt_service_v2
