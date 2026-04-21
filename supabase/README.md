# Supabase (Tirith sync)

## Prerequisites

- [Supabase CLI](https://supabase.com/docs/guides/cli)
- Project created on [supabase.com](https://supabase.com)

## Schema

Migration [`migrations/20260121000000_jobber_clients.sql`](migrations/20260121000000_jobber_clients.sql) creates `jobber_clients` with a JSON `snapshot` per Jobber client id.

## Apply database changes

```bash
cd supabase
supabase link --project-ref <YOUR_PROJECT_REF>
supabase db push
```

Or run the SQL file in the Supabase SQL editor.

## Edge Function: `sync-jobber-clients`

Deploy:

```bash
supabase secrets set SYNC_SECRET=<long-random-secret>
supabase functions deploy sync-jobber-clients --no-verify-jwt
```

(`--no-verify-jwt` is optional; the function checks `x-sync-secret` instead.)

Required function env (auto-injected by Supabase): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

## Manual test

```bash
curl -X POST "https://<PROJECT_REF>.supabase.co/functions/v1/sync-jobber-clients" \
  -H "Content-Type: application/json" \
  -H "x-sync-secret: YOUR_SYNC_SECRET" \
  -d '{"clients":[{"id":"test","name":"Demo","_pin":"red"}]}'
```

## Dashboard config

In `index.html`, set:

- `C.supabaseSyncUrl` — `https://<PROJECT_REF>.supabase.co/functions/v1/sync-jobber-clients`
- `C.syncSecret` — same value as `SYNC_SECRET` (do not commit real values)

Do not expose the **service role** key in the browser.
