"""
Generate preview images for template styles.

Each preview is a 400x225 (16:9) wireframe-style thumbnail
that visually represents the template's color scheme and layout.
"""

from pathlib import Path

from PIL import Image, ImageDraw

# Preview image size (16:9 aspect ratio)
WIDTH = 400
HEIGHT = 225

PREVIEWS_DIR = Path(__file__).parent / "previews"
PREVIEWS_DIR.mkdir(exist_ok=True)


def create_professional_corporate():
    """企業專業風格 — 深藍＋金色，穩重對稱佈局"""
    img = Image.new("RGB", (WIDTH, HEIGHT), "#1e3a8a")  # 深藍底
    draw = ImageDraw.Draw(img)

    # 頂部金色裝飾線
    draw.rectangle([0, 0, WIDTH, 5], fill="#d4a843")

    # 標題區
    draw.rectangle([30, 25, 230, 50], fill="#ffffff")  # 標題 placeholder
    draw.rectangle([30, 58, 130, 68], fill="#d4a843")  # 金色副標題

    # 內容區白底
    draw.rectangle([30, 85, WIDTH - 30, HEIGHT - 25], fill="#ffffff")

    # 內容區：左側文字行
    draw.rectangle([45, 100, 180, 115], fill="#1e3a8a")  # 深色標題
    draw.rectangle([45, 125, 260, 133], fill="#cbd5e1")  # 灰色文字
    draw.rectangle([45, 142, 230, 150], fill="#e2e8f0")  # 灰色文字
    draw.rectangle([45, 159, 250, 167], fill="#e2e8f0")  # 灰色文字

    # 右側金色豎線裝飾
    draw.rectangle([WIDTH - 60, 100, WIDTH - 55, HEIGHT - 35], fill="#d4a843")

    img.save(PREVIEWS_DIR / "professional_corporate.png")
    print("Created: professional_corporate.png")


def create_education_basic():
    """學術研究風格 — 藍色系，結構化列點佈局"""
    img = Image.new("RGB", (WIDTH, HEIGHT), "#1e40af")  # 深藍底
    draw = ImageDraw.Draw(img)

    # 標題區
    draw.rectangle([0, 0, WIDTH, 65], fill="#1e3a8a")
    draw.rectangle([25, 20, 210, 48], fill="#60a5fa")  # 標題 placeholder

    # 內容區白底
    draw.rectangle([20, 80, WIDTH - 20, HEIGHT - 18], fill="#ffffff")

    # 列點清單
    for i in range(4):
        y = 95 + i * 28
        draw.ellipse([38, y, 48, y + 10], fill="#3b82f6")  # 藍色圓點
        draw.rectangle([58, y, 260, y + 10], fill="#e5e7eb")  # 灰色文字行

    # 右側裝飾面板
    draw.rectangle([WIDTH - 65, 88, WIDTH - 28, HEIGHT - 26], fill="#dbeafe")

    img.save(PREVIEWS_DIR / "education_basic.png")
    print("Created: education_basic.png")


def create_industrial_tech():
    """工業科技風格 — 深灰＋橙色，金屬質感"""
    img = Image.new("RGB", (WIDTH, HEIGHT), "#374151")  # 深灰底
    draw = ImageDraw.Draw(img)

    # 左側橙色豎條
    draw.rectangle([0, 0, 10, HEIGHT], fill="#ea580c")

    # 標題區
    draw.rectangle([30, 18, 200, 42], fill="#ffffff")  # 白色標題
    draw.rectangle([WIDTH - 100, 22, WIDTH - 30, 34], fill="#6b7280")  # 右上小灰塊

    # 內容區淺灰底
    draw.rectangle([30, 60, WIDTH - 30, HEIGHT - 18], fill="#f3f4f6")

    # 橙色圓點列表
    for i in range(3):
        y = 78 + i * 35
        draw.ellipse([48, y, 58, y + 10], fill="#ea580c")
        draw.rectangle([68, y, 240, y + 10], fill="#4b5563")

    # 右側橙框圖表 placeholder
    draw.rectangle(
        [WIDTH - 100, 72, WIDTH - 45, HEIGHT - 30], fill="#1f2937", outline="#ea580c", width=2
    )
    # 圖表內部橫線
    for i in range(3):
        y = 90 + i * 28
        draw.rectangle([WIDTH - 90, y, WIDTH - 55, y + 8], fill="#4b5563")

    # 底部細灰線
    draw.rectangle([0, HEIGHT - 4, WIDTH, HEIGHT], fill="#6b7280")

    img.save(PREVIEWS_DIR / "industrial_tech.png")
    print("Created: industrial_tech.png")


