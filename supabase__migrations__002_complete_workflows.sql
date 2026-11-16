-- AdServiceBot production workflow expansion. Apply after 001_initial.sql.
create table if not exists public.telegram_sessions (
  telegram_user_id text primary key,
  chat_id text not null,
  state text not null default 'home',
  data jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);
create table if not exists public.support_tickets (
  id uuid primary key default gen_random_uuid(),
  ticket_number text not null unique default ('SUP-' || upper(substr(replace(gen_random_uuid()::text,'-',''),1,8))),
  customer_id uuid references public.profiles(id),
  telegram_user_id text,
  subject text not null,
  status text not null default 'open' check(status in ('open','answered','closed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.support_messages (
  id uuid primary key default gen_random_uuid(),
  ticket_id uuid not null references public.support_tickets(id) on delete cascade,
  sender_type text not null check(sender_type in ('customer','admin')),
  sender_id text,
  body text not null,
  created_at timestamptz not null default now()
);
create table if not exists public.app_settings (
  key text primary key,
  value jsonb not null default '{}'::jsonb,
  updated_by uuid references public.profiles(id),
  updated_at timestamptz not null default now()
);
alter table public.products add column if not exists product_type text;
alter table public.products add column if not exists form_schema jsonb not null default '{}'::jsonb;
alter table public.packages add column if not exists sort_order integer not null default 0;
alter table public.orders add column if not exists completed_at timestamptz;
alter table public.orders add column if not exists package_snapshot jsonb not null default '{}'::jsonb;
alter table public.orders add column if not exists telegram_user_id text;
alter table public.orders add column if not exists updated_at timestamptz not null default now();
alter table public.payment_submissions add column if not exists expected_amount numeric(18,6);
alter table public.payment_submissions add column if not exists payment_method_snapshot jsonb not null default '{}'::jsonb;
alter table public.crypto_methods add column if not exists sort_order integer not null default 0;
alter table public.crypto_methods add column if not exists minimum_amount numeric(18,6);
alter table public.crypto_methods add column if not exists maximum_amount numeric(18,6);
alter table public.telegram_sessions enable row level security;
alter table public.support_tickets enable row level security;
alter table public.support_messages enable row level security;
alter table public.app_settings enable row level security;
-- Sessions are service-role only. Customers can only read their own tickets through their profile.
create policy "tickets customer or support admin read" on public.support_tickets for select to authenticated
using (customer_id=auth.uid() or public.has_permission('support_read'));
create policy "ticket messages customer or support admin read" on public.support_messages for select to authenticated
using (exists(select 1 from public.support_tickets t where t.id=ticket_id and (t.customer_id=auth.uid() or public.has_permission('support_read'))));
create policy "settings privileged read" on public.app_settings for select to authenticated
using (public.has_permission('technical_read') or public.has_permission('settings_read'));
-- Correct product typing for the four seeded products.
update public.products set product_type='force_join' where slug like '%force-join%';
update public.products set product_type='banner_24h' where slug like '%banner-24h%';
-- Public catalog only exposes active records; privileged writes are server-side.
drop policy if exists "catalog public read" on public.categories;
create policy "active categories readable" on public.categories for select to anon,authenticated using (active);
drop policy if exists "products public read" on public.products;
create policy "active products readable" on public.products for select to anon,authenticated using (active);
drop policy if exists "packages public read" on public.packages;
create policy "active packages readable" on public.packages for select to anon,authenticated using (active);
-- No direct client mutation of privileged records.
create index if not exists orders_created_at_idx on public.orders(created_at desc);
create index if not exists orders_status_idx on public.orders(status);
create index if not exists payments_status_idx on public.payment_submissions(status);
create index if not exists packages_product_active_idx on public.packages(product_id,active,sort_order);
create index if not exists support_tickets_status_idx on public.support_tickets(status,created_at desc);
-- Telegram-first customers may not have a dashboard Auth account yet.
alter table public.orders alter column customer_id drop not null;
alter table public.payment_submissions alter column customer_id drop not null;
-- Service role handles Telegram records; clients still cannot write privileged states.
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$ begin new.updated_at=now(); return new; end $$;
drop trigger if exists orders_touch_updated_at on public.orders;
create trigger orders_touch_updated_at before update on public.orders for each row execute function public.touch_updated_at();
drop trigger if exists support_tickets_touch_updated_at on public.support_tickets;
create trigger support_tickets_touch_updated_at before update on public.support_tickets for each row execute function public.touch_updated_at();
-- Automatically create a least-privilege customer profile after email signup.
create or replace function public.handle_new_auth_user()
returns trigger language plpgsql security definer set search_path=public
as $$ begin
  insert into public.profiles(id,display_name,role,permissions)
  values(new.id,coalesce(new.raw_user_meta_data->>'display_name',split_part(new.email,'@',1)),'customer','{}'::jsonb)
  on conflict(id) do nothing;
  return new;
end $$;
drop trigger if exists on_auth_user_created_profile on auth.users;
create trigger on_auth_user_created_profile after insert on auth.users
for each row execute procedure public.handle_new_auth_user();
-- Private bucket for advertising assets and payment receipts.
insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
values('ad-assets','ad-assets',false,10485760,array['image/jpeg','image/png','image/webp'])
on conflict(id) do nothing;
-- Fix the original seed's non-unique slugs and ensure all four category/product pairs exist.
update public.products p set slug=c.slug || '-' || p.slug
from public.categories c where p.category_id=c.id and p.slug in ('force-join','banner-24h');
insert into public.products(category_id,name,slug,product_type,sort_order)
select c.id,x.name,c.slug || '-' || x.slug,x.product_type,x.sort_order
from public.categories c cross join (values
 ('جوین اجباری','force-join','force_join',1),
 ('بنر ۲۴ ساعته','banner-24h','banner_24h',2)
) as x(name,slug,product_type,sort_order)
where c.slug in ('group-advertising','channel-advertising')
 and not exists(select 1 from public.products p where p.category_id=c.id and p.product_type=x.product_type);
update public.products set product_type=case when slug like '%force-join%' then 'force_join' when slug like '%banner-24h%' then 'banner_24h' else product_type end;
