#!/usr/bin/env python3
"""
Geister Medizintechnik - Custom Catalog Web UI
================================================
A local web application for generating customized product catalogs.

Usage:
    python3 webapp.py

Then open http://localhost:5000 in your browser.

Requirements:
    pip install flask pypdf pdfplumber reportlab
"""

import os
import sys
import json
import re
import time
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify, send_file

# Import the catalog generator
from geister_custom_catalog import (
    generate_catalog, build_article_index, discover_catalog_files,
    ART_PATTERN, SCRIPT_DIR
)

app = Flask(__name__)

# ============================================================
# INDEX MANAGEMENT
# ============================================================
INDEX_CACHE_FILE = os.path.join(SCRIPT_DIR, "article_index_cache.json")
ARTICLE_INDEX = {}
CATALOG_LIST = []


def load_or_build_index():
    """Load cached index or build from scratch."""
    global ARTICLE_INDEX, CATALOG_LIST

    CATALOG_LIST = discover_catalog_files()

    if os.path.exists(INDEX_CACHE_FILE):
        print("  Loading cached article index...")
        with open(INDEX_CACHE_FILE, "r") as f:
            raw = json.load(f)
        ARTICLE_INDEX = {}
        skipped = 0
        available_pdfs = set()
        for art, locs in raw.items():
            resolved = []
            for l in locs:
                fname = l["file"]
                # Resolve relative filenames to full paths
                if not os.path.isabs(fname):
                    fname = os.path.join(SCRIPT_DIR, fname)
                # Only include if the PDF file actually exists
                if os.path.exists(fname):
                    resolved.append((fname, l["page"]))
                    available_pdfs.add(os.path.basename(fname))
                else:
                    skipped += 1
            if resolved:
                ARTICLE_INDEX[art] = resolved
        print(f"  Loaded {len(ARTICLE_INDEX)} articles from {len(available_pdfs)} available catalogs.")
        if skipped > 0:
            print(f"  [Info] Skipped {skipped} references to missing PDF files.")
    else:
        print("  Building article index (first run, may take a few minutes)...")
        idx, _ = build_article_index(CATALOG_LIST)
        ARTICLE_INDEX = {}
        for art, locs in idx.items():
            ARTICLE_INDEX[art] = [(l[0], l[1]) for l in locs]
        # Cache it
        cache = {}
        for art, locs in ARTICLE_INDEX.items():
            cache[art] = [{"file": l[0], "page": l[1]} for l in locs]
        with open(INDEX_CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
        print(f"  Indexed {len(ARTICLE_INDEX)} articles. Cached for next start.")


# ============================================================
# HTML TEMPLATE
# ============================================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Geister - Custom Catalog Generator</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background: #f5f5f5;
            color: #1a1a1a;
            min-height: 100vh;
        }

        /* Header */
        .header {
            background: white;
            border-bottom: 3px solid #B5121B;
            padding: 16px 32px;
            display: flex;
            align-items: center;
            gap: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }

        .logo-box {
            background: #B5121B;
            color: white;
            width: 44px;
            height: 44px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Times New Roman', serif;
            font-size: 28px;
            font-style: italic;
            font-weight: bold;
            flex-shrink: 0;
        }

        .header-text h1 {
            font-size: 14px;
            font-weight: 400;
            letter-spacing: 4px;
            color: #B5121B;
        }

        .header-text p {
            font-size: 11px;
            color: #888;
            margin-top: 2px;
        }

        .header-right {
            margin-left: auto;
            text-align: right;
            font-size: 12px;
            color: #888;
        }

        .header-right strong {
            color: #B5121B;
            font-size: 18px;
        }

        /* Main Layout */
        .main {
            max-width: 1200px;
            margin: 24px auto;
            padding: 0 24px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
        }

        .full-width {
            grid-column: 1 / -1;
        }

        /* Cards */
        .card {
            background: white;
            border-radius: 8px;
            padding: 24px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.08);
        }

        .card h2 {
            font-size: 14px;
            font-weight: 600;
            color: #B5121B;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 16px;
            padding-bottom: 8px;
            border-bottom: 1px solid #eee;
        }

        /* Form elements */
        label {
            display: block;
            font-size: 12px;
            font-weight: 600;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 4px;
        }

        input[type="text"] {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            margin-bottom: 12px;
            transition: border-color 0.2s;
        }

        input[type="text"]:focus {
            outline: none;
            border-color: #B5121B;
            box-shadow: 0 0 0 2px rgba(181,18,27,0.1);
        }

        /* Search box */
        .search-container {
            position: relative;
        }

        #articleSearch {
            padding-right: 40px;
        }

        .search-icon {
            position: absolute;
            right: 12px;
            top: 38px;
            color: #aaa;
            font-size: 16px;
        }

        /* Autocomplete dropdown */
        .autocomplete-list {
            position: absolute;
            z-index: 100;
            background: white;
            border: 1px solid #ddd;
            border-top: none;
            border-radius: 0 0 6px 6px;
            max-height: 280px;
            overflow-y: auto;
            width: 100%;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            display: none;
        }

        .autocomplete-item {
            padding: 8px 12px;
            cursor: pointer;
            font-size: 13px;
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid #f0f0f0;
        }

        .autocomplete-item:hover, .autocomplete-item.active {
            background: #fef2f2;
        }

        .autocomplete-item .art-no {
            font-weight: 700;
            color: #B5121B;
            font-family: monospace;
            font-size: 13px;
        }

        .autocomplete-item .art-source {
            color: #aaa;
            font-size: 11px;
        }

        /* Selected articles */
        .selected-list {
            min-height: 60px;
            max-height: 400px;
            overflow-y: auto;
        }

        .selected-item {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            margin-bottom: 4px;
            background: #fafafa;
            border-radius: 6px;
            border: 1px solid #eee;
            font-size: 13px;
            transition: all 0.15s;
        }

        .selected-item:hover {
            border-color: #B5121B;
            background: #fef2f2;
        }

        .selected-item .art-no {
            font-weight: 700;
            font-family: monospace;
            color: #B5121B;
            width: 130px;
            flex-shrink: 0;
        }

        .selected-item .art-catalog {
            color: #888;
            font-size: 11px;
            flex: 1;
        }

        .selected-item .remove-btn {
            background: none;
            border: none;
            color: #ccc;
            cursor: pointer;
            font-size: 18px;
            padding: 0 4px;
            transition: color 0.15s;
        }

        .selected-item .remove-btn:hover {
            color: #B5121B;
        }

        /* Counter */
        .counter {
            display: inline-block;
            background: #B5121B;
            color: white;
            font-size: 11px;
            font-weight: 700;
            padding: 2px 8px;
            border-radius: 10px;
            margin-left: 8px;
        }

        /* Buttons */
        .btn-primary {
            background: #B5121B;
            color: white;
            border: none;
            padding: 14px 32px;
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
            border-radius: 6px;
            cursor: pointer;
            width: 100%;
            transition: all 0.2s;
        }

        .btn-primary:hover {
            background: #8C0E15;
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(181,18,27,0.3);
        }

        .btn-primary:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }

        .btn-secondary {
            background: white;
            color: #B5121B;
            border: 1px solid #B5121B;
            padding: 8px 16px;
            font-size: 12px;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .btn-secondary:hover {
            background: #fef2f2;
        }

        /* Status / Progress */
        .status-bar {
            padding: 12px 16px;
            border-radius: 6px;
            font-size: 13px;
            margin-top: 12px;
            display: none;
        }

        .status-bar.info {
            background: #f0f7ff;
            color: #1a6dba;
            border: 1px solid #cce0f5;
            display: block;
        }

        .status-bar.success {
            background: #f0faf0;
            color: #1a7a1a;
            border: 1px solid #c0e8c0;
            display: block;
        }

        .status-bar.error {
            background: #fef2f2;
            color: #B5121B;
            border: 1px solid #f5c0c0;
            display: block;
        }

        .status-bar a {
            color: #B5121B;
            font-weight: 700;
        }

        /* Spinner */
        .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #cce0f5;
            border-top-color: #1a6dba;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            vertical-align: middle;
            margin-right: 8px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Stats */
        .stats {
            display: flex;
            gap: 24px;
            margin-top: 8px;
        }

        .stat {
            text-align: center;
        }

        .stat-num {
            font-size: 28px;
            font-weight: 700;
            color: #B5121B;
        }

        .stat-label {
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* Empty state */
        .empty-state {
            text-align: center;
            padding: 30px;
            color: #bbb;
            font-size: 13px;
        }

        .empty-state .icon {
            font-size: 32px;
            margin-bottom: 8px;
        }

        /* Action row */
        .action-row {
            display: flex;
            gap: 8px;
            margin-top: 12px;
        }

        /* Footer */
        .footer {
            text-align: center;
            padding: 24px;
            color: #aaa;
            font-size: 11px;
        }

        .footer a { color: #B5121B; text-decoration: none; }
    </style>
</head>
<body>

<!-- Header -->
<div class="header">
    <div class="logo-box">G</div>
    <div class="header-text">
        <h1>G E I S T E R</h1>
        <p>Custom Catalog Generator</p>
    </div>
    <div class="header-right">
        <strong>{{ article_count }}</strong> articles<br>
        <span>{{ catalog_count }} catalogs</span>
    </div>
</div>

<!-- Main Content -->
<div class="main">

    <!-- Left: Customer Info -->
    <div class="card">
        <h2>Customer Information</h2>
        <label for="customerName">Name</label>
        <input type="text" id="customerName" placeholder="e.g. Dr. Max Mustermann">

        <label for="customerCompany">Company</label>
        <input type="text" id="customerCompany" placeholder="e.g. Klinikum Stuttgart">
    </div>

    <!-- Right: Stats & Generate -->
    <div class="card">
        <h2>Generate PDF</h2>
        <div class="stats">
            <div class="stat">
                <div class="stat-num" id="selectedCount">0</div>
                <div class="stat-label">Articles selected</div>
            </div>
            <div class="stat">
                <div class="stat-num" id="pageEstimate">0</div>
                <div class="stat-label">Est. pages</div>
            </div>
        </div>
        <div style="margin-top: 20px;">
            <button class="btn-primary" id="generateBtn" onclick="generatePDF()" disabled>
                Generate Catalog PDF
            </button>
        </div>
        <div class="status-bar" id="statusBar"></div>
    </div>

    <!-- Full width: Article Search & Selection -->
    <div class="card full-width">
        <h2>Article Selection <span class="counter" id="selectionCounter" style="display:none">0</span></h2>

        <div class="search-container">
            <label for="articleSearch">Search articles (number or keyword)</label>
            <input type="text" id="articleSearch" placeholder="Type article number, e.g. 34-7286 or search keyword..."
                   autocomplete="off" oninput="onSearchInput()" onkeydown="onSearchKeydown(event)">
            <div class="autocomplete-list" id="autocompleteList"></div>
        </div>

        <div class="action-row">
            <button class="btn-secondary" onclick="clearSelection()">Clear All</button>
        </div>

        <div class="selected-list" id="selectedList">
            <div class="empty-state" id="emptyState">
                <div class="icon">&#128270;</div>
                Search and add articles above
            </div>
        </div>
    </div>

</div>

<div class="footer">
    Geister Medizintechnik GmbH &mdash;
    <a href="https://www.geister.com" target="_blank">www.geister.com</a>
    &mdash; The better way to operate&trade;
</div>

<script>
// All articles from server
const ALL_ARTICLES = {{ articles_json | safe }};
const selectedArticles = new Set();

function onSearchInput() {
    const query = document.getElementById('articleSearch').value.trim().toUpperCase();
    const list = document.getElementById('autocompleteList');

    if (query.length < 2) {
        list.style.display = 'none';
        return;
    }

    const matches = ALL_ARTICLES.filter(a =>
        a.art_no.toUpperCase().includes(query) ||
        a.catalog.toUpperCase().includes(query)
    ).slice(0, 30);

    if (matches.length === 0) {
        list.style.display = 'none';
        return;
    }

    list.innerHTML = matches.map((a, i) => `
        <div class="autocomplete-item ${selectedArticles.has(a.art_no) ? 'active' : ''}"
             onclick="addArticle('${a.art_no}')"
             data-index="${i}">
            <span class="art-no">${a.art_no}</span>
            <span class="art-source">${a.catalog_short} p.${a.pages}</span>
        </div>
    `).join('');

    list.style.display = 'block';
}

function onSearchKeydown(e) {
    if (e.key === 'Escape') {
        document.getElementById('autocompleteList').style.display = 'none';
    }
    if (e.key === 'Enter') {
        const query = document.getElementById('articleSearch').value.trim();
        // Try exact match first
        const exact = ALL_ARTICLES.find(a => a.art_no.toUpperCase() === query.toUpperCase());
        if (exact) {
            addArticle(exact.art_no);
            document.getElementById('articleSearch').value = '';
            document.getElementById('autocompleteList').style.display = 'none';
        } else {
            // Add first match
            const first = document.querySelector('.autocomplete-item');
            if (first) first.click();
        }
    }
}

function addArticle(artNo) {
    if (selectedArticles.has(artNo)) return;
    selectedArticles.add(artNo);

    const art = ALL_ARTICLES.find(a => a.art_no === artNo);
    if (!art) return;

    document.getElementById('emptyState').style.display = 'none';

    const div = document.createElement('div');
    div.className = 'selected-item';
    div.id = 'sel-' + artNo.replace(/[^a-zA-Z0-9]/g, '_');
    div.innerHTML = `
        <span class="art-no">${artNo}</span>
        <span class="art-catalog">${art.catalog_short} &mdash; Original p. ${art.pages}</span>
        <button class="remove-btn" onclick="removeArticle('${artNo}')">&times;</button>
    `;

    document.getElementById('selectedList').appendChild(div);
    updateCounters();

    // Clear search
    document.getElementById('articleSearch').value = '';
    document.getElementById('autocompleteList').style.display = 'none';
    document.getElementById('articleSearch').focus();
}

function removeArticle(artNo) {
    selectedArticles.delete(artNo);
    const el = document.getElementById('sel-' + artNo.replace(/[^a-zA-Z0-9]/g, '_'));
    if (el) el.remove();
    updateCounters();

    if (selectedArticles.size === 0) {
        document.getElementById('emptyState').style.display = 'block';
    }
}

function clearSelection() {
    selectedArticles.clear();
    const list = document.getElementById('selectedList');
    list.innerHTML = `
        <div class="empty-state" id="emptyState">
            <div class="icon">&#128270;</div>
            Search and add articles above
        </div>
    `;
    updateCounters();
}

function updateCounters() {
    const count = selectedArticles.size;
    document.getElementById('selectedCount').textContent = count;
    document.getElementById('selectionCounter').textContent = count;
    document.getElementById('selectionCounter').style.display = count > 0 ? 'inline-block' : 'none';

    // Estimate unique pages
    const pages = new Set();
    selectedArticles.forEach(artNo => {
        const art = ALL_ARTICLES.find(a => a.art_no === artNo);
        if (art) pages.add(art.catalog + ':' + art.best_page);
    });
    document.getElementById('pageEstimate').textContent = pages.size + 2;

    document.getElementById('generateBtn').disabled = (count === 0);
}

async function generatePDF() {
    const name = document.getElementById('customerName').value.trim() || 'Customer';
    const company = document.getElementById('customerCompany').value.trim() || '';
    const articles = Array.from(selectedArticles);

    if (articles.length === 0) return;

    const btn = document.getElementById('generateBtn');
    const status = document.getElementById('statusBar');

    btn.disabled = true;
    btn.textContent = 'GENERATING...';
    status.className = 'status-bar info';
    status.innerHTML = '<span class="spinner"></span> Generating your custom catalog PDF...';

    try {
        const response = await fetch('/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, company, articles })
        });

        const result = await response.json();

        if (result.success) {
            status.className = 'status-bar success';
            status.innerHTML = `PDF generated! <a href="/download/${result.filename}" target="_blank">Download: ${result.filename}</a>
                <br><small>${result.article_count} articles on ${result.page_count} pages</small>`;
        } else {
            status.className = 'status-bar error';
            status.innerHTML = 'Error: ' + result.error;
        }
    } catch (e) {
        status.className = 'status-bar error';
        status.innerHTML = 'Connection error: ' + e.message;
    }

    btn.disabled = false;
    btn.textContent = 'Generate Catalog PDF';
}

// Close autocomplete when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-container')) {
        document.getElementById('autocompleteList').style.display = 'none';
    }
});
</script>

