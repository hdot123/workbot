-- Standardized Webhook Ingress Phase 1 schema for Supabase/PostgreSQL.
-- 1Password item: supabase-webhook数据库 (id: mgh2gmvw5w3kmjfhrcieoxfb54)
-- Project ref: rxrcidmnbyvwmhxqdgku

create extension if not exists pgcrypto;

create table if not exists public.webhook_raw_events (
    id bigserial primary key,
    event_id text not null unique,
    provider text not null,
    idempotency_key text not null,
    raw_body bytea not null,
    raw_body_sha256 text not null,
    raw_headers jsonb not null default '{}'::jsonb,
    request_path text not null,
    source_ip inet,
    received_at timestamptz not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_webhook_raw_events_provider
    on public.webhook_raw_events(provider);
create index if not exists idx_webhook_raw_events_idempotency
    on public.webhook_raw_events(idempotency_key);
create index if not exists idx_webhook_raw_events_sha
    on public.webhook_raw_events(raw_body_sha256);
create index if not exists idx_webhook_raw_events_received_at
    on public.webhook_raw_events(received_at desc);

create table if not exists public.webhook_canonical_events (
    id bigserial primary key,
    event_id text not null unique,
    canonical_version text not null default 'v1',
    provider text not null,
    provider_event_type text not null,
    provider_action text not null,
    provider_delivery_id text,
    canonical_type text not null,
    canonical_action text not null,
    event_timestamp timestamptz not null,
    received_at timestamptz not null,
    source_provider text not null,
    source_instance_url text,
    source_workspace_id text,
    source_resource_id text not null,
    source_resource_url text,
    actor_id text,
    actor_display_name text,
    actor_email text,
    payload jsonb not null default '{}'::jsonb,
    canonical_event jsonb not null,
    idempotency_key text not null unique,
    raw_body_sha256 text not null,
    n8n_forwarded smallint not null default 0,
    n8n_forwarded_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_webhook_canonical_provider_type
    on public.webhook_canonical_events(provider, canonical_type, canonical_action);
create index if not exists idx_webhook_canonical_idempotency
    on public.webhook_canonical_events(idempotency_key);
create index if not exists idx_webhook_canonical_resource
    on public.webhook_canonical_events(source_resource_id);
create index if not exists idx_webhook_canonical_received_at
    on public.webhook_canonical_events(received_at desc);

create table if not exists public.webhook_processing_logs (
    id bigserial primary key,
    event_id text,
    provider text not null,
    phase text not null,
    level text not null,
    message text not null,
    details jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_webhook_processing_logs_event
    on public.webhook_processing_logs(event_id);
create index if not exists idx_webhook_processing_logs_provider
    on public.webhook_processing_logs(provider);
create index if not exists idx_webhook_processing_logs_phase
    on public.webhook_processing_logs(phase);
create index if not exists idx_webhook_processing_logs_created_at
    on public.webhook_processing_logs(created_at desc);

create or replace function public.set_webhook_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_webhook_canonical_events_updated_at on public.webhook_canonical_events;
create trigger trg_webhook_canonical_events_updated_at
before update on public.webhook_canonical_events
for each row execute function public.set_webhook_updated_at();

alter table public.webhook_raw_events enable row level security;
alter table public.webhook_canonical_events enable row level security;
alter table public.webhook_processing_logs enable row level security;

-- No public anon policies are created. The ingress service should use the service_role key
-- or a dedicated server-side Postgres role, never the anon public key.
