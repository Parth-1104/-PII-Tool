import streamlit as st
import os
from pathlib import Path
from src.pipeline.redactor_pipeline import RedactionPipeline

st.set_page_config(page_title="Redaction Console", page_icon="◈", layout="centered")

# ──────────────────────────────────────────────────────────────────────────
# DESIGN SYSTEM
# Palette:  ink #0A0D12 · panel #12161E · line #232A36 · text #E7ECF3
#           mute #7C8797 · signal (cyan) #00E5C7 · redact (amber) #FFB020
# Type:     Space Grotesk (display) · Inter (body) · JetBrains Mono (data/log)
# Signature: the hero title "declassifies" itself on load — a black
# redaction bar wipes off each word, tying the motion directly to what
# the tool does to a document.
# ──────────────────────────────────────────────────────────────────────────

st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
:root{
  --ink:#0A0D12; --panel:#12161E; --panel-2:#161B25; --line:#232A36;
  --text:#E7ECF3; --mute:#7C8797; --signal:#00E5C7; --signal-dim:#0A8F7F;
  --redact:#FFB020; --danger:#FF5C5C;
}

html, body, .stApp{
  background:
    radial-gradient(1200px 500px at 15% -10%, rgba(0,229,199,0.07), transparent 60%),
    radial-gradient(900px 500px at 100% 0%, rgba(255,176,32,0.05), transparent 55%),
    var(--ink) !important;
  color:var(--text);
  font-family:'Inter',sans-serif;
}
[data-testid="stHeader"]{background:transparent;}
.block-container{padding-top:2.6rem; max-width:760px;}
::selection{background:rgba(0,229,199,0.25); color:#fff;}

/* ---------- App window chrome ---------- */
.console-bar{
  display:flex; align-items:center; gap:8px;
  padding:10px 16px; background:var(--panel);
  border:1px solid var(--line); border-bottom:none;
  border-radius:14px 14px 0 0;
}
.console-dot{width:10px; height:10px; border-radius:50%;}
.console-bar .d1{background:#FF5C5C;} .console-bar .d2{background:#FFB020;} .console-bar .d3{background:#00E5C7;}
.console-path{
  margin-left:12px; font-family:'JetBrains Mono',monospace; font-size:12px;
  color:var(--mute); letter-spacing:0.02em;
}

/* ---------- Hero ---------- */
.hero{
  background:var(--panel); border:1px solid var(--line); border-top:none;
  border-radius:0 0 14px 14px; padding:38px 34px 30px; margin-bottom:26px;
}
.eyebrow{
  font-family:'JetBrains Mono',monospace; font-size:12px; letter-spacing:0.18em;
  color:var(--signal); text-transform:uppercase; display:flex; align-items:center; gap:8px;
}
.eyebrow::before{content:"●"; font-size:8px; animation:pulse 1.8s ease-in-out infinite;}
@keyframes pulse{0%,100%{opacity:1;} 50%{opacity:0.25;}}

.hero h1{
  font-family:'Space Grotesk',sans-serif; font-weight:700;
  font-size:2.5rem; line-height:1.08; letter-spacing:-0.01em;
  margin:14px 0 12px; color:var(--text);
}
.redact-word{
  position:relative; display:inline-block; color:var(--signal);
  animation:reveal-text 0.1s linear 1.1s forwards;
  opacity:0;
}
.redact-word::after{
  content:""; position:absolute; inset:-2px -6px;
  background:#0A0A0A; border-radius:3px;
  animation:wipe-bar 1.1s cubic-bezier(.77,0,.18,1) forwards;
  transform-origin:right;
}
@keyframes reveal-text{ to{ opacity:1; } }
@keyframes wipe-bar{ 0%{transform:scaleX(1);} 70%{transform:scaleX(1);} 100%{transform:scaleX(0);} }

.hero p.sub{ color:var(--mute); font-size:15px; line-height:1.6; max-width:52ch; margin:0; }

/* ---------- Cards / sections ---------- */
.panel{
  background:var(--panel); border:1px solid var(--line); border-radius:14px;
  padding:22px 24px; margin-bottom:20px;
}
.panel h3{
  font-family:'Space Grotesk',sans-serif; font-size:14px; letter-spacing:0.06em;
  text-transform:uppercase; color:var(--mute); margin:0 0 14px; font-weight:600;
}

/* ---------- File uploader ---------- */
[data-testid="stFileUploader"]{
  background:var(--panel-2); border:1.5px dashed #2C3646; border-radius:12px;
  padding:6px; transition:border-color .2s ease;
}
[data-testid="stFileUploader"]:hover{ border-color:var(--signal); }
[data-testid="stFileUploaderDropzoneInstructions"] span{ color:var(--text) !important; }
[data-testid="stFileUploaderDropzoneInstructions"] small{ color:var(--mute) !important; }
[data-testid="stFileUploader"] button{
  background:transparent !important; border:1px solid var(--line) !important;
  color:var(--text) !important; border-radius:8px !important;
}

/* ---------- Buttons ---------- */
.stButton>button, [data-testid="stDownloadButton"]>button{
  font-family:'Space Grotesk',sans-serif; font-weight:600; letter-spacing:0.01em;
  background:linear-gradient(135deg, var(--signal), var(--signal-dim));
  color:#03110E; border:none; border-radius:10px; padding:0.7rem 1.4rem;
  box-shadow:0 0 0 1px rgba(0,229,199,0.25), 0 8px 24px -8px rgba(0,229,199,0.45);
  transition:transform .15s ease, box-shadow .15s ease;
  width:100%;
}
.stButton>button:hover, [data-testid="stDownloadButton"]>button:hover{
  transform:translateY(-1px);
  box-shadow:0 0 0 1px rgba(0,229,199,0.4), 0 10px 30px -6px rgba(0,229,199,0.6);
  color:#03110E;
}
.stButton>button:active{ transform:translateY(0); }

/* ---------- Status line (upload confirmation) ---------- */
.log-line{
  font-family:'JetBrains Mono',monospace; font-size:13px; color:var(--signal);
  background:rgba(0,229,199,0.06); border:1px solid rgba(0,229,199,0.25);
  border-radius:8px; padding:10px 14px; margin:14px 0 4px;
  display:flex; align-items:center; gap:10px;
}
.log-line .cursor{
  width:7px; height:14px; background:var(--signal);
  animation:blink 1s step-end infinite;
}
@keyframes blink{ 50%{ opacity:0; } }

/* ---------- Scanning progress ---------- */
.scan-wrap{
  height:6px; width:100%; background:#1A2029; border-radius:6px; overflow:hidden;
  position:relative; margin:16px 0 6px;
}
.scan-bar{
  position:absolute; top:0; bottom:0; width:35%;
  background:linear-gradient(90deg, transparent, var(--signal), transparent);
  animation:scan-move 1.2s ease-in-out infinite;
}
@keyframes scan-move{
  0%{ left:-35%; } 100%{ left:100%; }
}
.scan-label{
  font-family:'JetBrains Mono',monospace; font-size:12px; color:var(--mute);
  letter-spacing:0.04em;
}

/* ---------- Stat cards ---------- */
.stat-grid{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:6px; }
.stat-card{
  background:var(--panel-2); border:1px solid var(--line); border-radius:12px;
  padding:16px 14px; text-align:left; position:relative; overflow:hidden;
}
.stat-card::before{
  content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--signal);
}
.stat-num{
  font-family:'Space Grotesk',sans-serif; font-size:1.9rem; font-weight:700; color:var(--text);
  line-height:1;
}
.stat-label{
  font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--mute);
  text-transform:uppercase; letter-spacing:0.06em; margin-top:6px;
}

