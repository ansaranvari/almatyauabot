-- Add favorite locations feature
-- Migration: add_favorite_locations
-- Created: 2025-12-27

-- Create favorite_locations table
CREATE TABLE IF NOT EXISTS favorite_locations (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    location geography(POINT, 4326) NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_favorite_locations_user_id ON favorite_locations(user_id);
CREATE INDEX IF NOT EXISTS idx_favorite_locations_location ON favorite_locations USING GIST(location);

-- Add comment for table
COMMENT ON TABLE favorite_locations IS 'User saved favorite locations for quick air quality checks';
COMMENT ON COLUMN favorite_locations.name IS 'User-defined name for the location (e.g. "Home", "Work", "School")';
