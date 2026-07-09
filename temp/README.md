# Jinja2-шаблони порталу бригад ЗСУ

Готовий набір шаблонів + CSS у стилі редизайну (світла тема, військова олива),
розрахований на ваш стек **FastAPI + Jinja2 + SQLite без збірки фронтенду**.

## Що куди покласти

```
jinja_export/templates/*.html   →  app/templates/     (замінює наявні)
jinja_export/static/css/style.css →  static/css/style.css
```

Шаблони наслідують `base.html` і використовують ті самі змінні контексту, що вже
віддають ваші роутери. Нижче — які саме змінні очікує кожен шаблон і які невеликі
правки в роутерах увімкнуть повний функціонал (сортування, картки з роком/прапором,
пошук, дашборд).

## Розкладка навігації

`base.html` очікує роути: `/brigades`, `/battles`, `/equipment`, `/traditions`,
`/stats`. Активний пункт визначається за `request.url.path`. Логотип веде на `/brigades`.

---

## index.html — список бригад

Використовує наявний контекст (`brigades`, `military_branches`, `army_corps`,
`territorial_commands`, `filters`) **плюс** необов'язкові поля картки.

- **Перемикач «Картки / Таблиця»** — через `?view=cards|table` (кнопки submit у формі фільтрів). Нічого міняти не треба.
- **Фільтри-чипи** — радіо-кнопки в одній формі, автосабміт `onchange`; зберігають усі активні фільтри разом. Працюють із наявними параметрами `military_branch_id`, `corps_id`, `territorial_command_id`.
- **Групування за родом військ + розділювачі** — шаблон групує послідовні рядки за `branch_name`, тож **список має приходити вже відсортованим** у роутері (див. нижче).
- **Картки** показують емблему (`emblem_file` або №), рід військ, ППД (`city_name`), рік (`formed_date`) та індикатор прапора (`flag_date`). Якщо цих полів немає у вибірці — вони просто ховаються.

### Рекомендована правка роутера `list_brigades`

Розширте SELECT і додайте сортування + пошук:

```python
@router.get("")
def list_brigades(request, q: str | None = None,
                  military_branch_id=None, corps_id=None,
                  territorial_command_id=None, db=Depends(get_db)):
    query = """
        SELECT b.brigade_id, b.name, b.emblem_file, b.formed_date, b.flag_date,
               mb.branch_name, ac.corps_name, l.city_name,
               (SELECT COUNT(*) FROM brigade_battles bb WHERE bb.brigade_id = b.brigade_id) AS battle_count
        FROM brigades b
        LEFT JOIN military_branches mb ON b.military_branch_id = mb.branch_id
        LEFT JOIN army_corps ac        ON b.corps_id = ac.corps_id
        LEFT JOIN locations l          ON b.location_id = l.location_id
        WHERE 1=1
    """
    params = []
    if q:
        query += " AND b.name LIKE ?"; params.append(f"%{q}%")
    if military_branch_id:
        query += " AND b.military_branch_id = ?"; params.append(military_branch_id)
    if corps_id:
        query += " AND b.corps_id = ?"; params.append(corps_id)
    if territorial_command_id:
        query += " AND b.territorial_command_id = ?"; params.append(territorial_command_id)

    # Сортування: ДШВ → Сухопутні → ТрО → решта, потім за номером у назві
    query += """
        ORDER BY CASE mb.branch_name
                   WHEN 'Десантно-штурмові війська' THEN 1
                   WHEN 'Сухопутні війська'          THEN 2
                   WHEN 'Сили територіальної оборони' THEN 3
                   ELSE 9 END,
                 CAST(b.name AS INTEGER)
    """
    brigades = db.execute(query, params).fetchall()
    # ... решта як було (regions, _lookups, filters)
```

> `CAST(b.name AS INTEGER)` бере провідне число з назви («93-тя …» → 93).

---

## brigade_detail.html

