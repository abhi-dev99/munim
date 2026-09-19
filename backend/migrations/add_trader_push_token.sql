-- Stores each trader's Expo push token (from mobile/App.tsx's
-- Notifications.getExpoPushTokenAsync(), forwarded to the web page via a
-- MUNIM_PUSH_TOKEN postMessage and registered through
-- POST /api/v1/dashboard/register-push-token). Nullable: most traders are
-- WhatsApp-only and will never have one, and every existing alert path
-- (deadline alerts, supplier health checks) already works via WhatsApp
-- regardless -- this is an additional delivery channel, not a replacement.

ALTER TABLE traders ADD COLUMN IF NOT EXISTS push_token TEXT;
