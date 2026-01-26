"""
Input Classifier

Stage 0 (前處理): 判斷使用者輸入的是「短題目」還是「長文章」

功能：
- 多維度分析使用者輸入（字數、段落數、標點密度）
- 回傳分類結果與信心度
- 分類結果用於 ContentGenerator 調整 prompt 策略
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Module 層級編譯，避免重複 compile
_URL_PATTERN = re.compile(r"^https?://[^\s]+$")
_SENTENCE_ENDING_PATTERN = re.compile(r"[。！？.!?]")


class InputMode(Enum):
    """使用者輸入模式"""

    SEARCH = "SEARCH_MODE"  # 短題目：需要 LLM 生成完整內容
    DIRECT = "DIRECT_MODE"  # 長文章：LLM 結構化已有內容


@dataclass
class ClassificationResult:
    """分類結果"""

    mode: InputMode
    confidence: float  # 0.0 ~ 1.0
    char_count: int
    paragraph_count: int
    reason: str


def classify_user_input(
    text: str,
    length_threshold: int = 150,
) -> ClassificationResult:
    """
    多維度判斷使用者輸入模式。

    評分維度：
    - 字元數（基本指標）
    - 段落數（文章通常有多段）
    - 句末標點密度（文章有完整句子）

    Args:
        text: 使用者輸入文字
        length_threshold: 長短文判定閾值（預設 150 字元）

    Returns:
        ClassificationResult 包含分類模式、信心度和分析數據
    """
    text = text.strip()

    # 空值檢查
    if not text:
        return ClassificationResult(
            mode=InputMode.SEARCH,
            confidence=0.0,
            char_count=0,
            paragraph_count=0,
            reason="空白輸入",
        )

    # URL 檢查（整行都是 URL 才算）
    if _URL_PATTERN.match(text):
        return ClassificationResult(
            mode=InputMode.SEARCH,
            confidence=1.0,
            char_count=len(text),
            paragraph_count=0,
            reason="輸入為網址",
        )

    char_count = len(text)
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    paragraph_count = len(paragraphs)

    # 句末標點（中英文）
    sentence_endings = len(_SENTENCE_ENDING_PATTERN.findall(text))

    # --- 評分邏輯 ---
    # 正分 → DIRECT（長文章），負分 → SEARCH（短題目）
    score = 0.0

    # 維度 1：字數
    if char_count >= length_threshold * 2:
        score += 2.0
    elif char_count >= length_threshold:
        score += 1.0
    elif char_count >= length_threshold * 0.5:
        score -= 0.5
    else:
        score -= 2.0

    # 維度 2：段落數
    if paragraph_count >= 3:
        score += 1.0
    elif paragraph_count == 1:
        score -= 0.5

    # 維度 3：句末標點密度（每 100 字有幾個句號）
    if char_count > 0:
        punctuation_density = sentence_endings / (char_count / 100)
        if punctuation_density >= 2.0:
            score += 1.0
        elif punctuation_density < 0.5:
            score -= 0.5

    # 決策
    if score > 0:
        mode = InputMode.DIRECT
        confidence = min(score / 4.0, 1.0)
    else:
        mode = InputMode.SEARCH
        confidence = min(abs(score) / 4.0, 1.0)

    result = ClassificationResult(
        mode=mode,
        confidence=round(confidence, 2),
        char_count=char_count,
        paragraph_count=paragraph_count,
        reason=(
            f"score={score:.1f} "
            f"(字數={char_count}, 段落={paragraph_count}, 句末標點={sentence_endings})"
        ),
    )

    logger.info(f"輸入分類: {result.mode.value} (信心度={result.confidence}) {result.reason}")
    return result
