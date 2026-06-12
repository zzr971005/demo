-- Fix missing database fields
-- Run this in PostgreSQL to add missing IC-related fields

-- Add IC fields to evolution_factors table
ALTER TABLE evolution_factors 
ADD COLUMN IF NOT EXISTS ic_mean_4h FLOAT,
ADD COLUMN IF NOT EXISTS ic_mean_24h FLOAT,
ADD COLUMN IF NOT EXISTS ic_mean_168h FLOAT,
ADD COLUMN IF NOT EXISTS ic_std FLOAT,
ADD COLUMN IF NOT EXISTS ic_ir FLOAT,
ADD COLUMN IF NOT EXISTS ic_half_life INTEGER,
ADD COLUMN IF NOT EXISTS factor_category VARCHAR(32),
ADD COLUMN IF NOT EXISTS is_selected_strategy BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS strategy_rank INTEGER;

-- Create index for is_selected_strategy
CREATE INDEX IF NOT EXISTS ix_evolution_factors_is_selected_strategy 
ON evolution_factors (is_selected_strategy);

-- Add IC fields to validation_pipeline_data table
ALTER TABLE validation_pipeline_data
ADD COLUMN IF NOT EXISTS ic_input INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS ic_output INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS ic_drop INTEGER DEFAULT 0;

-- Add IC fields to candidates table
ALTER TABLE candidates
ADD COLUMN IF NOT EXISTS ic_mean_4h FLOAT,
ADD COLUMN IF NOT EXISTS ic_mean_24h FLOAT,
ADD COLUMN IF NOT EXISTS ic_mean_168h FLOAT,
ADD COLUMN IF NOT EXISTS ic_std FLOAT,
ADD COLUMN IF NOT EXISTS ic_ir FLOAT,
ADD COLUMN IF NOT EXISTS ic_half_life INTEGER;
