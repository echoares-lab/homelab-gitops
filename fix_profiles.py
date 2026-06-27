import yaml
import glob
for path in glob.glob("config/profiles/k3s-01.yml"):
    with open(path) as f:
        d = yaml.safe_load(f)
    if "vm_specs" not in d:
        d["vm_specs"] = {}
    d["vm_specs"]["guest_id"] = "fedora64Guest"
    with open(path, "w") as f:
        yaml.dump(d, f)
