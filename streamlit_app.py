import sys
import types
from importlib.machinery import SourceFileLoader

# Inject a lightweight fake `tkinter` module so importing the original
# code doesn't fail on Streamlit Cloud where system Tcl/Tk is missing.
# This is a minimal, non-GUI shim — any code that actually tries to open
# real GUI windows will need to be ported to Streamlit widgets.
if 'tkinter' not in sys.modules:
    fake_tk = types.ModuleType('tkinter')
    # provide submodules used by the code
    fake_tk.ttk = types.ModuleType('tkinter.ttk')
    fake_tk.messagebox = types.ModuleType('tkinter.messagebox')
    fake_tk.filedialog = types.ModuleType('tkinter.filedialog')
    sys.modules['tkinter'] = fake_tk
    sys.modules['tkinter.ttk'] = fake_tk.ttk
    sys.modules['tkinter.messagebox'] = fake_tk.messagebox
    sys.modules['tkinter.filedialog'] = fake_tk.filedialog

# Make matplotlib use a non-interactive backend if Tk isn't available.
import matplotlib
try:
    matplotlib.use('TkAgg')
except Exception:
    matplotlib.use('Agg')

# Import the large application module safely. The module will import our
# fake `tkinter` instead of trying to load the missing system _tkinter C lib.
# Using SourceFileLoader so we don't need to change the original filename.
try:
    paa = SourceFileLoader('paa_module', 'PAA_MERGED_177.py').load_module()
except Exception as e:
    # If importing still fails, expose the error in the Streamlit UI.
    import streamlit as st
    st.title('MYIPOLIVE-X — import error')
    st.error(f'Failed to import PAA_MERGED_177.py: {e}')
    raise

# Minimal Streamlit wrapper page while the full UI is ported.
import streamlit as st
st.title('MYIPOLIVE-X (temporary Streamlit wrapper)')
st.write('The application module has been imported with a tkinter shim so it no longer crashes on import in the cloud.')
st.write('Next: replace tkinter-based dialogs and any TkAgg figure canvases with Streamlit UI and st.pyplot/st.altair_chart.')

# Optional: if the original module exposes a function that runs the app
# (e.g., `main()`), call it here only if it's safe. We do not call any
# GUI startup functions automatically to avoid accidental GUI operations.
if hasattr(paa, 'main') and callable(getattr(paa, 'main')):
    st.write('Detected a `main()` entrypoint in the app module — not invoked automatically.')
    st.write('If you want it invoked here, edit streamlit_app.py to call paa.main() after ensuring it is Streamlit-safe.')
