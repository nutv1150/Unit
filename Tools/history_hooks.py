"""Optional GUI hooks: history failures must not change tool results."""
from tkinter import messagebox


def _failed(root, error):
    message = str(error)
    first = getattr(root, '_history_notified_error', '') != message
    root.history_error = message
    if first:
        root._history_notified_error = message
        messagebox.showwarning('History unavailable',
                               'History could not be saved. Tool results are unaffected.\n' + message,
                               parent=root)


def begin(root, **event):
    store = getattr(root, 'history_store', None)
    if store is None:
        if getattr(root, 'history_error', ''):
            _failed(root, root.history_error)
        return None
    try:
        event_id = store.begin(**event)
        if not hasattr(root, 'history_active'):
            root.history_active = set()
        root.history_active.add(event_id)
        root.history_error = ''
        root._history_notified_error = ''
        return event_id
    except Exception as error:
        _failed(root, error)
        return None


def finish(root, event_id, status, **result):
    if not event_id or getattr(root, 'history_store', None) is None:
        return
    try:
        root.history_store.finish(event_id, status, **result)
        root.history_active.discard(event_id)
    except Exception as error:
        _failed(root, error)


def open_history(root, category='All'):
    from pages.solve_history import HistoryWindow
    existing = getattr(root, '_history_window', None)
    if existing is not None and existing.winfo_exists():
        existing.set_category(category)
        existing.deiconify()
        existing.lift()
        return existing
    window = HistoryWindow(root, category)
    root._history_window = window
    return window


def attach_file(root, event_id, path):
    """Record an explicit saved/selected file reference, never read its contents."""
    if not event_id or getattr(root, 'history_store', None) is None:
        return
    try:
        event = root.history_store.get_event(event_id)
        if event is not None:
            files = list(dict.fromkeys(event['files'] + [str(path)]))
            root.history_store.finish(event_id, event['status'], output_data=event['output'],
                                      error=event['error'], files=files)
    except Exception as error:
        _failed(root, error)
