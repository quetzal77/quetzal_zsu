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

CREATE TABLE military_branches (
    branch_id      INTEGER PRIMARY KEY,
    branch_name    TEXT NOT NULL UNIQUE,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE territorial_commands (
    command_id     INTEGER PRIMARY KEY,
    command_name   TEXT NOT NULL UNIQUE,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE army_corps (
    corps_id       INTEGER PRIMARY KEY,
    corps_name     TEXT NOT NULL UNIQUE,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE troop_types (
    type_id        INTEGER PRIMARY KEY,
    type_name      TEXT NOT NULL UNIQUE,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE regions (
    region_id      INTEGER PRIMARY KEY,
    region_name    TEXT NOT NULL UNIQUE,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE equipment (
    equipment_id   INTEGER PRIMARY KEY,
    name           TEXT NOT NULL UNIQUE,
    description    TEXT,
    created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

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
    location_id              INTEGER REFERENCES locations (location_id),
    emblem_file              TEXT,
    created_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (formed_date IS NULL OR flag_date IS NULL OR formed_date <= flag_date)
);

CREATE INDEX idx_brigades_military_branch_id ON brigades (military_branch_id);
CREATE INDEX idx_brigades_corps_id ON brigades (corps_id);
CREATE INDEX idx_brigades_territorial_command_id ON brigades (territorial_command_id);
CREATE INDEX idx_brigades_troop_type_id ON brigades (troop_type_id);
CREATE INDEX idx_brigades_location_id ON brigades (location_id);

-- ---------------------------------------------------------------------
-- Junction tables (many-to-many)
-- ---------------------------------------------------------------------

CREATE TABLE brigade_battles (
    brigade_id   INTEGER NOT NULL REFERENCES brigades (brigade_id),
    battle_id    INTEGER NOT NULL REFERENCES battles (battle_id),
    role         TEXT,
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
