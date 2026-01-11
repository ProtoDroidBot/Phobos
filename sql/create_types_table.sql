-- Create types lookup table for EVE Online type data
-- This table provides fast ID to name lookups and includes common type attributes

CREATE TABLE IF NOT EXISTS types (
    typeID INTEGER PRIMARY KEY,
    typeName TEXT NOT NULL,
    groupID INTEGER,
    description TEXT,
    published INTEGER,
    mass REAL,
    volume REAL,
    capacity REAL,
    portionSize INTEGER,
    basePrice REAL,
    marketGroupID INTEGER,
    iconID INTEGER,
    soundID INTEGER,
    graphicID INTEGER
);

-- Indexes for common lookups
CREATE INDEX IF NOT EXISTS idx_types_name ON types(typeName);
CREATE INDEX IF NOT EXISTS idx_types_groupID ON types(groupID);
CREATE INDEX IF NOT EXISTS idx_types_marketGroupID ON types(marketGroupID);

-- Example queries:
-- 
-- Lookup type by ID:
--   SELECT typeName FROM types WHERE typeID = 34;
--
-- Find types by name:
--   SELECT typeID, typeName FROM types WHERE typeName LIKE '%Tritanium%';
--
-- Get all published types in a group:
--   SELECT typeID, typeName FROM types WHERE groupID = 18 AND published = 1;
--
-- Get market items:
--   SELECT typeID, typeName, basePrice FROM types WHERE marketGroupID IS NOT NULL;
