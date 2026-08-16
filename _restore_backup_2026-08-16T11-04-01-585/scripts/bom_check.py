#!/usr/bin/env python3
"""BOM completeness check for fitted parts.

Reads a CSV exported by `kicad-cli sch export bom` (DNP/exclude-from-BOM parts
already filtered out) and verifies every remaining (fitted) row has:

  - Value
  - Footprint
  - an LCSC number (turnkey-orderable via JLCPCB)

Exits non-zero if any fitted row is incomplete. Whether that failure *gates*
CI is decided by the ENFORCE toggle in the workflow, not here — this script
always reports the truth.

Usage: bom_check.py <bom.csv>
"""
import csv
import sys


def norm(row, *names):
    """Return the first non-empty value among the given column names (case-insensitive)."""
    lower = {k.lower(): (v or "").strip() for k, v in row.items() if k}
    for n in names:
        v = lower.get(n.lower(), "")
        if v:
            return v
    return ""


def main(path):
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        print(f"BOM file not found: {path}")
        return 2

    if not rows:
        print("BOM is empty — nothing to check (unexpected).")
        return 2

    problems = []
    for row in rows:
        ref = norm(row, "Reference", "References", "Designator") or "(no ref)"
        missing = []
        if not norm(row, "Value"):
            missing.append("Value")
        if not norm(row, "Footprint"):
            missing.append("Footprint")
        if not norm(row, "LCSC", "LCSC Part #"):
            missing.append("LCSC")
        if missing:
            problems.append((ref, ", ".join(missing)))

    total = len(rows)
    ok = total - len(problems)
    print(f"BOM completeness: {ok}/{total} fitted rows complete.")
    if problems:
        print("\nIncomplete rows:")
        width = max(len(r) for r, _ in problems)
        for ref, miss in problems:
            print(f"  {ref.ljust(width)}  missing: {miss}")
        return 1
    print("All fitted parts have Value, Footprint, and an LCSC number.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
