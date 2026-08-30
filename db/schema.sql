PRAGMA foreign_keys = ON;


-- ============================================================
-- VEHICLES
-- ============================================================

CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,

    registration_number TEXT NOT NULL UNIQUE,
    normalized_registration TEXT NOT NULL UNIQUE,

    model TEXT,
    model_year INTEGER,

    home_hub TEXT,

    status TEXT DEFAULT 'active',

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- DRIVERS
-- ============================================================

CREATE TABLE IF NOT EXISTS drivers (
    driver_id INTEGER PRIMARY KEY AUTOINCREMENT,

    driver_name TEXT NOT NULL,

    phone TEXT,
    dl_number TEXT,
    aadhaar TEXT,

    tenure_months REAL,

    home_hub TEXT,

    status TEXT DEFAULT 'active',

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- CLIENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS clients (
    client_id INTEGER PRIMARY KEY AUTOINCREMENT,

    name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,

    sla_hours REAL,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- TRIPS
-- ============================================================

CREATE TABLE IF NOT EXISTS trips (
    trip_id INTEGER PRIMARY KEY AUTOINCREMENT,

    vehicle_id INTEGER,

    vehicle_reg TEXT NOT NULL,
    normalized_vehicle_reg TEXT NOT NULL,

    client_id INTEGER,

    client TEXT,
    normalized_client TEXT,

    origin_hub TEXT,
    destination TEXT,

    departure_time TEXT,
    arrival_time TEXT,

    status TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (vehicle_id)
        REFERENCES vehicles(vehicle_id),

    FOREIGN KEY (client_id)
        REFERENCES clients(client_id)
);


-- ============================================================
-- MAINTENANCE EVENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS maintenance_events (
    maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,

    vehicle_id INTEGER,

    vehicle_reg TEXT NOT NULL,
    normalized_vehicle_reg TEXT NOT NULL,

    service_date TEXT,

    maintenance_type TEXT,

    note TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (vehicle_id)
        REFERENCES vehicles(vehicle_id)
);


-- ============================================================
-- ENTITY ALIASES
-- ============================================================

CREATE TABLE IF NOT EXISTS entity_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,

    entity_type TEXT NOT NULL,

    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,

    canonical_value TEXT NOT NULL,

    UNIQUE(entity_type, normalized_alias)
);


-- ============================================================
-- RULES
-- ============================================================

CREATE TABLE IF NOT EXISTS rules (
    rule_id TEXT PRIMARY KEY,

    description TEXT NOT NULL,

    rule_type TEXT,

    enabled INTEGER DEFAULT 1,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- PIPELINE IDEMPOTENCY LEDGER
-- ============================================================

CREATE TABLE IF NOT EXISTS pipeline_state (
    ticket_id TEXT PRIMARY KEY,

    content_hash TEXT NOT NULL,

    status TEXT NOT NULL,

    work_order_id TEXT,

    notification_id TEXT,

    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_vehicles_normalized_registration
ON vehicles(normalized_registration);


CREATE INDEX IF NOT EXISTS idx_drivers_name
ON drivers(driver_name);


CREATE INDEX IF NOT EXISTS idx_trips_vehicle
ON trips(normalized_vehicle_reg);


CREATE INDEX IF NOT EXISTS idx_trips_client
ON trips(normalized_client);


CREATE INDEX IF NOT EXISTS idx_maintenance_vehicle
ON maintenance_events(normalized_vehicle_reg);


CREATE INDEX IF NOT EXISTS idx_aliases_lookup
ON entity_aliases(entity_type, normalized_alias);