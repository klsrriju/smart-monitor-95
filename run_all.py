from __future__ import annotations
import subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
services=[
    ("portal", ROOT/"backend", "main:app", 8001),
    ("attendance", ROOT/"modules"/"attendance", "api:app", 8002),
    ("chatbot", ROOT/"modules"/"chatbot", "main:app", 8003),
    ("monitoring", ROOT/"modules"/"monitoring", "main:app", 8004),
]
procs=[]
for name,cwd,app,port in services:
    print(f"Starting {name} on {port}...")
    procs.append(subprocess.Popen([
        sys.executable,"-m","uvicorn",app,"--host","127.0.0.1","--port",str(port)
    ],cwd=str(cwd)))
print("Services running. Press Ctrl+C to stop.")
try:
    for p in procs: p.wait()
except KeyboardInterrupt:
    for p in procs:
        if p.poll() is None: p.terminate()
