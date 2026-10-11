"""Initial window sizes that leave room for desktop panels and decorations."""


def fit_window(window, geometry):
    """Set a preferred logical size, capped to the screen; keep manual resizing."""
    width, height = (int(value) for value in geometry.split('x'))
    # CTk geometry is logical, while Tk screen dimensions are physical pixels.
    scaling = getattr(window, '_get_window_scaling', lambda: 1.0)()
    width = min(width, max(1, int((window.winfo_screenwidth() - 80) / scaling)))
    height = min(height, max(1, int((window.winfo_screenheight() - 100) / scaling)))
    window.geometry(f'{width}x{height}')
    return width, height
