# CCTV 10-minute recorded history

The V14 dashboard records the latest occupancy snapshot for each camera every 10 minutes in browser localStorage and renders it in the camera detail Recorded history table. Capacity falls back to the camera configuration so it is not shown as undefined.

This is a frontend/demo persistence layer. PostgreSQL can later persist the same snapshots centrally.
