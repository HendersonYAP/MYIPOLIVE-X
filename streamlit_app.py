import os
import sys
import types
import importlib.util

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

# Load the legacy application module in a fresh module object so reloads work
PAA_PATH = os.path.join(os.path.dirname(__file__), 'PAA_MERGED_177.py')
try:
    if 'paa_module' in sys.modules:
        del sys.modules['paa_module']
    spec = importlib.util.spec_from_file_location('paa_module', PAA_PATH)
    paa = importlib.util.module_from_spec(spec)
    sys.modules['paa_module'] = paa
    spec.loader.exec_module(paa)
except Exception as e:
    import streamlit as st
    st.title('MYIPOLIVE-X — import error')
    st.error(f'Failed to import PAA_MERGED_177.py: {e}')
    raise

# --- Streamlit UI wrapper that exposes key app flows ---------------------------------
import streamlit as st
import pandas as pd
import inspect

st.set_page_config(page_title='MYIPOLIVE-X (Streamlit)', layout='wide')
st.title('MYIPOLIVE-X — Streamlit frontend')
st.markdown("""
This is the Streamlit frontend wrapper for the legacy MYIPOLIVE-X codebase.
The original Tk desktop UI has been shimmed so the core logic can run in the
cloud; use the controls below to load data and run the main flows.
""")

# Sidebar options
st.sidebar.header('Data source')
use_online = st.sidebar.button('Fetch online database (Google Sheet)')
uploaded_file = st.sidebar.file_uploader('Or upload local teet.csv', type=['csv'])

# Main area placeholders
log_placeholder = st.empty()
data_placeholder = st.empty()

# Helper log callback that writes to the log placeholder
def log_cb(msg):
    try:
        log_placeholder.info(msg)
    except Exception:
        pass

# Fallback online fetch if legacy module missing the function
def fallback_fetch_online_db(log_cb=None):
    import urllib.request, io, ssl, time as _time
    def log(m):
        if log_cb: log_cb(m)
    url = (
        'https://docs.google.com/spreadsheets/d/e/'
        '2PACX-1vTZQwnk6JF3NazIiGxXumkHio3_8q6NbB1P5KxNyCYBlA0BCszcv12ahR7hb-3hZYqzFN4FxR3GiVsg'
        '/pub?gid=147724768&single=true&output=csv'
    )
    try:
        log('⬇ Connecting to online database…')
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            raw = resp.read()
        df = pd.read_csv(io.BytesIO(raw), sep=',', dtype=str, keep_default_na=False,
                         low_memory=False, encoding_errors='replace')
        log(f'✅ Fetched {len(df)} rows (fallback)')
        return df, 'online-fallback'
    except Exception as e:
        log(f'⚠️ Fallback fetch failed: {e}')
        return None, str(e)

# Flow: fetch online database
if use_online:
    st.sidebar.info('Fetching online database...')
    try:
        # Some older loads may not have the function available — check
        if hasattr(paa, 'fetch_online_db') and callable(getattr(paa, 'fetch_online_db')):
            df_online, src = paa.fetch_online_db(log_cb=log_cb)
        else:
            df_online, src = fallback_fetch_online_db(log_cb=log_cb)

        if isinstance(df_online, pd.DataFrame):
            data_placeholder.write('Online database loaded — preview:')
            data_placeholder.dataframe(df_online.head(100))
            st.success('Online database fetch complete.')
        else:
            st.error(f'Online fetch returned unexpected type: {type(df_online)} (src={src})')
    except Exception as e:
        st.error(f'Failed to fetch online database: {e}')

# Flow: use uploaded file
uploaded_resolved = None
if uploaded_file is not None:
    st.sidebar.info(f'Uploaded file: {uploaded_file.name}')
    # Save uploaded file to a temporary path and give it to the resolve_input helper
    tmp_path = os.path.join('/tmp', uploaded_file.name)
    with open(tmp_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    st.sidebar.success('File saved to temporary path')
    # Resolve input — prefer local only so we don't try online
    try:
        if hasattr(paa, 'resolve_input') and callable(getattr(paa, 'resolve_input')):
            res, src = paa.resolve_input(tmp_path, prefer_online=False, log_cb=log_cb)
            uploaded_resolved = (res, src)
            if isinstance(res, pd.DataFrame):
                data_placeholder.write(f'Loaded DataFrame ({src}) — preview:')
                data_placeholder.dataframe(res.head(100))
            else:
                # resolve_input returned a path string
                try:
                    df = pd.read_csv(res)
                    data_placeholder.write(f'Loaded CSV from {res} — preview:')
                    data_placeholder.dataframe(df.head(100))
                except Exception as e:
                    data_placeholder.write(f'Input resolved to {res} (source: {src}). Could not read as CSV: {e}')
        else:
            st.error('Legacy module does not expose resolve_input — cannot load uploaded file via legacy logic.')
    except Exception as e:
        st.error(f'Failed to resolve uploaded input: {e}')

    # Offer a simple 'Process uploaded file' action that attempts to call common
    # legacy entrypoints in the imported module. This helps transition from the
    # desktop flow to a web-run flow without blindly invoking unknown GUI code.
    st.markdown('### Actions')
    if st.button('Process uploaded file'):
        if uploaded_resolved is None:
            st.error('No uploaded file resolved.')
        else:
            res, src = uploaded_resolved
            # Gather candidate functions to attempt (common names)
            candidates = ['build_indices', 'build', 'main', 'run', 'process', 'ingest']
            available = [n for n in candidates if hasattr(paa, n) and callable(getattr(paa, n))]
            # Also show other top-level callables so you can see what's in the module
            top_callables = [n for n in dir(paa) if not n.startswith('_') and callable(getattr(paa, n))]
            st.write('Detected top-level callables in legacy module:', top_callables)
            if not available:
                st.warning('No standard entrypoint (build/main/run) found. Pick a callable from the list and ask me to wire it.')
            else:
                for name in available:
                    fn = getattr(paa, name)
                    sig = None
                    try:
                        sig = inspect.signature(fn)
                    except Exception:
                        sig = None
                    st.write(f'Attempting {name} with signature {sig}')
                    try:
                        # If function expects no args -> call directly
                        if sig is None or len(sig.parameters) == 0:
                            out = fn()
                        elif len(sig.parameters) == 1:
                            # pass path or dataframe
                            out = fn(res)
                        else:
                            st.info(f'Skipping {name}: expects {len(sig.parameters)} parameters')
                            continue
                        st.success(f'Function {name} returned type {type(out)}')
                        if isinstance(out, pd.DataFrame):
                            st.write(out.head(50))
                        else:
                            st.write(out)
                    except Exception as e:
                        st.error(f'Calling {name} failed: {e}')

# Small utilities area — sample plot and debug
st.sidebar.header('Utilities')
if st.sidebar.button('Show sample price plot'):
    # Attempt to fetch a small sample series from yfinance and plot
    try:
        import yfinance as yf
        sample = yf.download('AAPL', period='7d')
        if not sample.empty:
            st.line_chart(sample['Close'])
        else:
            st.warning('No data returned from yfinance for sample ticker.')
    except Exception as e:
        st.error(f'Sample plot failed: {e}')

st.sidebar.markdown('---')
st.sidebar.caption('If you want additional flows ported (graphs, exports, run/refresh buttons), tell me which features to prioritise and I will implement them.')
