import json
import os


def atomic_write_json(path, data, backups=3):
    """Write JSON to `path` atomically (tmp file + os.replace), rotating up to
    `backups` previous versions to path.bak1..bakN. A crash mid-write leaves the
    previous file (and backups) intact."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    # Rotate existing backups: bak(N-1) -> bakN, ..., current -> bak1.
    if os.path.exists(path) and backups > 0:
        for i in range(backups, 1, -1):
            src = f"{path}.bak{i - 1}"
            dst = f"{path}.bak{i}"
            if os.path.exists(src):
                os.replace(src, dst)
        try:
            import shutil
            shutil.copy2(path, f"{path}.bak1")
        except OSError:
            pass

    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=4)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)  # atomic on POSIX
