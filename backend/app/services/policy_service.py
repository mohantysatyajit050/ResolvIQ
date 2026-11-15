"""Load policy documents (Markdown files) into the policies table.

File format:
    ---
    slug: late-delivery
    applies_to: late_delivery      (one of the ticket intents)
    version: 1
    ---
    # Title
    ## Section heading
    Section text...

Every '## section' becomes one row (a chunk). Text between the title and the
first '## ' is ignored.

Loading is safe to repeat:
- same version, same text    -> nothing happens
- same version, edited text  -> error: bump the version in the file
- higher version             -> new rows are added, older rows become inactive
- lower version than stored  -> error
Either every file loads or none does.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.policy import Policy
from app.models.ticket import TicketIntent

POLICY_DIR = Path(__file__).resolve().parents[2] / "policies"
_SLUG = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


class PolicyFileError(Exception):
    """A policy file is malformed."""


class PolicyVersionError(Exception):
    """A policy was edited without a version bump, or its version went backwards."""


@dataclass(frozen=True)
class ParsedChunk:
    section: str
    content: str


@dataclass(frozen=True)
class ParsedPolicy:
    slug: str
    title: str
    applies_to: str
    version: int
    chunks: tuple[ParsedChunk, ...]


@dataclass(frozen=True)
class LoadSummary:
    added: tuple[str, ...]  # slugs that got new rows
    unchanged: tuple[str, ...]  # slugs that were already up to date


def chunk_hash(title: str, applies_to: str, section: str, content: str) -> str:
    """Fingerprint of everything in a chunk that matters. Changes when the text changes."""
    raw = "\x1f".join([title, applies_to, section, content])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_policy_text(text: str, source: str = "policy text") -> ParsedPolicy:
    # Windows files use CRLF; normalise so the hash does not depend on line endings
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise PolicyFileError(f"{source}: the file must start with a '---' header")
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        raise PolicyFileError(f"{source}: the header is not closed with '---'")

    meta: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator:
            raise PolicyFileError(f"{source}: bad header line {line!r}")
        meta[key.strip()] = value.strip()

    missing = {"slug", "applies_to", "version"} - meta.keys()
    if missing:
        raise PolicyFileError(f"{source}: header is missing {sorted(missing)}")

    slug = meta["slug"]
    if not _SLUG.fullmatch(slug):
        raise PolicyFileError(f"{source}: slug {slug!r} must be lowercase words joined by '-'")

    applies_to = meta["applies_to"]
    if applies_to not in {intent.value for intent in TicketIntent}:
        raise PolicyFileError(f"{source}: unknown applies_to {applies_to!r}")

    try:
        version = int(meta["version"])
    except ValueError:
        raise PolicyFileError(f"{source}: version must be a whole number") from None
    if version < 1:
        raise PolicyFileError(f"{source}: version must be 1 or higher")

    title: str | None = None
    sections: list[tuple[str, list[str]]] = []
    for line in lines[end + 1 :]:
        if line.startswith("## "):
            sections.append((line[3:].strip(), []))
        elif line.startswith("# ") and title is None and not sections:
            title = line[2:].strip()
        elif sections:
            sections[-1][1].append(line)
    if not title:
        raise PolicyFileError(f"{source}: missing a '# Title' line")

    chunks: list[ParsedChunk] = []
    for name, body_lines in sections:
        content = "\n".join(body_lines).strip()
        if content:
            chunks.append(ParsedChunk(section=name, content=content))
    if not chunks:
        raise PolicyFileError(f"{source}: no '## section' with text found")

    return ParsedPolicy(
        slug=slug,
        title=title,
        applies_to=applies_to,
        version=version,
        chunks=tuple(chunks),
    )


def parse_policy_file(path: Path) -> ParsedPolicy:
    # utf-8-sig also accepts files that PowerShell saved with a BOM
    return parse_policy_text(path.read_text(encoding="utf-8-sig"), source=path.name)


def _rows_for(policy: ParsedPolicy) -> list[Policy]:
    return [
        Policy(
            slug=policy.slug,
            title=policy.title,
            section=chunk.section,
            chunk_index=index,
            version=policy.version,
            applies_to=policy.applies_to,
            content=chunk.content,
            content_hash=chunk_hash(
                policy.title, policy.applies_to, chunk.section, chunk.content
            ),
            is_active=True,
        )
        for index, chunk in enumerate(policy.chunks)
    ]


def _apply(db: Session, policy: ParsedPolicy) -> bool:
    """Store one policy. Returns True if rows were added, False if already up to date."""
    stored = db.scalars(select(Policy).where(Policy.slug == policy.slug)).all()
    stored_version = max((row.version for row in stored), default=0)

    if policy.version < stored_version:
        raise PolicyVersionError(
            f"{policy.slug}: the file has version {policy.version} "
            f"but version {stored_version} is already stored"
        )

    new_rows = _rows_for(policy)

    if policy.version == stored_version:
        current = {r.chunk_index: r.content_hash for r in stored if r.version == stored_version}
        wanted = {r.chunk_index: r.content_hash for r in new_rows}
        if current != wanted:
            raise PolicyVersionError(
                f"{policy.slug}: the text changed but the version is still {policy.version}. "
                "Bump the version in the file."
            )
        return False

    # first load, or a higher version: retire the old rows and add the new ones
    db.execute(
        update(Policy)
        .where(Policy.slug == policy.slug, Policy.is_active.is_(True))
        .values(is_active=False)
    )
    db.add_all(new_rows)
    return True


def load_policies(db: Session, directory: Path = POLICY_DIR) -> LoadSummary:
    files = sorted(directory.glob("*.md"))
    if not files:
        raise PolicyFileError(f"no policy files found in {directory}")

    parsed = [parse_policy_file(path) for path in files]  # any bad file stops here
    slugs = [policy.slug for policy in parsed]
    if len(set(slugs)) != len(slugs):
        raise PolicyFileError("two policy files use the same slug")

    added: list[str] = []
    unchanged: list[str] = []
    try:
        for policy in parsed:
            (added if _apply(db, policy) else unchanged).append(policy.slug)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return LoadSummary(added=tuple(added), unchanged=tuple(unchanged))


def active_chunks(db: Session, applies_to: str | None = None) -> list[Policy]:
    """The chunks the agent may use: active rows only, in document order."""
    stmt = select(Policy).where(Policy.is_active.is_(True))
    if applies_to is not None:
        stmt = stmt.where(Policy.applies_to == applies_to)
    return list(db.scalars(stmt.order_by(Policy.slug, Policy.chunk_index)).all())
