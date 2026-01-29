"""
PPT Generation Service V2

四階段流程（v0.3 架構）：
1. TemplateAnalyzer - 分析 Template 結構
2. ContentGenerator - LLM 直接輸出 placeholders 格式
3. ImageEnricher - 注入圖片（可選）
4. SlideBuilder - 建構最終 PPTX

核心原則：使用者輸入 → LLM 直接生成結構化內容 → 圖片注入 → PPTX 輸出

v0.3 更新：
- 移除 ContentOrganizerV2，ContentGenerator 直接輸出 placeholders 格式
- 簡化管線，減少 LLM 呼叫次數
- 支援 structure_rules 和 body_pool 輪替
- 支援 PICTURE placeholder (idx=10)
"""

import logging
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.pptagent_core.config import TemplateConfigLoader, get_template_config
from app.pptagent_core.roles.content_generator import ContentGenerator
from app.pptagent_core.roles.image_enricher import ImageEnricher
from app.pptagent_core.roles.input_classifier import classify_user_input
from app.pptagent_core.roles.slide_builder import SlideBuilder
from app.pptagent_core.roles.template_analyzer import TemplateAnalyzer
from app.services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)


class PPTServiceV2:
    """
    五階段 PPT 生成服務（含圖片）

    工作流程：
    User Input → ContentGenerator → Draft Content
                                          ↓
    Template → TemplateAnalyzer → Structure → ContentOrganizerV2 → Organized Content
                                                                          ↓
                                                              ImageEnricher → Enriched Content
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

        # v0.2: 載入 template config
        self.config_loader = TemplateConfigLoader()

    def _get_template_path(self, template: str | None) -> tuple[Path, str]:
        """取得 Template 檔案路徑和名稱（v0.3: 從 config 讀取 file_path）

        Returns:
            tuple: (template_path, template_name)
        """
        if template is None:
            template = self.config_loader.default_template_name
            logger.debug(f"使用預設 template: {template}")

        template_name = template  # 保存原始 template name

        # v0.3: 優先從 config 讀取 file_path
        try:
            config = self.config_loader.get_template_config(template)
            template_path = self.templates_path.parent / config.file_path
            if template_path.exists():
                return template_path, template_name
        except KeyError:
            pass

        # fallback: 直接用 template name 作為檔名
        if not template.endswith(".pptx"):
            template = f"{template}.pptx"

        template_path = self.templates_path / template

        if not template_path.exists():
            logger.warning(f"Template 不存在: {template_path}, 使用預設")
            available = list(self.templates_path.glob("*.pptx"))
            if available:
                template_path = available[0]
                template_name = template_path.stem
                logger.info(f"使用替代 Template: {template_path.name}")
            else:
                raise FileNotFoundError(f"找不到任何 PPTX Template: {self.templates_path}")

        return template_path, template_name

    async def generate(
        self,
        user_input: str,
        template: str | None = None,
        slide_count: int = 10,
        audience: str | None = None,
        language: str = "zh-TW",
        add_images: bool = True,
        images_per_slide: int = 1,
    ) -> bytes:
        """
        從使用者輸入生成簡報（v0.3: 移除 Stage 3，ContentGenerator 直接輸出 placeholders）

        Args:
            user_input: 使用者的 markdown/text 輸入
            template: Template 檔案名稱
            slide_count: 目標投影片數量
            audience: 目標受眾
            language: 輸出語言
            add_images: 是否自動加入圖片（預設啟用）
            images_per_slide: 每張投影片的圖片數量（1-3）

        Returns:
            PPTX 檔案的 bytes
        """
        start_time = datetime.now()
        total_stages = 4 if add_images else 3  # v0.3: 減少一個 stage
        logger.info(f"開始生成簡報: {len(user_input)} 字元輸入, 圖片: {add_images}")

        try:
            # 取得 Template 路徑和 config (v0.3: 返回 tuple)
            template_path, template_name = self._get_template_path(template)
            template_config = self.config_loader.get_template_config(template_name)

            # Stage 1: 分析 Template（v0.2: 傳入 config）
            logger.info(f"[1/{total_stages}] 分析 Template 結構...")
            analyzer = TemplateAnalyzer(template_path, config=template_config)
            template_structure = analyzer.analyze(
                slide_count=slide_count,
                include_title=True,
                include_closing=True,
            )

            # Stage 1.5: 分類使用者輸入
            classification = classify_user_input(user_input)
            logger.info(
                f"輸入分類: {classification.mode.value} "
                f"(信心度={classification.confidence}) {classification.reason}"
            )

            # Stage 2: 生成內容（v0.3: 直接輸出 placeholders 格式，不需要 Stage 3）
            logger.info(f"[2/{total_stages}] LLM 生成簡報內容...")
            generator = ContentGenerator(self.llm)
            content = await generator.generate(
                user_input=user_input,
                slide_count=slide_count,
                audience=audience,
                language=language,
                input_mode=classification.mode,
                prompt_path=template_config.prompt_path,
            )

            # Stage 3: 注入圖片（可選）
            if add_images:
                logger.info(f"[3/{total_stages}] 注入圖片...")
                enricher = ImageEnricher()
                enriched_content = await enricher.enrich(
                    organized_content=content,  # v0.3: 直接使用 content
                    draft_content=content,
                    presentation_title=content.get("title", "Presentation"),
                    images_per_slide=images_per_slide,
                )
            else:
                enriched_content = content

            # Stage 4 (or 3): 建構 PPTX（v0.2: 傳入 config）
            logger.info(f"[{total_stages}/{total_stages}] 建構 PPTX 檔案...")
            builder = SlideBuilder(template_path, config=template_config)
            pptx_bytes = builder.build(enriched_content)

            # 完成
            duration = (datetime.now() - start_time).total_seconds()
            total_images = sum(len(s.get("images", [])) for s in enriched_content.get("slides", []))
            logger.info(
                f"簡報生成完成: "
                f"{len(enriched_content.get('slides', []))} 張投影片, "
                f"{total_images} 張圖片, "
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
        add_images: bool = True,
        images_per_slide: int = 1,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        生成簡報（帶進度串流）（v0.3: 移除 Stage 3）

        Args:
            user_input: 使用者的 markdown/text 輸入
            template: Template 檔案名稱
            slide_count: 目標投影片數量
            audience: 目標受眾
            language: 輸出語言
            add_images: 是否自動加入圖片
            images_per_slide: 每張投影片的圖片數量

        Yields:
            進度更新，包含 stage, progress, message
            最後一則包含 result (PPTX bytes)
        """
        start_time = datetime.now()

        # v0.3 進度分配：
        # 有圖片: 0-10 (template) → 10-50 (content) → 50-80 (images) → 80-100 (build)
        # 無圖片: 0-10 (template) → 10-70 (content) → 70-100 (build)

        try:
            # v0.3: 取得 template 路徑和 config (返回 tuple)
            template_path, template_name = self._get_template_path(template)
            template_config = self.config_loader.get_template_config(template_name)

            # Stage 1: 分析 Template (0-10%)
            yield {
                "stage": "template_analysis",
                "progress": 0,
                "message": f"分析 Template: {template_path.name}",
            }

            analyzer = TemplateAnalyzer(template_path, config=template_config)
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

            # Stage 1.5: 分類使用者輸入
            classification = classify_user_input(user_input)
            mode_label = (
                "短題目 → 生成模式"
                if classification.mode.value == "SEARCH_MODE"
                else "長文章 → 結構化模式"
            )
            yield {
                "stage": "input_classification",
                "progress": 10,
                "message": f"輸入分類: {mode_label} (信心度 {classification.confidence:.0%})",
            }

            # Stage 2: 生成內容（v0.3: 直接輸出 placeholders 格式）
            yield {
                "stage": "content_generation",
                "progress": 12,
                "message": "LLM 正在生成簡報內容...",
            }

            generator = ContentGenerator(self.llm)
            content = await generator.generate(
                user_input=user_input,
                slide_count=slide_count,
                audience=audience,
                language=language,
                input_mode=classification.mode,
                prompt_path=template_config.prompt_path,
            )

            progress_after_content = 50 if add_images else 70
            yield {
                "stage": "content_generation",
                "progress": progress_after_content,
                "message": f"內容生成完成: {len(content.get('slides', []))} 張投影片",
            }

            # Stage 3: 注入圖片（可選）(50-80%)
            if add_images:
                yield {
                    "stage": "image_enrichment",
                    "progress": 50,
                    "message": "搜尋並注入圖片...",
                }

                enricher = ImageEnricher()
                enriched_content = await enricher.enrich(
                    organized_content=content,  # v0.3: 直接使用 content
                    draft_content=content,
                    presentation_title=content.get("title", "Presentation"),
                    images_per_slide=images_per_slide,
                )

                total_images = sum(
                    len(s.get("images", [])) for s in enriched_content.get("slides", [])
                )
                yield {
                    "stage": "image_enrichment",
                    "progress": 80,
                    "message": f"圖片注入完成: {total_images} 張圖片",
                }
            else:
                enriched_content = content
                total_images = 0

            # Stage 4 (or 3): 建構 PPTX (80-100% or 70-100%)
            progress_before_build = 80 if add_images else 70
            yield {
                "stage": "pptx_building",
                "progress": progress_before_build,
                "message": "建構 PPTX 檔案...",
            }

            builder = SlideBuilder(template_path, config=template_config)
            pptx_bytes = builder.build(enriched_content)

            duration = (datetime.now() - start_time).total_seconds()

            yield {
                "stage": "completed",
                "progress": 100,
                "message": f"完成: {duration:.2f}s",
                "result": pptx_bytes,
                "stats": {
                    "template": template_path.name,
                    "slide_count": len(enriched_content.get("slides", [])),
                    "image_count": total_images,
                    "duration_seconds": duration,
                    "file_size": len(pptx_bytes),
                },
                "draft_content": content,
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
        add_images: bool = True,
        images_per_slide: int = 1,
    ) -> Path:
        """
        生成簡報並存檔

        Args:
            user_input: 使用者的 markdown/text 輸入
            output_path: 輸出檔案路徑
            template: Template 檔案名稱
            slide_count: 目標投影片數量
            audience: 目標受眾
            language: 輸出語言
            add_images: 是否自動加入圖片
            images_per_slide: 每張投影片的圖片數量

        Returns:
            輸出檔案路徑
        """
        pptx_bytes = await self.generate(
            user_input=user_input,
            template=template,
            slide_count=slide_count,
            audience=audience,
            language=language,
            add_images=add_images,
            images_per_slide=images_per_slide,
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
