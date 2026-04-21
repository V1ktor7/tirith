-- Full client snapshots from Tirith dashboard (merged + enriched Jobber rows)

create table if not exists public.jobber_clients (
  jobber_client_id text primary key,
  snapshot jsonb not null,
  updated_at timestamptz not null default now(),
  source_last_updated timestamptz
);

comment on table public.jobber_clients is 'One row per Jobber client id; snapshot holds full enriched CLIENT object from Tirith index.html';

create index if not exists idx_jobber_clients_snapshot_gin on public.jobber_clients using gin (snapshot);

alter table public.jobber_clients enable row level security;

-- Edge Function uses service role (bypasses RLS). No public policies.
