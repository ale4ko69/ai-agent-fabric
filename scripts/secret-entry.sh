#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: secret-entry.sh <project-root> <relative-destination> <secret-label>" >&2
  exit 2
}

fail() {
  echo "$1" >&2
  exit 1
}

[ "$#" -eq 3 ] || usage
project_root=$1
relative_destination=$2
secret_label=$3

[ -d "$project_root" ] || fail "Project root does not exist."

python_command=$(command -v python3 || command -v python || true)
[ -n "$python_command" ] || fail "Python is required to validate the project profile."

# This phase processes only profile and path metadata. It completes before the hidden
# prompt; its output is limited to the declared non-secret allowed root.
allowed_relative=$("$python_command" - "$project_root" "$relative_destination" <<'PY'
import json
import sys
from pathlib import Path, PureWindowsPath


def fail(message):
    raise SystemExit(message)


def safe_relative(value):
    if not isinstance(value, str) or not value.strip():
        return False
    path = Path(value)
    windows_path = PureWindowsPath(value)
    return (
        not path.is_absolute()
        and not windows_path.is_absolute()
        and not windows_path.root
        and ".." not in path.parts
        and ".." not in windows_path.parts
    )


root = Path(sys.argv[1]).resolve()
destination = sys.argv[2]
if not safe_relative(destination):
    fail("Destination must stay inside the project root.")
try:
    profile = json.loads((root / ".agent-fabric" / "profile.json").read_text(encoding="utf-8"))
    allowed_root = profile["secrets"]["allowed_root"]
except (OSError, KeyError, TypeError, json.JSONDecodeError):
    fail("Project profile must declare secrets.allowed_root.")
if not safe_relative(allowed_root):
    fail("Profile secrets.allowed_root must be a safe relative path.")

destination_path = Path(destination)
allowed_path = Path(allowed_root)
if destination_path == allowed_path:
    fail("Destination must name a file below the profile-declared secret root.")
try:
    destination_path.relative_to(allowed_path)
except ValueError:
    fail("Destination must be under the profile-declared secret root.")
print(allowed_root)
PY
) || fail "Secret destination was not accepted."

# Resolve the caller-supplied project root once. All later operations are lexical or
# physical checks below this value; the secret itself has not yet been requested.
project_root=$(cd -P -- "$project_root" && pwd -P)
destination="$project_root/$relative_destination"
destination_parent=${destination%/*}
[ "$destination_parent" != "$destination" ] || fail "Secret destination must name a file."

printf 'Enter %s: ' "$secret_label" >&2
IFS= read -r -s secret_value
printf '\n' >&2
[ -n "$secret_value" ] || fail "No secret entered; nothing was written."

# Bash owns the interactive hidden prompt. The security-sensitive file creation below
# uses descriptor-relative Python primitives because Bash has no portable equivalent
# for holding a checked parent directory descriptor against symlink races. Secret bytes
# travel only through an inherited pipe descriptor: never via arguments, files, logs,
# or the Fabric CLI process.
umask 077
if ! printf '%s\n' "$secret_value" | "$python_command" - "$project_root" "$relative_destination" "$allowed_relative" 3<&0 <<'PY'
import os
import stat
import sys
from pathlib import Path


def fail(message):
    raise SystemExit(message)


root = Path(sys.argv[1]).resolve()
relative_destination = Path(sys.argv[2])
allowed_relative = Path(sys.argv[3])
destination = root / relative_destination
if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY") or os.open not in os.supports_dir_fd:
    fail("Secure descriptor-relative secret storage is unavailable on this host.")

directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
root_fd = None
parent_fd = None
descriptor = None
created = False
try:
    # Hold the physical project root, then walk and create every directory component
    # relative to trusted descriptors. No unchecked full pathname is opened after this.
    root_fd = os.open(root, directory_flags)
    parent_fd = root_fd
    for part in destination.relative_to(root).parts[:-1]:
        try:
            os.mkdir(part, 0o700, dir_fd=parent_fd)
        except FileExistsError:
            pass
        next_fd = os.open(part, directory_flags, dir_fd=parent_fd)
        if parent_fd != root_fd:
            os.close(parent_fd)
        parent_fd = next_fd
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    descriptor = os.open(destination.name, flags, 0o600, dir_fd=parent_fd)
    created = True
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            fail("Refusing a non-regular secret destination.")
        with os.fdopen(3, "rb") as secret_stream:
            secret = secret_stream.read()
        if not secret:
            fail("No secret entered; nothing was written.")
        written = 0
        while written < len(secret):
            count = os.write(descriptor, secret[written:])
            if count <= 0:
                fail("Secret could not be stored completely.")
            written += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
        descriptor = None
except BaseException:
    if created:
        try:
            os.unlink(destination.name, dir_fd=parent_fd)
        except OSError:
            pass
    raise
finally:
    if descriptor is not None:
        os.close(descriptor)
    if parent_fd is not None:
        os.close(parent_fd)
    if root_fd is not None and root_fd != parent_fd:
        os.close(root_fd)
PY
then
  unset secret_value
  fail "Secret was not stored."
fi
unset secret_value
echo "Secret stored in the declared project-local destination." >&2
