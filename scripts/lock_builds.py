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
        return data.get("Digest")
    except subprocess.CalledProcessError as e:
        print(f"Error fetching digest for {image}: {e.stderr}")
        return None

def lock_build_yaml(file_path, lock_data):
    """Update build.yaml with pinned digests."""
    with open(file_path, 'r') as f:
        content = f.read()

    # Regex to find architecture-specific images in build.yaml
    # Matches:   amd64: "image:tag"
    pattern = re.compile(r'(\s+)(\w+):\s+"([^"@]+)(?::([^"@]+))?(@sha256:[a-f0-9]+)?"')
    
    new_content = content
    changes_made = False

    for match in pattern.finditer(content):
        indent, arch, image_name, tag, existing_digest = match.groups()
        
        # Construct the full image reference for skopeo
        full_ref = f"{image_name}:{tag}" if tag else image_name
        
        # If already pinned, we might want to verify or update it
        if existing_digest:
            clean_digest = existing_digest.lstrip('@')
            print(f"  {arch} is already pinned: {clean_digest}")
            # We add it to lock_data anyway for sync
            lock_data[full_ref] = clean_digest
            continue

        # Fetch new digest
        digest = get_digest(full_ref, arch)
        if digest:
            print(f"  Found digest for {arch}: {digest}")
            # Replace image:tag with image:tag@sha256:digest
            old_str = f'"{full_ref}"'
            new_str = f'"{full_ref}@{digest}"'
            new_content = new_content.replace(old_str, new_str)
            lock_data[full_ref] = digest
            changes_made = True

    if changes_made:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Updated {file_path}")
        return True
    else:
        print(f"No changes needed for {file_path}")
        return False

def main():
    lock_data = {}
    original_lock_data = {}
    if os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, 'r') as f:
            lock_data = json.load(f)
            original_lock_data = json.loads(json.dumps(lock_data)) # Deep copy

    # Find all build.yaml files
    any_yaml_changed = False
    for root, dirs, files in os.walk('.'):
        if 'build.yaml' in files:
            file_path = os.path.join(root, 'build.yaml')
            print(f"Processing {file_path}...")
            if lock_build_yaml(file_path, lock_data):
                any_yaml_changed = True

    # Only save the central lock file if data actually changed
    if lock_data != original_lock_data or any_yaml_changed:
        with open(LOCK_FILE, 'w') as f:
            json.dump(lock_data, f, indent=2, sort_keys=True)
        print(f"Updated {LOCK_FILE}")
    else:
        print(f"No changes needed for {LOCK_FILE}")

if __name__ == "__main__":
    main()
