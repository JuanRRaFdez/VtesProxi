from __future__ import annotations

import argparse
import subprocess
import sys


SLICE_POLICY: dict[str, dict[str, set[str]]] = {
    "slice0": {"paths": set(), "debt_classes": set()},
    "slice1": {
        "paths": {
            "apps/cripta",
            "apps/libreria",
            "apps/mis_cartas",
            "apps/srv_importacion",
            "apps/usuarios",
        },
        "debt_classes": set(),
    },
    "slice2": {
        "paths": {"apps/layouts", "apps/srv_recorte"},
        "debt_classes": {"F841"},
    },
    "slice3": {
        "paths": {"apps/srv_textos"},
        "debt_classes": {"E501", "F841"},
    },
}


def _normalize(values: list[str]) -> set[str]:
    return {value.strip().rstrip("/") for value in values if value.strip()}


def _parse_stats_total(ruff_output: str) -> int:
    total = 0
    for line in ruff_output.splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0].isdigit() and len(parts) > 1:
            total += int(parts[0])
    return total


def _run_global_stats() -> int:
    result = subprocess.run(
        [".venv/bin/ruff", "check", ".", "--statistics"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        print("Policy check failed: unable to run 'ruff check . --statistics'.", file=sys.stderr)
        print(result.stderr.strip(), file=sys.stderr)
        raise SystemExit(2)
    return _parse_stats_total(result.stdout)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate ruff-debt slice policy constraints.")
    parser.add_argument("--slice", required=True, choices=sorted(SLICE_POLICY.keys()))
    parser.add_argument("--paths", nargs="+", required=True)
    parser.add_argument("--debt-classes", nargs="*", default=[])
    parser.add_argument("--baseline-total", type=int, required=True)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    expected = SLICE_POLICY[args.slice]
    got_paths = _normalize(args.paths)
    got_classes = _normalize(args.debt_classes)

    errors: list[str] = []
    if got_paths != expected["paths"]:
        expected_paths = sorted(expected["paths"])
        actual_paths = sorted(got_paths)
        errors.append(
            f"path set mismatch for {args.slice}: expected {expected_paths}, got {actual_paths}"
        )
    if got_classes != expected["debt_classes"]:
        errors.append(
            "debt class mismatch for "
            f"{args.slice}: expected {sorted(expected['debt_classes'])}, got {sorted(got_classes)}"
        )

    current_total = _run_global_stats()
    if current_total > args.baseline_total:
        errors.append(
            "global debt regression: "
            f"current_total={current_total} exceeds baseline_total={args.baseline_total}"
        )

    if errors:
        print("Policy check: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Policy check: PASS")
    print(f"- slice={args.slice}")
    print(f"- paths={sorted(got_paths)}")
    print(f"- debt_classes={sorted(got_classes)}")
    print(f"- global_debt_total={current_total}")
    print(f"- baseline_total={args.baseline_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
