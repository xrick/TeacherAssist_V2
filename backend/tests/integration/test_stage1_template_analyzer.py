"""
Stage 1 Integration Test: TemplateAnalyzer

驗證 TemplateAnalyzer.analyze() 輸出符合下游 Stage 期望的資料結構。
"""

import json
from pathlib import Path

import pytest

from app.pptagent_core.roles.template_analyzer import TemplateAnalyzer


@pytest.fixture
def template_path() -> Path:
    """取得測試用 Template 路徑"""
    path = Path(__file__).parent.parent.parent / "data" / "templates" / "modern_clean.pptx"
    if not path.exists():
        pytest.skip(f"Template 不存在: {path}")
    return path


class TestStage1TemplateAnalyzer:
    """Stage 1: TemplateAnalyzer 輸出驗證"""

    def test_analyze_returns_complete_structure(self, template_path: Path):
        """測試 analyze() 回傳完整結構"""
        analyzer = TemplateAnalyzer(template_path)
        result = analyzer.analyze(slide_count=10, include_title=True, include_closing=True)

        assert "slides" in result, "缺少 slides 欄位"
        assert "template" in result, "缺少 template 欄位"
        assert "slide_count" in result, "缺少 slide_count 欄位"
        assert isinstance(result["slides"], list), "slides 應為 list"
        assert len(result["slides"]) == result["slide_count"], "slides 長度應等於 slide_count"

    def test_each_slide_has_required_fields(self, template_path: Path):
        """測試每個 slide 都有必要欄位"""
        analyzer = TemplateAnalyzer(template_path)
        result = analyzer.analyze(slide_count=5)

        required_fields = ["index", "layout_index", "layout_name", "placeholders"]

        for i, slide in enumerate(result["slides"]):
            for field in required_fields:
                assert field in slide, f"Slide {i} 缺少 {field} 欄位"

    def test_placeholder_structure(self, template_path: Path):
        """測試 placeholder 結構正確"""
        analyzer = TemplateAnalyzer(template_path)
        result = analyzer.analyze(slide_count=5)

        for i, slide in enumerate(result["slides"]):
            placeholders = slide.get("placeholders", [])
            assert isinstance(placeholders, list), f"Slide {i} placeholders 應為 list"

            for j, ph in enumerate(placeholders):
                assert "idx" in ph, f"Slide {i} Placeholder {j} 缺少 idx"
                assert "type" in ph, f"Slide {i} Placeholder {j} 缺少 type"

    def test_title_slide_has_title_placeholder(self, template_path: Path):
        """測試 Title slide 有 title placeholder"""
        analyzer = TemplateAnalyzer(template_path)
        result = analyzer.analyze(slide_count=5, include_title=True)

        title_slide = result["slides"][0]
        placeholder_types = [ph.get("type") for ph in title_slide.get("placeholders", [])]

        assert any(
            "TITLE" in str(t).upper() or "CENTER_TITLE" in str(t).upper() for t in placeholder_types
        ), f"Title slide 應有 title placeholder, 實際: {placeholder_types}"

    def test_get_available_layouts(self, template_path: Path):
        """測試 get_available_layouts() 回傳有效的版面列表"""
        analyzer = TemplateAnalyzer(template_path)
        layouts = analyzer.get_available_layouts()

        assert isinstance(layouts, list), "layouts 應為 list"
        assert len(layouts) > 0, "應有至少一個 layout"

        for layout in layouts:
            assert "index" in layout, "layout 缺少 index"
            assert "name" in layout, "layout 缺少 name"

    def test_output_can_be_serialized_to_json(self, template_path: Path):
        """測試輸出可序列化為 JSON（傳遞給 LLM 需要）"""
        analyzer = TemplateAnalyzer(template_path)
        result = analyzer.analyze(slide_count=5)

        try:
            json_str = json.dumps(result, ensure_ascii=False)
            assert len(json_str) > 0
        except (TypeError, ValueError) as e:
            pytest.fail(f"無法序列化為 JSON: {e}")
