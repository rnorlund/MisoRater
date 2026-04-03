import streamlit as st
import os
import json
import random
import datetime
import base64
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MATA_ROOT = Path(__file__).parent / "MATA-main"
DATA_DIR = Path(__file__).parent / "user_data"
DATA_DIR.mkdir(exist_ok=True)

SOUNDS_PER_CATEGORY = 3

# ---------------------------------------------------------------------------
# Spider-graph groupings
# ---------------------------------------------------------------------------
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

# Human-readable descriptions of what each category contains
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
    '<div style="text-align:center;padding:1.2rem 0 0.5rem;border-top:1px solid rgba(255,255,255,0.06);'
    'margin-top:2rem;color:#777;font-size:0.82rem;line-height:1.7;">'
    'Sound stimuli from the '
    '<a href="https://github.com/Svetlana-Shinkareva/MATA" target="_blank" '
    'style="color:#9994ff;text-decoration:none;">Misophonia Audiovisual Trigger Archive (MATA)</a> '
    'by Shinkareva et al., licensed under '
    '<a href="https://creativecommons.org/licenses/by-nc/4.0/" target="_blank" '
    'style="color:#9994ff;text-decoration:none;">CC BY-NC 4.0</a>.'
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


def autoplay_audio_html(filepath: str) -> str:
    with open(filepath, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return (
        f'<audio autoplay controls controlsList="nodownload" style="width:100%">'
        f'<source src="data:audio/mp4;base64,{data}" type="audio/mp4">'
        f"Your browser does not support the audio element.</audio>"
    )


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
    """Generate a brief human-readable text describing what the person is sensitive to."""
    if not averages:
        return ""

    overall = sum(averages.values()) / len(averages)
    sorted_cats = sorted(averages.items(), key=lambda x: x[1], reverse=True)

    # Severity label
    if overall >= 7:
        severity = "high overall sound sensitivity"
    elif overall >= 4:
        severity = "moderate overall sound sensitivity"
    elif overall >= 2:
        severity = "mild overall sound sensitivity"
    else:
        severity = "low overall sound sensitivity"

    # Top triggers (score >= 5)
    high = [(cat, score) for cat, score in sorted_cats if score >= 5]
    # Moderate triggers (3-5)
    moderate = [(cat, score) for cat, score in sorted_cats if 3 <= score < 5]
    # Low triggers (< 3)
    low = [(cat, score) for cat, score in sorted_cats if score < 3]

    parts = [f"Your results indicate **{severity}** (average: {overall:.1f}/10)."]

    if high:
        triggers = ", ".join(
            f"**{cat}** ({CAT_DESCRIPTIONS.get(cat, '')})" for cat, _ in high
        )
        parts.append(
            f"Your strongest reactions are to {triggers}. "
            "These categories caused notable distress and may be primary misophonia triggers for you."
        )

    if moderate:
        triggers = ", ".join(f"**{cat}**" for cat, _ in moderate)
        parts.append(
            f"You show moderate sensitivity to {triggers} -- "
            "these sounds are uncomfortable but more tolerable."
        )

    if low:
        triggers = ", ".join(f"**{cat}**" for cat, _ in low)
        parts.append(f"You show little reaction to {triggers}.")

    if not high and not moderate:
        parts.append(
            "No categories triggered strong distress in this session. "
            "Your responses suggest low misophonia sensitivity across the tested sound types."
        )

    return "\n\n".join(parts)


def make_overall_avg_chart(history: list[dict]):
    """Line chart of overall average distress score across sessions."""
    if len(history) < 1:
        return None
    dates = [h["timestamp"][:10] for h in history]
    avgs = [
        round(sum(h["averages"].values()) / len(h["averages"]), 2) if h["averages"] else 0
        for h in history
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=avgs, mode="lines+markers+text",
        text=[f"{v:.1f}" for v in avgs],
        textposition="top center",
        textfont=dict(color="#ddd", size=13),
        line=dict(color="#6C63FF", width=3),
        marker=dict(size=10, color="#6C63FF", line=dict(color="white", width=2)),
        fill="tozeroy",
        fillcolor="rgba(108,99,255,0.10)",
        name="Overall average",
    ))
    fig.update_layout(
        xaxis=dict(title="Session date", color="#ccc", gridcolor="#333"),
        yaxis=dict(title="Overall distress (0-10)", range=[0, 10], color="#ccc", gridcolor="#333"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=50, r=20, t=30, b=50),
        height=320,
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
            r=[val],
            theta=[cat],
            mode="markers+text",
            marker=dict(color=colors[i], size=14, symbol="circle",
                        line=dict(color="white", width=1)),
            text=[f"{val:.1f}"],
            textposition="top center",
            textfont=dict(color=colors[i], size=14, family="Inter, sans-serif"),
            showlegend=False,
        ))

    fig.add_trace(go.Scatterpolar(
        r=vals_closed,
        theta=cats_closed,
        fill="toself",
        fillcolor="rgba(108,99,255,0.12)",
        line=dict(color="rgba(200,200,255,0.5)", width=2, shape="spline"),
        name=title if title else "Score",
        showlegend=bool(title),
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10],
                            tickfont=dict(size=12, color="#888"),
                            gridcolor="rgba(255,255,255,0.08)"),
            angularaxis=dict(
                tickfont=dict(size=15, color="#ddd", family="Inter, sans-serif"),
                gridcolor="rgba(255,255,255,0.06)"),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=bool(title),
        legend=dict(font=dict(color="#ccc", size=13)),
        margin=dict(l=80, r=80, t=50, b=50),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=550,
    )
    return fig


