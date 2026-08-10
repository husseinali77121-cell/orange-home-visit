# login_theme.py
# ══════════════════════════════════════════════════════════════════════════════
#  💡 ثيم شاشة الدخول — لمبة متحركة CSS خالص (من غير JavaScript)
#
#  ليه CSS بس؟  Streamlit بيشيل أي <script> جوه st.markdown، و components.html
#  بيتحط في iframe منفصل مش هيقدر يبعت الإيميل للـ session_state من غير custom
#  component متبني بـ npm. فالحل العملي: نسيب حقول Streamlit الأصلية شغالة،
#  ونلبّسها CSS + نحط اللمبة فوقها.
#
#  التشغيل/الإيقاف: امسح الملف ده والبرنامج هيشتغل عادي (app.py بيستورده في try).
# ══════════════════════════════════════════════════════════════════════════════

CSS = """
<style>
/* ── الخلفية الليلية (شاشة الدخول بس) ─────────────────────────────── */
.stApp{
  background:radial-gradient(1200px 600px at 50% -10%,#2a2438 0%,#141019 55%,#0d0a12 100%);
}
.stApp, .stApp p, .stApp label, .stApp span, .stApp h1, .stApp h2, .stApp h3{
  color:#EDE7F5 !important;
}

/* ── اللمبة ─────────────────────────────────────────────────────────── */
.ol-lamp-wrap{
  position:relative; height:190px; margin:-10px auto 6px; width:100%;
  display:flex; flex-direction:column; align-items:center;
  overflow:visible;
}
.ol-cord{
  width:2px; height:52px;
  background:linear-gradient(#5a5170,#7d7396);
  animation:ol-sway 4.5s ease-in-out infinite; transform-origin:top center;
}
.ol-shade{
  width:132px; height:66px; position:relative;
  background:linear-gradient(180deg,#F2EDE2 0%,#DCD5C6 100%);
  border-radius:132px 132px 14px 14px;
  animation:ol-sway 4.5s ease-in-out infinite; transform-origin:top center;
  box-shadow:0 10px 26px rgba(0,0,0,.45);
}
.ol-bulb{
  position:absolute; left:50%; bottom:-9px; transform:translateX(-50%);
  width:22px; height:22px; border-radius:50%;
  background:#FFD9A0; filter:blur(1px);
  box-shadow:0 0 22px 8px rgba(255,168,66,.85);
  animation:ol-flicker 3.2s ease-in-out infinite;
}
/* مخروط الضوء */
.ol-beam{
  position:absolute; top:112px; left:50%; transform:translateX(-50%);
  width:0; height:0; pointer-events:none;
  border-left:118px solid transparent; border-right:118px solid transparent;
  border-top:230px solid rgba(255,169,74,.16);
  filter:blur(14px);
  animation:ol-flicker 3.2s ease-in-out infinite;
}
@keyframes ol-sway{
  0%,100%{transform:rotate(-3.5deg)} 50%{transform:rotate(3.5deg)}
}
@keyframes ol-flicker{
  0%,100%{opacity:1} 45%{opacity:.86} 60%{opacity:1} 72%{opacity:.9}
}
@media (prefers-reduced-motion:reduce){
  .ol-cord,.ol-shade,.ol-bulb,.ol-beam{animation:none !important}
}

/* ── الشعار ─────────────────────────────────────────────────────────── */
.ol-brand{
  text-align:center; margin-top:6px;
  font-size:30px; font-weight:900; letter-spacing:.5px;
}
.ol-brand b{color:#FF7A1A}
.ol-brand span{color:#F3EEF9}
.ol-brand small{
  display:block; font-size:12px; font-weight:600; color:#9E93B5;
  letter-spacing:3px; margin-top:2px;
}

/* ── حقول Streamlit الأصلية (شغالة زي ما هي، متلبّسة بس) ───────────── */
[data-testid="stTextInput"] input{
  background:rgba(255,255,255,.05) !important;
  border:1px solid rgba(255,255,255,.14) !important;
  border-radius:12px !important; color:#F3EEF9 !important;
  padding:12px 14px !important; font-size:15px !important;
}
[data-testid="stTextInput"] input:focus{
  border-color:#FF7A1A !important;
  box-shadow:0 0 0 3px rgba(255,122,26,.22) !important;
}
[data-testid="stTextInput"] input::placeholder{color:#8b83a0 !important}

.stButton>button{
  background:linear-gradient(135deg,#FF7A1A,#FF9E4A) !important;
  color:#1a1220 !important; border:0 !important; border-radius:12px !important;
  font-weight:800 !important; padding:11px 0 !important; width:100% !important;
  box-shadow:0 6px 18px rgba(255,122,26,.3) !important;
  transition:transform .12s ease, box-shadow .12s ease !important;
}
.stButton>button:hover{
  transform:translateY(-1px);
  box-shadow:0 10px 24px rgba(255,122,26,.42) !important;
}
.stButton>button:active{transform:translateY(1px)}

hr{border-color:rgba(255,255,255,.10) !important}
</style>
"""

LAMP = """
<div class="ol-lamp-wrap">
  <div class="ol-beam"></div>
  <div class="ol-cord"></div>
  <div class="ol-shade"><div class="ol-bulb"></div></div>
</div>
<div class="ol-brand"><b>Ô</b><span>range</span>
  <small>LAB &nbsp;•&nbsp; HOME VISITS</small>
</div>
"""


def render(st):
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(LAMP, unsafe_allow_html=True)
