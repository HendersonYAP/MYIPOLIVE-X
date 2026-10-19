import os
import sys
import types
from importlib.machinery import SourceFileLoader

# Cloud-safe shim: the app runs on a headless server without Tcl/Tk installed.
if 'tkinter' not in sys.modules:
    fake_tk = types.ModuleType('tkinter')
    fake_tk.ttk = types.ModuleType('tkinter.ttk')
    fake_tk.messagebox = types.ModuleType('tkinter.messagebox')
    fake_tk.filedialog = types.ModuleType('tkinter.filedialog')
    fake_tk.constants = types.ModuleType('tkinter.constants')

    class _FakeTk:
        def __init__(self, *args, **kwargs):
            pass

    fake_tk.Tk = _FakeTk
    fake_tk.StringVar = lambda *args, **kwargs: ''
    fake_tk.IntVar = lambda *args, **kwargs: 0

    sys.modules['tkinter'] = fake_tk
    sys.modules['tkinter.ttk'] = fake_tk.ttk
    sys.modules['tkinter.messagebox'] = fake_tk.messagebox
    sys.modules['tkinter.filedialog'] = fake_tk.filedialog
    sys.modules['tkinter.constants'] = fake_tk.constants

# Force a headless backend for matplotlib in Streamlit Cloud / server deployments.
os.environ.setdefault('MPLBACKEND', 'Agg')
try:
    import matplotlib
    matplotlib.use('Agg')
except Exception:
    pass

try:
    paa = SourceFileLoader('paa_module', 'PAA_MERGED_177.py').load_module()
except Exception as e:
    import streamlit as st
    st.title('MYIPOLIVE-X — import error')
    st.error(f'Failed to import PAA_MERGED_177.py: {e}')
    raise

import streamlit as st
st.title('MYIPOLIVE-X (Streamlit Cloud wrapper)')
st.write('This app is running with a headless matplotlib backend and a tkinter shim so it can start safely in the cloud.')
st.write('The original Tkinter desktop UI is not available in Streamlit Cloud; the next step is to replace Tk widgets with Streamlit UI components.')

if hasattr(paa, 'main') and callable(getattr(paa, 'main')):
    st.write('Found a `main()` function in the legacy app module. It is not invoked automatically because this is a cloud-safe wrapper.')
