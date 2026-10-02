import os, json, datetime
LOCAL = r"D:\FSTDD003\.fstdd\_notices\FSTDD003"
STATE = r"D:\FSTDD003\.fstdd\_daemon_tmp\server_state.json"

st = json.load(open(STATE, encoding="utf-8"))
server_names = set(f["name"] for f in st["files"])
local_files = sorted(os.listdir(LOCAL))
local_names = set(local_files)

recv_local = sorted(f for f in local_files if f.startswith("FSTDD003收-"))
resp_local = sorted(f for f in local_files if f.startswith("FSTDD003复-"))

# Show mtime for local files
mtimes = []
for f in sorted(local_files):
    fp = os.path.join(LOCAL, f)
    m = os.path.getmtime(fp)
    mtimes.append((datetime.datetime.fromtimestamp(m).strftime("%m-%d %H:%M"), f))

print("local_files=%d (server=%d)" % (len(local_files), len(server_names)))
print("local 收=%d, 复=%d" % (len(recv_local), len(resp_local)))
print("missing from local (server has, local missing):")
for f in sorted(server_names - local_names):
    print("  M>", f)
print("extra in local (local has, server missing):")
for f in sorted(local_names - server_names):
    print("  X>", f)
print("--- Recent local mtimes (newest 10) ---")
mtimes.sort(reverse=True)
for ts, f in mtimes[:10]:
    print("  %s  %s" % (ts, f))