</body>
</html>
"""


# ============================================================
# ROUTES
# ============================================================
@app.route("/")
def index():
    """Serve the main UI."""
    # Prepare article list for frontend
    articles = []
    for art_no, locs in sorted(ARTICLE_INDEX.items()):
        # Use first location as primary
        primary = locs[0]
        catalog_file = primary[0] if isinstance(primary, tuple) else primary
        page_idx = primary[1] if isinstance(primary, tuple) else 0

        catalog_short = os.path.basename(catalog_file).replace(".pdf", "").replace("_", " ")
        # Shorten very long names
        if len(catalog_short) > 40:
            catalog_short = catalog_short[:37] + "..."

        pages_str = str(page_idx + 1)
        if len(locs) > 1:
            all_pages = sorted(set(str(l[1] + 1) for l in locs))
            pages_str = ",".join(all_pages)

        articles.append({
            "art_no": art_no,
            "catalog": catalog_file,
            "catalog_short": catalog_short,
            "pages": pages_str,
            "best_page": page_idx,
        })

    return render_template_string(
        HTML_TEMPLATE,
        articles_json=json.dumps(articles),
        article_count=len(ARTICLE_INDEX),
        catalog_count=len(CATALOG_LIST),
    )


@app.route("/generate", methods=["POST"])
def generate():
    """Generate the PDF catalog."""
    data = request.json
    name = data.get("name", "Customer")
    company = data.get("company", "")
    article_numbers = data.get("articles", [])

    if not article_numbers:
        return jsonify({"success": False, "error": "No articles selected"})

    try:
        safe_name = re.sub(r'[^\w\s-]', '', company or name)
        safe_name = re.sub(r'\s+', '_', safe_name).strip('_')
        date_str = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"Geister_Selection_{safe_name}_{date_str}.pdf"
        output_path = os.path.join(SCRIPT_DIR, filename)

        result = generate_catalog(name, company, article_numbers, output_path,
                                  cached_index=ARTICLE_INDEX)

        if result:
            # Count pages in generated PDF
            from pypdf import PdfReader
            reader = PdfReader(result)
            page_count = len(reader.pages)

            return jsonify({
                "success": True,
                "filename": filename,
                "article_count": len(article_numbers),
                "page_count": page_count,
            })
        else:
            return jsonify({"success": False, "error": "No matching articles found in catalogs"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/download/<filename>")
def download(filename):
    """Download a generated PDF."""
    filepath = os.path.join(SCRIPT_DIR, filename)
    if os.path.exists(filepath) and filename.startswith("Geister_Selection_"):
        return send_file(filepath, as_attachment=True)
    return "File not found", 404


# ============================================================
# LOAD INDEX ON IMPORT (needed for gunicorn)
# ============================================================
print("\n" + "=" * 50)
print("  GEISTER Custom Catalog Generator")
print("=" * 50)

load_or_build_index()

print(f"\n  Catalogs: {len(CATALOG_LIST)}")
print(f"  Articles: {len(ARTICLE_INDEX)}")
print(f"{'=' * 50}\n")

# ============================================================
# MAIN (for local development)
# ============================================================
if __name__ == "__main__":
    print(f"  Starting web server...")
    print(f"  Open in browser: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
