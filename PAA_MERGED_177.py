import pandas as pd
import yfinance as yf
import numpy as np
import os
import re
import random
import threading
import time as time_module
from datetime import datetime, time
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    TK_AVAILABLE = True
except Exception:
    tk = None
    ttk = None
    messagebox = None
    filedialog = None
    TK_AVAILABLE = False

try:
    import streamlit as st
    ST_AVAILABLE = True
except Exception:
    st = None
    ST_AVAILABLE = False

if ST_AVAILABLE:
    import hashlib
    import types

    _mb = types.SimpleNamespace()

    def _mb_showinfo(title, message, **kwargs):
        st.info(f"**{title}**\n{message}")

    def _mb_showwarning(title, message, **kwargs):
        st.warning(f"**{title}**\n{message}")

    def _mb_showerror(title, message, **kwargs):
        st.error(f"**{title}**\n{message}")

    def _mb_askyesno(title, message, key=None, **kwargs):
        k = key or f"askyesno_{abs(hashlib.sha256((title + message).encode()).digest()[0])}"
        st.write(f"**{title}**\n{message}")
        col1, col2 = st.columns(2)
        if col1.button('Yes', key=f"{k}_yes"):
            st.session_state[k] = True
        if col2.button('No', key=f"{k}_no"):
            st.session_state[k] = False
        return st.session_state.get(k, False)

    _mb.showinfo = _mb_showinfo
    _mb.showwarning = _mb_showwarning
    _mb.showerror = _mb_showerror
    _mb.askyesno = _mb_askyesno

    _fd = types.SimpleNamespace()

    def _fd_askopenfilename(title='Select file', key=None, accept_multiple=False, type=None, **kwargs):
        k = key or f"file_uploader_{abs(hashlib.sha256(title.encode()).digest()[0])}"
        uploaded = st.file_uploader(title, type=type, key=k, accept_multiple_files=accept_multiple)
        if not uploaded:
            return ''
        files = uploaded if isinstance(uploaded, list) else [uploaded]
        p = os.path.join('/tmp', files[0].name)
        with open(p, 'wb') as f:
            f.write(files[0].getbuffer())
        return p

    def _fd_asksaveasfilename(title='Save file as', defaultextension=None, key=None, **kwargs):
        st.info('Use the browser download button when saving files in Streamlit.')
        return ''

    _fd.askopenfilename = _fd_askopenfilename
    _fd.asksaveasfilename = _fd_asksaveasfilename

    messagebox = _mb
    filedialog = _fd

    def display_figure_in_host(fig, caption=None):
        if caption:
            st.caption(caption)
        st.pyplot(fig)
else:
    def display_figure_in_host(fig, caption=None):
        try:
            import matplotlib.pyplot as plt
            plt.show(fig)
        except Exception:
            pass

# OPIE (local decision-support layer) is temporarily disabled — module removed.
# from opie import OPIEAgent

# Optional WebView backends for the in-app ad area (both degrade gracefully):
#   tkinterweb — pure-Python HTML frame embeddable INSIDE a Tkinter layout
#                (limited JS support, fine for static/sponsored HTML)
#   pywebview  — real native browser window (Edge WebView2 on Windows) for
#                the pop-up ad page; falls back to the system browser if absent
try:
    from tkinterweb import HtmlFrame as _AdHtmlFrame   # pip install tkinterweb
    _HAS_TKINTERWEB = True
except Exception:
    _AdHtmlFrame, _HAS_TKINTERWEB = None, False
try:
    import webview as _pywebview                        # pip install pywebview
    _HAS_PYWEBVIEW = True
except Exception:
    _pywebview, _HAS_PYWEBVIEW = None, False
import webbrowser as _webbrowser

import matplotlib
if TK_AVAILABLE:
    try:
        matplotlib.use('TkAgg')
    except Exception:
        pass
else:
    matplotlib.use('Agg')

try:
    import matplotlib.dates as mdates
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
except Exception:
    import matplotlib.dates as mdates
    FigureCanvasTkAgg = None
    NavigationToolbar2Tk = None
    from matplotlib.figure import Figure
