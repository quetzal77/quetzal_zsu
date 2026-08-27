-- Canonical schema for quetzal_zsu.db
-- Kept under version control so schema changes are reviewable via `git diff`.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Auth
-- ---------------------------------------------------------------------

CREATE TABLE users (
    user_id        INTEGER PRIMARY KEY,
    username       TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Lookup tables
-- ---------------------------------------------------------------------

-- Самостійний довідник деталей роду військ (керується окремою плашкою
-- "Деталі родів військ" в /settings); military_branches.details_id обирає
-- потрібний рядок за details_name — так само, як territorial_commands
-- обирає рід військ через military_branch_id.
CREATE TABLE military_branch_details (
    details_id         INTEGER PRIMARY KEY,
    details_name       TEXT NOT NULL UNIQUE,
    emblem_file        TEXT, -- посилання/ім'я файлу герба роду військ
    flag_file          TEXT, -- посилання/ім'я файлу прапора роду військ
    founded_date       DATE,
    hq_location_id     INTEGER REFERENCES locations (location_id), -- локація штабу
    patch_file         TEXT, -- посилання/ім'я файлу нарукавного знака
    beret_badge_file   TEXT, -- посилання/ім'я файлу беретного знака
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE military_branches (
    branch_id          INTEGER PRIMARY KEY,
    branch_name        TEXT NOT NULL UNIQUE,
    details_id         INTEGER REFERENCES military_branch_details (details_id),
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE territorial_commands (
    command_id           INTEGER PRIMARY KEY,
    command_name         TEXT NOT NULL UNIQUE,
    military_branch_id   INTEGER REFERENCES military_branches (branch_id), -- рід військ, якому підпорядковане ОК
    details_id           INTEGER REFERENCES military_branch_details (details_id),
    is_force             INTEGER NOT NULL DEFAULT 0, -- позначка "сила" (напр. Сили ТрО) на відміну від звичайного ОК
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE army_corps (
    corps_id       INTEGER PRIMARY KEY,
    corps_name     TEXT NOT NULL UNIQUE,
    founded_date   DATE, -- дата заснування корпусу
    emblem_file    TEXT, -- посилання/ім'я файлу емблеми корпусу
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE troop_types (
    type_id              INTEGER PRIMARY KEY,
    type_name            TEXT NOT NULL UNIQUE,
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    collar_emblem_file   TEXT -- посилання/ім'я файлу комірної емблеми
);

CREATE TABLE unit_types (
    unit_type_id   INTEGER PRIMARY KEY,
    type_name      TEXT NOT NULL UNIQUE, -- Бригада / Полк / Батальон
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE regions (
    region_id      INTEGER PRIMARY KEY,
    region_name    TEXT NOT NULL UNIQUE,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE equipment_types (
    equipment_type_id  INTEGER PRIMARY KEY,
    type_name          TEXT NOT NULL UNIQUE,
    created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE equipment (
    equipment_id      INTEGER PRIMARY KEY,
    name              TEXT NOT NULL UNIQUE,
    description       TEXT,
    equipment_type_id INTEGER REFERENCES equipment_types (equipment_type_id),
    photo             TEXT,
    adopted_date      DATE, -- дата прийняття на озброєння
    created_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_equipment_equipment_type_id ON equipment (equipment_type_id);

CREATE TABLE traditions (
    tradition_id   INTEGER PRIMARY KEY,
    title          TEXT NOT NULL UNIQUE,
    description    TEXT,
    photo          TEXT,
    is_honorific   INTEGER NOT NULL DEFAULT 0, -- controls whether brigade_traditions.unit_name is shown for this tradition
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------
-- Geography
-- ---------------------------------------------------------------------

CREATE TABLE locations (
    location_id   INTEGER PRIMARY KEY,
    city_name     TEXT NOT NULL,
    region_id     INTEGER NOT NULL REFERENCES regions (region_id),
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (city_name, region_id)
);

CREATE INDEX idx_locations_region_id ON locations (region_id);
CREATE INDEX idx_military_branch_details_hq_location_id ON military_branch_details (hq_location_id);
CREATE INDEX idx_military_branches_details_id ON military_branches (details_id);
CREATE INDEX idx_territorial_commands_military_branch_id ON territorial_commands (military_branch_id);
CREATE INDEX idx_territorial_commands_details_id ON territorial_commands (details_id);

-- ---------------------------------------------------------------------
-- Core entities
-- ---------------------------------------------------------------------

CREATE TABLE battles (
    battle_id      INTEGER PRIMARY KEY,
    name           TEXT NOT NULL,
    location_id    INTEGER REFERENCES locations (location_id),
    start_date     DATE,
    end_date       DATE,
    description    TEXT,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (start_date IS NULL OR end_date IS NULL OR start_date <= end_date)
);

CREATE INDEX idx_battles_location_id ON battles (location_id);

CREATE TABLE brigades (
    brigade_id               INTEGER PRIMARY KEY,
    name                     TEXT NOT NULL,
    description              TEXT,
    military_branch_id       INTEGER REFERENCES military_branches (branch_id),
    corps_id                 INTEGER REFERENCES army_corps (corps_id),
    territorial_command_id   INTEGER REFERENCES territorial_commands (command_id),
    troop_type_id            INTEGER REFERENCES troop_types (type_id),
    formed_date              DATE,
    flag_date                DATE,
    brigade_date             DATE, -- дата, коли підрозділ став бригадою; якщо порожньо, на списках показується formed_date
    location_id              INTEGER REFERENCES locations (location_id),
    emblem_file              TEXT,
    unit_type_id             INTEGER REFERENCES unit_types (unit_type_id), -- Бригада / Полк / Батальон
    created_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (formed_date IS NULL OR flag_date IS NULL OR formed_date <= flag_date)
);

CREATE INDEX idx_brigades_military_branch_id ON brigades (military_branch_id);
CREATE INDEX idx_brigades_corps_id ON brigades (corps_id);
CREATE INDEX idx_brigades_territorial_command_id ON brigades (territorial_command_id);
CREATE INDEX idx_brigades_troop_type_id ON brigades (troop_type_id);
CREATE INDEX idx_brigades_location_id ON brigades (location_id);
CREATE INDEX idx_brigades_unit_type_id ON brigades (unit_type_id);

-- ---------------------------------------------------------------------
-- Junction tables (many-to-many)
-- ---------------------------------------------------------------------

CREATE TABLE brigade_battles (
    brigade_id   INTEGER NOT NULL REFERENCES brigades (brigade_id),
    battle_id    INTEGER NOT NULL REFERENCES battles (battle_id),
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (brigade_id, battle_id)
);

CREATE INDEX idx_brigade_battles_battle_id ON brigade_battles (battle_id);

CREATE TABLE brigade_equipment (
    brigade_id     INTEGER NOT NULL REFERENCES brigades (brigade_id),
    equipment_id   INTEGER NOT NULL REFERENCES equipment (equipment_id),
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (brigade_id, equipment_id)
);

CREATE INDEX idx_brigade_equipment_equipment_id ON brigade_equipment (equipment_id);

CREATE TABLE brigade_traditions (
    brigade_id      INTEGER NOT NULL REFERENCES brigades (brigade_id),
    tradition_id    INTEGER NOT NULL REFERENCES traditions (tradition_id),
    date_assigned   DATE,
    unit_name       TEXT,
    photo           TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (brigade_id, tradition_id)
);

CREATE INDEX idx_brigade_traditions_tradition_id ON brigade_traditions (tradition_id);

CREATE TABLE brigade_photos (
    photo_id     INTEGER PRIMARY KEY,
    brigade_id   INTEGER NOT NULL REFERENCES brigades (brigade_id),
    file_path    TEXT NOT NULL,
    position     INTEGER NOT NULL CHECK (position IN (1, 2, 3)),
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (brigade_id, position)
);

CREATE INDEX idx_brigade_photos_brigade_id ON brigade_photos (brigade_id);
