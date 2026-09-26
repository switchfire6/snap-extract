"""Native UI integration tests using synthetic ownership and no network."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from snap_extract.gui import App


class GuiTests(unittest.TestCase):
    def test_load_filter_preview_copy_and_save(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "state/CollectionState.json"
            source.parent.mkdir()
            source.write_text(json.dumps({"ServerState": {
                "Cards": [{"CardDefId": "A"}, {"CardDefId": "A"}, {"CardDefId": "B"}],
                "Decks": [{"Name": "First deck", "Cards": [{"CardDefId": "A"}]},
                          {"Name": "Second deck", "Cards": [{"CardDefId": "B"}]}]}}))
            catalog = {"fetched_at": "2026-09-06T12:00:00+00:00", "cards": {
                "A": {"card_id": "A", "name": "Alpha", "cost": 1, "power": 2, "ability": "Ongoing: Test.", "keywords": "Ongoing"},
                "B": {"card_id": "B", "name": "Beta", "cost": 7, "power": 0, "ability": "No ability."}}}
            with patch("snap_extract.gui.app_data_dir", return_value=root), \
                 patch("snap_extract.gui.default_collection_path", return_value=source), \
                 patch("snap_extract.gui.load_catalog", return_value=catalog), \
                 patch("snap_extract.gui.refresh_catalog", side_effect=AssertionError("Unexpected network call")):
                app = App()
                app.withdraw()
                try:
                    errors = []
                    app.report_callback_exception = lambda *args: errors.append(args)
                    deadline = time.monotonic() + 5
                    while app.collection is None and time.monotonic() < deadline:
                        app.update()
                        time.sleep(0.02)
                    self.assertIsNotNone(app.collection)
                    self.assertEqual(len(app.tree.get_children()), 2)
                    self.assertEqual(app.collection.duplicates, 1)
                    original = app.output
                    with patch("snap_extract.gui.refresh_catalog", side_effect=OSError("Offline")), \
                            patch("snap_extract.gui.messagebox.showerror") as error_dialog:
                        app.load(refresh=True)
                        deadline = time.monotonic() + 5
                        while app.busy and time.monotonic() < deadline:
                            app.update()
                            time.sleep(0.02)
                        self.assertFalse(app.busy)
                        self.assertEqual(app.output, original)
                        error_dialog.assert_called_once()
                    app.cost.set("6+")
                    self.assertEqual([r["name"] for r in app.rows], ["Beta"])
                    app.format.set("AI prompt")
                    self.assertIn("filtered subset", app.output)
                    app.query.set("nothing matches")
                    self.assertEqual(app.output, "")
                    self.assertIn("disabled", app.save_button.state())
                    app.reset_filters()
                    app.format.set("CSV")
                    app.columns["card_id"].set(True)
                    self.assertIn("card_id", app.output.splitlines()[0])
                    app.copy()
                    self.assertEqual(app.clipboard_get(), app.output)
                    destination = root / "export.csv"
                    with patch("snap_extract.gui.filedialog.asksaveasfilename", return_value=str(destination)):
                        app.save()
                    self.assertEqual(destination.read_text(encoding="utf-8-sig"), app.output)
                    app.tree.selection_set("0")
                    app.select_card()
                    self.assertIn("Ongoing: Test.", app.detail.get())
                    with patch.object(app.tree, "delete", wraps=app.tree.delete) as delete_rows:
                        app.format.set("JSON")
                        app.deck_request.set("Prefer Ongoing cards")
                        self.assertEqual(app.tree.selection(), ("0",))
                        self.assertIn("Ongoing: Test.", app.detail.get())
                        delete_rows.assert_not_called()
                    # Deck exports ignore collection filters and use their own selection.
                    app.query.set("nothing matches")
                    self.assertNotIn("disabled", app.decks_button.state())
                    dialog = app.open_decks()
                    try:
                        app.update()
                        self.assertIn("First deck", dialog.output)
                        self.assertIn("Second deck", dialog.output)
                        dialog.select_all(False)
                        self.assertEqual(dialog.output, "")
                        self.assertIn("disabled", dialog.save_button.state())
                        with patch("snap_extract.deck_gui.filedialog.asksaveasfilename") as choose:
                            dialog.save()
                            choose.assert_not_called()
                        dialog.tree.focus("1")
                        dialog.toggle_focused()
                        app.update()
                        self.assertEqual(dialog.selected, {1})
                        self.assertIn("Second deck", dialog.output)
                        self.assertNotIn("First deck", dialog.output)
                        dialog.copy()
                        self.assertEqual(app.clipboard_get(), dialog.output)
                        dialog.format.set("JSON")
                        destination = root / "decks.json"
                        with patch("snap_extract.deck_gui.filedialog.asksaveasfilename", return_value=str(destination)):
                            dialog.save()
                        self.assertEqual(json.loads(destination.read_text())[0]["name"], "Second deck")
                        self.assertEqual(len(json.loads(destination.read_text())), 1)
                        before = source.read_bytes()
                        with patch("snap_extract.deck_gui.filedialog.asksaveasfilename", return_value=str(source)), \
                                patch("snap_extract.deck_gui.messagebox.showerror") as error_dialog:
                            dialog.save()
                            error_dialog.assert_called_once()
                        self.assertEqual(source.read_bytes(), before)
                        dialog.select_all(True)
                        dialog.format.set("CSV")
                        destination = root / "decks.csv"
                        with patch("snap_extract.deck_gui.filedialog.asksaveasfilename", return_value=str(destination)):
                            dialog.save()
                        self.assertTrue(destination.read_bytes().startswith(b"\xef\xbb\xbf"))
                        self.assertEqual(destination.read_text(encoding="utf-8-sig"), dialog.output)
                    finally:
                        dialog.close()
                    self.assertEqual(app.deck_format, "CSV")
                    self.assertEqual(json.loads((root / "settings.json").read_text())["deck_format"], "CSV")
                    app.collection.decks = []
                    dialog = app.open_decks()
                    try:
                        self.assertIn("No saved decks found", dialog.status.get())
                        self.assertIn("disabled", dialog.copy_button.state())
                    finally:
                        dialog.close()
                    app.path.set(str(root / "different.json"))
                    self.assertEqual(app.output, "")
                    self.assertEqual(app.tree.get_children(), ())
                    self.assertIn("disabled", app.decks_button.state())
                    self.assertEqual(errors, [])
                finally:
                    app.destroy()


if __name__ == "__main__":
    unittest.main()
