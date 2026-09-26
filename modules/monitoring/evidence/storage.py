import os
from pathlib import Path
from uuid import uuid4

BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "inspection-evidence")
LOCAL_ROOT = Path(__file__).resolve().parents[1] / "data" / "uploads"
LOCAL_ROOT.mkdir(parents=True, exist_ok=True)

def upload_file(file_bytes: bytes, filename: str, content_type: str):
    """Uses Supabase Storage when configured; otherwise local storage keeps demo runnable."""
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
    safe_name = Path(filename).name.replace(" ", "_")
    object_path = f"{uuid4().hex}_{safe_name}"

    if supabase_url and supabase_key:
        from supabase import create_client
        client = create_client(supabase_url, supabase_key)
        client.storage.from_(BUCKET).upload(
            object_path, file_bytes, {"content-type": content_type, "upsert": "false"}
        )
        public_url = client.storage.from_(BUCKET).get_public_url(object_path)
        return object_path, public_url, "supabase"

    local_path = LOCAL_ROOT / object_path
    local_path.write_bytes(file_bytes)
    return str(local_path.relative_to(LOCAL_ROOT.parent.parent)), f"/uploads/{object_path}", "local-demo"
