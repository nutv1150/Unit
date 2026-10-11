"""Bounded file viewer and background atomic export for large tool results."""
from pathlib import Path
import os
import queue
import shutil
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from Tools.window_layout import fit_window

PAGE_CHARS = 64 * 1024


def background(parent, operation, complete):
    results = queue.Queue(maxsize=1)
    def worker():
        try:
            results.put((operation(), None))
        except Exception as error:
            results.put((None, error))
    def poll():
        try:
            if not parent.winfo_exists():
                return
            value, error = results.get_nowait()
        except queue.Empty:
            parent.after(40, poll)
            return
        except tk.TclError:
            return
        complete(value, error)
    threading.Thread(target=worker, daemon=True).start()
    parent.after(40, poll)


def copy_atomic(source, destination):
    destination = Path(destination)
    if isinstance(source, Path) and source.resolve() == destination.resolve():
        raise ValueError('Choose a different path from the source file.')
    name = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.unit-export-', delete=False) as output:
            name = output.name
            if isinstance(source, Path):
                with source.open('rb') as incoming:
                    shutil.copyfileobj(incoming, output, 1024 * 1024)
            else:
                output.write(source)
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, destination)
        name = None
    finally:
        if name:
            os.unlink(name)


def save_async(parent, source, destination, on_done=None):
    def complete(_, error):
        if error:
            messagebox.showerror('Save output', str(error), parent=parent)
        elif on_done:
            on_done()
    background(parent, lambda: copy_atomic(source, destination), complete)


def open_text_view(parent, path):
    path = Path(path)
    win = ctk.CTkToplevel(parent)
    win.title('Full output — paged view')
    fit_window(win, '1100x760')
    box = ctk.CTkTextbox(win, wrap='none')
    box.pack(fill='both', expand=True, padx=12, pady=12)
    bar = ctk.CTkFrame(win)
    bar.pack(fill='x', padx=12, pady=(0, 12))
    status = ctk.CTkLabel(bar, text='')
    status.pack(side='right', padx=10)
    cookies, current, busy = [0], [0], [False]
    def show(index):
        if busy[0] or index < 0 or index >= len(cookies):
            return
        busy[0] = True
        status.configure(text='Loading…')
        previous.configure(state='disabled')
        following.configure(state='disabled')
        cookie = cookies[index]
        def load():
            with path.open('r', encoding='utf-8', errors='replace', newline='') as stream:
                stream.seek(cookie)
                text = stream.read(PAGE_CHARS)
                next_cookie = stream.tell()
                has_next = bool(stream.read(1))
            return text, next_cookie, has_next
        def ready(value, error):
            busy[0] = False
            if error:
                status.configure(text=f'Cannot read output: {error}')
                return
            text, next_cookie, has_next = value
            current[0] = index
            if has_next and len(cookies) == index + 1:
                cookies.append(next_cookie)
            box.configure(state='normal')
            box.delete('1.0', 'end')
            box.insert('1.0', text)
            box.configure(state='disabled')
            previous.configure(state='normal' if index else 'disabled')
            following.configure(state='normal' if has_next else 'disabled')
            status.configure(text=f'Page {index + 1} · UTF-8 display; Save keeps exact bytes')
        background(win, load, ready)
    def save():
        destination = filedialog.asksaveasfilename(parent=win, title='Save complete output')
        if destination:
            save_async(win, path, destination)
    previous = ctk.CTkButton(bar, text='Previous', command=lambda: show(current[0] - 1))
    previous.pack(side='left', padx=4)
    following = ctk.CTkButton(bar, text='Next', command=lambda: show(current[0] + 1))
    following.pack(side='left', padx=4)
    ctk.CTkButton(bar, text='Save Full Output', command=save).pack(side='left', padx=4)
    show(0)
    return win
