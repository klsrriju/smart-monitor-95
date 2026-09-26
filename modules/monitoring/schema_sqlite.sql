create table if not exists projects(
 id text primary key, name text not null, district text, organization text, created_at text default current_timestamp
);
create table if not exists project_metrics(
 project_id text primary key, attendance_pct real not null, capacity integer not null,
 people_detected integer not null, fund_utilization_pct real not null,
 physical_progress_pct real not null, updated_at text default current_timestamp
);
create table if not exists inspections(
 id text primary key, project_id text not null, inspector_id text not null, date text not null,
 start_time text, end_time text, status text not null, checklist text default '[]',
 remarks text, latitude real, longitude real, created_at text, updated_at text
);
create table if not exists evidence(
 id text primary key, project_id text not null, inspection_id text not null, inspector_id text not null,
 file_path text not null, file_url text, file_type text not null, upload_time text,
 latitude real, longitude real, description text, verification_status text default 'PENDING',
 storage_backend text default 'local-demo'
);
create table if not exists anomalies(
 id integer primary key autoincrement, project_id text not null, anomaly_type text not null,
 severity text not null, title text not null, description text not null,
 detected_at text, status text default 'OPEN'
);
