"""Static guard for the background-concepts deck (PRES-002 sections 9.2 and 9.3). No browser needed.
Env: DECK_HTML=path (default: docs/presentation/background-deck/background-concepts.html)
     DECK_SCENES=20 if the section 6 fallback was used; DECK_STARTER=1 while the logos are still placeholders."""
import os, re, shutil, subprocess, tempfile, warnings
from pathlib import Path
import pytest

HTML_PATH = Path(os.environ.get("DECK_HTML") or Path(__file__).resolve().parents[1] / "docs/presentation/background-deck/background-concepts.html")
EXPECTED_SCENES = int(os.environ.get("DECK_SCENES", "24"))
STARTER = os.environ.get("DECK_STARTER") == "1"
PAYLOAD = re.compile(r"data:image/png;base64,[A-Za-z0-9+/=]+")
TERMS = ["Empirical", "Complexity", "Analysis", "Narrowing", "Strategy", "Incremental", "LLM (Large Language Model)", "Graph construction", "Node", "Edge", "Graph", "Directed edge", "Prerequisite", "Knowledge graph", "Concept", "Domain expert", "Scale", "Prompt", "API call", "API", "Wall-clock time", "Database", "Batch construction", "Incremental insertion", "Insertion", "n", "Brute force", "Linear growth", "Control", "Shortlist", "Candidate", "Candidate narrowing", "Embedding", "Vector", "Local model", "Cosine similarity", "Threshold", "θ (theta)", "Top-k", "Cap", "Nearest neighbour", "ANN (approximate nearest-neighbour search)", "HNSW (Hierarchical Navigable Small World)", "efSearch", "efConstruction", "Greedy", "FAISS", "Bucket", "Random hyperplane", "Bit", "Binary code", "Gray order", "Bounded", "EraRAG", "Seed", "Decision step", "Label", "Temperature 0", "Fair test", "Worst case", "Gold-standard graph", "Ground truth", "DSA (Data Structures and Algorithms)", "Metacademy", "Leave-one-out", "Synthetic data", "Precision", "Recall", "F1", "Harmonic mean", "Micro", "Macro", "Shortlist recall", "Neighbour", "Random baseline", "Trial", "Mean", "Bootstrap", "With replacement", "Resample", "Percentile", "95% bootstrap interval", "Research gap", "Aggregate", "Head-to-head", "Like-for-like", "Literature search", "Research question (RQ)", "Amortized cost", "Theorem", "Premise", "Conceptual framework", "Input / Process / Output"]

raw = HTML_PATH.read_text(encoding="utf-8")
scan = PAYLOAD.sub("data:image/png;base64,PAYLOAD", raw)            # V3: never scan the logo bytes
script_m = re.search(r"<script>(.*?)</script>", scan, re.S)
script = script_m.group(1) if script_m else ""
markup = re.sub(r"<(script|style)\b.*?</\1>", "", scan, flags=re.S)  # markup only: JS legitimately contains [0]
text = re.sub(r"<[^>]+>", " ", markup)

def num(s):  # a number that is not part of a longer number
    return r"(?<![\d.,])" + s + r"(?![\d])"

CASE_SENSITIVE = {r"\b(V3|V4|G1|G2|G3|Flash)\b": "model or gate token (whole word, case-sensitive)"}
CASE_INSENSITIVE = {
    "deepseek": "model identity", "topsis": "Chapter 4", "kendall": "Chapter 4", "pareto": "Chapter 4", "dominat": "Chapter 4",
    num(r"1,713"): "Chapter 4 time", num("1713"): "Chapter 4 time", num(r"8\.28"): "Chapter 4", num(r"0\.586"): "Chapter 4", num(r"0\.294"): "Chapter 4",
    r"0\.8\s*[\u2013-]\s*0\.9\s*s": "per-call duration",
    num(r"0\.541"): "pilot", num(r"0\.611"): "pilot", num(r"0\.485"): "pilot", num(r"15\.38"): "pilot", num(r"85\.71"): "calibration",
    num(r"0\.841"): "calibration", num(r"0\.968"): "calibration", num(r"0\.999"): "calibration",
    r"22 to 50": "Funk et al.", r"22\s*[\u2013-]\s*50": "Funk et al.", r"\$0\.11": "Funk et al.", num(r"12\.45"): "Funk et al.",
    "nobody has ever": "banned phrase", r"we prove": "banned phrase", r"strategy [a-d]\b": "use S1-S4 only",
    r"@import": "network", r"<link": "network", r"<script[^>]*\ssrc": "network", r"url\(\s*['\"]?http": "network",
    r"fetch\(": "network", "XMLHttpRequest": "network",
}

