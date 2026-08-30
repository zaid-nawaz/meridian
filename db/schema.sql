PRAGMA foreign_keys = ON;


-- ============================================================
-- VEHICLES
-- ============================================================

CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id TEXT PRIMARY KEY,

    registration_number TEXT NOT NULL UNIQUE,
    normalized_registration TEXT NOT NULL UNIQUE,

    model TEXT,
    model_year INTEGER,

    bs_stage TEXT,
    engine_heater TEXT,

    home_hub TEXT,
    capacity_tonnes REAL,

    status TEXT,

    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- DRIVERS
-- ============================================================

CREATE TABLE IF NOT EXISTS drivers (
    driver_id TEXT PRIMARY KEY,

    driver_name TEXT NOT NULL,

    phone TEXT,
    dl_number TEXT,
    aadhaar TEXT,

    joining_date TEXT,
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
    trip_id TEXT PRIMARY KEY,

    created_at TEXT,

    route_type TEXT,

    origin_center TEXT,
    origin_name TEXT,

    dest_center TEXT,
    dest_name TEXT,

    dispatch_time TEXT,
    delivery_time TEXT,

    osrm_distance_km REAL,
    osrm_time_min REAL,
    actual_time_min REAL,

    vehicle_reg TEXT NOT NULL,
    normalized_vehicle_reg TEXT NOT NULL,

    vehicle_id TEXT,

    driver_id TEXT,

    client TEXT,
    normalized_client TEXT,

    status TEXT,

    billed_amount REAL,

    created_at_db TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (vehicle_id)
        REFERENCES vehicles(vehicle_id),

    FOREIGN KEY (driver_id)
        REFERENCES drivers(driver_id)
);


-- ============================================================
-- MAINTENANCE EVENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS maintenance_events (
    maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,

    service_date TEXT,

    vehicle_reg TEXT NOT NULL,
    normalized_vehicle_reg TEXT NOT NULL,

    vehicle_id TEXT,

    odometer_km REAL,

    mechanic TEXT,

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