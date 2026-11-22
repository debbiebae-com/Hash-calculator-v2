"""Hash local sample files without following links or scanning other folders."""

import argparse
import hashlib
import os
from pathlib import Path
import stat
import sys
import tempfile


PROJECT_DIR = Path(__file__).resolve().parent
TEST_FOLDER = PROJECT_DIR / "test_folder"
CHUNK_SIZE = 4096
ALGORITHMS = {"sha256": "SHA-256", "sha1": "SHA-1"}


def validate_algorithm(algorithm):
    """Accept the documented names, with or without a hyphen."""
    normalized = algorithm.lower().replace("-", "")
    if normalized not in ALGORITHMS:
        raise ValueError("Unsupported algorithm. Choose sha256 (recommended) or sha1.")
    return normalized


def checked_path(path):
    """Reject paths outside the local test folder, including symbolic links."""
    root = TEST_FOLDER.absolute()
    if root.is_symlink():
        raise ValueError("test_folder must be a real local folder, not a symbolic link.")
    candidate = Path(os.path.abspath(path))
    try:
        relative = candidate.relative_to(root)
    except ValueError:
        raise ValueError("Only files inside test_folder may be read.") from None

    # Check every component, so links to outside directories are rejected too.
    current = root
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise ValueError("Symbolic links are not allowed.")
    if not stat.S_ISREG(candidate.stat().st_mode):
        raise ValueError("Only regular files may be read.")
    return candidate


def hash_file(path, algorithm="sha256"):
    """Return a hex digest, or None with a readable error if hashing fails.

    Paths must be inside this project's test_folder. Relative paths are relative
    to the current working directory; scanning itself uses script-relative paths.
    """
    try:
        algorithm = validate_algorithm(algorithm)
        safe_path = checked_path(path)
        digest = hashlib.new(algorithm)
        # Binary mode hashes the exact bytes, including line endings.
        with safe_path.open("rb") as file:
            while True:
                chunk = file.read(CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
    except (OSError, ValueError) as error:
        print(f"Cannot hash {Path(path).name}: {error}", file=sys.stderr)
        return None


def scan_files(algorithm="sha256"):
    """Print hashes of immediate regular files, returning (successes, errors)."""
    algorithm = validate_algorithm(algorithm)
    print(f"\n{ALGORITHMS[algorithm]} hashes — local test_folder only")
    print("-" * 88)
    if TEST_FOLDER.is_symlink():
        print("Cannot scan: test_folder must not be a symbolic link.", file=sys.stderr)
        return 0, 1
    try:
        paths = sorted(TEST_FOLDER.iterdir(), key=lambda path: path.name)
    except OSError as error:
        print(f"Cannot open test_folder: {error}", file=sys.stderr)
        return 0, 1

    successes = errors = regular_files = 0
    for path in paths:
        try:
            if path.is_symlink():
                print(f"Skipping symbolic link: {path.name}")
                continue
            if not stat.S_ISREG(path.stat().st_mode):
                continue
        except OSError as error:
            print(f"Cannot inspect {path.name}: {error}", file=sys.stderr)
            errors += 1
            continue
        regular_files += 1
        digest = hash_file(path, algorithm)
        if digest is None:
            errors += 1
        else:
            print(f"{path.name:<24} {digest}")
            successes += 1
    if regular_files == 0 and errors == 0:
        print("No regular files found in test_folder.")
    print(f"Hashed: {successes}; errors: {errors}")
    return successes, errors


def demonstrate_integrity(algorithm="sha256"):
    """Change one character in a temporary UTF-8 copy, never in the original."""
    algorithm = validate_algorithm(algorithm)
    print("\nIntegrity demonstration (explicitly requested with --demo)")
    print("I will copy file1.txt into a temporary directory INSIDE test_folder,")
    print("replace its first character, compare hashes, then delete the copy.")
    print("The original sample file will not be changed.")
    try:
        source = checked_path(TEST_FOLDER / "file1.txt")
        text = source.read_bytes().decode("utf-8")
        if not text:
            raise ValueError("file1.txt must contain at least one UTF-8 character.")
        with tempfile.TemporaryDirectory(prefix="integrity-demo-", dir=TEST_FOLDER) as directory:
            copy = Path(directory) / "file1-copy.txt"
            copy.write_bytes(text.encode("utf-8"))
            original = hash_file(copy, algorithm)
            if original is None:
                return False
            print(f"Original hash: {original}")
            replacement = "B" if text[0] == "A" else "A"
            print(f"Changing the copy's first character: {text[0]!r} -> {replacement!r}")
            copy.write_bytes((replacement + text[1:]).encode("utf-8"))
            changed = hash_file(copy, algorithm)
            if changed is None:
                return False
            print(f"New hash:      {changed}")
            if original != changed:
                print("CHANGED: the hashes differ, so the copy's contents have changed.")
                return True
            print("UNCHANGED: the hashes match.")
            return False
    except (OSError, ValueError, UnicodeError) as error:
        print(f"Cannot run demonstration: {error}", file=sys.stderr)
        return False


def argument_algorithm(value):
    """Turn invalid CLI selections into helpful argparse usage errors."""
    try:
        return validate_algorithm(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Hash only local test_folder files (SHA-256 by default)."
    )
    parser.add_argument(
        "--algorithm", type=argument_algorithm, default="sha256",
        metavar="{sha256,sha1}", help="hash algorithm (default: sha256)",
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="demonstrate a one-character change using a temporary local copy",
    )
    args = parser.parse_args(argv)
    _, errors = scan_files(args.algorithm)
    demo_ok = demonstrate_integrity(args.algorithm) if args.demo else True
    return 1 if errors or not demo_ok else 0


if __name__ == "__main__":
    sys.exit(main())
