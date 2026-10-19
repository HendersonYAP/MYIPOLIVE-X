import os
import sys
import types
import importlib.util
import io
import contextlib
import glob

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

st.set_page_config(page_title='MYIPO+ (Streamlit)', layout='wide')

# Initialize session state keys
if 'kid' not in st.session_state:
    st.session_state['kid'] = ''
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'data_loaded' not in st.session_state:
    st.session_state['data_loaded'] = False
if 'resolved' not in st.session_state:
    st.session_state['resolved'] = None
if 'resolved_src' not in st.session_state:
    st.session_state['resolved_src'] = None
if 'tmp_path' not in st.session_state:
    st.session_state['tmp_path'] = None

# Small helpers
def log_cb(msg):
    try:
        st.session_state['_last_log'] = msg
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
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            raw = resp.read()
        df = pd.read_csv(io.BytesIO(raw), sep=',', dtype=str, keep_default_na=False,
                         low_memory=False, encoding_errors='replace')
        log(f'✅ Fetched {len(df)} rows (fallback)')
        return df, 'online-fallback'
    except Exception as e:
        log(f'⚠️ Fallback fetch failed: {e}')
        return None, str(e)

# Layout: Sign-in (full page) -> Load Data -> Dashboard

st.title('MYIPO+ — Streamlit Dashboard')

# If not logged in, show a focused sign-in form (E1)
if not st.session_state['logged_in']:
    st.markdown("""
    <div style='max-width:520px;margin:50px auto;padding:30px;border-radius:8px;background:#0b1220;color:#d7eefc;text-align:center;'>
      <h1 style='color:#00c2ff'>ID</h1>
      <h2>K-ID</h2>
      <p>Sign in to continue</p>
    </div>
    """, unsafe_allow_html=True)
    with st.form('signin_form'):
        username = st.text_input('Username')
        pin = st.text_input('PIN (4–8 digits)', type='password')
        submitted = st.form_submit_button('Sign In')
        if submitted:
            # Basic validation
            if not username or not pin:
                st.error('Please enter username and PIN')
            elif not pin.isdigit() or not (4 <= len(pin) <= 8):
                st.error('PIN must be 4–8 digits')
            else:
                st.session_state['kid'] = username.strip()
                st.session_state['pin'] = pin
                st.session_state['logged_in'] = True
                # expose to legacy module
                try:
                    setattr(paa, 'CURRENT_KID', st.session_state['kid'])
                except Exception:
                    pass
                st.success(f'Logged in as {st.session_state["kid"]}')
                # st.experimental_rerun was removed; use st.rerun()
                st.rerun()
    st.stop()

# At this point user is logged in — show Load Data screen (E2)
st.sidebar.write(f'Logged in: {st.session_state.get("kid")}')
st.sidebar.markdown('---')

st.header('Load Data')
col1, col2 = st.columns([3,1])
with col1:
    # Show detection status for teet.csv in repo root
    repo_teet = os.path.join(os.path.dirname(__file__), 'teet.csv')
    if os.path.exists(repo_teet):
        st.write('teet.csv: found in repo')
    else:
        st.write('teet.csv: not found — will use uploaded file or online DB')
    st.write('Press Load to start.')
    st.text_input('Status', value=st.session_state.get('_last_log', ''), disabled=True)

with col2:
    use_online = st.checkbox('Use Online Database (Google Sheets)', value=True)
    apply_fee = st.checkbox('Apply RM2.01 sell fee on exits', value=True)

uploaded_file = st.file_uploader('Or upload local teet.csv', type=['csv'])

load_clicked = st.button('Load Data', key='loaddata')

# Helper to resolve input
def resolve_input_and_store(path=None, prefer_online=True):
    # If legacy resolve_input exists, use it. Otherwise attempt to read CSV directly.
    try:
        if hasattr(paa, 'resolve_input') and callable(getattr(paa, 'resolve_input')):
            res, src = paa.resolve_input(path if path else '', prefer_online=prefer_online, log_cb=log_cb)
            st.session_state['resolved'] = res
            st.session_state['resolved_src'] = src
            return res, src
    except Exception as e:
        log_cb(f'resolve_input failed: {e}')
    # fallback: read path or fetch online
    if path and os.path.exists(path):
        try:
            df = pd.read_csv(path)
            st.session_state['resolved'] = df
            st.session_state['resolved_src'] = 'uploaded'
            return df, 'uploaded'
        except Exception as e:
            log_cb(f'failed to read uploaded CSV: {e}')
            return None, str(e)
    if prefer_online:
        df, src = fallback_fetch_online_db(log_cb=log_cb)
        st.session_state['resolved'] = df
        st.session_state['resolved_src'] = src
        return df, src
    return None, 'no-input'

