# File Integrity Checker – SHA-256

A beginner-friendly Python cybersecurity project that fingerprints local sample files with cryptographic hashes. Learn how replacing one character changes a file's digest without modifying the original samples.

## Legal and ethical notice

> Scanning or attacking systems you do not own or have written permission to test is illegal. This tool only monitors your own test folder.

## Objectives and features

- Understand file integrity, cryptographic hashing, and safe local testing.
- Print a SHA-256 digest for every regular sample file, in sorted order.
- Optionally use SHA-1 for educational comparison.
- Hash binary data in 4096-byte chunks without loading entire files into memory.
- Handle missing/unreadable files and empty folders without stopping the scan.
- Demonstrate a one-character change using an explicitly requested temporary copy.
- Restrict scanning to immediate regular files in this project's `test_folder`.
- Skip directories, special files, and symbolic links; reject outside paths and linked path components in the hashing function. Refuse a symbolic-link `test_folder`.
- Use no external dependencies, network access, arbitrary scan-path options, or background services.

This is an **on-demand checker**, not a continuous monitoring daemon. Normal runs print hashes; they do not save a baseline or automatically compare previous runs. The demonstration compares before/after hashes in memory.

## Technologies and installation requirements

Use **Python 3.9 or newer** on Windows, Linux, or macOS. The project uses only Python's standard library: `hashlib`, `argparse`, `pathlib`, `tempfile`, `unittest`, and supporting modules. No `pip install` or virtual environment is required.

Check Python:

```sh
python --version
```

On Linux/macOS, substitute `python3` if necessary; on Windows, `py -3` also works. If needed, install Python 3 from https://www.python.org/downloads/ (enable **Add Python to PATH** on Windows), or use your operating system's package manager.

You need read access to the samples, and write access to `test_folder` for demonstrations and tests.

## Project structure

```text
Hash-calculator-v2/
├── .gitignore
├── README.md
└── file-integrity-checker/
    ├── main.py
    ├── README.md
    ├── test_main.py
    └── test_folder/
        ├── file1.txt
        ├── file2.txt
        ├── file3.txt
        ├── file4.txt
        └── file5.txt
```

`test_main.py` contains automated tests. Temporary test/demo folders are removed automatically and ignored by Git if an interrupted run leaves remnants.

## Step-by-step setup and usage

1. Download or clone this repository and open a terminal in its root directory.
2. Check your Python version using the command above.
3. Enter the project folder:

   ```sh
   cd file-integrity-checker
   ```

4. Hash the samples with the default SHA-256 algorithm:

   ```sh
   python main.py
   ```

   Each row contains a filename and a 64-character hexadecimal digest. Repeating the command without editing files produces identical output.

5. Explicitly select an algorithm:

   ```sh
   python main.py --algorithm sha256
   python main.py --algorithm sha1
   ```

   Names are case-insensitive; `SHA-256` and `SHA-1` also work. Unsupported choices such as `md5` produce a helpful usage error.

6. Request the safe integrity demonstration:

   ```sh
   python main.py --demo
   python main.py --algorithm sha1 --demo
   ```

   After the scan, the program explains its operation before creating or changing anything. It copies `file1.txt` into a temporary directory inside `test_folder`, displays the original hash, replaces the copy's first UTF-8 character with `A` (or `B` if it was already `A`), displays the new hash, and prints **CHANGED** when they differ. It then deletes the copy; the original stays untouched. An empty, missing, or non-UTF-8 source produces an error. Only this small demonstration reads a whole file into memory. Normal hashing always uses chunks. `--demo` explicitly authorizes the temporary-copy operation; no interactive prompt is required.

7. View help:

   ```sh
   python main.py --help
   ```

The folder is anchored to `main.py`, not your terminal's working directory. From the repository root you can also run `python file-integrity-checker/main.py`. There is intentionally no option to scan another folder.

Exit codes: **0** = success (including an empty folder), **1** = a scan/read/demo error, **2** = invalid command-line arguments. One unreadable file does not stop other files from being processed.