/* ---------- Breakdown rows ---------- */
[data-testid="stExpander"]{
  background:var(--panel-2); border:1px solid var(--line); border-radius:10px;
}
.pii-row{
  font-family:'JetBrains Mono',monospace; font-size:13px; color:var(--text);
  display:flex; align-items:center; gap:10px; padding:6px 0;
  border-bottom:1px dashed #202836;
}
.pii-row:last-child{ border-bottom:none; }
.pii-dot{ width:7px; height:7px; border-radius:50%; background:var(--signal); flex-shrink:0; }
.pii-count{ margin-left:auto; color:var(--mute); }

/* ---------- Misc Streamlit overrides ---------- */
[data-testid="stMarkdownContainer"] p{ color:var(--text); }
hr{ border-color:var(--line) !important; }
[data-testid="stAlertContentSuccess"], [data-testid="stAlertContentError"]{
  font-family:'JetBrains Mono',monospace; font-size:13px; border-radius:10px;
}
footer, #MainMenu{ visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────
# HERO
# ──────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="console-bar">
  <div class="console-dot d1"></div><div class="console-dot d2"></div><div class="console-dot d3"></div>
  <div class="console-path">~/secure/redaction-console</div>
</div>
<div class="hero">
  <div class="eyebrow">Local document sanitation</div>
  <h1>PII Redaction <span class="redact-word">Console</span></h1>
  <p class="sub">Drop in a Word document and every name, email, company, and
  address is swapped for realistic synthetic data — text and embedded media alike.
  Nothing leaves this session.</p>
