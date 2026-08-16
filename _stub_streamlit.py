# -*- coding: utf-8 -*-
"""
_stub_streamlit.py — Streamlit وهمي لتشغيل app.py فعليًا خارج المتصفح

الهدف: تنفيذ الكود **الحقيقي** سطر بسطر بدل التحليل الثابت. أي NameError أو
TypeError أو مفتاح ناقص أو توقيع دالة غلط بيظهر هنا، مش في وش المستخدم.

الفلسفة: الـ stub بيقلّد الواجهة مش السلوك. الودجت بترجّع قيمة افتراضية
معقولة (index=0 للـ selectbox، value للـ number_input... إلخ)، والأزرار
بترجّع False إلا لو الاختبار طلب غير كده صراحة.
"""
import sys, types, io
from datetime import date, datetime

CALLS = []          # سجل كل النداءات — للتحقق بعد التشغيل
RERUN_COUNT = [0]
BUTTON_TRUE = set()  # مفاتيح الأزرار اللي هترجّع True


class _Rerun(Exception):
    """st.rerun() بيوقف السكربت — نفس سلوك Streamlit الحقيقي."""


class _Stop(Exception):
    """st.stop()"""


class SessionState(dict):
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)

    def __setattr__(self, k, v):
        self[k] = v

    def __delattr__(self, k):
        self.pop(k, None)


class Secrets(dict):
    def get(self, k, default=None):
        return dict.get(self, k, default)


class _Ctx:
    """st.context — كوكيز وهيدرز"""
    cookies = {}
    headers = {}
    ip_address = "127.0.0.1"


class _QueryParams(dict):
    def get(self, k, default=None):
        return dict.get(self, k, default)

    def pop(self, k, default=None):
        return dict.pop(self, k, default)

    def clear(self):
        dict.clear(self)


class _Ctxmgr:
    """أي حاجة بتستخدم `with` — columns / expander / container / spinner / form"""
    def __init__(self, name="ctx"):
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    # الودجت جوّه الـ with بتتنادى كـ col.button(...) كمان
    def __getattr__(self, item):
        return getattr(sys.modules[__name__], item, _noop)


def _rec(name):
    def f(*a, **k):
        CALLS.append((name, a, k))
        return None
    return f


def _noop(*a, **k):
    return None


# ── الودجت: بترجّع قيمة افتراضية معقولة ─────────────────────────────────────
def button(label="", *a, **k):
    CALLS.append(("button", (label,), k))
    return k.get("key") in BUTTON_TRUE


def form_submit_button(label="", *a, **k):
    CALLS.append(("form_submit_button", (label,), k))
    return k.get("key") in BUTTON_TRUE


def download_button(label="", data=None, *a, **k):
    CALLS.append(("download_button", (label,), k))
    return False


def checkbox(label="", value=False, *a, **k):
    CALLS.append(("checkbox", (label,), k))
    return bool(value)


def selectbox(label="", options=(), index=0, *a, **k):
    CALLS.append(("selectbox", (label,), k))
    opts = list(options)
    if not opts:
        return None
    i = index if isinstance(index, int) and 0 <= index < len(opts) else 0
    return opts[i]


def radio(label="", options=(), index=0, *a, **k):
    return selectbox(label, options, index, **k)


def multiselect(label="", options=(), default=None, *a, **k):
    CALLS.append(("multiselect", (label,), k))
    return list(default or [])


def text_input(label="", value="", *a, **k):
    CALLS.append(("text_input", (label,), k))
    return str(value or "")


def text_area(label="", value="", *a, **k):
    CALLS.append(("text_area", (label,), k))
    return str(value or "")


def number_input(label="", min_value=None, max_value=None, value=0, *a, **k):
    CALLS.append(("number_input", (label,), k))
    return value if value is not None else (min_value or 0)


def date_input(label="", value=None, *a, **k):
    CALLS.append(("date_input", (label,), k))
    return value if value is not None else date.today()


def time_input(label="", value=None, *a, **k):
    CALLS.append(("time_input", (label,), k))
    return value


def file_uploader(label="", *a, **k):
    CALLS.append(("file_uploader", (label,), k))
    return None


def columns(spec, *a, **k):
    n = spec if isinstance(spec, int) else len(spec)
    return [_Ctxmgr(f"col{i}") for i in range(n)]


def tabs(names, *a, **k):
    return [_Ctxmgr(f"tab{i}") for i in range(len(names))]


def expander(label="", *a, **k):
    return _Ctxmgr("expander")


def container(*a, **k):
    return _Ctxmgr("container")


def spinner(text="", *a, **k):
    return _Ctxmgr("spinner")


def form(key=None, *a, **k):
    return _Ctxmgr("form")


def empty(*a, **k):
    return _Ctxmgr("empty")


def rerun(*a, **k):
    RERUN_COUNT[0] += 1
    raise _Rerun()


def stop(*a, **k):
    raise _Stop()


def cache_resource(func=None, **kw):
    """@st.cache_resource — بينفّذ مرة ويخزّن"""
    def deco(f):
        store = {}

        def wrapper(*a, **k):
            key = (a, tuple(sorted(k.items())))
            try:
                if key not in store:
                    store[key] = f(*a, **k)
                return store[key]
            except TypeError:          # وسائط مش hashable
                return f(*a, **k)
        wrapper.clear = store.clear
        wrapper.__wrapped__ = f
        return wrapper
    return deco(func) if callable(func) else deco


cache_data = cache_resource


# ── العرض: بتسجّل بس ────────────────────────────────────────────────────────
for _n in ("markdown", "write", "title", "header", "subheader", "caption", "code",
           "json", "error", "warning", "success", "info", "toast", "dataframe",
           "table", "metric", "plotly_chart", "bar_chart", "line_chart",
           "area_chart", "image", "divider", "progress", "balloons", "snow",
           "set_page_config", "html", "badge", "audio", "video", "altair_chart",
           "pyplot", "map", "graphviz_chart", "status", "toggle", "slider",
           "color_picker", "camera_input", "data_editor", "link_button",
           "page_link", "logo", "help", "exception"):
    globals()[_n] = _rec(_n)

session_state = SessionState()
secrets = Secrets()
query_params = _QueryParams()
context = _Ctx()

# st.sidebar — نفس الواجهة
sidebar = _Ctxmgr("sidebar")


def install(secrets_dict=None):
    """بيركّب الـ stub في sys.modules قبل استيراد app.py"""
    mod = sys.modules[__name__]
    mod.secrets = Secrets(secrets_dict or {})
    sys.modules["streamlit"] = mod

    # plotly مش متثبّت — stub بسيط
    px = types.ModuleType("plotly.express")
    px.bar = px.line = px.pie = px.scatter = px.histogram = lambda *a, **k: _Ctxmgr("fig")
    go = types.ModuleType("plotly.graph_objects")

    class _Fig:
        def __init__(self, *a, **k): pass
        def update_layout(self, *a, **k): return self
        def update_traces(self, *a, **k): return self
        def add_trace(self, *a, **k): return self
    go.Figure = _Fig
    go.Pie = go.Bar = go.Scatter = lambda *a, **k: None
    plotly = types.ModuleType("plotly")
    plotly.express = px
    plotly.graph_objects = go
    sys.modules["plotly"] = plotly
    sys.modules["plotly.express"] = px
    sys.modules["plotly.graph_objects"] = go
    return mod


def reset():
    CALLS.clear()
    RERUN_COUNT[0] = 0
    BUTTON_TRUE.clear()
    session_state.clear()
    query_params.clear()
