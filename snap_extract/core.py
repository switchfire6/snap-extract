"""Read ownership locally and join it to a public, cached card catalog."""
from __future__ import annotations

import csv
import io
import json
import os
import tempfile
import time
import urllib.request
from urllib.parse import urlsplit
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

from . import __version__

CATALOG_URL = "https://snap.fan/cards/"
DEFAULT_COLUMNS = ("name", "cost", "power", "ability")
EXTRA_COLUMNS = ("series", "keywords", "card_id")
ALL_COLUMNS = DEFAULT_COLUMNS + EXTRA_COLUMNS


def app_data_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local/share")) / "SnapExtract"


def default_collection_path() -> Path:
    return Path.home() / "AppData/LocalLow/Second Dinner/SNAP/Standalone/States/nvprod/CollectionState.json"


def read_json(path: Path):
    # SNAP can replace its state file during a read. Retry brief incomplete writes.
    for attempt in range(3):
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, PermissionError, FileNotFoundError):
            if attempt == 2:
                raise
            time.sleep(0.1)


def atomic_write(path: Path, content: str, encoding: str = "utf-8", *, overwrite: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding=encoding, newline="",
                                         dir=path.parent, delete=False) as f:
            temp_path = Path(f.name)
            f.write(content)
        if overwrite:
            os.replace(temp_path, path)
        else:
            # Publish the complete file only if the destination is still absent.
            # A separate exists() check cannot protect against concurrent writers.
            os.link(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


class CatalogParser(HTMLParser):
    """Use the catalog's explicit card attributes and visible descriptions."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.cards: dict[str, dict] = {}
        self.current: dict | None = None
        self.div_depth = 0
        self.card_depth = 0
        self.description_depth = 0
        self.parts: list[str] = []
        self.document_closed = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div":
            self.div_depth += 1
        if attrs.get("data-card-key"):
            try:
                self.current = {
                    "card_id": attrs["data-card-key"],
                    "name": attrs["data-card-name"],
                    "cost": int(attrs["data-card-cost"]),
                    "power": int(attrs["data-card-power"]),
                    "series": attrs.get("data-card-series-key") or "",
                    "keywords": (attrs.get("data-card-abilities") or "").replace("|", "; "),
                    "card_type": attrs.get("data-card-type") or "",
                    "ability": "",
                }
            except (ValueError, KeyError, TypeError) as exc:
                raise ValueError("The public catalog format changed; the existing cache was kept.") from exc
            self.card_depth = self.div_depth
        if self.current is not None and "card-grid__cell-description" in (attrs.get("class") or "").split():
            self.description_depth = self.div_depth
            self.parts = []
        if tag == "br" and self.description_depth:
            self.parts.append(" ")

    def handle_data(self, data):
        if self.description_depth:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "html":
            self.document_closed = True
        if tag != "div":
            return
        if self.current is not None:
            if self.description_depth == self.div_depth:
                self.current["ability"] = " ".join("".join(self.parts).split())
                self.description_depth = 0
            if self.div_depth == self.card_depth:
                card = self.current
                if "No Ability" in card["keywords"].split("; "):
                    card["ability"] = "No ability."
                # Unreleased placeholders sometimes have no description. They are
                # deliberately not usable metadata; an owned one is flagged unknown.
                if card["ability"]:
                    self.cards[card["card_id"]] = card
                self.current = None
        self.div_depth -= 1


def parse_catalog(page: str, *, require_document: bool = False) -> dict[str, dict]:
    parser = CatalogParser()
    parser.feed(page)
    parser.close()
    if parser.current is not None or (require_document and not parser.document_closed):
        raise ValueError("The public catalog download was incomplete; the existing cache was kept.")
    return parser.cards


def validate_catalog(payload: dict) -> dict:
    if not isinstance(payload, dict) or payload.get("schema") != 1:
        raise ValueError("Unsupported card catalog. Refresh card data to create a new cache.")
    cards = payload.get("cards")
    if not isinstance(cards, dict) or len(cards) < 100:
        raise ValueError("The card catalog is incomplete. Refresh card data.")
    for key, card in cards.items():
        if (not isinstance(key, str) or not key.strip()
                or not isinstance(card, dict) or card.get("card_id") != key
                or not isinstance(card.get("name"), str) or not card["name"].strip()
                or type(card.get("cost")) is not int or type(card.get("power")) is not int
                or not isinstance(card.get("ability"), str) or not card["ability"].strip()
                or any(not isinstance(card.get(field, ""), str) for field in ("series", "keywords", "card_type"))):
            raise ValueError("Invalid card data. Refresh card data to repair the cache.")
    try:
        stamp = datetime.fromisoformat(payload["fetched_at"])
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError("Missing timezone")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Invalid catalog retrieval date. Refresh card data to repair the cache.") from exc
    return payload


class CatalogRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Keep catalog requests on the trusted HTTPS origin, including redirects."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if (target.scheme != "https" or target.hostname != "snap.fan"
                or target.port not in (None, 443) or target.username is not None or target.password is not None):
            raise ValueError("The catalog redirected outside https://snap.fan; the existing cache was kept.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def refresh_catalog(cache_path: Path | None = None) -> dict:
    # The URL and headers never contain account, collection, or owned card data.
    request = urllib.request.Request(CATALOG_URL, headers={
        "User-Agent": f"SnapExtract/{__version__} (personal collection CSV exporter)",
        "Accept": "text/html",
    })
    opener = urllib.request.build_opener(CatalogRedirectHandler())
    with opener.open(request, timeout=25) as response:
        raw = response.read(8_000_001)
        if len(raw) > 8_000_000:
            raise ValueError("The catalog response is unexpectedly large; the existing cache was kept.")
        page = raw.decode("utf-8")
    payload = validate_catalog({
        "schema": 1, "source": CATALOG_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cards": parse_catalog(page, require_document=True),
    })
    atomic_write(cache_path or app_data_dir() / "catalog.json", json.dumps(payload, ensure_ascii=False))
    return payload


def load_catalog(cache_path: Path | None = None) -> dict:
    return validate_catalog(read_json(cache_path or app_data_dir() / "catalog.json"))


@dataclass
class Deck:
    name: str
    rows: list[dict]


@dataclass
class Collection:
    rows: list[dict]
    instances: int
    duplicates: int
    ignored: int
    missing: list[str] = field(default_factory=list)
    modified: str = ""
    version: str = ""
    decks: list[Deck] = field(default_factory=list)
    deck_warnings: list[str] = field(default_factory=list)


def card_row(card_id: str, catalog: dict) -> dict:
    card = catalog["cards"].get(card_id)
    if card is None:
        card = {"card_id": card_id, "name": card_id, "cost": None, "power": None,
                "ability": "UNKNOWN - refresh card data before using this card.",
                "series": "", "keywords": ""}
    return {k: card.get(k, "") for k in ALL_COLUMNS}


def extract_decks(server: dict, catalog: dict) -> tuple[list[Deck], list[str]]:
    """Read saved decks, keeping card order and excluding account/cosmetic fields."""
    items = server.get("Decks", [])
    if not isinstance(items, list):
        return [], ["Saved decks could not be read: ServerState.Decks is not a list."]
    # Some saves contain instance references instead of embedded deck cards.
    instances = {c["Id"]: c.get("CardDefId") for c in server.get("Cards", [])
                 if isinstance(c, dict) and isinstance(c.get("Id"), str)}
    decks, warnings = [], []
    for index, item in enumerate(items, 1):
        if not isinstance(item, dict):
            warnings.append(f"Skipped saved deck {index}: invalid deck entry.")
            continue
        name = item.get("Name")
        name = name if isinstance(name, str) and name.strip() else f"Untitled deck {index}"
        if "Cards" in item:
            cards = item["Cards"]
            ids = [c.get("CardDefId") if isinstance(c, dict) else None for c in cards] if isinstance(cards, list) else None
        else:
            references = item.get("CardIds")
            ids = [instances.get(ref) if isinstance(ref, str) else None for ref in references] if isinstance(references, list) else None
        if ids is None or any(not isinstance(card_id, str) or not card_id.strip() for card_id in ids):
            # Never silently export a truncated deck or guess a missing card.
            warnings.append(f"Skipped saved deck {index} ({name}): unreadable card references. Reload after opening SNAP.")
            continue
        decks.append(Deck(name, [card_row(card_id, catalog) for card_id in ids]))
    return decks, warnings


def extract_collection(path: Path, catalog: dict) -> Collection:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("Expected a CollectionState.json object.")
    server = payload.get("ServerState")
    if not isinstance(server, dict) or not isinstance(server.get("Cards"), list):
        raise ValueError("This file has no ServerState.Cards list. Select SNAP's CollectionState.json.")
    counts: Counter = Counter()
    ignored = 0
    for item in server["Cards"]:
        card_id = item.get("CardDefId") if isinstance(item, dict) else None
        if isinstance(card_id, str) and card_id.strip():
            counts[card_id] += 1
        else:
            ignored += 1
    rows, missing = [], []
    for card_id in counts:
        if card_id not in catalog["cards"]:
            missing.append(card_id)
        rows.append(card_row(card_id, catalog))
    decks, deck_warnings = extract_decks(server, catalog)
    return Collection(rows, sum(counts.values()), sum(n - 1 for n in counts.values()), ignored,
                      sorted(missing), datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
                      str(payload.get("ApplicationVersion", "unknown")), decks, deck_warnings)


def filter_rows(rows: list[dict], query: str = "", cost: str = "Any", sort: str = "Cost, then name") -> list[dict]:
    query = query.strip().casefold()
    result = [r for r in rows if not query or query in " ".join(str(r.get(k, "")) for k in ("name", "ability", "keywords", "card_id")).casefold()]
    if cost != "Any":
        result = [r for r in result if isinstance(r["cost"], int) and (r["cost"] >= 6 if cost == "6+" else r["cost"] == int(cost))]
    if sort == "Name":
        return sorted(result, key=lambda r: r["name"].casefold())
    if sort == "Power, highest first":
        return sorted(result, key=lambda r: (r["power"] is None, -(r["power"] or 0), r["name"].casefold()))
    return sorted(result, key=lambda r: (r["cost"] is None, r["cost"] or 0, r["name"].casefold()))


def safe_cell(value):
    # Preserve real negative numeric power; only escape text formulas for spreadsheet viewers.
    if isinstance(value, str) and (value.startswith(("\t", "\r", "\n"))
                                  or value.lstrip().startswith(("=", "+", "-", "@", "＝", "＋", "－", "＠"))):
        return "'" + value
    return value


def render_export(rows: list[dict], columns=DEFAULT_COLUMNS, format: str = "CSV",
                  catalog: dict | None = None, collection: Collection | None = None,
                  deck_request: str = "", filtered: bool = False) -> str:
    columns = tuple(columns)
    if (not columns or "name" not in columns or any(c not in ALL_COLUMNS for c in columns)
            or len(set(columns)) != len(columns)):
        raise ValueError("Choose valid export columns, including name.")
    if not rows:
        raise ValueError("No cards match the current filters.")
    if format == "JSON":
        return json.dumps([{c: r.get(c) for c in columns} for r in rows], ensure_ascii=False, indent=2) + "\n"
    if format not in ("CSV", "TSV", "AI prompt"):
        raise ValueError("Unknown export format.")
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter="\t" if format == "TSV" else ",", lineterminator="\n", quoting=csv.QUOTE_ALL)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([safe_cell(row.get(c)) for c in columns])
    data = stream.getvalue()
    if format != "AI prompt":
        return data
    stamp = catalog.get("fetched_at", "unknown") if catalog else "unknown"
    modified = collection.modified if collection else "unknown"
    request = deck_request.strip() or "Suggest three standard 12-card decks, explain their game plans, key synergies, and substitutions from this list."
    return ("Help me build Marvel Snap decks using only the owned cards listed below.\n"
            "Do not recommend unowned cards or duplicate copies in a standard deck. "
            "Distinguish generated cards from cards I must own.\n"
            "Use the supplied cost, power, and ability text. Do not invent missing values. "
            "These are cached third-party stats; mention any suspected balance changes or uncertainty.\n"
            f"Request: {request}\n\n"
            f"Scope: {'filtered subset of' if filtered else 'all cards in'} my saved collection ({len(rows)} unique cards).\n"
            f"Collection last saved: {modified}\n"
            f"Card data: {CATALOG_URL} (retrieved {stamp}; retrieval date is not a guarantee of current balance).\n\n"
            "<owned_cards_csv>\n" + data + "</owned_cards_csv>\n")


def render_deck_export(decks: list[Deck], format: str = "Text") -> str:
    """Export exactly the selected decks, including empty decks and repeated names."""
    if not decks:
        raise ValueError("Select at least one deck to export.")
    if format == "JSON":
        return json.dumps([{"name": deck.name, "cards": deck.rows} for deck in decks], ensure_ascii=False, indent=2) + "\n"
    if format in ("CSV", "TSV"):
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, delimiter="\t" if format == "TSV" else ",", lineterminator="\n", quoting=csv.QUOTE_ALL)
        writer.writerow(("deck_number", "deck_name", *ALL_COLUMNS))
        for number, deck in enumerate(decks, 1):
            for row in deck.rows or [{}]:
                writer.writerow([number, safe_cell(deck.name), *(safe_cell(row.get(c)) for c in ALL_COLUMNS)])
        return stream.getvalue()
    if format != "Text":
        raise ValueError("Unknown deck export format.")
    parts = []
    for number, deck in enumerate(decks, 1):
        parts.append(f"Deck {number}: {deck.name}\n{len(deck.rows)} cards\n")
        for row in deck.rows:
            cost = row["cost"] if row["cost"] is not None else "?"
            power = row["power"] if row["power"] is not None else "?"
            parts.append(f"- {row['name']} (cost {cost}, power {power})\n  {row['ability']}\n")
        if not deck.rows:
            parts.append("(Empty saved deck)\n")
        parts.append("\n")
    return "".join(parts).rstrip() + "\n"


def save_export(path: Path, text: str, format: str, source: Path, *, overwrite: bool = True) -> None:
    # Never overwrite the user's input or SNAP state files through the save dialog/CLI.
    target = path.resolve()
    source = source.resolve()
    protected = (source.parent, default_collection_path().resolve().parent)
    if any(target == folder or folder in target.parents for folder in protected):
        raise ValueError("Choose an export folder outside SNAP's state folder.")
    atomic_write(path, text, encoding="utf-8-sig" if format == "CSV" else "utf-8", overwrite=overwrite)
