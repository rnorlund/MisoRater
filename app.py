import streamlit as st
import os
import json
import random
import datetime
import base64
import plotly.graph_objects as go
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MATA_ROOT = Path(__file__).parent / "MATA-main"
DATA_DIR = Path(__file__).parent / "user_data"
DATA_DIR.mkdir(exist_ok=True)

SOUNDS_PER_CATEGORY = 3

TEST_DURATIONS = {
    "Quick (3 min)":    2,
    "Standard (6 min)": 4,
    "Extended (9 min)": 6,
    "Full (12 min)":    8,
}

SPIDER_GROUPS = {
    "Eating / Chewing": ["Mouth Sounds (eating)"],
    "Oral (non-eating)": ["Mouth Sounds (not eating)"],
    "Nasal / Throat": ["Nasal-Throat Sounds"],
    "Body Sounds": ["Body Part Sounds", "Walking Sounds"],
    "Human Repetitive": ["Repetitive & Continuous Sounds (human)"],
    "Animal Sounds": ["Repetitive & Continuous Sounds (animal)"],
    "Environmental": ["Repetitive & Continuous Sounds (non-human)"],
    "Texture / Rustling": ["Rustling & Tearing Sounds", "Rubbing Sounds"],
    "Speech / Voice": ["Speech & Vocalization Sounds", "Talking Sounds"],
}

CAT_COLORS = {
    "Eating / Chewing":  "#FF6584",
    "Oral (non-eating)": "#FF922B",
    "Nasal / Throat":    "#FFD93D",
    "Body Sounds":       "#6BCB77",
    "Human Repetitive":  "#43E8D8",
    "Animal Sounds":     "#4D96FF",
    "Environmental":     "#6C63FF",
    "Texture / Rustling":"#C084FC",
    "Speech / Voice":    "#F472B6",
}

CAT_DESCRIPTIONS = {
    "Eating / Chewing":  "chewing, biting, slurping, swallowing, and gum sounds",
    "Oral (non-eating)": "lip smacking, whistling, tongue clicking, teeth grinding, and mouth noises",
    "Nasal / Throat":    "sniffling, sneezing, coughing, throat clearing, and breathing sounds",
    "Body Sounds":       "clapping, joint cracking, skin scratching, finger snapping, and footsteps",
    "Human Repetitive":  "tapping, typing, scratching surfaces, dragging, and kitchenware clanking",
    "Animal Sounds":     "barking, licking, chirping, purring, and animal chewing",
    "Environmental":     "alarms, beeping, water dripping, machinery humming, and crackling",
    "Texture / Rustling":"paper crinkling, plastic rustling, foam squeaking, velcro, and fabric rubbing",
    "Speech / Voice":    "whispering, crowd murmur, and vocal sounds",
}

PRIMARY = "#6C63FF"

ATTRIBUTION_HTML = (
    '<div class="attribution">'
    'Sound stimuli from the '
    '<a href="https://github.com/Svetlana-Shinkareva/MATA" target="_blank">Misophonia Audiovisual Trigger Archive (MATA)</a> '
    'by Shinkareva et al., licensed under '
    '<a href="https://creativecommons.org/licenses/by-nc/4.0/" target="_blank">CC BY-NC 4.0</a>.'
    '</div>'
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@st.cache_data
def collect_sounds() -> dict[str, list[str]]:
    group_files: dict[str, list[str]] = {g: [] for g in SPIDER_GROUPS}
    for group, folders in SPIDER_GROUPS.items():
        for folder in folders:
            root = MATA_ROOT / folder
            if not root.exists():
                continue
            for dirpath, _, filenames in os.walk(root):
                for f in filenames:
                    if f.lower().endswith(".mp4"):
                        group_files[group].append(os.path.join(dirpath, f))
    return group_files


def sample_test(group_files: dict[str, list[str]], n: int = SOUNDS_PER_CATEGORY) -> list[dict]:
    items = []
    for group, paths in group_files.items():
        chosen = random.sample(paths, min(n, len(paths)))
        for p in chosen:
            pretty = Path(p).stem.replace("norm_mono_", "").replace("_", " ")
            items.append({"group": group, "path": p, "name": pretty})
    random.shuffle(items)
    return items


def render_audio_player(filepath: str, _idx: int = 0):
    import streamlit.components.v1 as components
    with open(filepath, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    html = f"""
    <html><body style="margin:0;padding:0;background:transparent;">
    <audio id="player" controls controlsList="nodownload"
           style="width:100%;border-radius:8px;">
        <source src="data:audio/mp4;base64,{data}" type="audio/mp4">
    </audio>
    <script>
        var a = document.getElementById('player');
        a.play().catch(function(){{}});
    </script>
    </body></html>
    """
    components.html(html, height=55, scrolling=False)


def save_result(username: str, ratings: dict[str, list[int]]):
    path = DATA_DIR / f"{username}.json"
    history = []
    if path.exists():
        history = json.loads(path.read_text())
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "ratings": {g: vals for g, vals in ratings.items()},
        "averages": {g: round(sum(v) / len(v), 2) if v else 0 for g, v in ratings.items()},
    }
    history.append(entry)
    path.write_text(json.dumps(history, indent=2))
    return entry, history


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{alpha})"


