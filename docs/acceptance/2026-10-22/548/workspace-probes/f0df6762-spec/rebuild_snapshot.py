from pathlib import Path
import subprocess,json,hashlib
r=Path(__file__).resolve().parent;m=json.loads((r/"archive_manifest.json").read_text())
for e in m["entries"]:
 b=subprocess.check_output(["git","show",m["target"]+":"+e["path"]],cwd=m["repository"])
 if hashlib.sha256(b).hexdigest()!=e["sha256"]:raise RuntimeError("Fixed blob mismatch")
 p=r/e["path"]
 if p.exists()and p.read_bytes()!=b:raise RuntimeError("Preserving changed file: "+e["path"])
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
for l in m["dependency_symlinks"]:
 p=r/l["path"]
 if not p.exists()and not p.is_symlink():p.parent.mkdir(parents=True,exist_ok=True);p.symlink_to(l["target"],target_is_directory=True)
print("Rebuilt",len(m["entries"]),"fixed files")
