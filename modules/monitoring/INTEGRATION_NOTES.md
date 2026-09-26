# Integration notes

1. `member4_frontend.html` is a copy of the supplied HTML with a new **Member 4 Monitoring** admin section.
2. Existing CCTV/YOLO sections are not changed.
3. Start the backend at `http://127.0.0.1:8000`.
4. Serve the HTML with `python -m http.server 5500`.
5. Login as Admin and open **Member 4 Monitoring**.
6. The UI calls only Member 4 endpoints:
   - inspections
   - evidence
   - anomalies
   - risk
   - reports
7. Later, the SmartMonitor integration can replace the sample metric inputs with values from CCTV/YOLO, face recognition/attendance and project finance services.
