create extension if not exists pgcrypto;

create type public.app_role as enum ('owner','developer','admin','customer');
create type public.order_status as enum ('awaiting_payment','payment_submitted','payment_under_review','payment_rejected','paid','queued','in_progress','completed','cancelled');
create type public.payment_status as enum ('not_submitted','submitted','under_review','approved','rejected');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  telegram_id text unique,
  display_name text,
  role public.app_role not null default 'customer',
  permissions jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.categories (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  slug text not null unique,
  active boolean not null default true,
  sort_order int not null default 0,
  created_at timestamptz not null default now()
);

create table public.products (
  id uuid primary key default gen_random_uuid(),
  category_id uuid not null references public.categories(id),
  name text not null,
  slug text not null unique,
  description text,
  active boolean not null default true,
  sort_order int not null default 0,
  created_at timestamptz not null default now()
);

create table public.packages (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references public.products(id) on delete cascade,
  title text not null,
  description text,
  price numeric(18,6) not null check(price >= 0),
  currency text not null,
  duration_hours int,
  conditions jsonb not null default '{}'::jsonb,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table public.crypto_methods (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  currency_code text not null,
  network text not null,
  wallet_address text not null,
  instructions text,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table public.orders (
  id uuid primary key default gen_random_uuid(),
  order_number text not null unique default ('ADS-' || upper(substr(replace(gen_random_uuid()::text,'-',''),1,10))),
  customer_id uuid not null references public.profiles(id),
  category text not null,
  product text not null,
  package_id uuid references public.packages(id),
  order_details jsonb not null default '{}'::jsonb,
  total_amount numeric(18,6),
  currency text,
  status public.order_status not null default 'awaiting_payment',
  payment_state public.payment_status not null default 'not_submitted',
  scheduled_start timestamptz,
  scheduled_end timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.payment_submissions (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.orders(id) on delete cascade,
  customer_id uuid not null references public.profiles(id),
  crypto_method_id uuid references public.crypto_methods(id),
  txid text not null,
  receipt_path text,
  status public.payment_status not null default 'submitted',
  reviewed_by uuid references public.profiles(id),
  review_note text,
  reviewed_at timestamptz,
  created_at timestamptz not null default now()
);

create table public.order_status_history (
  id uuid primary key default gen_random_uuid(),
  order_id uuid not null references public.orders(id) on delete cascade,
  old_status public.order_status,
  new_status public.order_status not null,
  changed_by uuid references public.profiles(id),
  note text,
  created_at timestamptz not null default now()
);

create table public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references public.profiles(id),
  action text not null,
  target_type text,
  target_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

insert into public.categories(name,slug,sort_order) values
 ('تبلیغات گروه','group-advertising',1),('تبلیغات چنل','channel-advertising',2)
on conflict(slug) do nothing;

insert into public.products(category_id,name,slug,sort_order)
select c.id,p.name,p.slug,p.sort_order
from public.categories c
cross join (values
 ('جوین اجباری','force-join',1),
 ('بنر ۲۴ ساعته','banner-24h',2)
) as p(name,slug,sort_order)
where c.slug in ('group-advertising','channel-advertising')
on conflict(slug) do nothing;

alter table public.profiles enable row level security;
alter table public.categories enable row level security;
alter table public.products enable row level security;
alter table public.packages enable row level security;
alter table public.crypto_methods enable row level security;
alter table public.orders enable row level security;
alter table public.payment_submissions enable row level security;
alter table public.order_status_history enable row level security;
alter table public.audit_logs enable row level security;

create or replace function public.current_role()
returns public.app_role language sql stable security definer set search_path=public
as $$ select role from public.profiles where id=auth.uid() $$;

create or replace function public.has_permission(permission_name text)
returns boolean language sql stable security definer set search_path=public
as $$
 select coalesce(
   (select role='owner' or (role='admin' and permissions->>permission_name='true')
    or (role='developer' and permission_name in ('technical_read','technical_settings'))
    from public.profiles where id=auth.uid()), false)
$$;

create policy "profiles self or privileged read" on public.profiles for select to authenticated
using (id=auth.uid() or public.has_permission('users_read'));
create policy "catalog public read" on public.categories for select to anon,authenticated using (active or auth.uid() is not null);
create policy "products public read" on public.products for select to anon,authenticated using (active or auth.uid() is not null);
create policy "packages public read" on public.packages for select to anon,authenticated using (active or auth.uid() is not null);
create policy "crypto methods authenticated read" on public.crypto_methods for select to authenticated using (active);
create policy "orders customer or privileged read" on public.orders for select to authenticated
using (customer_id=auth.uid() or public.has_permission('orders_read'));
create policy "orders customer create" on public.orders for insert to authenticated
with check (customer_id=auth.uid());
create policy "payment own or privileged read" on public.payment_submissions for select to authenticated
using (customer_id=auth.uid() or public.has_permission('payments_review'));
create policy "payment own create" on public.payment_submissions for insert to authenticated
with check (customer_id=auth.uid());
create policy "history own order read" on public.order_status_history for select to authenticated
using (exists(select 1 from public.orders o where o.id=order_id and (o.customer_id=auth.uid() or public.has_permission('orders_read'))));
create policy "audit privileged read" on public.audit_logs for select to authenticated
using (public.has_permission('audit_read'));

-- Privileged writes should be performed through Edge Functions using the service role,
-- with explicit permission checks and audit logging. Never expose service-role credentials.
