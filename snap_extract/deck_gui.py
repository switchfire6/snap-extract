"""Select and export saved decks from the loaded collection snapshot."""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import render_deck_export, save_export


class DeckExportDialog(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.decks = app.collection.decks
        self.source = app.source
        self.selected = set(range(len(self.decks)))
        self.output = ""
        self.format = tk.StringVar(self, value=app.deck_format)
        self.summary = tk.StringVar(self)
        self.status = tk.StringVar(self, value="Choose decks to share or back up. Card order is preserved.")
        self.title("Export saved decks — Snap Extract")
        self.configure(bg=app.cget("bg"))
        self.geometry("980x720")
        self.minsize(760, 580)
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self.close)

        outer = ttk.Frame(self, padding=20)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Export saved decks", font=("Segoe UI Semibold", 20)).pack(anchor="w")
        ttk.Label(outer, text="Click a deck to include or exclude it. Collection search and cost filters do not apply.",
                  style="Muted.TLabel", wraplength=700).pack(anchor="w", pady=(5, 12))

        actions = ttk.Frame(outer)
        actions.pack(side="bottom", fill="x", pady=(12, 0))
        ttk.Label(actions, textvariable=self.status, style="Muted.TLabel", wraplength=700).pack(fill="x", pady=(0, 10))
        buttons = ttk.Frame(actions)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Close", command=self.close).pack(side="left")
        self.save_button = ttk.Button(buttons, text="Save selected…", style="Accent.TButton", command=self.save)
        self.save_button.pack(side="right")
        self.copy_button = ttk.Button(buttons, text="Copy selected", command=self.copy)
        self.copy_button.pack(side="right", padx=8)

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 10))
        ttk.Button(controls, text="Select all", command=lambda: self.select_all(True)).pack(side="left")
        ttk.Button(controls, text="Clear selection", command=lambda: self.select_all(False)).pack(side="left", padx=8)
        ttk.Combobox(controls, textvariable=self.format, values=("Text", "CSV", "TSV", "JSON"),
                     state="readonly", width=10).pack(side="right")
        ttk.Label(controls, text="Format", style="Muted.TLabel").pack(side="right", padx=8)
        ttk.Label(outer, textvariable=self.summary, style="Muted.TLabel").pack(anchor="w", pady=(0, 8))

        deck_frame = ttk.Frame(outer, style="Panel.TFrame")
        deck_frame.pack(fill="x")
        self.tree = ttk.Treeview(deck_frame, columns=("include", "name", "cards"), show="headings",
                                 selectmode="browse", height=5)
        for key, label, width in (("include", "Export", 65), ("name", "Saved deck", 460), ("cards", "Cards", 70)):
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, minwidth=width if key != "name" else 180,
                             stretch=key == "name", anchor="w" if key == "name" else "center")
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(deck_frame, command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.bind("<Configure>", self.resize_deck_list)
        for index, deck in enumerate(self.decks):
            self.tree.insert("", "end", iid=str(index), values=("☑", deck.name, len(deck.rows)))
        self.tree.bind("<Button-1>", self.click_deck)
        self.tree.bind("<space>", self.toggle_focused)
        self.tree.bind("<Return>", self.toggle_focused)
        if self.decks:
            self.tree.focus("0")
            self.tree.selection_set("0")
        else:
            self.status.set("No saved decks found. Save a deck in SNAP, then reload the collection.")

        if app.collection.deck_warnings:
            warnings = app.collection.deck_warnings
            warning_text = "\n".join(warnings[:2])
            if len(warnings) > 2:
                warning_text += f"\n{len(warnings) - 2} more unreadable decks were skipped. Reload after opening SNAP."
            ttk.Label(outer, text=warning_text, foreground="#ffd38a",
                      wraplength=700).pack(fill="x", pady=(8, 0))
        ttk.Label(outer, text="Export preview", style="Muted.TLabel").pack(anchor="w", pady=(12, 6))
        preview_frame = ttk.Frame(outer, style="Panel.TFrame")
        preview_frame.pack(fill="both", expand=True)
        self.preview = tk.Text(preview_frame, bg="#191f2d", fg="#eff2f8", relief="flat", wrap="word",
                               font=("Consolas", 10), padx=12, pady=10, state="disabled", height=6, width=1)
        self.preview.pack(side="left", fill="both", expand=True)
        preview_scroll = ttk.Scrollbar(preview_frame, command=self.preview.yview)
        preview_scroll.pack(side="right", fill="y")
        self.preview.configure(yscrollcommand=preview_scroll.set)
        self.format.trace_add("write", lambda *_: self.update_preview())
        self.bind("<Control-s>", lambda _: self.save())
        self.bind("<Escape>", lambda _: self.close())
        self.update_preview()
        # Keep this snapshot and its source together until the dialog closes.
        self.grab_set()
        self.tree.focus_set()

    def resize_deck_list(self, event):
        if event.widget is self:
            self.tree.configure(height=3 if event.height < 660 else 5)

    def selected_decks(self):
        return [deck for index, deck in enumerate(self.decks) if index in self.selected]

    def click_deck(self, event):
        row = self.tree.identify_row(event.y)
        if row and self.tree.identify_region(event.x, event.y) == "cell":
            self.tree.focus(row)
            self.tree.selection_set(row)
            self.tree.focus_set()
            self.toggle_focused()
            return "break"

    def toggle_focused(self, _=None):
        row = self.tree.focus()
        if row:
            index = int(row)
            self.selected.symmetric_difference_update({index})
            self.tree.set(row, "include", "☑" if index in self.selected else "☐")
            self.update_preview()
        return "break"

    def select_all(self, include):
        self.selected = set(range(len(self.decks))) if include else set()
        for row in self.tree.get_children():
            self.tree.set(row, "include", "☑" if include else "☐")
        self.update_preview()

    def update_preview(self):
        decks = self.selected_decks()
        self.summary.set(f"{len(decks)} of {len(self.decks)} decks selected · {sum(len(deck.rows) for deck in decks)} cards")
        self.output = render_deck_export(decks, self.format.get()) if decks else ""
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", self.output or "Select at least one saved deck to preview and export.")
        self.preview.configure(state="disabled")
        state = "normal" if self.output else "disabled"
        self.copy_button.configure(state=state)
        self.save_button.configure(state=state)

    def copy(self):
        if not self.output:
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(self.output)
            self.update_idletasks()
            self.status.set(f"Copied {len(self.selected)} selected decks as {self.format.get()}.")
        except tk.TclError as exc:
            messagebox.showerror("Clipboard unavailable", str(exc), parent=self)

    def save(self):
        if not self.output:
            return
        format_name = self.format.get()
        extension = {"Text": ".txt", "CSV": ".csv", "TSV": ".tsv", "JSON": ".json"}[format_name]
        folder = Path(self.app.export_dir)
        filename = filedialog.asksaveasfilename(parent=self, title="Save selected decks",
            initialdir=str(folder if folder.is_dir() else Path.home()), initialfile="snap-decks" + extension,
            defaultextension=extension, filetypes=[(format_name + " file", "*" + extension)])
        if filename:
            try:
                save_export(Path(filename), self.output, format_name, self.source)
            except (OSError, ValueError) as exc:
                messagebox.showerror("Could not save decks", str(exc), parent=self)
                return
            self.app.export_dir = str(Path(filename).parent)
            self.app.deck_format = format_name
            self.app.persist()
            self.status.set(f"Saved {len(self.selected)} selected decks to {filename}")

    def close(self):
        self.app.deck_format = self.format.get()
        self.app.persist()
        self.grab_release()
        self.destroy()
