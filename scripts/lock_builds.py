import os
import re
import subprocess
import json

LOCK_FILE = "docker-lock.json"

ARCH_MAP = {
    "aarch64": "arm64",
    "amd64": "amd64",
    "armhf": "arm",
    "armv7": "arm",
    "i386": "386"
}

def get_digest(image, arch=None):
    """Fetch the SHA256 digest for an image using skopeo."""
    print(f"Fetching digest for {image} ({arch if arch else 'default arch'})...")
    try:
        cmd = ["skopeo", "inspect"]
        if arch and arch in ARCH_MAP:
            cmd.extend(["--override-arch", ARCH_MAP[arch]])
        cmd.append(f"docker://{image}")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        data = json.loads(result.stdout)
        digest = data.get("Digest")
        if not digest:
            raise ValueError(f"No digest found in manifest for {image}")
        return digest
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
        error_msg = getattr(e, 'stderr', str(e))
        print(f"Error fetching digest for {image}: {error_msg}")
        return None

def lock_build_yaml(file_path, lock_data):
    """Update build.yaml with pinned digests. Returns True if successful, False if no changes, and raises Error on failure."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Regex to find architecture-specific images in build.yaml
    # Matches:   amd64: "image:tag"
    pattern = re.compile(r'(\s+)(\w+):\s+"([^"@]+)(?::([^"@]+))?(@sha256:[a-f0-9]+)?"')
    
    new_content = content
    changes_made = False
    errors = []

    for match in pattern.finditer(content):
        indent, arch, image_name, tag, existing_digest = match.groups()
        
        # Construct the full image reference for skopeo
        full_ref = f"{image_name}:{tag}" if tag else image_name
        
        # If already pinned, we might want to verify or update it
        # Actually, if it's already pinned, we might want to keep it or update it.
        # For now, let's allow updating if it's not pinned or if we want to refresh.
        # But the original script skipped already pinned. Let's keep that but check if it exists.

        # Fetch new digest
        digest = get_digest(full_ref, arch)
        if not digest:
            errors.append(f"Failed to fetch digest for {arch} ({full_ref})")
            continue

        print(f"  Found digest for {arch}: {digest}")
        
        if existing_digest:
            clean_digest = existing_digest.lstrip('@')
            if clean_digest == digest:
                print(f"  {arch} is already pinned to current digest.")
                lock_data[full_ref] = clean_digest
                continue
            else:
                print(f"  Updating {arch} pin from {clean_digest} to {digest}")
                old_str = f'"{full_ref}@{clean_digest}"'
                new_str = f'"{full_ref}@{digest}"'
                new_content = new_content.replace(old_str, new_str)
                lock_data[full_ref] = digest
                changes_made = True
        else:
            # Replace image:tag with image:tag@sha256:digest
            old_str = f'"{full_ref}"'
            new_str = f'"{full_ref}@{digest}"'
            new_content = new_content.replace(old_str, new_str)
            lock_data[full_ref] = digest
            changes_made = True

    if errors:
        raise RuntimeError("\n".join(errors))

    if changes_made:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Updated {file_path}")
        return True
    else:
        print(f"No changes needed for {file_path}")
        return False

def main():
    import sys
    lock_data = {}
    original_lock_data = {}
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, 'r') as f:
            lock_data = json.load(f)
            original_lock_data = json.loads(json.dumps(lock_data)) # Deep copy

    # Find all build.yaml files
    any_yaml_changed = False
    has_errors = False
    for root, dirs, files in os.walk('.'):
        if 'build.yaml' in files:
            file_path = os.path.join(root, 'build.yaml')
            print(f"Processing {file_path}...")
            try:
                if lock_build_yaml(file_path, lock_data):
                    any_yaml_changed = True
            except RuntimeError as e:
                print(f"Error processing {file_path}: {e}")
                has_errors = True

    # Only save the central lock file if data actually changed
    if lock_data != original_lock_data or any_yaml_changed:
        with open(LOCK_FILE, 'w') as f:
            json.dump(lock_data, f, indent=2, sort_keys=True)
        print(f"Updated {LOCK_FILE}")

    if has_errors:
        print("Build locking failed with errors.")
        sys.exit(1)

if __name__ == "__main__":
    main()
