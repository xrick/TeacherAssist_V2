"""
Generate preview images for template styles
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# Preview image size (16:9 aspect ratio)
WIDTH = 400
HEIGHT = 225

PREVIEWS_DIR = Path(__file__).parent / "previews"
PREVIEWS_DIR.mkdir(exist_ok=True)


def create_education_basic():
    """教育基礎風格 - 藍色系，清晰專業"""
    img = Image.new('RGB', (WIDTH, HEIGHT), '#1e40af')  # 深藍底
    draw = ImageDraw.Draw(img)

    # 標題區
    draw.rectangle([0, 0, WIDTH, 60], fill='#1e3a8a')
    draw.rectangle([20, 20, 200, 45], fill='#60a5fa')  # 標題placeholder

    # 內容區
    draw.rectangle([20, 80, WIDTH-20, HEIGHT-20], fill='#ffffff')

    # 模擬內容列表
    for i in range(4):
        y = 95 + i * 28
        draw.ellipse([35, y, 45, y+10], fill='#3b82f6')
        draw.rectangle([55, y, 250, y+10], fill='#e5e7eb')

    # 側邊裝飾
    draw.rectangle([WIDTH-60, 90, WIDTH-30, HEIGHT-30], fill='#dbeafe')

    img.save(PREVIEWS_DIR / "education_basic.png")
    print("Created: education_basic.png")


def create_modern_clean():
    """現代簡約風格 - 灰白色系，極簡設計"""
    img = Image.new('RGB', (WIDTH, HEIGHT), '#f8fafc')  # 淺灰白底
    draw = ImageDraw.Draw(img)

    # 左側色塊
    draw.rectangle([0, 0, 15, HEIGHT], fill='#0f172a')

    # 標題區
    draw.rectangle([40, 30, 250, 55], fill='#1e293b')
    draw.rectangle([40, 65, 150, 75], fill='#94a3b8')

    # 內容卡片
    draw.rectangle([40, 100, 180, 200], fill='#ffffff', outline='#e2e8f0', width=2)
    draw.rectangle([50, 115, 170, 130], fill='#cbd5e1')
    draw.rectangle([50, 140, 140, 150], fill='#e2e8f0')
    draw.rectangle([50, 160, 160, 170], fill='#e2e8f0')

    draw.rectangle([200, 100, 340, 200], fill='#ffffff', outline='#e2e8f0', width=2)
    draw.rectangle([210, 115, 330, 130], fill='#cbd5e1')
    draw.rectangle([210, 140, 300, 150], fill='#e2e8f0')
    draw.rectangle([210, 160, 320, 170], fill='#e2e8f0')

    img.save(PREVIEWS_DIR / "modern_clean.png")
    print("Created: modern_clean.png")


def create_creative_colorful():
    """創意多彩風格 - 鮮豔漸層，活潑設計"""
    img = Image.new('RGB', (WIDTH, HEIGHT), '#fef3c7')  # 淡黃底
    draw = ImageDraw.Draw(img)

    # 漸層效果模擬（使用色塊）
    draw.polygon([(0, 0), (150, 0), (100, HEIGHT), (0, HEIGHT)], fill='#f97316')
    draw.polygon([(WIDTH, 0), (WIDTH, HEIGHT), (300, HEIGHT), (350, 0)], fill='#ec4899')

    # 中央內容區
    draw.rounded_rectangle([60, 40, WIDTH-60, HEIGHT-40], radius=15, fill='#ffffff')

    # 標題
    draw.rectangle([80, 55, 220, 75], fill='#7c3aed')

    # 彩色裝飾點
    colors = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6']
    for i, color in enumerate(colors):
        draw.ellipse([80 + i*50, 95, 100 + i*50, 115], fill=color)

    # 內容區塊
    draw.rounded_rectangle([80, 130, 180, 185], radius=8, fill='#fef3c7')
    draw.rounded_rectangle([195, 130, 295, 185], radius=8, fill='#dcfce7')

    img.save(PREVIEWS_DIR / "creative_colorful.png")
    print("Created: creative_colorful.png")


def create_nature_artistic():
    """自然藝術風格 - 綠色系，自然元素"""
    img = Image.new('RGB', (WIDTH, HEIGHT), '#ecfdf5')  # 淡綠底
    draw = ImageDraw.Draw(img)

    # 底部山脈/自然形狀
    draw.polygon([(0, HEIGHT), (0, 160), (80, 130), (150, 170), (220, 120), (300, 150), (WIDTH, 140), (WIDTH, HEIGHT)], fill='#86efac')
    draw.polygon([(0, HEIGHT), (50, 170), (120, 150), (200, 180), (280, 140), (350, 160), (WIDTH, 150), (WIDTH, HEIGHT)], fill='#4ade80')

    # 上方標題區
    draw.rounded_rectangle([30, 25, 280, 55], radius=10, fill='#166534')

    # 內容卡片（帶自然感圓角）
    draw.rounded_rectangle([30, 70, 190, 140], radius=12, fill='#ffffff', outline='#22c55e', width=2)
    draw.rectangle([45, 85, 175, 95], fill='#bbf7d0')
    draw.rectangle([45, 105, 140, 115], fill='#dcfce7')
    draw.rectangle([45, 120, 160, 130], fill='#dcfce7')

    draw.rounded_rectangle([205, 70, 365, 140], radius=12, fill='#ffffff', outline='#22c55e', width=2)
    draw.rectangle([220, 85, 350, 95], fill='#bbf7d0')
    draw.rectangle([220, 105, 315, 115], fill='#dcfce7')
    draw.rectangle([220, 120, 335, 130], fill='#dcfce7')

    # 裝飾葉子形狀
    draw.ellipse([350, 20, 380, 60], fill='#22c55e')
    draw.ellipse([360, 35, 390, 70], fill='#16a34a')

    img.save(PREVIEWS_DIR / "nature_artistic.png")
    print("Created: nature_artistic.png")


if __name__ == "__main__":
    create_education_basic()
    create_modern_clean()
    create_creative_colorful()
    create_nature_artistic()
    print(f"\nAll preview images created in: {PREVIEWS_DIR}")
