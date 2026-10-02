import subprocess, os, tarfile, io, datetime

SSH = r"C:\Windows\System32\OpenSSH\ssh.exe"
KEY = r"D:\id_ed25519"
HOST = "ubuntu@43.134.236.80"
REMOTE_DIR = "/home/ubuntu/fstdd-notices/FSTDD003"
LOCAL_DIR = r"D:\FSTDD003\.fstdd\_notices\FSTDD003"

os.makedirs(LOCAL_DIR, exist_ok=True)

# Robust: ssh + tar streaming
remote_cmd = "cd " + REMOTE_DIR + " && tar -cf - ."
cmd = [SSH, "-i", KEY,
       "-o", "StrictHostKeyChecking=no",
       "-o", "ConnectTimeout=25",
       HOST, remote_cmd]
p = subprocess.run(cmd, capture_output=True, timeout=180)
err = p.stderr.decode("utf-8", "replace")

# Extract tar in Python using tarfile (handles UTF-8 filenames correctly)
extracted = 0
skipped = 0
with tarfile.open(fileobj=io.BytesIO(p.stdout), mode="r:") as tf:
    for member in tf.getmembers():
        name = member.name
        # strip leading "./"
        if name.startswith("./"):
            name = name[2:]
        if not name or name == ".":
            continue
        target = os.path.join(LOCAL_DIR, name)
        # security: ensure inside LOCAL_DIR
        if not os.path.abspath(target).startswith(os.path.abspath(LOCAL_DIR)):
            skipped += 1
            continue
        if member.isfile():
            f = tf.extractfile(member)
            if f is None:
                continue
            data = f.read()
            with open(target, "wb") as fout:
                fout.write(data)
            extracted += 1
        elif member.isdir():
            os.makedirs(target, exist_ok=True)

entries = sorted(os.listdir(LOCAL_DIR))
print("ssh exit=%d, extracted=%d, skipped=%d" % (p.returncode, extracted, skipped))
print("local_files=%d" % len(entries))
if err:
    print("SSH STDERR (first 500):", err[:500])
print("ts=%s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
