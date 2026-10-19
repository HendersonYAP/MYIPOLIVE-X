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