</div>
""", unsafe_allow_html=True)

# Initialize the pipeline in cache so it doesn't reload the AI models on every click
@st.cache_resource
def load_pipeline():
    return RedactionPipeline(
        config_path=None,
        score_threshold=0.65,
        enable_persistence=True,
        persistence_path="./web_entity_vault.json"
    )

try:
    pipeline = load_pipeline()
except Exception as e:
    st.error(f"Failed to initialize the NLP pipeline: {e}")
    st.stop()

# ──────────────────────────────────────────────────────────────────────────
# UPLOAD
# ──────────────────────────────────────────────────────────────────────────
st.markdown('<div class="panel"><h3>01 · Intake</h3>', unsafe_allow_html=True)
uploaded_file = st.file_uploader("Choose a Microsoft Word Document (.docx)", type=["docx"], label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

if uploaded_file is not None:
    # Save the uploaded file temporarily to disk
    temp_input_path = Path(f"temp_input_{uploaded_file.name}")
    temp_output_path = Path(f"redacted_{uploaded_file.name}")

    with open(temp_input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.markdown(f"""
    <div class="log-line"><span class="cursor"></span> {uploaded_file.name} staged for processing</div>
    """, unsafe_allow_html=True)

    # Trigger Redaction Process
    st.markdown('<div class="panel" style="margin-top:18px;"><h3>02 · Run</h3>', unsafe_allow_html=True)
    run_clicked = st.button("🚀 Run PII Redaction")
    st.markdown('</div>', unsafe_allow_html=True)

    if run_clicked:
        status_area = st.empty()
        status_area.markdown("""
        <div class="scan-label">scanning paragraphs · masking text · replacing media…</div>
        <div class="scan-wrap"><div class="scan-bar"></div></div>
        """, unsafe_allow_html=True)

        # Upper Edge Feature Setup: Define path to the custom visual compliance badge
        custom_badge_path = Path("redacted_placeholder.png")

        # Runtime fallback check: Generate a robust 1x1 light-gray PNG stream if the image isn't pushed yet
        if not custom_badge_path.exists():
            fallback_png_bytes = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x01\x00\x00\x00\x1c\xf3\xffa\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
            custom_badge_path.write_bytes(fallback_png_bytes)

        try:
            # Run the pipeline passing down the custom compliance image target
            # (Note: Ensure your pipeline's underlying redact_document updates pass this to processor.process_and_redact)
            summary = pipeline.redact_document(
                input_path=temp_input_path,
                output_path=temp_output_path,
                create_backup=False,
                placeholder_image_path=custom_badge_path
            )

            status_area.empty()
            st.success("Redaction complete — text and media layers sanitized.")

            # Display Summary Metrics Box
            st.markdown('<div class="panel"><h3>03 · Audit Report</h3>', unsafe_allow_html=True)

            paragraphs = summary.get("paragraphs_processed", 0)
            replacements = summary.get("total_replacements", 0)
            visual_swaps = summary.get("images_redacted", 0)

            st.markdown(f"""
            <div class="stat-grid">
              <div class="stat-card"><div class="stat-num">{paragraphs}</div><div class="stat-label">Paragraphs scanned</div></div>
              <div class="stat-card"><div class="stat-num">{replacements}</div><div class="stat-label">Text replacements</div></div>
              <div class="stat-card"><div class="stat-num">{visual_swaps}</div><div class="stat-label">Visual assets swapped</div></div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # Expandable detailed metrics
            if "entity_counts" in summary and summary["entity_counts"]:
                with st.expander("View breakdown by PII type"):
                    rows = ""
                    for pii_type, count in summary["entity_counts"].items():
                        rows += f'<div class="pii-row"><span class="pii-dot"></span>{pii_type}<span class="pii-count">{count}</span></div>'
                    if visual_swaps > 0:
                        rows += f'<div class="pii-row"><span class="pii-dot" style="background:var(--redact);"></span>VISUAL_COMPLIANCE_MEDIA<span class="pii-count">{visual_swaps}</span></div>'
                    st.markdown(rows, unsafe_allow_html=True)

            # Read the file back into memory for the download button
            st.markdown('<div class="panel"><h3>04 · Export</h3>', unsafe_allow_html=True)
            with open(temp_output_path, "rb") as file_bytes:
                st.download_button(
                    label="📥 Download Redacted Document",
                    data=file_bytes,
                    file_name=f"Redacted_{uploaded_file.name}",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            st.markdown('</div>', unsafe_allow_html=True)

        except Exception as err:
            status_area.empty()
            st.error(f"An error occurred during processing: {err}")
        finally:
            # Clean up temporary disk files safely to prevent memory bloat on server nodes
            if temp_input_path.exists():
                os.remove(temp_input_path)
            if temp_output_path.exists():
                try:
                    os.remove(temp_output_path)
                except:
                    pass