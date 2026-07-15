# 🪖 Паспорт бази даних бойових бригад
Фінальна версія документа, що описує повну структуру бази даних SQLite для моделювання бойових бригад, їх участі у боях, оснащення, традицій, географії та класифікаційних зв’язків.

---

## 1️⃣ Таблиця: `army_corps`
| Поле | Тип даних | Опис | Примітки |
|------|------------|------|-----------|
| `corps_id` | INTEGER | Ідентифікатор корпусу | PK |
| `corps_name` | TEXT | Назва корпусу | Унікальне |
| `created_at` | TIMESTAMP | Створено | CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | Оновлено | CURRENT_TIMESTAMP |

---

## 2️⃣ Таблиця: `battles`
| Поле | Тип даних | Опис | Примітки |
|------|------------|------|-----------|
| `battle_id` | INTEGER | Ідентифікатор бою | PK |
| `name` | TEXT | Назва бою | — |
| `location_id` | INTEGER | Локація | FK → `locations(location_id)` |
| `start_date` | DATE | Початок | — |
| `end_date` | DATE | Завершення | — |
| `description` | TEXT | Опис | — |
| `created_at` | TIMESTAMP | Створено | CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | Оновлено | CURRENT_TIMESTAMP |

---

## 3️⃣ Таблиця: `brigade_battles`
| Поле | Тип даних | Опис | Примітки |
|------|------------|------|-----------|
| `brigade_id` | INTEGER | Ідентифікатор бригади | FK |
| `battle_id` | INTEGER | Ідентифікатор бою | FK |
| `created_at` | TIMESTAMP | Створено | CURRENT_TIMESTAMP |

**PK:** `(brigade_id, battle_id)`

---

## 4️⃣ Таблиця: `brigades`
| Поле | Тип даних | Опис | Примітки |
|------|------------|------|-----------|
| `brigade_id` | INTEGER | Ідентифікатор бригади | PK |
| `name` | TEXT | Назва | — |
| `description` | TEXT | Опис | — |
| `military_branch_id` | INTEGER | Вид ЗС | FK |
| `corps_id` | INTEGER | Корпус | FK |
| `territorial_command_id` | INTEGER | Командування | FK |
| `troop_type_id` | INTEGER | Тип військ | FK |
| `formed_date` | DATE | Дата формування | — |
| `flag_date` | DATE | Дата прапора | — |
| `brigade_date` | DATE | Дата, коли підрозділ став бригадою | Якщо порожньо — на списках показується `formed_date` |
| `location_id` | INTEGER | Дислокація | FK |
| `emblem_file` | TEXT | Файл емблеми | — |
| `created_at` | TIMESTAMP | Створено | CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | Оновлено | CURRENT_TIMESTAMP |

---

## 5️⃣ Таблиця: `brigade_equipment`
| Поле | Тип даних | Опис | Примітки |
|------|------------|------|-----------|
| `brigade_id` | INTEGER | Ідентифікатор бригади | FK |
| `equipment_id` | INTEGER | Ідентифікатор техніки | FK |
| `created_at` | TIMESTAMP | Створено | CURRENT_TIMESTAMP |

**PK:** `(brigade_id, equipment_id)`

---

## 6️⃣ Таблиця: `brigade_photos`
| Поле | Тип даних | Опис | Примітки |
|------|------------|------|-----------|
| `photo_id` | INTEGER | Ідентифікатор фото | PK |
| `brigade_id` | INTEGER | Ідентифікатор бригади | FK |
| `file_path` | TEXT | Шлях до фото | — |
| `position` | INTEGER | Порядковий номер | CHECK |
| `created_at` | TIMESTAMP | Створено | CURRENT_TIMESTAMP |

**UNIQUE:** `(brigade_id, position)`

---

