import subprocess, json, os, datetime

SSH = r"C:\Windows\System32\OpenSSH\ssh.exe"
KEY = r"D:\id_ed25519"
HOST = "ubuntu@43.134.236.80"
REMOTE_DIR = "/home/ubuntu/fstdd-notices/FSTDD003/"
OUT = r"D:\FSTDD003\.fstdd\_daemon_tmp"

# Use find -printf with TAB delimiter to safely handle filenames with spaces
cmd = [SSH, "-i", KEY, "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=25",
       HOST, "find " + REMOTE_DIR + " -maxdepth 1 -type f -printf '%T+\\t%f\\n'"]
p = subprocess.run(cmd, capture_output=True)
raw = p.stdout.decode("utf-8", "replace")
err = p.stderr.decode("utf-8", "replace").strip()

recs = []
for line in raw.split("\n"):
    if not line:
        continue
    idx = line.find("\t")
    if idx >= 0:
        recs.append({"mtime": line[:idx], "name": line[idx+1:]})
    else:
        recs.append({"mtime": "", "name": line})

res = {
    "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "exit": p.returncode,
    "count": len(recs),
    "err": err[:500],
    "files": sorted(recs, key=lambda r: r["name"]),
}
with open(os.path.join(OUT, "server_state.json"), "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=True, indent=1)
print("DONE exit=%s count=%d" % (p.returncode, len(recs)))
