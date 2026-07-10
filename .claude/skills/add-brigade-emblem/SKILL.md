---
name: add-brigade-emblem
description: Завантажує нарукавний знак бригади з Вікіпедії, нормалізує зображення (440×520 PNG, прозорий фон, centered), прописує emblem_file у БД, перевіряє результат. Використовуй коли потрібно додати або оновити емблему для бригади.
---

# Додавання емблеми бригади

## Загальний процес

1. **Знайти пряме посилання на файл** через `WebFetch` на сторінку файлу Вікіпедії → отримати `upload.wikimedia.org` URL.
2. **Завантажити файл** через `curl -sL -A "Mozilla/5.0"` у `static/img/brigade-{N}.png` (або `.svg`). Якщо отримано HTML 429 — зачекай 10–15 секунд і повтори.
3. **Перевірити** що файл є валідним зображенням (не HTML-сторінка помилки): `head -c 100` — має починатись з `<?xml`, `<svg` або бінарного заголовку PNG.
4. **Растеризувати якщо SVG** через `python3 -m cairosvg` у тимчасовий PNG: `python3 -m cairosvg input.svg -o /tmp/raw.png --output-height 1000`
5. **Нормалізація і видалення фону** — запусти скрипт нижче.
6. **Перевірити результат** через `Read` на щойно збережений файл.
7. **Прописати у БД** `UPDATE brigades SET emblem_file = 'brigade-N.png' WHERE name LIKE 'N-%'`
8. **Перевірити** через `curl` що файл роздається (200) і посилання є в HTML `/brigades`.

## Скрипт нормалізації

```python
from PIL import Image
import numpy as np

TARGET_W, TARGET_H = 440, 520   # єдиний стандартний розмір
TOLERANCE = 18                   # поріг для видалення білого фону

def flood_fill_transparent(img: Image.Image, tolerance: int = TOLERANCE) -> Image.Image:
    """Видаляє білий фон flood-fill від кутів → прозорий RGBA."""
    src = img.convert("RGBA")
    arr = np.array(src, dtype=np.uint16)
    h, w = arr.shape[:2]
    visited = np.zeros((h, w), dtype=bool)
    result_alpha = np.ones((h, w), dtype=np.uint8) * 255
    seeds = [(0,0),(0,w-1),(h-1,0),(h-1,w-1)]
    stack = [s for s in seeds if all(arr[s[0],s[1],:3] >= 255 - tolerance)]
    while stack:
        y, x = stack.pop()
        if visited[y, x]: continue
        if not all(arr[y,x,:3] >= 255 - tolerance): continue
        visited[y, x] = True
        result_alpha[y, x] = 0
        for ny, nx in [(y-1,x),(y+1,x),(y,x-1),(y,x+1)]:
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                stack.append((ny, nx))
    out_arr = np.array(src)
    out_arr[:, :, 3] = result_alpha
    return Image.fromarray(out_arr, "RGBA")

def normalize_emblem(src_path: str, out_path: str):
    """Вписує зображення у 440×520 RGBA з прозорим фоном (contain-fit, по центру)."""
    im = Image.open(src_path).convert("RGBA")
    # якщо є білий фон — прибрати
    im = flood_fill_transparent(im)
    # вписати у стандартний розмір
    src_w, src_h = im.size
    scale = min(TARGET_W / src_w, TARGET_H / src_h)
    new_w, new_h = max(1, round(src_w * scale)), max(1, round(src_h * scale))
    resized = im.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGBA", (TARGET_W, TARGET_H), (0, 0, 0, 0))  # прозорий холст
    off_x = (TARGET_W - new_w) // 2
    off_y = (TARGET_H - new_h) // 2
    canvas.alpha_composite(resized, (off_x, off_y))
    canvas.save(out_path, "PNG")

normalize_emblem("input.png", "static/img/brigade-N.png")
```

## Важливі деталі

- **Формат:** завжди зберігати як PNG з прозорістю (RGBA). Не використовувати JPEG, не конвертувати в RGB.
- **Розмір:** строго 440×520 px. Не міняти без оновлення цього скіла і CSS.
- **CSS контейнер** (вже налаштовано в `static/css/style.css`): `.emblem.has-image` і `.detail-emblem.has-image` мають `background: transparent; border: none` — не міняти на `#fff`.
- **DB поле** `brigades.emblem_file` — лише ім'я файлу без шляху, наприклад `brigade-79.png`. Шлях підставляє шаблон: `/static/img/{{ b.emblem_file }}`.
- **Перевірка fidelity:** перед записом у БД обов'язково переглянь результат через `Read` — перевір що фон прозорий і деталі щита збережені (не "з'їдені" tolerance).
- **Якщо flood-fill прибирає забагато** (щит має дуже світлий фон, ліцензійний watermark тощо): знизь `tolerance` до 8–12 або зроби обрізку спочатку (`im.crop(bbox)`), потім нормалізуй.
- **Ліцензія:** перевіряти що файл Public Domain або CC0 (державна символіка України, ст. 8 ЗУ про авторське право, звільнена від охорони). Всі поточні емблеми в `static/img/` відповідають цій умові.

## Назви файлів

Конвенція: `brigade-{номер}.png`, де номер — це числовий номер бригади (25, 46, 68, ...). Якщо у назві бригади є літера (наприклад "78-й полк") — використовуй однаково лише цифру.
