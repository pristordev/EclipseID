"""Генерация SVG-табличек званий ИСБ"""

# Цвета в паттернах
COLORS = {
    "y": "#ffe600",   # жёлтый
    "b": "#1e5cb8",   # синий
    "r": "#d42020",   # красный
}


def generate_insignia_svg(pattern: list, cell_size: int = 24) -> str:
    """
    Генерирует SVG-табличку звания из паттерна.

    pattern: [["y", "b"], ["r", "r"]] — 2x2
    Возвращает строку SVG.
    """
    if not pattern or not pattern[0]:
        return ""

    rows = len(pattern)
    cols = len(pattern[0])
    width = cols * cell_size
    height = rows * cell_size

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'shape-rendering="crispEdges">'
    )

    for r_idx, row in enumerate(pattern):
        for c_idx, color_key in enumerate(row):
            color = COLORS.get(color_key, "#000")
            x = c_idx * cell_size
            y = r_idx * cell_size
            svg += (
                f'<rect x="{x}" y="{y}" width="{cell_size}" '
                f'height="{cell_size}" fill="{color}"/>'
            )

    # Тонкая тёмная обводка
    svg += (
        f'<rect x="0" y="0" width="{width}" height="{height}" '
        f'fill="none" stroke="#0a0a0a" stroke-width="1.5"/>'
    )

    svg += "</svg>"
    return svg