def test_forbidden_content_absent():
    hits = []
    for pat, why in CASE_SENSITIVE.items():
        hits += [(m.group(0), why) for m in re.finditer(pat, scan)]
    for pat, why in CASE_INSENSITIVE.items():
        hits += [(m.group(0), why) for m in re.finditer(pat, scan, re.I)]
    hits += [(m.group(0), "network") for m in re.finditer(r"https?://", scan.replace('xmlns="http://www.w3.org/2000/svg"', ""))]
    hits += [(m.group(0), "reference marker (markup only)") for m in re.finditer(r"\[\d+\]", markup)]
    assert not hits, hits[:10]

def test_scene_count_and_metadata():
    scenes = re.findall(r'<section class="scene[^"]*"[^>]*>', scan)
    assert len(scenes) == EXPECTED_SCENES, f"{len(scenes)} scenes, expected {EXPECTED_SCENES}"
    for i, s in enumerate(scenes, 1):
        for a in ("data-title", "data-teaches"):
            m = re.search(a + r'="([^"]+)"', s); assert m and m.group(1).strip(), f"scene {i} lacks {a}"

def test_size_and_logos():
    assert len(raw.encode("utf-8")) < 1_500_000
    uris = re.findall(r"data:[^\s\"')]+", scan)
    others = [u for u in uris if not u.startswith("data:image/png;base64,")]
    assert not others, others
    placeholders = scan.count("__LOGO_LOCKUP__") + scan.count("__LOGO_50__")
    assert len(uris) + placeholders == 2
    if not STARTER: assert placeholders == 0, "logos not inlined (set DECK_STARTER=1 only for the starter kit)"

def test_required_phrases():
    low = re.sub(r"\s+", " ", text.lower().replace("&mdash;", "\u2014").replace("&rsquo;", "\u2019"))
    for p in ("none of the studies we reviewed", "strictly above", "premise", "illustration", "made-up numbers",
              "s3 and s4 both cap at 10", "not thesis data", "95% bootstrap interval", "with replacement",
              "2.5th", "97.5th", "fixed seed", "efsearch = 128", "efconstruction"):
        assert p in low or p in scan.lower(), f"missing phrase: {p}"

def test_tags_on_every_scene_that_needs_them():                         # V4
    secs = {int(m.group(1)): m.group(0) for m in re.finditer(r'<section class="scene[^"]*" id="s(\d\d)".*?</section>', scan, re.S)}
    miss = []
    for n in list(range(4, 15)) + [16]:
        s = secs.get(n, "")
        if ("data-ex=" in s and '"tag"' in s) or "not thesis data" in s: continue
        if n in (4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16) and "illustration" not in s: miss.append(("illustration", n))
    for n in (7, 9, 10, 11, 17, 19, 20):
        if "made-up numbers" not in secs.get(n, ""): miss.append(("made-up numbers", n))
    assert not miss, miss

def test_every_gloss_bank_term_is_a_chip():
    chips = {m.group(1).replace("&amp;", "&") for m in re.finditer(r'data-term="([^"]+)"', scan)}
    missing = [t for t in TERMS if t not in chips]
    assert not missing, f"{len(missing)} of {len(TERMS)} terms missing, e.g. {missing[:6]}"

def test_gloss_length_limit():
    long = [(m.group(1), len(m.group(2).split())) for m in re.finditer(r'data-term="([^"]+)"[^>]*data-gloss="([^"]+)"', scan) if len(m.group(2).split()) > 16]
    assert not long, long

def test_no_shell_markers_left():
    assert "data-steps=" not in scan and 'class="todo"' not in scan, "scene shells remain (data-steps / class=todo)"

def test_term_before_chip_lint():                                        # lint list, never a failure
    start = (re.search(r'id="s03"', markup) or re.search(r"<main", markup)).start()
    flagged = []
    for m in re.finditer(r'<span class="term"[^>]*data-term="([^"]+)"[^>]*>(.*?)</span>', markup, re.S):
        label = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if m.start() < start or len(label) < 4: continue
        pre = re.sub(r"<[^>]+>", " ", markup[start:m.start()])
        if re.search(r"\b" + re.escape(label) + r"\b", pre, re.I): flagged.append(label)
    if flagged: warnings.warn("term appears before its chip (resolve or justify in the report): " + ", ".join(sorted(set(flagged))))

def test_script_parses_with_node():
    node = shutil.which("node")
    if not node: pytest.skip("node not installed")
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f: f.write(script)
    r = subprocess.run([node, "--check", f.name], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
