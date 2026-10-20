"""Convert JSON files to JSON Lines (one JSON value per line).

Examples:
    python event_log_creation\\convert_script.py "default_process\\*.json"
    python event_log_creation\\convert_script.py input.json --output output.jsonl
    python event_log_creation\\convert_script.py data --output-dir jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


def read_json_values(path: Path) -> Iterable[Any]:
    """Read either regular JSON or an existing JSON Lines file."""
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return

    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        values = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                values.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"{path}: invalid JSON on line {line_number}: {error.msg}"
                ) from error
        return values

    if isinstance(document, list):
        return document
    return (document,)


def convert_file(input_path: Path, output_path: Path) -> int:
    """Convert one file and return the number of JSON Lines written."""
    values = read_json_values(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as output:
        for value in values:
            output.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")))
            output.write("\n")
            count += 1
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="JSON files, directories, or glob patterns to convert",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="output file; only valid when exactly one input file is selected",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="directory for converted files (default: next to each input file)",
    )
    return parser.parse_args()


def resolve_inputs(input_paths: Iterable[Path]) -> list[Path]:
    files = []
    for input_path in input_paths:
        if input_path.is_dir():
            files.extend(sorted(input_path.glob("*.json")))
        elif input_path.is_file():
            files.append(input_path)
        else:
            files.extend(sorted(input_path.parent.glob(input_path.name)))

    unique_files = list(dict.fromkeys(path.resolve() for path in files))
    if not unique_files:
        raise ValueError("No input JSON files found.")
    return unique_files


def main() -> None:
    args = parse_args()
    input_files = resolve_inputs(args.inputs)

    if args.output and len(input_files) != 1:
        raise ValueError("--output requires exactly one input file.")
    if args.output and args.output.resolve() == input_files[0]:
        raise ValueError("The output file must differ from the input file.")

    total = 0
    for input_path in input_files:
        if args.output:
            output_path = args.output
        elif args.output_dir:
            output_path = args.output_dir / f"{input_path.stem}.jsonl"
        else:
            output_path = input_path.with_suffix(".jsonl")

        if output_path.resolve() == input_path:
            raise ValueError(f"The output file must differ from the input file: {input_path}")
        count = convert_file(input_path, output_path)
        print(f"{input_path} -> {output_path} ({count} records)")
        total += count

    print(f"Converted {len(input_files)} file(s), {total} record(s).")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f"Error: {error}") from error