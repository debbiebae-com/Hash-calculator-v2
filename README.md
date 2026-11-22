# File Integrity Checker – SHA-256

A beginner-friendly Python cybersecurity portfolio project for hashing local sample files and safely demonstrating a one-character change.

> Scanning or attacking systems you do not own or have written permission to test is illegal. This tool only monitors your own test folder.

The complete project, setup guide, algorithm explanation, manual verification commands, and testing instructions are in **[file-integrity-checker/README.md](file-integrity-checker/README.md)**.

Requires Python 3.9+; no external dependencies.

```sh
cd file-integrity-checker
python main.py
python main.py --demo
python main.py --algorithm sha1
python -m unittest -v
```

Use `python3` instead of `python` if needed on Linux/macOS. Only regular files inside the project's local `test_folder` are scanned. The opt-in demonstration changes a temporary copy, never the original samples.