def make_comparison_radar(history: list[dict]):
    if len(history) < 2:
        return None
    first = history[0]["averages"]
    latest = history[-1]["averages"]
    cats = list(first.keys())

    fig = go.Figure()
    for avgs, label, color, dash in [
        (first, f"Session 1  ({history[0]['timestamp'][:10]})", "#FF6584", "dot"),
        (latest, f"Session {len(history)}  ({history[-1]['timestamp'][:10]})", "#43E8D8", "solid"),
    ]:
        vals = [avgs.get(c, 0) for c in cats] + [avgs.get(cats[0], 0)]
        fig.add_trace(go.Scatterpolar(
            r=vals,
            theta=cats + [cats[0]],
            fill="toself",
            fillcolor=_hex_to_rgba(color, 0.12),
            line=dict(color=color, width=3, dash=dash),
            name=label,
        ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10],
                            tickfont=dict(size=12, color="#888"),
                            gridcolor="rgba(255,255,255,0.08)"),
            angularaxis=dict(
                tickfont=dict(size=14, color="#ddd", family="Inter, sans-serif"),
                gridcolor="rgba(255,255,255,0.06)"),
            bgcolor="rgba(0,0,0,0)",
        ),
        showlegend=True,
        legend=dict(font=dict(color="#ccc", size=13), orientation="h",
                    yanchor="bottom", y=-0.18, xanchor="center", x=0.5),
        margin=dict(l=80, r=80, t=50, b=70),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=560,
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
            line=dict(color=CAT_COLORS.get(cat, "#888"), width=2),
            marker=dict(size=7),
        ))
    fig.update_layout(
        xaxis=dict(title="Session date", color="#ccc", gridcolor="#333"),
        yaxis=dict(title="Avg. distress (0-10)", range=[0, 10], color="#ccc", gridcolor="#333"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(color="#ccc", size=11), orientation="h",
                    yanchor="bottom", y=-0.35, xanchor="center", x=0.5),
        margin=dict(l=50, r=20, t=30, b=80),
        height=420,
    )
    return fig


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stProgress > div > div > div { background: linear-gradient(90deg, #6C63FF, #43E8D8); }

    .hero { text-align: center; padding: 2rem 1rem 1rem; }
    .hero h1 {
        font-size: 2.6rem;
        background: linear-gradient(135deg, #6C63FF, #43E8D8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .hero p { color: #999; font-size: 1.05rem; }

    .sound-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 0.6rem;
    }
    .sound-card .group-badge {
        display: inline-block;
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }
    .sound-card .sound-name {
        font-size: 1rem;
        color: #e0e0e0;
        margin-bottom: 0.2rem;
    }

    .rating-label-row { display: flex; justify-content: space-between; padding: 0 4px; }
    .rating-label { color: #666; font-size: 0.75rem; }

    .report-header {
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 1.5rem 2rem;
        margin-bottom: 1.5rem;
        background: linear-gradient(135deg, rgba(108,99,255,0.08), rgba(67,232,216,0.05));
    }
    .report-header h2 {
        margin: 0 0 0.3rem;
        font-size: 1.8rem;
        background: linear-gradient(135deg, #6C63FF, #43E8D8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .report-meta { color: #999; font-size: 0.95rem; line-height: 1.8; }
    .report-meta strong { color: #ccc; }

    .score-row {
        display: flex; align-items: center; gap: 12px;
        padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.04);
    }
    .score-label { width: 160px; font-size: 0.9rem; font-weight: 600; text-align: right; }
    .score-bar-bg {
        flex: 1; height: 28px; border-radius: 8px;
        background: rgba(255,255,255,0.05); position: relative; overflow: hidden;
    }
    .score-bar-fill {
        height: 100%; border-radius: 8px;
        display: flex; align-items: center; justify-content: flex-end;
        padding-right: 10px; font-size: 0.8rem; font-weight: 700; color: #fff;
        min-width: 36px; transition: width 0.6s ease;
    }
    .score-value { width: 50px; text-align: left; font-size: 1rem; font-weight: 700; }

    .summary-box {
        background: rgba(255,255,255,0.03);
        border-left: 4px solid #6C63FF;
        border-radius: 0 12px 12px 0;
        padding: 1.2rem 1.5rem;
        margin: 1rem 0;
        color: #ccc;
        font-size: 0.95rem;
        line-height: 1.7;
    }
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

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### How it works")
        st.markdown(
            "1. Enter your name to create a profile\n"
            "2. Listen to short sounds from 9 categories\n"
            "3. Rate each on a 0-10 distress scale\n"
            "4. Get a **spider graph** of your sensitivity profile\n"
            "5. Retake weekly to track progress during training"
        )
    with col2:
        st.markdown("#### Sound categories")
        for cat, color in CAT_COLORS.items():
            st.markdown(f'<span style="color:{color}">&#9679;</span> {cat}',
                        unsafe_allow_html=True)

    st.divider()

    username = st.text_input("Enter your name to begin", placeholder="e.g. Alex", key="home_user")
    if username:
        st.session_state["username"] = username.strip().lower().replace(" ", "_")
        path = DATA_DIR / f"{st.session_state['username']}.json"
        if path.exists():
            history = json.loads(path.read_text())
            st.success(f"Welcome back! You have **{len(history)}** previous session(s).")
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Start new test", type="primary", use_container_width=True):
                st.session_state["page"] = "test"
                st.session_state["test_items"] = None
                st.session_state["current_idx"] = 0
                st.session_state["collected_ratings"] = {}
                st.rerun()
        with col_b:
            if st.button("View my history", use_container_width=True):
                st.session_state["page"] = "history"
                st.rerun()

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

    st.markdown(f"### Sound {idx + 1} of {total}")
    st.progress((idx) / total)

    if idx < total:
        item = items[idx]
        group = item["group"]
        name = item["name"]
        filepath = item["path"]
        badge_color = CAT_COLORS.get(group, "#6C63FF")

        st.markdown(f"""
        <div class="sound-card">
            <div class="group-badge" style="background:{_hex_to_rgba(badge_color,0.2)};color:{badge_color};">{group}</div>
            <div class="sound-name">{name}</div>
        </div>
        """, unsafe_allow_html=True)

        # Autoplay audio
        st.markdown(autoplay_audio_html(filepath), unsafe_allow_html=True)

        # Rating buttons row
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
                if st.button(str(val), key=f"rbtn_{idx}_{val}", type=btn_type,
                             use_container_width=True):
                    st.session_state[f"btn_rating_{idx}"] = val
                    st.rerun()

        st.markdown("")

        col_prev, col_skip, col_next = st.columns([1, 1, 1])
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
    date_str = ts[:10]
    time_str = ts[11:16]
    session_num = len(history)
    overall_avg = sum(averages.values()) / len(averages) if averages else 0

    # --- Report header ---
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

    # --- Sensitivity summary ---
    summary = generate_sensitivity_summary(averages)
    st.markdown("#### Your Sensitivity Summary")
    st.markdown(f'<div class="summary-box">{summary}</div>', unsafe_allow_html=True)

    # --- Spider chart ---
    st.markdown("#### Sensitivity Profile")
    fig = make_radar(averages, title="Current session")
    st.plotly_chart(fig, use_container_width=True)

    # --- Colored score bars ---
    st.markdown("#### Category Breakdown")
    sorted_cats = sorted(averages.items(), key=lambda x: x[1], reverse=True)

    bars_html = ""
    for cat, score in sorted_cats:
        color = CAT_COLORS.get(cat, "#888")
        pct = max(score / 10 * 100, 5)
        bars_html += f"""
        <div class="score-row">
            <div class="score-label" style="color:{color};">{cat}</div>
            <div class="score-bar-bg">
                <div class="score-bar-fill" style="width:{pct}%;background:linear-gradient(90deg,{_hex_to_rgba(color,0.7)},{color});">
                </div>
            </div>
            <div class="score-value" style="color:{color};">{score:.1f}</div>
        </div>
        """
    st.markdown(bars_html, unsafe_allow_html=True)

    # --- Overall average over time ---
    if len(history) >= 2:
        st.divider()
        st.markdown("#### Overall Distress Over Time")
        avg_fig = make_overall_avg_chart(history)
        if avg_fig:
            st.plotly_chart(avg_fig, use_container_width=True)

    # --- Comparison ---
    if len(history) >= 2:
        st.markdown("#### Progress: First vs. Latest")
        comp_fig = make_comparison_radar(history)
        if comp_fig:
            st.plotly_chart(comp_fig, use_container_width=True)

        first_avgs = history[0]["averages"]
        st.markdown("#### Change by Category")
        delta_html = ""
        for cat in averages:
            curr = averages.get(cat, 0)
            prev = first_avgs.get(cat, 0)
            diff = curr - prev
            color = CAT_COLORS.get(cat, "#888")
            arrow = "&#9650;" if diff > 0 else "&#9660;" if diff < 0 else "&#9679;"
            diff_color = "#FF6584" if diff > 0 else "#6BCB77" if diff < 0 else "#888"
            delta_html += f"""
            <div style="display:flex;align-items:center;gap:10px;padding:6px 0;
                        border-bottom:1px solid rgba(255,255,255,0.04);">
                <span style="width:160px;text-align:right;color:{color};font-weight:600;font-size:0.9rem;">{cat}</span>
                <span style="width:60px;color:#aaa;">{prev:.1f}</span>
                <span style="color:{diff_color};font-size:1.1rem;">{arrow}</span>
                <span style="width:60px;font-weight:700;color:#ddd;">{curr:.1f}</span>
                <span style="color:{diff_color};font-weight:600;">({diff:+.1f})</span>
            </div>
            """
        st.markdown(delta_html, unsafe_allow_html=True)

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Take another test", type="primary", use_container_width=True):
            st.session_state["page"] = "test"
            st.session_state["test_items"] = None
            st.rerun()
    with col2:
        if st.button("View full history", use_container_width=True):
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
            <strong>Sessions completed:</strong> {len(history)} &nbsp;&middot;&nbsp;
            <strong>First test:</strong> {history[0]['timestamp'][:10]} &nbsp;&middot;&nbsp;
            <strong>Latest:</strong> {history[-1]['timestamp'][:10]}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- Latest sensitivity summary ---
    latest_avgs = history[-1]["averages"]
    summary = generate_sensitivity_summary(latest_avgs)
    st.markdown("#### Current Sensitivity Summary")
    st.markdown(f'<div class="summary-box">{summary}</div>', unsafe_allow_html=True)

    # --- Overall average over time ---
    st.markdown("#### Overall Distress Over Time")
    avg_fig = make_overall_avg_chart(history)
    if avg_fig:
        st.plotly_chart(avg_fig, use_container_width=True)

    # --- Per-category trend chart ---
    trend = trend_chart(history)
    if trend:
        st.markdown("#### Category Sensitivity Over Time")
        st.plotly_chart(trend, use_container_width=True)

    # Comparison radar
    comp = make_comparison_radar(history)
    if comp:
        st.markdown("#### First vs. Latest Session")
        st.plotly_chart(comp, use_container_width=True)

    # Overall change
    if len(history) >= 2:
        first_avg = sum(history[0]["averages"].values()) / len(history[0]["averages"])
        latest_avg = sum(history[-1]["averages"].values()) / len(history[-1]["averages"])
        delta = latest_avg - first_avg
        st.markdown("#### Overall Change")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("First session avg", f"{first_avg:.1f}")
        with col2:
            st.metric("Latest session avg", f"{latest_avg:.1f}", delta=f"{delta:+.1f}", delta_color="inverse")
        with col3:
            st.metric("Sessions completed", len(history))

    st.divider()
    st.markdown("#### Session Details")
    for i, sess in enumerate(reversed(history)):
        sess_num = len(history) - i
        sess_avg = sum(sess["averages"].values()) / len(sess["averages"]) if sess["averages"] else 0
        with st.expander(f"Session {sess_num} -- {sess['timestamp'][:10]}  (avg: {sess_avg:.1f})"):
            fig = make_radar(sess["averages"])
            st.plotly_chart(fig, use_container_width=True)

            # Score bars for this session
            bars_html = ""
            for cat, score in sorted(sess["averages"].items(), key=lambda x: x[1], reverse=True):
                color = CAT_COLORS.get(cat, "#888")
                pct = max(score / 10 * 100, 5)
                bars_html += f"""
                <div class="score-row">
                    <div class="score-label" style="color:{color};">{cat}</div>
                    <div class="score-bar-bg">
                        <div class="score-bar-fill" style="width:{pct}%;background:linear-gradient(90deg,{_hex_to_rgba(color,0.7)},{color});">
                        </div>
                    </div>
                    <div class="score-value" style="color:{color};">{score:.1f}</div>
                </div>
                """
            st.markdown(bars_html, unsafe_allow_html=True)

            # Text summary for this session
            sess_summary = generate_sensitivity_summary(sess["averages"])
            st.markdown(f'<div class="summary-box">{sess_summary}</div>', unsafe_allow_html=True)

    st.divider()
    if st.button("Back to home", use_container_width=True):
        st.session_state["page"] = "home"
        st.rerun()

    st.markdown(ATTRIBUTION_HTML, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(
        page_title="MisoRater",
        page_icon="🕸️",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    inject_css()

    if "page" not in st.session_state:
        st.session_state["page"] = "home"

    with st.sidebar:
        st.markdown("### MisoRater")
        if st.button("Home", use_container_width=True):
            st.session_state["page"] = "home"
            st.rerun()
        if st.button("Take test", use_container_width=True):
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

        st.divider()
        st.markdown(f"**Sounds per category:** {SOUNDS_PER_CATEGORY}")
        new_n = st.slider("Adjust", 1, 8, SOUNDS_PER_CATEGORY, key="n_slider")
        if new_n != SOUNDS_PER_CATEGORY:
            st.session_state["sounds_per_cat"] = new_n

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