## How the file hashing function works

`hash_file(path)` defaults to SHA-256:

1. Validate the algorithm and ensure the path is a regular file inside the local test folder, without symbolic links.
2. Create a digest object with Python's built-in `hashlib` library.
3. Open the file in binary read mode (`rb`) so its exact bytes are hashed.
4. Read **4096 bytes** at a time and pass each chunk to `digest.update()` until the file ends.
5. Return `digest.hexdigest()` (64 hexadecimal characters for SHA-256, 40 for SHA-1).
6. On a missing file, permission failure, or other unreadable-file error, print a message to standard error and return `None`. The scanner continues with other files.

An optional second argument selects the algorithm: `hash_file(path, "sha1")`. Never treat `None` as a valid baseline. Relative paths passed to this function are relative to the current working directory; the scanner supplies script-relative absolute paths.

## Why changing one character changes the hash

Cryptographic hashes are designed to exhibit the **avalanche effect**: a small input change typically changes approximately half the output bits. A one-character edit therefore produces a very different-looking digest, though not necessarily every hexadecimal character changes. Hashes have finite output lengths, so collisions are theoretically possible; a digest is not mathematical proof of uniqueness.

**SHA-256 is preferred over SHA-1 because SHA-1 has known collision weaknesses, while SHA-256 is part of the stronger SHA-2 family.** SHA-1 is included only for educational comparison, not recommended for security-sensitive integrity checks. Some security-restricted Python installations disable SHA-1; this program reports that error rather than bypassing platform policy.

Hashing is not encryption, does not hide data, and does not prove authorship. A matching digest is useful only if the reference digest is trusted. Someone who can replace both a file and its saved baseline can defeat a simple comparison. Real deployments need protected baselines or authenticated manifests/signatures.

## Verify hashes manually

Run these commands **inside `file-integrity-checker`**. Compare the digest with the `file1.txt` row from `python main.py`.

**Windows (Command Prompt or PowerShell):**

```text
certutil -hashfile test_folder/file1.txt SHA256
```

**Linux:**

```sh
sha256sum test_folder/file1.txt
```

**macOS:**

```sh
shasum -a 256 test_folder/file1.txt
```

For SHA-1, use `SHA1` with `certutil`, `sha1sum` on Linux, or `shasum -a 1` on macOS. Ignore letter case and surrounding labels when comparing digests. Whitespace, line endings (LF versus CRLF), encoding, and trailing newlines affect hashes because they change the bytes. Compare tools on the same local file rather than assuming checkouts on different operating systems have identical bytes.

## Testing

Inside `file-integrity-checker`:

```sh
python -m unittest -v
```

Or from the repository root:

```sh
python -m unittest discover -s file-integrity-checker -v
```

Tests cover default SHA-256 and a known digest, every-file output, multi-chunk binary reads, one-character changes, repeated-run consistency, missing/unreadable files, continued scanning after errors, empty/missing folders, directory skipping, outside-path and symbolic-link rejection, SHA-1, invalid algorithms, opt-in demonstrations, original preservation, cleanup, and the mandatory legal notice.

Permission and read failures are simulated with `unittest.mock` to work consistently even under administrator accounts. Symbolic-link tests are skipped if the platform cannot create links. Fixtures stay inside `test_folder`; tests never edit the five samples.

For manual checks, run `python main.py` twice and compare the rows. Run `python main.py --demo` and confirm the before/after hashes differ; another normal run should still report the samples' original hashes.

## Scope and limitations

This is an educational local checker, not a forensic tool or adversarial filesystem sandbox. Keep `test_folder` under your control. Do not let another process replace paths or modify files during a scan: path validation and reads are not atomic, and a file edited while being hashed may not represent a stable snapshot. Hard links and mounted filesystems cannot be distinguished from ordinary local files by these portable checks; do not put them in the test folder. Use only your own sample files. No external-system or network scanning is implemented.