Контекст: `brigade` (усі поля + `branch_name`, `corps_name`, `command_name`,
`type_name`, `city_name`, `region_name`, `emblem_file`) і `stats.{battles,equipment,traditions}`
— усе вже є у вашому роутері.

Необов'язково: передайте `battles` (список битв бригади з полем `role`) — з'явиться
панель «Бойовий шлях»; і `photos` (рядки `brigade_photos`) — заповнять фотогалерею.

---

## brigade_form.html

Контекст без змін: `brigade` (або `None`), `military_branches`, `army_corps`,
`territorial_commands`, `troop_types`, `locations`. Додано поле «Армійський корпус».

---

## battles_list.html / battle_detail.html

- Список: `battles` (`battle_id`, `name`, `start_date`, `end_date`, опц. `city_name`, `region_name`, `description`).
- Деталь: `battle` (+ `city_name`, `region_name`) та `brigades` (учасниці з `role`).
  Необов'язкове поле `battle.status` (напр. «Перемога») підсвітиться тегом.

## equipment_list.html / traditions_list.html

`equipment` (`name`, `description`) / `traditions` (`title`, `description`).
Необов'язкове `brigade_count` у рядку покаже, за скількома бригадами закріплено позицію.

---

## stats.html — дашборд (новий роут `/stats`)

Приклад роутера:

```python
@router.get("/stats")
def stats(request, db=Depends(get_db)):
    counts = {
        "brigades":   db.execute("SELECT COUNT(*) FROM brigades").fetchone()[0],
        "battles":    db.execute("SELECT COUNT(*) FROM battles").fetchone()[0],
        "equipment":  db.execute("SELECT COUNT(*) FROM equipment").fetchone()[0],
        "traditions": db.execute("SELECT COUNT(*) FROM traditions").fetchone()[0],
    }
    def dist(sql):
        rows = db.execute(sql).fetchall()
        mx = max([r[1] for r in rows], default=1) or 1
        return [{"label": r[0] or "—", "count": r[1], "pct": round(r[1] / mx * 100)} for r in rows]

    branch_dist = dist("""SELECT mb.branch_name, COUNT(*) FROM brigades b
        LEFT JOIN military_branches mb ON b.military_branch_id = mb.branch_id
        GROUP BY mb.branch_name ORDER BY COUNT(*) DESC""")
    command_dist = dist("""SELECT tc.command_name, COUNT(*) FROM brigades b
        LEFT JOIN territorial_commands tc ON b.territorial_command_id = tc.command_id
        GROUP BY tc.command_name ORDER BY COUNT(*) DESC""")
    recent = db.execute("""SELECT battle_id, name, start_date, end_date FROM battles
        ORDER BY start_date DESC LIMIT 6""").fetchall()
    recent_battles = [{"battle_id": r[0], "name": r[1],
                       "period": (r[2] or "") + ((" – " + r[3]) if r[3] else "")}
                      for r in recent]

    return templates.TemplateResponse(request, "stats.html", {
        "counts": counts, "branch_dist": branch_dist,
        "command_dist": command_dist, "recent_battles": recent_battles})
```

Зареєструйте роут (напр. окремий `stats` router або в `main.py`) на шляху `/stats`.

---

## Примітки

- **Емблеми/фото**: покладіть файли у `static/img/`, а в БД зберігайте ім'я файлу
  (`brigades.emblem_file`, `brigade_photos.file_path`). Якщо файлу немає — картка
  показує монограму з номера, а прапор — порожню пунктирну рамку.
- **Позивний** (`callsign`) у поточній схемі відсутній; шаблони показують його лише
  якщо додасте таке поле у вибірку — інакше рядок просто не рендериться.
- **Мобільна версія** вбудована в CSS (гамбургер-меню, одноколонкові сітки,
  горизонтальна прокрутка таблиці) — окремого коду не треба.
- CSS не потребує збірки: один файл `style.css`, змінні теми — у `:root`
  (перефарбування в один шар).