## 7️⃣ Таблиця: `brigade_traditions`
| Поле | Тип даних | Опис | Примітки |
|------|------------|------|-----------|
| `brigade_id` | INTEGER | Ідентифікатор бригади | FK |
| `tradition_id` | INTEGER | Ідентифікатор традиції | FK |
| `date_assigned` | DATE | Дата присвоєння | — |
| `created_at` | TIMESTAMP | Створено | CURRENT_TIMESTAMP |
| `unit_name` | TEXT | Почесна назва | — |
| `photo` | TEXT | Фото | — |

**PK:** `(brigade_id, tradition_id)`

---

## 8️⃣ Таблиця: `equipment`
| Поле | Тип даних | Опис | Примітки |
|------|------------|------|-----------|
| `equipment_id` | INTEGER | Ідентифікатор техніки | PK |
| `name` | TEXT | Назва | Унікальне |
| `description` | TEXT | Опис | — |
| `created_at` | TIMESTAMP | Створено | CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | Оновлено | CURRENT_TIMESTAMP |

---

## 9️⃣ Таблиця: `locations`
| Поле | Тип даних | Опис | Примітки |
|------|------------|------|-----------|
| `location_id` | INTEGER | Ідентифікатор локації | PK |
| `city_name` | TEXT | Назва міста | — |
| `region_id` | INTEGER | Регіон | FK |
| `created_at` | TIMESTAMP | Створено | CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | Оновлено | CURRENT_TIMESTAMP |

**UNIQUE:** `(city_name, region_id)`

---

## 🔟 Таблиця: `military_branches`
| Поле | Тип даних | Опис | Примітки |
|------|------------|------|-----------|
| `branch_id` | INTEGER | Ідентифікатор виду ЗС | PK |
| `branch_name` | TEXT | Назва | Унікальне |
| `created_at` | TIMESTAMP | Створено | CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | Оновлено | CURRENT_TIMESTAMP |

---

## 11️⃣ Таблиця: `regions`
| Поле | Тип даних | Опис | Примітки |
|------|------------|------|-----------|
| `region_id` | INTEGER | Ідентифікатор регіону | PK |
| `region_name` | TEXT | Назва | Унікальне |
| `created_at` | TIMESTAMP | Створено | CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | Оновлено | CURRENT_TIMESTAMP |

---

## 12️⃣ Таблиця: `territorial_commands`
| Поле | Тип даних | Опис | Примітки |
|------|------------|------|-----------|
| `command_id` | INTEGER | Ідентифікатор командування | PK |
| `command_name` | TEXT | Назва | Унікальне |
| `created_at` | TIMESTAMP | Створено | CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | Оновлено | CURRENT_TIMESTAMP |

---

## 13️⃣ Таблиця: `traditions`
| Поле | Тип даних | Опис | Примітки |
|------|------------|------|-----------|
| `tradition_id` | INTEGER | Ідентифікатор традиції | PK |
| `title` | TEXT | Назва | Унікальне |
| `description` | TEXT | Опис | — |
| `created_at` | TIMESTAMP | Створено | CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | Оновлено | CURRENT_TIMESTAMP |
| `photo` | TEXT | Фото | — |

---

## 14️⃣ Таблиця: `troop_types`
| Поле | Тип даних | Опис | Примітки |
|------|------------|------|-----------|
| `type_id` | INTEGER | Ідентифікатор типу військ | PK |
| `type_name` | TEXT | Назва типу військ | Унікальне |
| `created_at` | TIMESTAMP | Створено | CURRENT_TIMESTAMP |
| `updated_at` | TIMESTAMP | Оновлено | CURRENT_TIMESTAMP |

---

## 🔗 Загальна схема зв’язків
## 🔗 Загальна схема зв’язків

army_corps ─┬─ brigades ─┬─ brigade_battles ─┬─ battles
│            ├─ brigade_equipment ─┬─ equipment
│            ├─ brigade_photos
│            └─ brigade_traditions ─┬─ traditions

locations ─┬─ brigades
└─ battles

military_branches ─┬─ brigades
territorial_commands ─┬─ brigades
regions ─┬─ locations