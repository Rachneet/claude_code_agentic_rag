-- ============================================
-- Module 1: Initial Schema
-- Run this in Supabase SQL Editor
-- ============================================

-- Threads table
create table public.threads (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users(id) on delete cascade not null,
  title text not null default 'New Chat',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- Messages table
create table public.messages (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid references public.threads(id) on delete cascade not null,
  user_id uuid references auth.users(id) on delete cascade not null,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  created_at timestamptz default now()
);

-- Indexes
create index idx_threads_user_id on public.threads(user_id);
create index idx_threads_updated_at on public.threads(updated_at desc);
create index idx_messages_thread_id on public.messages(thread_id);
create index idx_messages_created_at on public.messages(created_at);

-- RLS: Threads
alter table public.threads enable row level security;

create policy "Users can select own threads"
  on public.threads for select using (auth.uid() = user_id);
create policy "Users can insert own threads"
  on public.threads for insert with check (auth.uid() = user_id);
create policy "Users can update own threads"
  on public.threads for update using (auth.uid() = user_id);
create policy "Users can delete own threads"
  on public.threads for delete using (auth.uid() = user_id);

-- RLS: Messages
alter table public.messages enable row level security;

create policy "Users can select own messages"
  on public.messages for select using (auth.uid() = user_id);
create policy "Users can insert own messages"
  on public.messages for insert with check (auth.uid() = user_id);
create policy "Users can update own messages"
  on public.messages for update using (auth.uid() = user_id);
create policy "Users can delete own messages"
  on public.messages for delete using (auth.uid() = user_id);

-- Auto-update updated_at on threads
create or replace function public.update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger set_threads_updated_at
  before update on public.threads
  for each row execute function public.update_updated_at_column();
