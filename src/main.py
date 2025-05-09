import sys
import os

# Add the src directory to the Python path
# This is necessary so that Flask can find the modules in the src directory
# when the app is run from the project root directory (almukhtar_aroudi_app)
# The create_flask_app template adds a similar line, but it's specific to its own structure.
# We adjust it here for our current structure where main.py is in src/
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # This is /home/ubuntu/almukhtar_aroudi_app/src
PROJECT_ROOT = os.path.dirname(BASE_DIR) # This is /home/ubuntu/almukhtar_aroudi_app
sys.path.insert(0, PROJECT_ROOT) # Add project root to import src.module
sys.path.insert(0, BASE_DIR) # Add src to import module directly if needed

from flask import Flask, render_template, request, jsonify
import sqlite3

# Import from our project files
from src import config
from src.core import PoetryMatcher, RuleEngine, TextCleaner, UnitExtractor, LineSplitter, Processor, MeterIndexer
from src.data import load_replacements_from_db

app = Flask(__name__, template_folder=".", static_folder="static")
# The template_folder is set to "." because main.py is in src/ and templates/ is also in src/
# So, effectively, templates are in src/templates/
app.template_folder = os.path.join(BASE_DIR, "templates")
app.static_folder = os.path.join(BASE_DIR, "static")

class ResultProcessorForWeb:
    def __init__(self, weights_db_path, tafeelat_db_path):
        self.weights_db = weights_db_path
        self.tafeelat_db = tafeelat_db_path
        self.html_output = ""

    def get_weights(self, sea):
        conn = sqlite3.connect(self.weights_db)
        cur = conn.cursor()
        cur.execute(
            "SELECT pattern FROM weights WHERE bahr_name = ?;",
            (sea,)
        )
        row = cur.fetchone()
        conn.close()
        return row[0] if row else ""

    def compare(self, sea, res):
        w = self.get_weights(sea)
        wl = w.split(" *** ")
        rl = res.split(" *** ")
        if len(wl) == 2 and len(rl) == 2:
            wp = wl[0].split() + wl[1].split()
            rp = rl[0].split() + rl[1].split()
        elif len(wl) == 1 and len(rl) == 1:
            wp = wl[0].split()
            rp = rl[0].split()
        elif len(wl) == 1 and len(rl) == 2: # Case where original weight is single part, but result is two parts (e.g. مجزوء)
            wp = wl[0].split()
            rp = rl[0].split() + rl[1].split()
        else: # Fallback or error case
            # This case might need more robust handling depending on expected data
            app.logger.warning(f"Weight/Result length mismatch: wl={len(wl)}, rl={len(rl)} for sea={sea}, w='{w}', res='{res}'")
            # Attempt to process what we can, e.g. the first part if available
            wp = wl[0].split() if wl else []
            rp = rl[0].split() if rl else []
            if len(wl) > 1 and len(rl) == 1:
                 rp = rl[0].split() # if result is single and weight is double, this is likely an error in data or logic
            elif len(wl) == 0 or len(rl) == 0:
                 return "خطأ في تطابق الأوزان والتفاعيل.", []
        
        comps = list(zip(wp, rp))
        fmt = (
            f"تفعيلة بحر [{sea}]:<br><strong>{w}</strong><br>"
            f"تفاعيل البيت:<br><strong>{res}</strong>"
        )
        return fmt, comps

    def process_comps(self, comps):
        conn = sqlite3.connect(self.tafeelat_db)
        cur = conn.cursor()
        out = []
        for wt, rt in comps:
            cur.execute(
                "SELECT type FROM tafeelat WHERE asal = ? AND lamh_asl = ?;",
                (wt, rt)
            )
            row = cur.fetchone()
            if row:
                typ = row[0]
            else:
                cur.execute(
                    "SELECT type FROM tafeelat WHERE asal = ? AND image = ?;",
                    (wt, rt)
                )
                r2 = cur.fetchone()
                typ = r2[0] if r2 else f"{wt}\tبقيت على الأصل"
            out.append(f"{wt} = {rt} : {typ}")
        conn.close()
        return out

    def process(self, orig_poem_line, processed_poem_line, full_matches):
        self.html_output = ""
        self.html_output += (
            f"<div class=\"result\">"
            f"<p class=\"original\"><strong>البيت الأصلي:</strong> {orig_poem_line}</p>"
            f"<p class=\"processed\"><strong>البيت المعالج:</strong> {processed_poem_line}</p>"
        )
        if full_matches:
            self.html_output += "<h2>مطابقة تامة للشطرين:</h2>"
            for sea, line in full_matches.items():
                fmt, comps = self.compare(sea, line)
                if not comps and fmt.startswith("خطأ"):
                    self.html_output += f"<p style='color:red;'>{fmt}</p>"
                    continue
                frs = self.process_comps(comps)
                self.html_output += f"<h3 class=\"meter\">بحر {sea}</h3><p class=\"tafeelat\">{fmt}</p><ul>"
                for r_item in frs:
                    self.html_output += f"<li>{r_item}</li>"
                self.html_output += "</ul>"
        else:
            self.html_output += "<p>لا توجد مطابقة تامة للشطرين.</p>"
        self.html_output += "<div class=\"separator\"></div></div>"
        return self.html_output

# Initialize once
try:
    replacements = load_replacements_from_db(config.REPLACEMENTS_DB)
    poetry_matcher = PoetryMatcher(config.DB_PATH, replacements)
    result_processor = ResultProcessorForWeb(config.WEIGHTS_DB, config.TAFEELAT_DB)
except Exception as e:
    app.logger.error(f"Error initializing poetry tools: {e}")
    replacements = {}
    poetry_matcher = None
    result_processor = None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    if not poetry_matcher or not result_processor:
        return jsonify({"error": "خدمة التحليل غير متاحة حالياً بسبب خطأ في الإعدادات الأولية."}), 500

    data = request.get_json()
    poem_text = data.get("poem", "")
    
    if not poem_text.strip():
        return jsonify({"error": "الرجاء إدخال نص لتحليله."})

    lines = poem_text.strip().split("\n")
    # User requested max 10 lines (verses)
    if len(lines) > 10:
        lines = lines[:10]
    
    final_html_output = ""

    for single_poem_line in lines:
        if not single_poem_line.strip():
            continue
        try:
            # Ensure each line has ***, if not, it might be a single shatr or malformed
            # The original code expects '***' for splitting. If not present, processing might be partial.
            # For now, we pass it as is, core.py's PoetryMatcher handles it.
            processed_line, full_matches = poetry_matcher.process_poem(single_poem_line.strip())
            line_html = result_processor.process(single_poem_line.strip(), processed_line, full_matches)
            final_html_output += line_html
        except Exception as e:
            app.logger.error(f"Error processing line: {single_poem_line} - {e}")
            final_html_output += f"<div class=\"result\"><p style=\"color:red;\">حدث خطأ أثناء معالجة البيت: {single_poem_line}<br/>التفاصيل: {e}</p></div>"

    if not final_html_output:
        final_html_output = "<p>لم يتم العثور على أبيات صالحة للتحليل أو لم يتم إرجاع نتائج.</p>"

    return jsonify({"html_output": final_html_output})

if __name__ == "__main__":
    # Make sure to run with python -m src.main when testing locally from project root,
    # or adjust PYTHONPATH. For deployment, gunicorn or similar will handle this.
    app.run(host="0.0.0.0", port=5000, debug=True)

