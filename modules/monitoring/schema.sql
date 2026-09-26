-- Supabase/PostgreSQL schema for production.
create table if not exists projects (
  id text primary key,
  name text not null,
  district text,
  organization text,
  created_at timestamptz default now()
);

create table if not exists project_metrics (
  project_id text primary key references projects(id) on delete cascade,
  attendance_pct numeric not null default 0,
  capacity integer not null default 0,
  people_detected integer not null default 0,
  fund_utilization_pct numeric not null default 0,
  physical_progress_pct numeric not null default 0,
  updated_at timestamptz default now()
);

create table if not exists inspections (
  id text primary key,
  project_id text not null references projects(id) on delete cascade,
  inspector_id text not null,
  date date not null,
  start_time time,
  end_time time,
  status text not null check (status in ('SCHEDULED','IN_PROGRESS','COMPLETED','CANCELLED')),
  checklist jsonb default '[]'::jsonb,
  remarks text,
  latitude double precision,
  longitude double precision,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists evidence (
  id text primary key,
  project_id text not null references projects(id) on delete cascade,
  inspection_id text not null references inspections(id) on delete cascade,
  inspector_id text not null,
  file_path text not null,
  file_url text,
  file_type text not null,
  upload_time timestamptz default now(),
  latitude double precision,
  longitude double precision,
  description text,
  verification_status text not null default 'PENDING'
    check (verification_status in ('PENDING','VERIFIED','REJECTED')),
  storage_backend text default 'supabase'
);

create table if not exists anomalies (
  id bigint generated always as identity primary key,
  project_id text not null references projects(id) on delete cascade,
  anomaly_type text not null,
  severity text not null check (severity in ('LOW','MEDIUM','HIGH')),
  title text not null,
  description text not null,
  detected_at timestamptz default now(),
  status text not null default 'OPEN'
);

create index if not exists idx_inspections_project on inspections(project_id);
create index if not exists idx_evidence_project on evidence(project_id);
create index if not exists idx_anomalies_project on anomalies(project_id);

-- Supabase Storage bucket. Create it from the dashboard if this statement
-- is not enabled for your project:
-- Bucket name: inspection-evidence
-- Recommended: private bucket + signed URLs.
