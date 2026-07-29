"""Dependency-free validation helpers for registered reader manuscripts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUPPORTED_ENGINES = {"pdflatex", "xelatex"}


@dataclass(frozen=True)
class ManuscriptSpec:
    identifier: str
    locale: str
    source: Path
    engine: str
    claim_map: Path
    bibliography: Path
    output: str


def _scalar(value: str) -> str:
    value = value.strip()
    if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
        return value[1:-1]
    return value


def _parse_manifest_lines(text: str) -> tuple[dict[str, str], list[dict[str, str]]]:
    """Parse the small YAML subset used by manuscript manifests."""

    root: dict[str, str] = {}
    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_entries = False
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped in {"manuscripts:", "entries:"}:
            in_entries = True
            continue
        if stripped.startswith("- "):
            if not in_entries:
                raise ValueError(f"Manifest line {number}: unexpected list item")
            current = {}
            entries.append(current)
            stripped = stripped[2:].strip()
        if ":" not in stripped:
            raise ValueError(f"Manifest line {number}: expected key: value")
        key, value = (part.strip() for part in stripped.split(":", 1))
        if not key or not value:
            raise ValueError(f"Manifest line {number}: empty key or value")
        if in_entries:
            if current is None:
                raise ValueError(f"Manifest line {number}: entry field without list item")
            if key in current:
                raise ValueError(f"Manifest line {number}: duplicate entry field {key}")
            current[key] = _scalar(value)
        else:
            if key in root:
                raise ValueError(f"Manifest line {number}: duplicate field {key}")
            root[key] = _scalar(value)
    return root, entries


def parse_manuscripts_manifest(path: Path | str, *, root: Path | str) -> list[ManuscriptSpec]:
    """Load a manifest and confine every registered input to the project root."""

    root = Path(root).resolve()
    manifest_path = Path(path)
    data, entries = _parse_manifest_lines(manifest_path.read_text(encoding="utf-8"))
    if data.get("version") != "1":
        raise ValueError("Manifest requires version: 1")
    if data.get("output_directory") != "dist/pdf":
        raise ValueError("Manifest output_directory must be dist/pdf")
    if not entries:
        raise ValueError("Manifest requires at least one manuscript entry")

    result: list[ManuscriptSpec] = []
    seen_ids: set[str] = set()
    seen_outputs: set[str] = set()
    required = {"id", "locale", "source", "engine", "claim_map", "bibliography", "output"}
    for entry in entries:
        missing = sorted(required - set(entry))
        if missing:
            raise ValueError(f"Manifest entry missing fields: {', '.join(missing)}")
        identifier = entry["id"]
        engine = entry["engine"]
        output = entry["output"]
        if identifier in seen_ids:
            raise ValueError(f"Duplicate manuscript id: {identifier}")
        if output in seen_outputs or Path(output).name != output or not output.endswith(".pdf"):
            raise ValueError(f"Invalid or duplicate manuscript output: {output}")
        if engine not in SUPPORTED_ENGINES:
            raise ValueError(f"Unsupported LaTeX engine for {identifier}: {engine}")

        source = (root / entry["source"]).resolve()
        claim_map = (root / entry["claim_map"]).resolve()
        bibliography = (root / entry["bibliography"]).resolve()
        try:
            source.relative_to(root)
            claim_map.relative_to(root)
            bibliography.relative_to(root)
        except ValueError as exc:
            raise ValueError("Manifest source paths must stay inside the project root") from exc
        for label, candidate in (
            ("manuscript source", source),
            ("claim map", claim_map),
            ("bibliography", bibliography),
        ):
            if not candidate.is_file():
                raise ValueError(f"Missing {label}: {candidate.relative_to(root)}")

        result.append(
            ManuscriptSpec(
                identifier,
                entry["locale"],
                source,
                engine,
                claim_map,
                bibliography,
                output,
            )
        )
        seen_ids.add(identifier)
        seen_outputs.add(output)
    return result


def latex_command(spec: ManuscriptSpec, build_directory: Path | str) -> list[str]:
    """Return a deterministic LaTeX pass with auxiliaries confined to build/."""

    return [
        spec.engine,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        f"-output-directory={Path(build_directory).resolve()}",
        spec.source.name,
    ]
