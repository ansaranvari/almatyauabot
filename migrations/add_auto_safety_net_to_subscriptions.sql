-- Add auto_safety_net column to subscriptions table
-- This enables automatic creation of 4h safety net after clean air notifications

ALTER TABLE subscriptions
ADD COLUMN IF NOT EXISTS auto_safety_net BOOLEAN DEFAULT FALSE NOT NULL;

-- Update existing subscriptions to have the default value
UPDATE subscriptions
SET auto_safety_net = FALSE
WHERE auto_safety_net IS NULL;
