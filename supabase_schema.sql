-- Cole no SQL Editor do Supabase e clique em Run

-- Tokens OAuth (substitui o token.json — necessário para Vercel stateless)
create table if not exists tokens (
  id           uuid        default gen_random_uuid() primary key,
  user_id      text        not null unique default 'default',
  token        text,
  refresh_token text,
  token_uri    text,
  client_id    text,
  client_secret text,
  scopes       text[],
  updated_at   timestamptz default now()
);

-- Histórico de descadastros
create table if not exists unsubscribes (
  id              uuid        default gen_random_uuid() primary key,
  email_id        text        not null,
  sender          text        not null,
  subject         text,
  unsubscribe_url text,
  status          text        not null,
  status_code     integer,
  error_message   text,
  created_at      timestamptz default now()
);

create index if not exists idx_unsubscribes_sender     on unsubscribes (sender);
create index if not exists idx_unsubscribes_created_at on unsubscribes (created_at desc);
