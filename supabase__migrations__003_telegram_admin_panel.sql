-- Telegram-first admin panel additions. Additive and safe to re-run.
create table if not exists public.app_settings (
  key text primary key,
  value jsonb not null default '{}'::jsonb,
  updated_by uuid references public.profiles(id),
  updated_at timestamptz not null default now()
);

create table if not exists public.premium_emojis (
  key text primary key,
  emoji_id text not null check (emoji_id ~ '^[0-9]{5,25}$'),
  fallback text not null default '✨',
  description text,
  active boolean not null default true,
  updated_at timestamptz not null default now()
);

grant all on public.app_settings to service_role;
grant all on public.premium_emojis to service_role;
alter table public.app_settings enable row level security;
alter table public.premium_emojis enable row level security;

do $$ begin
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='app_settings' and policyname='settings privileged read') then
    create policy "settings privileged read" on public.app_settings for select to authenticated
      using (public.has_permission('technical_read') or public.has_permission('settings_read'));
  end if;
  if not exists (select 1 from pg_policies where schemaname='public' and tablename='premium_emojis' and policyname='emojis privileged read') then
    create policy "emojis privileged read" on public.premium_emojis for select to authenticated
      using (public.has_permission('technical_read') or public.has_permission('settings_read'));
  end if;
end $$;

alter table public.support_tickets add column if not exists chat_id text;
alter table public.products add column if not exists product_type text;
alter table public.products add column if not exists form_schema jsonb not null default '{}'::jsonb;
alter table public.packages add column if not exists sort_order integer not null default 0;
alter table public.orders add column if not exists telegram_user_id text;
alter table public.orders add column if not exists telegram_chat_id text;
alter table public.orders add column if not exists completed_at timestamptz;
alter table public.orders add column if not exists package_snapshot jsonb not null default '{}'::jsonb;
alter table public.payment_submissions add column if not exists expected_amount numeric(18,6);
alter table public.payment_submissions add column if not exists payment_method_snapshot jsonb not null default '{}'::jsonb;
alter table public.crypto_methods add column if not exists sort_order integer not null default 0;
alter table public.orders alter column customer_id drop not null;
alter table public.payment_submissions alter column customer_id drop not null;

create index if not exists orders_telegram_user_idx on public.orders(telegram_user_id);
create index if not exists support_tickets_status_created_idx on public.support_tickets(status, created_at desc);
create index if not exists payment_submissions_status_created_idx on public.payment_submissions(status, created_at desc);