# If user uploaded a file, save it to tmp for later use
if uploaded_file is not None:
    tmp_path = os.path.join('/tmp', uploaded_file.name)
    with open(tmp_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    st.session_state['tmp_path'] = tmp_path
    st.success(f'Uploaded and saved to {tmp_path}')

if load_clicked:
    # Ensure logged in (should be)
    if not st.session_state.get('logged_in'):
        st.error('You must sign in before loading data')
    else:
        # resolve input
        preferred = use_online
        path = st.session_state.get('tmp_path')
        res, src = resolve_input_and_store(path=path, prefer_online=preferred)
        if isinstance(res, pd.DataFrame):
            st.success(f'Loaded data ({src}) — {len(res)} rows')
            st.session_state['data_loaded'] = True
            # replaced st.experimental_rerun() with st.rerun()
            st.rerun()
        else:
            st.error(f'Failed to load data: {src}')

# If data not loaded, show helper and stop
if not st.session_state.get('data_loaded'):
    st.info('No data loaded yet. Sign in and press Load Data (or upload teet.csv).')
    st.stop()

# Data is loaded — show Dashboard (E3)
st.markdown('---')
st.header('Dashboard')
res = st.session_state.get('resolved')
src = st.session_state.get('resolved_src')

left, center, right = st.columns([2,6,3])
with left:
    st.subheader('Indices')
    # For now show a simple multi-select of index names if available
    if isinstance(res, pd.DataFrame):
        # assume there is a column 'Index' or use columns as options
        options = []
        if 'Index' in res.columns:
            options = sorted(res['Index'].unique().tolist())
        else:
            options = res.columns.tolist()[:20]
        selected = st.multiselect('Select indices to view', options=options, default=options[:6])
    else:
        selected = []
    st.markdown('Period')
    period = st.select_slider('Period', options=['1D','5D','1M','3M','6M','YTD','1Y','3Y','5Y','All'], value='All')
    st.markdown('Summary')
    if isinstance(res, pd.DataFrame):
        st.dataframe(res.head(10))

with center:
    st.subheader('Main Chart')
    # Attempt to run a legacy plotting function if available, else show a simple line chart
    plotted = False
    # If legacy provides a function to produce a plot/data, call it
    plot_candidates = ['plot_indices', 'plot_chart', 'render_chart']
    for name in plot_candidates:
        if hasattr(paa, name) and callable(getattr(paa, name)):
            try:
                fn = getattr(paa, name)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    out = fn(res if isinstance(res, pd.DataFrame) else None)
                logs = buf.getvalue()
                if logs:
                    st.text(logs)
                # If function returned a dataframe, plot it
                if isinstance(out, pd.DataFrame):
                    st.line_chart(out)
                    plotted = True
                    break
            except Exception as e:
                st.write(f'Plot function {name} failed: {e}')
    if not plotted:
        # Fallback: if numeric columns exist, plot first few
        if isinstance(res, pd.DataFrame):
            numeric = res.select_dtypes(include='number')
            if not numeric.empty:
                st.line_chart(numeric.iloc[:, :min(5, numeric.shape[1])])
            else:
                st.info('No numeric columns to plot')

with right:
    st.subheader('Actions & Outputs')
    if st.button('Run full pipeline (attempt)'):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            candidates = ['build_indices', 'build', 'main', 'run', 'process', 'ingest']
            succeeded = False
            for name in candidates:
                if hasattr(paa, name) and callable(getattr(paa, name)):
                    fn = getattr(paa, name)
                    try:
                        # try calling with K-ID if signature asks for it
                        sig = None
                        try:
                            sig = inspect.signature(fn)
                        except Exception:
                            sig = None
                        kwargs = {}
                        if sig:
                            params = sig.parameters
                            if any(p.lower() in ('kid','k_id','k') for p in params):
                                kwargs_next = {n: st.session_state.get('kid') for n in params if n.lower() in ('kid','k_id','k')}
                                kwargs.update(kwargs_next)
                        if sig is None or len(sig.parameters) == 0 or (len(sig.parameters) == len(kwargs)):
                            out = fn(**kwargs) if kwargs else fn()
                        elif len(sig.parameters) == 1 or (len(sig.parameters) == 1 + len(kwargs)):
                            main_arg = st.session_state.get('tmp_path') or None
                            if kwargs:
                                out = fn(main_arg, **kwargs)
                            else:
                                out = fn(main_arg)
                        else:
                            continue
                        st.success(f'Called {name} → returned {type(out)}')
                        succeeded = True
                        break
                    except Exception as e:
                        st.error(f'Call to {name} failed: {e}')
            if not succeeded:
                st.warning('No pipeline entrypoint succeeded')
        logs = buf.getvalue()
        if logs:
            st.text(logs)

    st.markdown('### Outputs')
    root_csvs = glob.glob(os.path.join(os.path.dirname(__file__), '*.csv'))
    cache_dir = getattr(paa, '_CACHE_DIR', os.path.join(os.path.dirname(__file__), 'paa_cache'))
    cache_csvs = glob.glob(os.path.join(cache_dir, '**', '*.csv'), recursive=True)
    any_files = root_csvs + cache_csvs
    if any_files:
        for f in any_files:
            try:
                with open(f, 'rb') as fh:
                    st.download_button(label=f'Download {os.path.basename(f)}', data=fh, file_name=os.path.basename(f))
            except Exception as e:
                st.write(f'Could not provide {f}: {e}')
    else:
        st.write('No CSV outputs detected yet.')

st.markdown('---')
st.caption('This Streamlit UI reproduces the desktop flow: Sign in → Load Data → Dashboard. Let me know which desktop widgets or behaviors you want replicated next.')
