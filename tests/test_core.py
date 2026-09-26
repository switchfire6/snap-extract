import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from snap_extract.core import (CatalogRedirectHandler, atomic_write, extract_collection, filter_rows,
                               parse_catalog, read_json, refresh_catalog, render_export, save_export, validate_catalog)
from urllib.request import Request


CARD = {"card_id": "A", "name": 'A, the "Great"', "cost": 0, "power": -1,
        "ability": "On Reveal: Draw a card, then discard one.", "series": "Series1", "keywords": "On Reveal"}


def catalog_html(key="A", name="Alpha", keywords="On Reveal", ability="<b>On Reveal:</b> Draw &amp; discard.<br>Then move."):
    return (f'<div class="card-grid__cell" data-card-key="{key}" data-card-name="{name}" '
            f'data-card-cost="0" data-card-power="-1" data-card-abilities="{keywords}">'
            f'<div><div class="card-grid__cell-description">{ability}</div></div></div>')


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "state/CollectionState.json"
        self.source.parent.mkdir()

    def write_collection(self, cards):
        self.source.write_text(json.dumps({"ServerState": {"Cards": cards, "Avatars": [{"CardDefId": "NotOwned"}]},
                                           "AccountId": "private-account", "ApplicationVersion": "56.4"}), encoding="utf-8-sig")

    def test_ownership_is_deduplicated_by_id_even_if_only_variant_is_owned(self):
        self.write_collection([{"CardDefId": "A", "ArtVariantDefId": "Variant1"},
                               {"CardDefId": "A", "ArtVariantDefId": "Variant2"},
                               {"CardDefId": "B", "ArtVariantDefId": "VariantOnly"}])
        result = extract_collection(self.source, {"cards": {"A": CARD}})
        self.assertEqual((result.instances, result.duplicates, len(result.rows)), (3, 1, 2))
        self.assertEqual(result.missing, ["B"])
        self.assertEqual(result.rows[1]["cost"], None)
        text = render_export(result.rows)
        self.assertNotIn("private-account", text)
        self.assertNotIn("Variant", text)
        self.assertNotIn("NotOwned", text)

    def test_bad_entries_are_counted_not_guessed(self):
        self.write_collection([None, 1, {}, {"CardDefId": ""}, {"CardDefId": ["A"]}, {"CardDefId": "A"}])
        result = extract_collection(self.source, {"cards": {"A": CARD}})
        self.assertEqual((result.ignored, len(result.rows)), (5, 1))

    def test_wrong_file_rejected(self):
        self.source.write_text('{"Cards": []}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "ServerState.Cards"):
            extract_collection(self.source, {"cards": {}})

    def test_broken_json_rejected(self):
        self.source.write_text('{"ServerState":', encoding="utf-8")
        with patch("snap_extract.core.time.sleep"), self.assertRaises(json.JSONDecodeError):
            extract_collection(self.source, {"cards": {}})

    def test_parser_preserves_case_and_decodes_entities(self):
        card = parse_catalog(catalog_html())["A"]
        self.assertEqual(card["ability"], "On Reveal: Draw & discard. Then move.")
        self.assertEqual((card["cost"], card["power"]), (0, -1))

    def test_no_ability_flavor_text_is_removed(self):
        card = parse_catalog(catalog_html(keywords="No Ability", ability="<i>Hulk smash!</i>"))["A"]
        self.assertEqual(card["ability"], "No ability.")

    def test_unreleased_placeholders_not_used_as_metadata(self):
        self.assertEqual(parse_catalog(catalog_html(keywords="", ability="")), {})

    def test_incomplete_catalog_rejected(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            parse_catalog(catalog_html()[:-6])

    def test_download_truncated_between_cards_rejected(self):
        page = "<html><body>" + catalog_html()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            parse_catalog(page, require_document=True)

    def test_cache_timestamp_requires_timezone(self):
        payload = {"schema": 1, "cards": {str(i): dict(CARD, card_id=str(i)) for i in range(100)}}
        for stamp in (None, 42, "not a date", "2026-09-06T12:00:00"):
            with self.subTest(stamp=stamp), self.assertRaisesRegex(ValueError, "retrieval date"):
                validate_catalog(dict(payload, fetched_at=stamp))
        validate_catalog(dict(payload, fetched_at="2026-09-06T12:00:00+00:00"))

    def test_atomic_state_replacement_is_retried(self):
        with patch.object(Path, "read_text", side_effect=[FileNotFoundError(), '{"ok": true}']), \
                patch("snap_extract.core.time.sleep"):
            self.assertEqual(read_json(self.source), {"ok": True})

    def test_failed_refresh_does_not_destroy_cache(self):
        cache = self.root / "catalog.json"
        cache.write_text("previous cache", encoding="utf-8")
        response = io.BytesIO(b"<html>Service unavailable</html>")
        with patch("snap_extract.core.urllib.request.OpenerDirector.open", return_value=response):
            with self.assertRaisesRegex(ValueError, "incomplete"):
                refresh_catalog(cache)
        self.assertEqual(cache.read_text(), "previous cache")

    def test_redirects_cannot_downgrade_https_or_leave_catalog_origin(self):
        handler = CatalogRedirectHandler()
        request = Request("https://snap.fan/cards/")
        for url in ("http://snap.fan/cards/", "https://example.com/", "https://snap.fan.evil.test/",
                    "https://snap.fan:444/cards/", "https://user:password@snap.fan/cards/"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                handler.redirect_request(request, None, 302, "Found", {}, url)
        result = handler.redirect_request(request, None, 302, "Found", {}, "https://snap.fan/cards/?page=1")
        self.assertEqual(result.full_url, "https://snap.fan/cards/?page=1")

    def test_oversized_catalog_preserves_cache(self):
        cache = self.root / "catalog.json"
        cache.write_text("previous cache", encoding="utf-8")
        with patch("snap_extract.core.urllib.request.OpenerDirector.open", return_value=io.BytesIO(b"x" * 8_000_001)):
            with self.assertRaisesRegex(ValueError, "large"):
                refresh_catalog(cache)
        self.assertEqual(cache.read_text(), "previous cache")

    def test_cache_rejects_malformed_optional_fields(self):
        payload = {"schema": 1, "fetched_at": "2026-09-06T12:00:00+00:00",
                   "cards": {str(i): dict(CARD, card_id=str(i)) for i in range(100)}}
        for field in ("series", "keywords", "card_type"):
            with self.subTest(field=field):
                malformed = dict(payload, cards=dict(payload["cards"], bad=dict(CARD, card_id="bad", **{field: {}})))
                with self.assertRaisesRegex(ValueError, "Invalid card data"):
                    validate_catalog(malformed)

    def test_csv_round_trip_quotes_commas_newlines_and_negative_power(self):
        card = dict(CARD, ability='Line one, "quoted"\nLine two')
        text = render_export([card])
        row = next(csv.DictReader(io.StringIO(text)))
        self.assertEqual(row, {"name": card["name"], "cost": "0", "power": "-1", "ability": card["ability"]})

    def test_text_formulas_escaped_but_numeric_power_preserved(self):
        text = render_export([dict(CARD, name="=HYPERLINK(test)")])
        row = next(csv.DictReader(io.StringIO(text)))
        self.assertTrue(row["name"].startswith("'="))
        self.assertEqual(row["power"], "-1")

    def test_json_preserves_numeric_and_unknown_values(self):
        result = json.loads(render_export([dict(CARD, cost=None)], format="JSON"))[0]
        self.assertIsNone(result["cost"])
        self.assertEqual(result["power"], -1)

    def test_spreadsheet_control_characters_and_fullwidth_formulas(self):
        for name in ("\ttext", "\rtext", "\ntext", "  =1+1", "＝1+1", "＋1+1", "－1+1", "＠SUM(1)"):
            for format_name, delimiter in (("CSV", ","), ("TSV", "\t")):
                with self.subTest(name=name, format=format_name):
                    data = render_export([dict(CARD, name=name)], format=format_name)
                    row = next(csv.DictReader(io.StringIO(data, newline=""), delimiter=delimiter))
                    self.assertEqual(row["name"], "'" + name)
                    self.assertEqual(row["power"], "-1")

    def test_embedded_carriage_return_cannot_create_an_unquoted_record(self):
        name = "Alpha\r=1+1"
        data = render_export([dict(CARD, name=name)])
        rows = list(csv.DictReader(io.StringIO(data, newline="")))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], name)

    def test_filter_high_cost_unknown_and_zero_power(self):
        rows = [CARD, dict(CARD, name="Big", cost=8, power=0), dict(CARD, name="Missing", cost=None, power=None)]
        self.assertEqual([r["name"] for r in filter_rows(rows, cost="6+")], ["Big"])
        self.assertEqual(len(filter_rows(rows, query="discard", cost="0")), 1)
        self.assertEqual([r["name"] for r in filter_rows(rows, sort="Power, highest first")], ["Big", CARD["name"], "Missing"])

    def test_prompt_marks_filtered_scope_and_source(self):
        result = render_export([CARD], format="AI prompt", filtered=True, deck_request="Build an Ongoing deck.")
        self.assertIn("filtered subset", result)
        self.assertIn("Build an Ongoing deck.", result)
        self.assertIn("https://snap.fan/cards/", result)
        self.assertIn("Do not invent missing values", result)

    def test_protected_save_and_utf8_bom(self):
        self.write_collection([])
        before = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, "outside"):
            save_export(self.source, "oops", "CSV", self.source)
        with self.assertRaises(ValueError):
            save_export(self.source.parent / "nested/output.csv", "oops", "CSV", self.source)
        self.assertEqual(self.source.read_bytes(), before)
        output = self.root / "exports/cards.csv"
        save_export(output, render_export([CARD]), "CSV", self.source)
        self.assertTrue(output.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_default_game_state_protected_even_when_reading_a_copy(self):
        game_file = self.root / "game/CollectionState.json"
        with patch("snap_extract.core.default_collection_path", return_value=game_file):
            with self.assertRaisesRegex(ValueError, "outside"):
                save_export(game_file.parent / "other.json", "oops", "JSON", self.source)
        self.assertFalse(game_file.parent.exists())

    def test_exclusive_atomic_write_does_not_replace_existing_file(self):
        output = self.root / "result.txt"
        atomic_write(output, "first", overwrite=False)
        with self.assertRaises(FileExistsError):
            atomic_write(output, "second", overwrite=False)
        self.assertEqual(output.read_text(), "first")
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["result.txt", "state"])

    def test_empty_export_and_invalid_columns_rejected(self):
        for rows, columns in [([], ["name"]), ([CARD], []), ([CARD], ["account_id"]),
                              ([CARD], ["power"]), ([CARD], ["name", "name"])]:
            with self.assertRaises(ValueError):
                render_export(rows, columns)


if __name__ == "__main__":
    unittest.main()