def generate_sensitivity_summary(averages: dict[str, float]) -> str:
    if not averages:
        return ""
    overall = sum(averages.values()) / len(averages)
    sorted_cats = sorted(averages.items(), key=lambda x: x[1], reverse=True)

    if overall >= 7:
        severity = "high overall sound sensitivity"
    elif overall >= 4:
        severity = "moderate overall sound sensitivity"
    elif overall >= 2:
        severity = "mild overall sound sensitivity"
    else:
        severity = "low overall sound sensitivity"

    high = [(c, s) for c, s in sorted_cats if s >= 5]
    moderate = [(c, s) for c, s in sorted_cats if 3 <= s < 5]
    low = [(c, s) for c, s in sorted_cats if s < 3]

    parts = [f"Your results indicate **{severity}** (average: {overall:.1f}/10)."]
    if high:
        triggers = ", ".join(f"**{c}** ({CAT_DESCRIPTIONS.get(c, '')})" for c, _ in high)
        parts.append(f"Your strongest reactions are to {triggers}. "
                     "These categories caused notable distress and may be primary misophonia triggers for you.")
    if moderate:
        triggers = ", ".join(f"**{c}**" for c, _ in moderate)
        parts.append(f"You show moderate sensitivity to {triggers} -- these sounds are uncomfortable but more tolerable.")
    if low:
        triggers = ", ".join(f"**{c}**" for c, _ in low)
        parts.append(f"You show little reaction to {triggers}.")
    if not high and not moderate:
        parts.append("No categories triggered strong distress. Your responses suggest low misophonia sensitivity across tested sound types.")
    return "\n\n".join(parts)