def create_strategic_consulting():
    """策略顧問風格 — 極簡冷灰，2x2 矩陣佈局（MECE）"""
    img = Image.new("RGB", (WIDTH, HEIGHT), "#f8fafc")  # 極淺灰底
    draw = ImageDraw.Draw(img)

    # 頂部深藍窄橫條
    draw.rectangle([0, 0, WIDTH, 8], fill="#1e3a5f")

    # 右上角小方塊裝飾
    draw.rectangle([WIDTH - 35, 18, WIDTH - 15, 38], fill="#1e3a5f")

    # 標題區
    draw.rectangle([25, 22, 200, 42], fill="#1e3a5f")  # 深藍標題
    draw.rectangle([25, 50, 140, 58], fill="#94a3b8")  # 冷灰副標題

    # 2x2 矩陣（MECE 四象限）
    cx, cy = 25, 72  # 起始座標
    cw, ch = 168, 65  # 每格寬高
    gap = 12

    # 左上
    draw.rectangle([cx, cy, cx + cw, cy + ch], fill="#e2e8f0", outline="#cbd5e1", width=1)
    draw.rectangle([cx + 10, cy + 12, cx + 80, cy + 20], fill="#64748b")
    draw.rectangle([cx + 10, cy + 30, cx + 120, cy + 37], fill="#cbd5e1")
    draw.rectangle([cx + 10, cy + 44, cx + 100, cy + 51], fill="#cbd5e1")

    # 右上
    rx = cx + cw + gap
    draw.rectangle([rx, cy, rx + cw, cy + ch], fill="#e2e8f0", outline="#cbd5e1", width=1)
    draw.rectangle([rx + 10, cy + 12, rx + 80, cy + 20], fill="#64748b")
    draw.rectangle([rx + 10, cy + 30, rx + 120, cy + 37], fill="#cbd5e1")
    draw.rectangle([rx + 10, cy + 44, rx + 100, cy + 51], fill="#cbd5e1")

    # 左下
    by = cy + ch + gap
    draw.rectangle([cx, by, cx + cw, by + ch], fill="#e2e8f0", outline="#cbd5e1", width=1)
    draw.rectangle([cx + 10, by + 12, cx + 80, by + 20], fill="#64748b")
    draw.rectangle([cx + 10, by + 30, cx + 120, by + 37], fill="#cbd5e1")
    draw.rectangle([cx + 10, by + 44, cx + 100, by + 51], fill="#cbd5e1")

    # 右下
    draw.rectangle([rx, by, rx + cw, by + ch], fill="#e2e8f0", outline="#cbd5e1", width=1)
    draw.rectangle([rx + 10, by + 12, rx + 80, by + 20], fill="#64748b")
    draw.rectangle([rx + 10, by + 30, rx + 120, by + 37], fill="#cbd5e1")
    draw.rectangle([rx + 10, by + 44, rx + 100, by + 51], fill="#cbd5e1")

    # 底部冷灰細線
    draw.rectangle([25, HEIGHT - 10, WIDTH - 25, HEIGHT - 8], fill="#94a3b8")

    img.save(PREVIEWS_DIR / "strategic_consulting.png")
    print("Created: strategic_consulting.png")


def create_visionary_story():
    """願景敘事風格 — 暗色電影感，大量留白居中佈局"""
    img = Image.new("RGB", (WIDTH, HEIGHT), "#0f172a")  # 近黑深藍底
    draw = ImageDraw.Draw(img)

    # 頂部微弱漸層裝飾線
    draw.rectangle([0, 0, WIDTH, 2], fill="#334155")

    # 中央大面積影像 placeholder（深灰矩形帶微弱邊框）
    img_x1, img_y1 = 50, 30
    img_x2, img_y2 = WIDTH - 50, 140
    draw.rectangle([img_x1, img_y1, img_x2, img_y2], fill="#1e293b", outline="#334155", width=1)

    # 影像 placeholder 中央的播放鍵三角形（暗示影片/電影感）
    tri_cx, tri_cy = (img_x1 + img_x2) // 2, (img_y1 + img_y2) // 2
    tri_size = 15
    draw.polygon(
        [
            (tri_cx - tri_size // 2, tri_cy - tri_size),
            (tri_cx - tri_size // 2, tri_cy + tri_size),
            (tri_cx + tri_size, tri_cy),
        ],
        fill="#475569",
    )

    # 居中標題線
    title_w = 180
    draw.rectangle([(WIDTH - title_w) // 2, 158, (WIDTH + title_w) // 2, 170], fill="#e2e8f0")

    # 居中副標題線（更細更短）
    sub_w = 120
    draw.rectangle([(WIDTH - sub_w) // 2, 180, (WIDTH + sub_w) // 2, 188], fill="#64748b")

    # 底部微弱裝飾線
    draw.rectangle([80, HEIGHT - 12, WIDTH - 80, HEIGHT - 10], fill="#334155")

    img.save(PREVIEWS_DIR / "visionary_story.png")
    print("Created: visionary_story.png")


if __name__ == "__main__":
    create_professional_corporate()
    create_education_basic()
    create_industrial_tech()
    create_strategic_consulting()
    create_visionary_story()
    print(f"\nAll 5 preview images created in: {PREVIEWS_DIR}")
