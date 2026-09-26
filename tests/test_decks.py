"""Offline regression coverage for saved-deck extraction and serialization."""
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from snap_extract.core import extract_collection, render_deck_export


class DeckTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.source = Path(self.folder.name) / "CollectionState.json"
        self.catalog = {"cards": {
            "A": {"card_id": "A", "name": "Alpha", "cost": 0, "power": -1, "ability": 'Draw, then "discard".\nAgain.'},
            "B": {"card_id": "B", "name": "Beta", "cost": 7, "power": 0, "ability": "No ability."}}}
        self.cards = [{"Id": "private-instance-a", "CardDefId": "A", "ArtVariantDefId": "PrivateVariant"},
                      {"Id": "private-instance-b", "CardDefId": "B"}]

    def extract(self, decks):
        payload = {"AccountId": "private-account", "ServerState": {
            "Cards": self.cards, "Decks": decks, "PremadeDecks": [{"Name": "Not my deck", "Cards": []}]}}
        self.source.write_text(json.dumps(payload), encoding="utf-8-sig")
        before = self.source.read_bytes()
        result = extract_collection(self.source, self.catalog)
        self.assertEqual(self.source.read_bytes(), before)
        return result

    def test_embedded_cards_preserve_order_and_unknowns_without_private_fields(self):
        result = self.extract([{"Name": "My deck", "Id": "private-deck", "AvatarId": "private-avatar", "Cards": [
            self.cards[1], self.cards[0], {"CardDefId": "NewCard"}]}])
        deck = result.decks[0]
        self.assertEqual([r["card_id"] for r in deck.rows], ["B", "A", "NewCard"])
        self.assertIsNone(deck.rows[2]["cost"])
        self.assertIn("UNKNOWN", deck.rows[2]["ability"])
        self.assertEqual(result.deck_warnings, [])
        self.assertEqual(len(result.rows), 2)  # Deck-only entries do not become collection ownership.
        for format_name in ("Text", "CSV", "TSV", "JSON"):
            with self.subTest(format=format_name):
                output = render_deck_export(result.decks, format_name)
                self.assertNotIn("private-", output)
                self.assertNotIn("PrivateVariant", output)
                self.assertNotIn("Not my deck", output)
                self.assertIn("NewCard", output)

    def test_instance_references_are_resolved_to_card_definitions(self):
        result = self.extract([{"Name": "References", "CardIds": ["private-instance-b", "private-instance-a"]}])
        self.assertEqual([r["card_id"] for r in result.decks[0].rows], ["B", "A"])
        self.assertEqual(result.deck_warnings, [])

    def test_malformed_decks_warn_without_breaking_collection_or_truncating_decks(self):
        for bad in (None, {}, {"Cards": None}, {"Cards": [{"CardDefId": "A"}, None]},
                    {"CardIds": ["A"]}, {"CardIds": ["private-instance-a", "unresolved"]},
                    {"Cards": [{"CardDefId": " "}]}, {"Cards": [{"CardDefId": []}]}):
            with self.subTest(bad=bad):
                result = self.extract([bad, {"Name": "Good", "Cards": self.cards}])
                self.assertEqual([d.name for d in result.decks], ["Good"])
                self.assertEqual(len(result.deck_warnings), 1)
                self.assertEqual(len(result.rows), 2)
        result = self.extract({"unexpected": "shape"})
        self.assertEqual(result.decks, [])
        self.assertIn("not a list", result.deck_warnings[0])

    def test_embedded_cards_take_precedence_over_redundant_instance_references(self):
        result = self.extract([{"Name": "Both", "Cards": self.cards, "CardIds": ["unresolved"]}])
        self.assertEqual(len(result.decks[0].rows), 2)
        self.assertEqual(result.deck_warnings, [])

    def test_empty_and_duplicate_names_are_preserved_and_unnamed_decks_get_labels(self):
        result = self.extract([{"Name": "Same", "Cards": []}, {"Name": "Same", "Cards": self.cards},
                               {"Name": " ", "Cards": []}])
        self.assertEqual([d.name for d in result.decks], ["Same", "Same", "Untitled deck 3"])
        for format_name, delimiter in (("CSV", ","), ("TSV", "\t")):
            rows = list(csv.DictReader(io.StringIO(render_deck_export(result.decks, format_name)), delimiter=delimiter))
            self.assertEqual([r["deck_number"] for r in rows], ["1", "2", "2", "3"])
            self.assertEqual(rows[0]["name"], "")
        data = json.loads(render_deck_export(result.decks, "JSON"))
        self.assertEqual(data[0], {"name": "Same", "cards": []})
        self.assertIn("Empty saved deck", render_deck_export(result.decks))

    def test_selected_subset_only_and_spreadsheet_escaping(self):
        result = self.extract([{"Name": "Excluded", "Cards": [self.cards[1]]},
                               {"Name": '=HYPERLINK("test")\nDeck', "Cards": [self.cards[0]]}])
        selected = result.decks[1:]
        for format_name in ("Text", "CSV", "TSV", "JSON"):
            output = render_deck_export(selected, format_name)
            self.assertNotIn("Excluded", output)
            self.assertNotIn("Beta", output)
        row = next(csv.DictReader(io.StringIO(render_deck_export(selected, "CSV"))))
        self.assertTrue(row["deck_name"].startswith("'="))
        self.assertEqual(row["cost"], "0")
        self.assertEqual(row["power"], "-1")
        self.assertEqual(row["ability"], self.catalog["cards"]["A"]["ability"])
        data = json.loads(render_deck_export(selected, "JSON"))[0]
        self.assertEqual(data["name"], selected[0].name)
        self.assertEqual(data["cards"][0]["power"], -1)

    def test_missing_decks_field_is_supported_and_empty_selection_rejected(self):
        self.source.write_text(json.dumps({"ServerState": {"Cards": self.cards}}), encoding="utf-8")
        result = extract_collection(self.source, self.catalog)
        self.assertEqual((result.decks, result.deck_warnings), ([], []))
        with self.assertRaisesRegex(ValueError, "Select at least one"):
            render_deck_export([])
        with self.assertRaisesRegex(ValueError, "Unknown deck export"):
            render_deck_export(self.extract([{"Name": "Empty", "Cards": []}]).decks, "invalid")


if __name__ == "__main__":
    unittest.main()
