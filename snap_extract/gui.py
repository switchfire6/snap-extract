"""Small native desktop interface. All collection processing stays on this PC."""
from __future__ import annotations

import json
import queue
import threading
import tkinter as tk
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import (ALL_COLUMNS, DEFAULT_COLUMNS, app_data_dir, atomic_write,
                   default_collection_path, extract_collection, filter_rows,
                   load_catalog, read_json, refresh_catalog, render_export, save_export)

BG = "#10141f"
PANEL = "#191f2d"
FIELD = "#222b3b"
TEXT = "#eff2f8"
MUTED = "#a5b2c7"
ACCENT = "#84edcc"


class App(tk.Tk):
    def __init__(self, collection_path: Path | None = None):
        super().__init__()
        # Layout dimensions are in physical pixels; use matching, crisp font sizes
        # instead of letting Windows font scaling overrun the fixed initial window.
        self.tk.call("tk", "scaling", 4 / 3)
        self.title("Snap Extract")
        self.geometry("1180x840")
        self.minsize(960, 740)
        self.configure(bg=BG)
        self.catalog = None
        self.collection = None
        self.source = None
        self.rows = []
        self.output = ""
        self.busy = False
        self.jobs = queue.Queue()
        self.settings_path = app_data_dir() / "settings.json"
        try:
            settings = read_json(self.settings_path)
            if not isinstance(settings, dict):
                settings = {}
        except (OSError, ValueError):
            settings = {}
        self.path = tk.StringVar(value=str(collection_path or settings.get("collection_path", default_collection_path())))
        self.format = tk.StringVar(value=settings.get("format", "CSV"))
        if self.format.get() not in ("CSV", "AI prompt", "TSV", "JSON"):
            self.format.set("CSV")
        self.query = tk.StringVar()
        self.cost = tk.StringVar(value="Any")
        self.sort = tk.StringVar(value="Cost, then name")
        selected = settings.get("columns", DEFAULT_COLUMNS)
        if not isinstance(selected, list):
            selected = DEFAULT_COLUMNS
        self.columns = {c: tk.BooleanVar(value=c == "name" or c in selected) for c in ALL_COLUMNS}
        self.deck_request = tk.StringVar(value=str(settings.get("deck_request", "")))
        self.export_dir = str(settings.get("export_dir", Path.home() / "Documents/Snap Extract"))
        self.status = tk.StringVar(value="Loading your collection…")
        self.catalog_status = tk.StringVar(value="Reading cached card data…")
        self.summary = tk.StringVar(value="Your collection, ready for the next deck.")
        self.count = tk.StringVar(value="—")
        self.detail = tk.StringVar(value="Select a card to read its full ability.")
        self._style()
        self._build()
        for variable in (self.query, self.cost, self.sort, self.format, self.deck_request, *self.columns.values()):
            variable.trace_add("write", lambda *_: self.update_preview())
        self.path.trace_add("write", self._path_changed)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Control-r>", lambda _: self.load())
        self.bind("<Control-s>", lambda _: self.save())
        self.after(60, self.load)
        self.after(100, self.poll)

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background=BG, foreground=TEXT)
        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Panel.TLabel", background=PANEL)
        style.configure("PanelMuted.TLabel", background=PANEL, foreground=MUTED)
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 27))
        style.configure("Section.TLabel", font=("Segoe UI Semibold", 12), background=PANEL)
        style.configure("Count.TLabel", font=("Segoe UI Semibold", 30), foreground=ACCENT, background=PANEL)
        style.configure("TButton", padding=(13, 9), background=FIELD, borderwidth=0)
        style.map("TButton", background=[("active", "#34425a"), ("disabled", PANEL)], foreground=[("disabled", "#778399")])
        style.configure("Accent.TButton", foreground=BG, background=ACCENT, font=("Segoe UI Semibold", 10))
        style.map("Accent.TButton", background=[("active", "#aff5de"), ("disabled", FIELD)], foreground=[("disabled", MUTED)])
        style.configure("TEntry", padding=7, fieldbackground=FIELD, foreground=TEXT, insertcolor=TEXT, bordercolor=FIELD)
        style.configure("TCombobox", padding=7, fieldbackground=FIELD, background=FIELD, foreground=TEXT, arrowcolor=ACCENT)
        style.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", TEXT)], selectbackground=[("readonly", FIELD)])
        style.configure("TCheckbutton", background=PANEL, foreground=TEXT, padding=(0, 3))
        style.map("TCheckbutton", background=[("active", PANEL)], foreground=[("disabled", MUTED)])
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=TEXT, rowheight=33, borderwidth=0)
        style.configure("Treeview.Heading", background=FIELD, foreground=MUTED, font=("Segoe UI Semibold", 10), padding=8)
        style.map("Treeview", background=[("selected", "#2a4b50")], foreground=[("selected", TEXT)])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=FIELD, padding=(18, 10))
        style.map("TNotebook.Tab", background=[("selected", PANEL)], foreground=[("selected", ACCENT)])
        self.option_add("*TCombobox*Listbox.background", FIELD)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)

    def _build(self):
        outer = ttk.Frame(self, padding=26)
        outer.pack(fill="both", expand=True)
        title = ttk.Frame(outer)
        title.pack(fill="x")
        ttk.Label(title, text="SNAP EXTRACT", style="Title.TLabel").pack(side="left")
        ttk.Label(title, text="LOCAL COLLECTION  /  CLEAN EXPORT", style="Muted.TLabel").pack(side="right", pady=(10, 0))
        ttk.Label(outer, text="Bring your cards. Build something better.", style="Muted.TLabel").pack(anchor="w", pady=(4, 19))

        source = ttk.Frame(outer, style="Panel.TFrame", padding=14)
        source.pack(fill="x", pady=(0, 18))
        ttk.Label(source, text="COLLECTION FILE", style="PanelMuted.TLabel").pack(anchor="w", pady=(0, 7))
        line = ttk.Frame(source, style="Panel.TFrame")
        line.pack(fill="x")
        self.path_entry = ttk.Entry(line, textvariable=self.path)
        self.path_entry.pack(side="left", fill="x", expand=True)
        self.browse_button = ttk.Button(line, text="Browse…", command=self.browse)
        self.browse_button.pack(side="left", padx=8)
        self.load_button = ttk.Button(line, text="Load collection", command=self.load)
        self.load_button.pack(side="left")

        # Reserve the action area before allocating remaining space to the table.
        footer = ttk.Frame(outer)
        footer.pack(side="bottom", fill="x", pady=(17, 0))
        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        sidebar_host = ttk.Frame(body, style="Panel.TFrame", width=265)
        sidebar_host.pack(side="left", fill="y", padx=(0, 18))
        sidebar_canvas = tk.Canvas(sidebar_host, width=263, bg=PANEL, highlightthickness=0)
        sidebar_scroll = ttk.Scrollbar(sidebar_host, orient="vertical", command=sidebar_canvas.yview)
        sidebar_scroll.pack(side="right", fill="y")
        sidebar_canvas.pack(side="left", fill="both", expand=True)
        sidebar_canvas.configure(yscrollcommand=sidebar_scroll.set)
        sidebar = ttk.Frame(sidebar_canvas, style="Panel.TFrame", padding=18)
        sidebar_window = sidebar_canvas.create_window(0, 0, window=sidebar, anchor="nw")
        sidebar.bind("<Configure>", lambda _: sidebar_canvas.configure(scrollregion=sidebar_canvas.bbox("all")))
        sidebar_canvas.bind("<Configure>", lambda e: sidebar_canvas.itemconfigure(sidebar_window, width=e.width))
        ttk.Label(sidebar, textvariable=self.count, style="Count.TLabel").pack(anchor="w")
        ttk.Label(sidebar, text="unique cards in your collection", style="PanelMuted.TLabel").pack(anchor="w", pady=(0, 17))
        ttk.Label(sidebar, text="Export options", style="Section.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(sidebar, text="Format", style="PanelMuted.TLabel").pack(anchor="w")
        ttk.Combobox(sidebar, textvariable=self.format, values=("CSV", "AI prompt", "TSV", "JSON"), state="readonly", width=25).pack(fill="x", pady=(5, 7))
        self.format_hint = ttk.Label(sidebar, text="", style="PanelMuted.TLabel", wraplength=230)
        self.format_hint.pack(anchor="w", pady=(0, 15))
        ttk.Label(sidebar, text="Include columns", style="PanelMuted.TLabel").pack(anchor="w", pady=(0, 5))
        column_grid = ttk.Frame(sidebar, style="Panel.TFrame")
        column_grid.pack(fill="x")
        for index, column in enumerate(ALL_COLUMNS):
            ttk.Checkbutton(column_grid, text=column.replace("_", " ").capitalize(), variable=self.columns[column],
                            state="disabled" if column == "name" else "normal").grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 13))
        ttk.Label(sidebar, text="AI deck request (optional)", style="PanelMuted.TLabel").pack(anchor="w", pady=(14, 5))
        ttk.Entry(sidebar, textvariable=self.deck_request, width=26).pack(fill="x")
        ttk.Label(sidebar, text="Example: a consistent Ongoing deck", style="PanelMuted.TLabel", wraplength=235).pack(anchor="w", pady=(5, 13))
        ttk.Label(sidebar, text="Variants, splits, cosmetics, and account details are left out automatically.",
                  style="PanelMuted.TLabel", wraplength=235).pack(anchor="w", side="bottom", pady=(10, 0))

        main = ttk.Frame(body)
        main.pack(side="left", fill="both", expand=True)
        filters = ttk.Frame(main)
        filters.pack(fill="x", pady=(0, 10))
        ttk.Label(filters, text="Search", style="Muted.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))
        ttk.Label(filters, text="Cost", style="Muted.TLabel").grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(filters, text="Sort", style="Muted.TLabel").grid(row=0, column=2, sticky="w")
        ttk.Entry(filters, textvariable=self.query, width=18).grid(row=1, column=0, sticky="ew")
        ttk.Combobox(filters, textvariable=self.cost, values=("Any", "0", "1", "2", "3", "4", "5", "6+"), state="readonly", width=5).grid(row=1, column=1, padx=8)
        ttk.Combobox(filters, textvariable=self.sort, values=("Cost, then name", "Name", "Power, highest first"), state="readonly", width=21).grid(row=1, column=2)
        ttk.Button(filters, text="Reset", command=self.reset_filters).grid(row=1, column=3, padx=(8, 0))
        filters.columnconfigure(0, weight=1)
        ttk.Label(main, textvariable=self.summary, style="Muted.TLabel", wraplength=650).pack(anchor="w", pady=(0, 9))

        self.detail_label = ttk.Label(main, textvariable=self.detail, style="Muted.TLabel", wraplength=670)
        self.detail_label.pack(side="bottom", fill="x", pady=(10, 0))
        main.bind("<Configure>", lambda event: self.detail_label.configure(wraplength=max(200, event.width - 10)))
        tabs = ttk.Notebook(main)
        tabs.pack(fill="both", expand=True)
        cards_tab = ttk.Frame(tabs, style="Panel.TFrame")
        text_tab = ttk.Frame(tabs, style="Panel.TFrame")
        tabs.add(cards_tab, text="Collection")
        tabs.add(text_tab, text="Export preview")
        self.tree = ttk.Treeview(cards_tab, columns=("name", "cost", "power", "ability"), show="headings", selectmode="browse")
        for name, width in (("name", 175), ("cost", 65), ("power", 70), ("ability", 350)):
            self.tree.heading(name, text=name.capitalize())
            self.tree.column(name, width=width, minwidth=45, stretch=name in ("name", "ability"), anchor="center" if name in ("cost", "power") else "w")
        scroll = ttk.Scrollbar(cards_tab, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(cards_tab, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=horizontal.set)
        horizontal.grid(row=1, column=0, sticky="ew")
        cards_tab.rowconfigure(0, weight=1)
        cards_tab.columnconfigure(0, weight=1)
        self.tree.tag_configure("alternate", background="#1d2534")
        self.tree.bind("<<TreeviewSelect>>", self.select_card)
        self.preview = tk.Text(text_tab, bg=PANEL, fg=TEXT, insertbackground=TEXT, relief="flat", wrap="word",
                               font=("Consolas", 10), padx=15, pady=12, state="disabled")
        self.preview.pack(side="left", fill="both", expand=True)
        text_scroll = ttk.Scrollbar(text_tab, command=self.preview.yview)
        text_scroll.pack(side="right", fill="y")
        self.preview.configure(yscrollcommand=text_scroll.set)

        def scroll_options(event):
            widget = self.winfo_containing(event.x_root, event.y_root)
            if widget is not None and str(widget).startswith(str(sidebar_host)):
                sidebar_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
                return "break"
        self.bind("<MouseWheel>", scroll_options)

        bottom = ttk.Frame(footer)
        bottom.pack(fill="x")
        info = ttk.Frame(bottom)
        info.pack(side="left", fill="x", expand=True)
        ttk.Label(info, textvariable=self.catalog_status, style="Muted.TLabel").pack(anchor="w")
        link = ttk.Label(info, text="Card data: snap.fan  ↗", style="Muted.TLabel", cursor="hand2")
        link.pack(anchor="w", pady=(4, 0))
        link.bind("<Button-1>", lambda _: webbrowser.open("https://snap.fan/cards/"))
        self.refresh_button = ttk.Button(bottom, text="Refresh card data", command=lambda: self.load(refresh=True))
        self.refresh_button.pack(side="left", padx=6)
        self.copy_button = ttk.Button(bottom, text="Copy export", command=self.copy)
        self.copy_button.pack(side="left", padx=6)
        self.save_button = ttk.Button(bottom, text="Save CSV…", style="Accent.TButton", command=self.save)
        self.save_button.pack(side="left", padx=(6, 0))
        status_label = ttk.Label(footer, textvariable=self.status, style="Muted.TLabel", wraplength=1100)
        status_label.pack(anchor="w", pady=(13, 0))
        footer.bind("<Configure>", lambda event: status_label.configure(wraplength=max(200, event.width)))
        self.set_busy(False)

    def set_busy(self, busy):
        self.busy = busy
        for widget in (self.load_button, self.refresh_button, self.browse_button, self.path_entry):
            widget.configure(state="disabled" if busy else "normal")
        self.update_actions()

    def update_actions(self):
        state = "normal" if self.output and not self.busy else "disabled"
        self.copy_button.configure(state=state)
        self.save_button.configure(state=state)

    def _path_changed(self, *_):
        self.output = ""
        self.collection = None
        self.update_preview()
        self.count.set("—")
        self.summary.set("Load the selected collection to preview and export it.")

    def browse(self):
        path = filedialog.askopenfilename(title="Choose CollectionState.json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")])
        if path:
            self.path.set(path)
            self.load()

    def load(self, refresh=False):
        if self.busy:
            return
        source = Path(self.path.get()).expanduser()
        self.set_busy(True)
        self.status.set("Downloading the public catalog; your collection stays on this PC…" if refresh else "Reading collection and cached card data…")

        def worker():
            try:
                if not source.is_file():
                    raise FileNotFoundError("Collection file not found. Open SNAP once, or use Browse to choose CollectionState.json.")
                if refresh:
                    catalog = refresh_catalog()
                else:
                    try:
                        catalog = load_catalog()
                    except (OSError, ValueError, KeyError, TypeError):
                        catalog = refresh_catalog()
                result = extract_collection(source, catalog)
                self.jobs.put(("loaded", (source, catalog, result)))
            except Exception as exc:
                self.jobs.put(("error", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            kind, payload = self.jobs.get_nowait()
        except queue.Empty:
            pass
        else:
            self.set_busy(False)
            if kind == "loaded":
                self.source, self.catalog, self.collection = payload
                self.count.set(str(len(self.collection.rows)))
                stamp = datetime.fromisoformat(self.catalog["fetched_at"])
                age = (datetime.now(timezone.utc) - stamp.astimezone(timezone.utc)).days
                self.catalog_status.set(f"Catalog retrieved {stamp.astimezone():%b %d, %Y}" + (" · refresh recommended" if age >= 7 else " · cached locally"))
                self.update_preview()
                warnings = []
                if self.collection.missing:
                    warnings.append(f"{len(self.collection.missing)} cards have UNKNOWN stats. Refresh card data.")
                if self.collection.ignored:
                    warnings.append(f"Skipped {self.collection.ignored} malformed entries without a card ID.")
                self.status.set(" ".join(warnings) or "Ready. Filters apply to both preview and export. Collection last saved " + self.collection.modified[:16].replace("T", " ") + ".")
                self.persist()
            else:
                self.status.set("Could not load: " + payload)
                messagebox.showerror("Could not load collection", payload + ("\n\nYour previous preview and cached card data are still available." if self.output else "\n\nAn internet connection is needed for the first card catalog download."))
        self.after(100, self.poll)

    def reset_filters(self):
        self.query.set("")
        self.cost.set("Any")
        self.sort.set("Cost, then name")

    def update_preview(self):
        self.format_hint.configure(text={"CSV": "Compact and easy to paste into an AI or open in a spreadsheet.",
            "AI prompt": "Your cards plus deck-building instructions, ready to paste into an AI.",
            "TSV": "Tab-separated columns for pasting directly into a spreadsheet.",
            "JSON": "Structured data for scripts and other tools."}[self.format.get()])
        self.save_button.configure(text=f"Save {'prompt' if self.format.get() == 'AI prompt' else self.format.get()}…")
        self.rows = filter_rows(self.collection.rows, self.query.get(), self.cost.get(), self.sort.get()) if self.collection else []
        self.tree.delete(*self.tree.get_children())
        for index, row in enumerate(self.rows):
            self.tree.insert("", "end", iid=str(index), values=tuple(row[c] if row[c] is not None else "?" for c in DEFAULT_COLUMNS), tags=("alternate",) if index % 2 else ())
        self.detail.set("Select a card to read its full ability.")
        if self.collection:
            self.summary.set(f"{len(self.rows)} of {len(self.collection.rows)} cards in export  ·  {self.collection.duplicates} duplicate copies removed")
        columns = [c for c, variable in self.columns.items() if variable.get()]
        self.output = render_export(self.rows, columns, self.format.get(), self.catalog, self.collection,
                                    self.deck_request.get(), bool(self.query.get().strip() or self.cost.get() != "Any")) if self.rows else ""
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", self.output or "No cards to export. Load a collection or reset the filters.")
        self.preview.configure(state="disabled")
        self.update_actions()

    def select_card(self, _=None):
        selection = self.tree.selection()
        if selection:
            row = self.rows[int(selection[0])]
            self.detail.set(f"{row['name']}  ·  {row['ability']}")

    def copy(self):
        if self.output and not self.busy:
            try:
                self.clipboard_clear()
                self.clipboard_append(self.output)
                self.update_idletasks()
                self.status.set(f"Copied {len(self.rows)} cards as {self.format.get()}. Paste into your AI conversation.")
            except tk.TclError as exc:
                messagebox.showerror("Clipboard unavailable", str(exc))

    def save(self):
        if not self.output or self.busy:
            return
        extension = {"CSV": ".csv", "TSV": ".tsv", "JSON": ".json", "AI prompt": ".txt"}[self.format.get()]
        folder = Path(self.export_dir)
        filename = filedialog.asksaveasfilename(title="Save collection export", initialdir=str(folder if folder.is_dir() else Path.home()),
            initialfile="snap-collection" + extension, defaultextension=extension,
            filetypes=[(self.format.get() + " file", "*" + extension)])
        if filename:
            try:
                save_export(Path(filename), self.output, self.format.get(), self.source)
            except (OSError, ValueError) as exc:
                messagebox.showerror("Could not save", str(exc))
                return
            self.export_dir = str(Path(filename).parent)
            self.persist()
            self.status.set(f"Saved {len(self.rows)} cards to {filename}")

    def persist(self):
        settings = {"collection_path": self.path.get(), "format": self.format.get(),
                    "columns": [c for c, v in self.columns.items() if v.get()],
                    "deck_request": self.deck_request.get(), "export_dir": self.export_dir}
        try:
            atomic_write(self.settings_path, json.dumps(settings, indent=2))
        except OSError:
            self.status.set("Export is ready, but preferences could not be saved.")

    def close(self):
        self.persist()
        self.destroy()


def main(collection_path: Path | None = None):
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    App(collection_path=collection_path).mainloop()
