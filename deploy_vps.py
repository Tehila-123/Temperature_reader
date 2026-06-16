#!/usr/bin/env python3
"""
VPS Deployment Script (No-sudo version)
Uploads dashboard.html and starts a Python HTTP server on port 8265.
"""

import os
import sys
import time
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

import paramiko
from pathlib import Path

# --- VPS CREDENTIALS ----------------------------------------------------------
VPS_HOST = "157.173.101.159"
VPS_PORT = 22
VPS_USER = "user265"
VPS_PASS = "!MZ2Q9@R"

# --- LOCAL FILES --------------------------------------------------------------
SCRIPT_DIR   = Path(__file__).parent
DASHBOARD_HTML = SCRIPT_DIR / "Dashboard" / "dashboard.html"

# --- REMOTE SETTINGS ----------------------------------------------------------
HTTP_PORT    = 8265                     # Try 8265; fallback 9265 if blocked
REMOTE_DIR   = f"/home/{VPS_USER}/tehila"
REMOTE_HTML  = f"{REMOTE_DIR}/index.html"

# --- HELPERS ------------------------------------------------------------------
def run(ssh, cmd, check=False):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if err and check:
        print(f"  [WARN] {err[:300]}")
    return out

def main():
    print("=" * 60)
    print("  [*] Tehila Dashboard - VPS Deployment (port {})".format(HTTP_PORT))
    print("=" * 60)

    # 1. Validate local file
    if not DASHBOARD_HTML.exists():
        print(f"[ERROR] Could not find: {DASHBOARD_HTML}")
        sys.exit(1)
    print(f"[OK] dashboard.html found ({DASHBOARD_HTML.stat().st_size} bytes)")

    # 2. SSH connect
    print(f"\n[->] Connecting to {VPS_USER}@{VPS_HOST}:{VPS_PORT} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(VPS_HOST, port=VPS_PORT, username=VPS_USER,
                    password=VPS_PASS, timeout=20)
        print("[OK] SSH connected.")
    except Exception as e:
        print(f"[ERROR] SSH failed: {e}")
        sys.exit(1)

    # 3. Create remote directory (no sudo needed in home dir)
    print(f"\n[->] Creating remote directory: {REMOTE_DIR}")
    run(ssh, f"mkdir -p {REMOTE_DIR}")
    print(f"[OK] Directory ready.")

    # 4. Upload dashboard.html via SFTP (directly to home dir - no sudo needed)
    print(f"[->] Uploading dashboard.html -> {REMOTE_HTML}")
    sftp = ssh.open_sftp()
    try:
        sftp.put(str(DASHBOARD_HTML), REMOTE_HTML)
        print(f"[OK] Upload complete.")
    except Exception as e:
        print(f"[ERROR] SFTP upload failed: {e}")
        sftp.close()
        ssh.close()
        sys.exit(1)
    finally:
        sftp.close()

    # 5. Kill any previous Python HTTP server on our port
    print(f"\n[->] Stopping any existing server on port {HTTP_PORT} ...")
    run(ssh, f"fuser -k {HTTP_PORT}/tcp 2>/dev/null || true")
    run(ssh, f"pkill -f 'python.*{HTTP_PORT}' 2>/dev/null || true")
    time.sleep(1)

    # 6. Start Python HTTP server in the background (persists after SSH closes)
    start_cmd = (
        f"nohup python3 -m http.server {HTTP_PORT} "
        f"--directory {REMOTE_DIR} "
        f"> /tmp/tehila_server.log 2>&1 &"
    )
    print(f"[->] Starting Python HTTP server on port {HTTP_PORT} ...")
    run(ssh, start_cmd)
    time.sleep(3)  # Give server time to start

    # 7. Verify server is running
    print(f"[->] Verifying server ...")
    pid = run(ssh, f"pgrep -f 'python.*{HTTP_PORT}' | head -1")
    if pid:
        print(f"[OK] Server is running (PID {pid})")
    else:
        print("[WARN] Could not confirm server PID. Checking port ...")

    curl_code = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' http://localhost:{HTTP_PORT}/")
    print(f"[OK] HTTP status from VPS localhost:{HTTP_PORT} -> {curl_code}")

    # 8. Also try port 9265 as a backup (run a second server)
    backup_port = 9265
    print(f"\n[->] Also starting backup server on port {backup_port} ...")
    run(ssh, f"fuser -k {backup_port}/tcp 2>/dev/null || true")
    backup_cmd = (
        f"nohup python3 -m http.server {backup_port} "
        f"--directory {REMOTE_DIR} "
        f"> /tmp/tehila_server_backup.log 2>&1 &"
    )
    run(ssh, backup_cmd)
    time.sleep(2)

    ssh.close()

    # 9. Print results
    primary_url = f"http://{VPS_HOST}:{HTTP_PORT}/"
    backup_url  = f"http://{VPS_HOST}:{backup_port}/"
    print("\n" + "=" * 60)
    print("  DEPLOYMENT COMPLETE!")
    print("=" * 60)
    print(f"\n  Primary Dashboard URL (port {HTTP_PORT}):")
    print(f"      {primary_url}")
    print(f"\n  Backup Dashboard URL (port {backup_port}):")
    print(f"      {backup_url}")
    print("\n  Try the primary link first. If it does not open,")
    print("  use the backup link.")
    print("=" * 60)

if __name__ == "__main__":
    main()