def make_overall_avg_chart(history: list[dict]):
    if len(history) < 1:
        return None
    dates = [h["timestamp"][:10] for h in history]
    avgs = [round(sum(h["averages"].values()) / len(h["averages"]), 2) if h["averages"] else 0 for h in history]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=avgs, mode="lines+markers+text",
        text=[f"{v:.1f}" for v in avgs], textposition="top center",
        textfont=dict(color="#ddd", size=13),
        line=dict(color="#6C63FF", width=3),
        marker=dict(size=10, color="#6C63FF", line=dict(color="white", width=2)),
        fill="tozeroy", fillcolor="rgba(108,99,255,0.10)", name="Overall average",
    ))
    fig.update_layout(
        xaxis=dict(title="Session date", color="#ccc", gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(title="Overall distress (0-10)", range=[0, 10], color="#ccc", gridcolor="rgba(255,255,255,0.06)"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False, margin=dict(l=50, r=20, t=30, b=50), height=320,
    )
    return fig


def make_radar(averages: dict[str, float], title: str = ""):
    cats = list(averages.keys())
    vals = [averages[c] for c in cats]
    cats_closed = cats + [cats[0]]
    vals_closed = vals + [vals[0]]
    colors = [CAT_COLORS.get(c, "#888") for c in cats]
    fig = go.Figure()
    for i, (cat, val) in enumerate(zip(cats, vals)):
        fig.add_trace(go.Scatterpolar(
            r=[val], theta=[cat], mode="markers+text",
            marker=dict(color=colors[i], size=14, symbol="circle", line=dict(color="white", width=1)),
            text=[f"{val:.1f}"], textposition="top center",
            textfont=dict(color=colors[i], size=14, family="Inter, sans-serif"), showlegend=False,
        ))
    fig.add_trace(go.Scatterpolar(
        r=vals_closed, theta=cats_closed, fill="toself",
        fillcolor="rgba(108,99,255,0.12)",
        line=dict(color="rgba(200,200,255,0.5)", width=2, shape="spline"),
        name=title if title else "Score", showlegend=bool(title),
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], tickfont=dict(size=12, color="#888"), gridcolor="rgba(255,255,255,0.08)"),
            angularaxis=dict(tickfont=dict(size=15, color="#ddd", family="Inter, sans-serif"), gridcolor="rgba(255,255,255,0.06)"),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=bool(title), legend=dict(font=dict(color="#ccc", size=13)),
        margin=dict(l=80, r=80, t=50, b=50),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=550,
    )
    return fig


def make_comparison_radar(history: list[dict]):
    if len(history) < 2:
        return None
    first, latest = history[0]["averages"], history[-1]["averages"]
    cats = list(first.keys())
    fig = go.Figure()
    for avgs, label, color, dash in [
        (first, f"Session 1  ({history[0]['timestamp'][:10]})", "#FF6584", "dot"),
        (latest, f"Session {len(history)}  ({history[-1]['timestamp'][:10]})", "#43E8D8", "solid"),
    ]:
        vals = [avgs.get(c, 0) for c in cats] + [avgs.get(cats[0], 0)]
        fig.add_trace(go.Scatterpolar(
            r=vals, theta=cats + [cats[0]], fill="toself",
            fillcolor=_hex_to_rgba(color, 0.12), line=dict(color=color, width=3, dash=dash), name=label,
        ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], tickfont=dict(size=12, color="#888"), gridcolor="rgba(255,255,255,0.08)"),
            angularaxis=dict(tickfont=dict(size=14, color="#ddd", family="Inter, sans-serif"), gridcolor="rgba(255,255,255,0.06)"),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        legend=dict(font=dict(color="#ccc", size=13), orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5),
        margin=dict(l=80, r=80, t=50, b=70),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=560,
    )
    return fig


def trend_chart(history: list[dict]):
    if len(history) < 2:
        return None
    cats = list(history[0]["averages"].keys())
    dates = [h["timestamp"][:10] for h in history]
    fig = go.Figure()
    for cat in cats:
        vals = [h["averages"].get(cat, 0) for h in history]
        fig.add_trace(go.Scatter(
            x=dates, y=vals, mode="lines+markers", name=cat,
            line=dict(color=CAT_COLORS.get(cat, "#888"), width=2), marker=dict(size=7),
        ))
    fig.update_layout(
        xaxis=dict(title="Session date", color="#ccc", gridcolor="rgba(255,255,255,0.06)"),
        yaxis=dict(title="Avg. distress (0-10)", range=[0, 10], color="#ccc", gridcolor="rgba(255,255,255,0.06)"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(color="#ccc", size=11), orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5),
        margin=dict(l=50, r=20, t=30, b=80), height=420,
    )
    return fig


