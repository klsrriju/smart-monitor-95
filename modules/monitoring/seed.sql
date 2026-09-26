insert into projects(id,name,district,organization) values
('PS-26095','Community Skills Centre','Chennai','Sample Welfare Trust'),
('PS-26096','Rural Learning Hub','Kanchipuram','Sample Education NGO')
on conflict (id) do nothing;

insert into project_metrics(project_id,attendance_pct,capacity,people_detected,fund_utilization_pct,physical_progress_pct)
values
('PS-26095',62,25,31,80,55),
('PS-26096',91,40,35,52,60)
on conflict (project_id) do update set
attendance_pct=excluded.attendance_pct, capacity=excluded.capacity,
people_detected=excluded.people_detected, fund_utilization_pct=excluded.fund_utilization_pct,
physical_progress_pct=excluded.physical_progress_pct;
