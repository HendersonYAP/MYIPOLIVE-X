import os
import sys
import types
import importlib.util
import io
import contextlib

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
import glob

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

# K-ID login UI
st.sidebar.markdown('---')
st.sidebar.header('K-ID Login')
if 'kid' not in st.session_state:
    st.session_state['kid'] = ''
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

kid_input = st.sidebar.text_input('Enter K-ID (e.g. K12345)', value=st.session_state['kid'])
if st.sidebar.button('Login with K-ID'):
    if kid_input and kid_input.strip():
        st.session_state['kid'] = kid_input.strip()
        st.session_state['logged_in'] = True
        # Expose the K-ID to the legacy module if it reads a global
        try:
            setattr(paa, 'CURRENT_KID', st.session_state['kid'])
        except Exception:
            pass
        st.sidebar.success(f'Logged in as {st.session_state["kid"]}')
    else:
        st.sidebar.error('Please enter a valid K-ID before logging in.')

if st.session_state.get('logged_in'):
    st.sidebar.write(f'Logged in: {st.session_state.get("kid")}')
else:
    st.sidebar.info('Not logged in — enter K-ID to enable processing')

# Main area placeholders
log_placeholder = st.empty()
data_placeholder = st.empty()
output_placeholder = st.empty()

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

    # Offer interactive controls to run legacy functions safely
    st.markdown('### Actions')
    if st.button('Show available callables'):
        top_callables = [n for n in dir(paa) if not n.startswith('_') and callable(getattr(paa, n))]
        st.write('Detected top-level callables in legacy module:', top_callables)

    # Selection box to pick a callable to run
    top_callables = [n for n in dir(paa) if not n.startswith('_') and callable(getattr(paa, n))]
    sel = st.selectbox('Pick a callable to invoke (choose carefully)', options=['--none--'] + top_callables)
    arg_mode = st.radio('Argument to pass', options=['None', 'temp_filepath', 'dataframe'])

    # Only allow runs if logged in with K-ID
    if not st.session_state.get('logged_in'):
        st.warning('You must log in with a K-ID before running processing.')
    else:
        if st.button('Run selected callable'):
            if sel == '--none--':
                st.warning('No callable selected')
            else:
                fn = getattr(paa, sel)
                try:
                    buf = io.StringIO()
                    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                        # Prepare args based on signature and arg_mode
                        sig = None
                        try:
                            sig = inspect.signature(fn)
                        except Exception:
                            sig = None
                        kwargs = {}
                        # If function accepts a 'kid' or 'KID' param, provide it
                        if sig:
                            params = sig.parameters
                            if any(p.lower() in ('kid', 'k_id', 'k') for p in params):
                                kwargs_next = {n: st.session_state.get('kid') for n in params if n.lower() in ('kid', 'k_id', 'k')}
                                kwargs.update(kwargs_next)
                        # Determine main positional arg
                        if arg_mode == 'None':
                            if kwargs:
                                out = fn(**kwargs)
                            else:
                                out = fn()
                        elif arg_mode == 'temp_filepath':
                            main_arg = res if not isinstance(res, pd.DataFrame) else tmp_path
                            if kwargs:
                                out = fn(main_arg, **kwargs)
                            else:
                                out = fn(main_arg)
                        else:
                            main_arg = res if isinstance(res, pd.DataFrame) else pd.read_csv(res)
                            if kwargs:
                                out = fn(main_arg, **kwargs)
                            else:
                                out = fn(main_arg)
                    logs = buf.getvalue()
                    if logs:
                        log_placeholder.text(logs)
                    st.success(f'Callable {sel} finished, returned type {type(out)}')
                    if isinstance(out, pd.DataFrame):
                        output_placeholder.dataframe(out.head(200))
                    else:
                        output_placeholder.write(out)
                except Exception as e:
                    st.error(f'Callable {sel} raised an exception: {e}')

        # Quick "Run full pipeline" which tries common names in order
        if st.button('Run full pipeline (attempt)'):
            candidates = ['build_indices', 'build', 'main', 'run', 'process', 'ingest']
            attempted = []
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                for name in candidates:
                    if hasattr(paa, name) and callable(getattr(paa, name)):
                        attempted.append(name)
                        fn = getattr(paa, name)
                        try:
                            sig = None
                            try:
                                sig = inspect.signature(fn)
                            except Exception:
                                sig = None
                            # Build args: if fn accepts kid -> pass it; if accepts 1 arg -> pass path/data
                            kwargs = {}
                            if sig:
                                params = sig.parameters
                                if any(p.lower() in ('kid', 'k_id', 'k') for p in params):
                                    kwargs_next = {n: st.session_state.get('kid') for n in params if n.lower() in ('kid', 'k_id', 'k')}
                                    kwargs.update(kwargs_next)
                            if sig is None or len(sig.parameters) == 0 or (len(sig.parameters) == len(kwargs)):
                                out = fn(**kwargs) if kwargs else fn()
                            elif len(sig.parameters) == 1 or (len(sig.parameters) == 1 + len(kwargs)):
                                main_arg = res if not isinstance(res, pd.DataFrame) else tmp_path
                                if kwargs:
                                    out = fn(main_arg, **kwargs)
                                else:
                                    out = fn(main_arg)
                            else:
                                # skip if signature doesn't match simple patterns
                                continue
                            st.success(f'Pipeline: called {name}, returned {type(out)}')
                            if isinstance(out, pd.DataFrame):
                                output_placeholder.dataframe(out.head(200))
                            break
                        except Exception as e:
                            st.error(f'Call to {name} failed: {e}')
                else:
                    st.warning('No candidate entrypoint succeeded.')
            logs = buf.getvalue()
            if logs:
                log_placeholder.text(logs)

    # After a run, show produced CSVs in repo and cache
    st.markdown('### Outputs')
    root_csvs = glob.glob(os.path.join(os.path.dirname(__file__), '*.csv'))
    cache_dir = getattr(paa, '_CACHE_DIR', os.path.join(os.path.dirname(__file__), 'paa_cache'))
    cache_csvs = glob.glob(os.path.join(cache_dir, '**', '*.csv'), recursive=True)
    any_files = root_csvs + cache_csvs
    if any_files:
        st.write('Generated CSVs:')
        for f in any_files:
            try:
                st.write(f)
                with open(f, 'rb') as fh:
                    btn = st.download_button(label=f'Download {os.path.basename(f)}', data=fh, file_name=os.path.basename(f))
            except Exception as e:
                st.write(f'Could not provide {f}: {e}')
    else:
        st.write('No CSV outputs detected yet.')

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