def score_bars_html(averages: dict[str, float]) -> str:
    sorted_cats = sorted(averages.items(), key=lambda x: x[1], reverse=True)
    html = ""
    for cat, score in sorted_cats:
        color = CAT_COLORS.get(cat, "#888")
        pct = max(score / 10 * 100, 5)
        html += f"""
        <div class="score-row">
            <div class="score-label" style="color:{color};">{cat}</div>
            <div class="score-bar-bg">
                <div class="score-bar-fill" style="width:{pct}%;background:linear-gradient(90deg,{_hex_to_rgba(color,0.7)},{color});"></div>
            </div>
            <div class="score-value" style="color:{color};">{score:.1f}</div>
        </div>"""
    return html


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Global tweaks */
    .block-container { max-width: 740px; padding-top: 2rem; }
    .stProgress > div > div > div { background: linear-gradient(90deg, #6C63FF, #43E8D8); border-radius: 8px; }

    /* Hero */
    .hero {
        text-align: center; padding: 2.5rem 1rem 0.5rem;
    }
    .hero h1 {
        font-size: 2.8rem; font-weight: 700; letter-spacing: -0.5px;
        background: linear-gradient(135deg, #6C63FF 0%, #43E8D8 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    .hero p { color: #888; font-size: 1.05rem; margin: 0; }

    /* Card */
    .card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 1rem;
    }
    .card h3 {
        font-size: 1rem; font-weight: 600; color: #ddd;
        margin: 0 0 0.8rem; letter-spacing: 0.3px;
    }
    .card ul { margin: 0; padding-left: 1.2rem; }
    .card li { color: #bbb; font-size: 0.92rem; line-height: 1.75; }

    /* Sound card */
    .sound-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 1rem 1.3rem;
        margin-bottom: 0.5rem;
    }
    .sound-card .group-badge {
        display: inline-block; border-radius: 20px;
        padding: 3px 14px; font-size: 0.78rem; font-weight: 600; margin-bottom: 0.4rem;
    }
    .sound-card .sound-name { font-size: 1rem; color: #e0e0e0; }

    /* Rating labels */
    .rating-label-row { display: flex; justify-content: space-between; padding: 0 4px; margin-bottom: 2px; }
    .rating-label { color: #666; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.5px; }

    /* Report header */
    .report-header {
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 1.6rem 2rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(135deg, rgba(108,99,255,0.08), rgba(67,232,216,0.04));
    }
    .report-header h2 {
        margin: 0 0 0.4rem; font-size: 1.8rem; font-weight: 700;
        background: linear-gradient(135deg, #6C63FF, #43E8D8);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .report-meta { color: #999; font-size: 0.93rem; line-height: 1.9; }
    .report-meta strong { color: #ccc; }

    /* Score bars */
    .score-row {
        display: flex; align-items: center; gap: 12px;
        padding: 7px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .score-label { width: 150px; font-size: 0.85rem; font-weight: 600; text-align: right; }
    .score-bar-bg {
        flex: 1; height: 26px; border-radius: 8px;
        background: rgba(255,255,255,0.05); overflow: hidden;
    }
    .score-bar-fill {
        height: 100%; border-radius: 8px; min-width: 30px;
        transition: width 0.6s ease;
    }
    .score-value { width: 44px; text-align: left; font-size: 0.95rem; font-weight: 700; }

    /* Summary box */
    .summary-box {
        background: rgba(255,255,255,0.03);
        border-left: 4px solid #6C63FF;
        border-radius: 0 12px 12px 0;
        padding: 1.1rem 1.4rem;
        margin: 0.8rem 0;
        color: #bbb; font-size: 0.93rem; line-height: 1.75;
    }

    /* Section heading */
    .section-title {
        font-size: 0.82rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 1.2px; color: #777; margin: 1.8rem 0 0.6rem; padding-bottom: 0.4rem;
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }

    /* Attribution */
    .attribution {
        text-align: center; padding: 1.2rem 0 0.5rem;
        border-top: 1px solid rgba(255,255,255,0.06);
        margin-top: 2.5rem; color: #666; font-size: 0.8rem; line-height: 1.7;
    }
    .attribution a { color: #9994ff; text-decoration: none; }
    .attribution a:hover { text-decoration: underline; }

    /* Category dot */
    .cat-dot {
        display: flex; align-items: center; gap: 8px;
        font-size: 0.9rem; color: #bbb; line-height: 1.9;
    }
    .cat-dot span { font-size: 0.6rem; }
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def page_home():
    st.markdown("""
    <div class="hero">
        <h1>MisoRater</h1>
        <p>Measure your sound sensitivity &middot; Track your progress over time</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    # --- Name + duration + buttons: centered action area ---
    username = st.text_input("Your name", placeholder="e.g. Alex", key="home_user", label_visibility="collapsed")

    if username:
        st.session_state["username"] = username.strip().lower().replace(" ", "_")
        path = DATA_DIR / f"{st.session_state['username']}.json"
        if path.exists():
            history = json.loads(path.read_text())
            st.success(f"Welcome back, **{username}**! You have **{len(history)}** previous session(s).")

        duration_labels = list(TEST_DURATIONS.keys())
        selected = st.radio("Test length", duration_labels, index=1, horizontal=True, key="duration_radio")
        n_per_cat = TEST_DURATIONS[selected]
        total_sounds = n_per_cat * len(SPIDER_GROUPS)
        st.caption(f"{total_sounds} sounds  |  {n_per_cat} per category  |  ~{total_sounds * 10 // 60} minutes")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Start Test", type="primary", use_container_width=True):
                st.session_state["sounds_per_cat"] = n_per_cat
                st.session_state["page"] = "test"
                st.session_state["test_items"] = None
                st.session_state["current_idx"] = 0
                st.session_state["collected_ratings"] = {}
                st.rerun()
        with col_b:
            if st.button("View History", use_container_width=True):
                st.session_state["page"] = "history"
                st.rerun()
    else:
        st.markdown('<p style="text-align:center;color:#666;font-size:0.9rem;">Enter your name above to get started</p>',
                    unsafe_allow_html=True)

    st.markdown("")

    # --- Two symmetrical info cards ---
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class="card">
            <h3>How it works</h3>
            <ul>
                <li>Enter your name to create a profile</li>
                <li>Listen to sounds from 9 categories</li>
                <li>Rate each on a 0 &ndash; 10 distress scale</li>
                <li>Get a spider graph of your sensitivity</li>
                <li>Retake weekly to track training progress</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        cats_html = "".join(
            f'<div class="cat-dot"><span style="color:{color};">&#11044;</span> {cat}</div>'
            for cat, color in CAT_COLORS.items()
        )
        st.markdown(f'<div class="card"><h3>Sound categories</h3>{cats_html}</div>', unsafe_allow_html=True)

    st.markdown(ATTRIBUTION_HTML, unsafe_allow_html=True)


def page_test():
    username = st.session_state.get("username", "")
    if not username:
        st.session_state["page"] = "home"
        st.rerun()
        return

    group_files = collect_sounds()
    if st.session_state.get("test_items") is None:
        n = st.session_state.get("sounds_per_cat", SOUNDS_PER_CATEGORY)
        st.session_state["test_items"] = sample_test(group_files, n=n)
        st.session_state["current_idx"] = 0
        st.session_state["collected_ratings"] = {}

    items = st.session_state["test_items"]
    idx = st.session_state["current_idx"]
    total = len(items)

    # Header bar
    col_l, col_r = st.columns([3, 1])
    with col_l:
        st.markdown(f"##### Sound {idx + 1} of {total}")
    with col_r:
        st.markdown(f'<p style="text-align:right;color:#666;font-size:0.85rem;margin-top:6px;">'
                    f'{username.replace("_"," ").title()}</p>', unsafe_allow_html=True)
    st.progress(idx / total)

    if idx < total:
        item = items[idx]
        group, name, filepath = item["group"], item["name"], item["path"]
        badge_color = CAT_COLORS.get(group, "#6C63FF")

        st.markdown(f"""
        <div class="sound-card">
            <div class="group-badge" style="background:{_hex_to_rgba(badge_color,0.2)};color:{badge_color};">{group}</div>
            <div class="sound-name">{name}</div>
        </div>
        """, unsafe_allow_html=True)

        render_audio_player(filepath, idx)

        # Rating buttons
        current_rating = st.session_state.get(f"btn_rating_{idx}", None)
        st.markdown('<div class="rating-label-row">'
                    '<span class="rating-label">Not at all</span>'
                    '<span class="rating-label">Extremely distressing</span>'
                    '</div>', unsafe_allow_html=True)

        cols = st.columns(11)
        for val in range(11):
            with cols[val]:
                selected = current_rating == val
                btn_type = "primary" if selected else "secondary"
                if st.button(str(val), key=f"rbtn_{idx}_{val}", type=btn_type, use_container_width=True):
                    st.session_state[f"btn_rating_{idx}"] = val
                    st.rerun()

        st.markdown("")

        col_prev, col_skip, col_next = st.columns(3)
        with col_prev:
            if idx > 0 and st.button("Back", use_container_width=True):
                st.session_state["current_idx"] -= 1
                st.rerun()
        with col_skip:
            if st.button("Skip", use_container_width=True):
                st.session_state["current_idx"] += 1
                st.rerun()
        with col_next:
            label = "Next" if idx < total - 1 else "Finish"
            if st.button(label, type="primary", use_container_width=True):
                rating = st.session_state.get(f"btn_rating_{idx}", 5)
                ratings = st.session_state["collected_ratings"]
                ratings.setdefault(group, []).append(rating)
                st.session_state["collected_ratings"] = ratings
                st.session_state["current_idx"] += 1
                st.rerun()
    else:
        st.balloons()
        ratings = st.session_state["collected_ratings"]
        entry, history = save_result(username, ratings)
        st.session_state["last_entry"] = entry
        st.session_state["history"] = history
        st.session_state["page"] = "results"
        st.rerun()


def page_results():
    username = st.session_state.get("username", "")
    entry = st.session_state.get("last_entry")
    history = st.session_state.get("history", [])
    if not entry:
        st.session_state["page"] = "home"
        st.rerun()
        return

    averages = entry["averages"]
    ts = entry["timestamp"]
    date_str, time_str = ts[:10], ts[11:16]
    session_num = len(history)
    overall_avg = sum(averages.values()) / len(averages) if averages else 0

    st.markdown(f"""
    <div class="report-header">
        <h2>MisoRater Report</h2>
        <div class="report-meta">
            <strong>Participant:</strong> {username.replace("_", " ").title()}<br>
            <strong>Date:</strong> {date_str} &nbsp;&middot;&nbsp; <strong>Time:</strong> {time_str}<br>
            <strong>Session:</strong> #{session_num} &nbsp;&middot;&nbsp;
            <strong>Overall distress:</strong> {overall_avg:.1f} / 10
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Summary
    st.markdown('<div class="section-title">Sensitivity Summary</div>', unsafe_allow_html=True)
    summary = generate_sensitivity_summary(averages)
    st.markdown(f'<div class="summary-box">{summary}</div>', unsafe_allow_html=True)

    # Spider chart
    st.markdown('<div class="section-title">Sensitivity Profile</div>', unsafe_allow_html=True)
    st.plotly_chart(make_radar(averages, title="Current session"), use_container_width=True)

    # Score bars
    st.markdown('<div class="section-title">Category Breakdown</div>', unsafe_allow_html=True)
    st.markdown(score_bars_html(averages), unsafe_allow_html=True)

    # Over-time charts (only if 2+ sessions)
    if len(history) >= 2:
        st.markdown('<div class="section-title">Overall Distress Over Time</div>', unsafe_allow_html=True)
        avg_fig = make_overall_avg_chart(history)
        if avg_fig:
            st.plotly_chart(avg_fig, use_container_width=True)

        st.markdown('<div class="section-title">Progress: First vs. Latest</div>', unsafe_allow_html=True)
        comp_fig = make_comparison_radar(history)
        if comp_fig:
            st.plotly_chart(comp_fig, use_container_width=True)

        first_avgs = history[0]["averages"]
        st.markdown('<div class="section-title">Change by Category</div>', unsafe_allow_html=True)
        delta_html = ""
        for cat in averages:
            curr, prev = averages.get(cat, 0), first_avgs.get(cat, 0)
            diff = curr - prev
            color = CAT_COLORS.get(cat, "#888")
            arrow = "&#9650;" if diff > 0 else "&#9660;" if diff < 0 else "&#8212;"
            diff_color = "#FF6584" if diff > 0 else "#6BCB77" if diff < 0 else "#555"
            delta_html += (
                f'<div style="display:flex;align-items:center;gap:10px;padding:5px 0;'
                f'border-bottom:1px solid rgba(255,255,255,0.04);">'
                f'<span style="width:150px;text-align:right;color:{color};font-weight:600;font-size:0.85rem;">{cat}</span>'
                f'<span style="width:50px;color:#888;font-size:0.9rem;">{prev:.1f}</span>'
                f'<span style="color:{diff_color};font-size:1rem;">{arrow}</span>'
                f'<span style="width:50px;font-weight:700;color:#ddd;font-size:0.9rem;">{curr:.1f}</span>'
                f'<span style="color:{diff_color};font-weight:600;font-size:0.85rem;">({diff:+.1f})</span>'
                f'</div>'
            )
        st.markdown(delta_html, unsafe_allow_html=True)

    st.markdown("")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Take Another Test", type="primary", use_container_width=True):
            st.session_state["page"] = "test"
            st.session_state["test_items"] = None
            st.rerun()
    with col2:
        if st.button("View Full History", use_container_width=True):
            st.session_state["page"] = "history"
            st.rerun()

    st.markdown(ATTRIBUTION_HTML, unsafe_allow_html=True)


def page_history():
    username = st.session_state.get("username", "")
    if not username:
        st.session_state["page"] = "home"
        st.rerun()
        return

    path = DATA_DIR / f"{username}.json"
    if not path.exists():
        st.info("No history yet. Take your first test!")
        if st.button("Go to test"):
            st.session_state["page"] = "home"
            st.rerun()
        return

    history = json.loads(path.read_text())

    st.markdown(f"""
    <div class="report-header">
        <h2>Training History</h2>
        <div class="report-meta">
            <strong>Participant:</strong> {username.replace("_", " ").title()}<br>
            <strong>Sessions:</strong> {len(history)} &nbsp;&middot;&nbsp;
            <strong>First:</strong> {history[0]['timestamp'][:10]} &nbsp;&middot;&nbsp;
            <strong>Latest:</strong> {history[-1]['timestamp'][:10]}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Summary
    st.markdown('<div class="section-title">Current Sensitivity Summary</div>', unsafe_allow_html=True)
    summary = generate_sensitivity_summary(history[-1]["averages"])
    st.markdown(f'<div class="summary-box">{summary}</div>', unsafe_allow_html=True)

    # Overall avg over time
    st.markdown('<div class="section-title">Overall Distress Over Time</div>', unsafe_allow_html=True)
    avg_fig = make_overall_avg_chart(history)
    if avg_fig:
        st.plotly_chart(avg_fig, use_container_width=True)

    # Per-category trends
    trend = trend_chart(history)
    if trend:
        st.markdown('<div class="section-title">Category Trends</div>', unsafe_allow_html=True)
        st.plotly_chart(trend, use_container_width=True)

    # Comparison radar
    comp = make_comparison_radar(history)
    if comp:
        st.markdown('<div class="section-title">First vs. Latest</div>', unsafe_allow_html=True)
        st.plotly_chart(comp, use_container_width=True)

    # Metrics
    if len(history) >= 2:
        first_avg = sum(history[0]["averages"].values()) / len(history[0]["averages"])
        latest_avg = sum(history[-1]["averages"].values()) / len(history[-1]["averages"])
        delta = latest_avg - first_avg
        st.markdown('<div class="section-title">Overall Change</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("First session", f"{first_avg:.1f}")
        with col2:
            st.metric("Latest session", f"{latest_avg:.1f}", delta=f"{delta:+.1f}", delta_color="inverse")
        with col3:
            st.metric("Total sessions", len(history))

    # Individual sessions
    st.markdown('<div class="section-title">Session Details</div>', unsafe_allow_html=True)
    for i, sess in enumerate(reversed(history)):
        sess_num = len(history) - i
        sess_avg = sum(sess["averages"].values()) / len(sess["averages"]) if sess["averages"] else 0
        with st.expander(f"Session {sess_num}  --  {sess['timestamp'][:10]}  (avg: {sess_avg:.1f})"):
            st.plotly_chart(make_radar(sess["averages"]), use_container_width=True)
            st.markdown(score_bars_html(sess["averages"]), unsafe_allow_html=True)
            st.markdown(f'<div class="summary-box">{generate_sensitivity_summary(sess["averages"])}</div>',
                        unsafe_allow_html=True)

    st.markdown("")
    if st.button("Back to Home", use_container_width=True):
        st.session_state["page"] = "home"
        st.rerun()

    st.markdown(ATTRIBUTION_HTML, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="MisoRater", page_icon="🕸️", layout="centered", initial_sidebar_state="collapsed")
    inject_css()

    if "page" not in st.session_state:
        st.session_state["page"] = "home"

    with st.sidebar:
        st.markdown("### MisoRater")
        if st.button("Home", use_container_width=True):
            st.session_state["page"] = "home"
            st.rerun()
        if st.button("Take Test", use_container_width=True):
            if st.session_state.get("username"):
                st.session_state["page"] = "test"
                st.session_state["test_items"] = None
                st.rerun()
            else:
                st.warning("Enter your name on the home page first.")
        if st.button("History", use_container_width=True):
            if st.session_state.get("username"):
                st.session_state["page"] = "history"
                st.rerun()
            else:
                st.warning("Enter your name on the home page first.")

    page = st.session_state["page"]
    if page == "home":
        page_home()
    elif page == "test":
        page_test()
    elif page == "results":
        page_results()
    elif page == "history":
        page_history()


if __name__ == "__main__":
    main()
