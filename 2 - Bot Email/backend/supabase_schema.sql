-- Run this in Supabase SQL Editor: supabase.com → seu projeto → SQL Editor

create table if not exists unsubscribes (
  id            uuid        default gen_random_uuid() primary key,
  email_id      text        not null,
  sender        text        not null,
  subject       text,
  unsubscribe_url text,
  status        text        not null check (status in ('success', 'failed', 'skipped_mailto_only', 'skipped_already_done')),
  status_code   integer,
  error_message text,
  created_at    timestamptz default now()
);

-- Index para evitar duplicatas de remetente
create index if not exists idx_unsubscribes_sender on unsubscribes (sender);
create index if not exists idx_unsubscribes_created_at on unsubscribes (created_at desc);

-- Row Level Security (opcional mas recomendado)
alter table unsubscribes enable row level security;

-- Permite tudo via service_role key (usada pelo backend)
create policy "service role full access"
  on unsubscribes
  using (true)
  with check (true);
