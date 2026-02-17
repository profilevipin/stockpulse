# Adding Users to StockPulse

## Finding Your Telegram User ID

1. Message @userinfobot on Telegram
2. It replies with your numeric user ID (e.g., `123456789`)

## Adding User 1 (Kite Provider)

```sql
-- Connect to database
docker exec -it stockpulse-db psql -U stockpulse -d stockpulse

-- Add User 1 (with Kite Connect)
INSERT INTO users (telegram_user_id, display_name, is_kite_provider, is_admin, private_chat_id)
VALUES (123456789, 'Your Name', true, true, 123456789);
```

The `private_chat_id` is usually the same as `telegram_user_id` for direct messages.

## Adding User 2 (No Kite)

```sql
INSERT INTO users (telegram_user_id, display_name, is_kite_provider, is_admin, private_chat_id)
VALUES (987654321, 'Friend Name', false, false, 987654321);
```

## If Using Telegram Groups/Topics

After creating the group and adding the bot:

```sql
-- Update with group chat IDs
UPDATE users SET
    alerts_chat_id = -1001234567890,    -- Group/topic chat ID
    commands_chat_id = -1001234567890
WHERE telegram_user_id = 123456789;
```

For topics, store topic IDs in settings:
```sql
UPDATE users SET settings = jsonb_set(
    settings, '{topic_ids}',
    '{"alerts": 2, "briefings": 4, "commands": 6}'::jsonb
) WHERE telegram_user_id = 123456789;
```

## Removing a User

```sql
UPDATE users SET is_active = false WHERE telegram_user_id = 987654321;
```

## Checking Users

```sql
SELECT id, telegram_user_id, display_name, is_kite_provider, is_active FROM users;
```
