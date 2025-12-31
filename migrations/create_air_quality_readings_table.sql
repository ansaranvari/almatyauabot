-- Create air_quality_readings table for storing historical data
CREATE TABLE IF NOT EXISTS air_quality_readings (
    id BIGSERIAL PRIMARY KEY,
    station_id VARCHAR(255) NOT NULL,
    pm25 DOUBLE PRECISION,
    pm10 DOUBLE PRECISION,
    pm1 DOUBLE PRECISION,
    aqi INTEGER,
    temperature DOUBLE PRECISION,
    humidity DOUBLE PRECISION,
    measured_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_air_quality_readings_station_id ON air_quality_readings(station_id);
CREATE INDEX IF NOT EXISTS idx_air_quality_readings_measured_at ON air_quality_readings(measured_at);
CREATE INDEX IF NOT EXISTS idx_air_quality_readings_station_measured ON air_quality_readings(station_id, measured_at DESC);

-- Add comment
COMMENT ON TABLE air_quality_readings IS 'Historical air quality readings for trend analysis and charts';
