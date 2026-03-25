"""
Flask web app for Vedic Kundali Generator.
Accepts birth details via a form, generates a PDF report, and serves it.

Designed for PythonAnywhere free-tier deployment.
"""

from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify
from datetime import datetime
import csv
import io
import os

from vedic_kundali import generate_chart, generate_pdf_to_buffer, generate_personalized_reading

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_USAGE_LOG = os.path.join(_APP_DIR, "usage_log.csv")


def log_usage(name, dob, time_of_birth, place):
    """Append a row to usage_log.csv."""
    file_exists = os.path.exists(_USAGE_LOG)
    with open(_USAGE_LOG, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp", "name", "dob", "time", "place"])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         name, dob, time_of_birth, place])

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    try:
        # ── Collect form data ─────────────────────────────────────
        name = request.form.get("name", "").strip()
        date_str = request.form.get("date", "").strip()       # YYYY-MM-DD (HTML date input)
        time_str = request.form.get("time", "").strip()        # HH:MM (HTML time input)
        place = request.form.get("place", "").strip()

        if not name or not date_str or not time_str or not place:
            flash("All fields are required.", "error")
            return redirect(url_for("index"))

        # Parse date
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            year, month, day = dt.year, dt.month, dt.day
        except ValueError:
            flash("Invalid date format.", "error")
            return redirect(url_for("index"))

        # Parse time
        try:
            tm = datetime.strptime(time_str, "%H:%M")
            hour, minute, second = tm.hour, tm.minute, 0
        except ValueError:
            flash("Invalid time format.", "error")
            return redirect(url_for("index"))

        # ── Resolve location ──────────────────────────────────────
        from vedic_kundali import lookup_city
        coords = lookup_city(place, birth_year=year, birth_month=month, birth_day=day)

        if coords is None:
            flash(f"Could not find '{place}'. Try a major city name like 'Mumbai' or 'New York'. "
                  f"If your city is not listed, please email astroshuklz@shuklz.com with the city and country details and we will add it.", "error")
            return redirect(url_for("index"))

        lat, lon, utc_offset = coords

        # ── Build birth_data dict ─────────────────────────────────
        birth_data = {
            "name": name,
            "year": year, "month": month, "day": day,
            "hour": hour, "minute": minute, "second": second,
            "utc_offset": utc_offset,
            "lat": lat, "lon": lon,
            "place": place,
        }

        # ── Log usage ─────────────────────────────────────────────
        log_usage(name, date_str, time_str, place)

        # ── Generate chart ────────────────────────────────────────
        chart = generate_chart(birth_data)

        # ── Generate PDF to memory buffer ─────────────────────────
        pdf_buffer = generate_pdf_to_buffer(chart)

        # ── Serve the PDF ─────────────────────────────────────────
        safe_name = name.replace(" ", "_").lower()
        filename = f"kundali_{safe_name}.pdf"

        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=False,           # opens inline in browser
            download_name=filename,
        )

    except Exception as e:
        flash(f"Error generating chart: {str(e)}", "error")
        return redirect(url_for("index"))


@app.route("/api/readings", methods=["POST"])
def readings():
    """Return personalized readings (week/month/year) as JSON with HTML content."""
    try:
        name = request.form.get("name", "").strip()
        date_str = request.form.get("date", "").strip()
        time_str = request.form.get("time", "").strip()
        place = request.form.get("place", "").strip()

        if not name or not date_str or not time_str or not place:
            return jsonify({"error": "All fields are required."}), 400

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            year, month, day = dt.year, dt.month, dt.day
        except ValueError:
            return jsonify({"error": "Invalid date format."}), 400

        try:
            tm = datetime.strptime(time_str, "%H:%M")
            hour, minute, second = tm.hour, tm.minute, 0
        except ValueError:
            return jsonify({"error": "Invalid time format."}), 400

        from vedic_kundali import lookup_city
        coords = lookup_city(place, birth_year=year, birth_month=month, birth_day=day)
        if coords is None:
            return jsonify({"error": f"Could not find '{place}'. Please use a major city name."}), 400

        lat, lon, utc_offset = coords

        birth_data = {
            "name": name,
            "year": year, "month": month, "day": day,
            "hour": hour, "minute": minute, "second": second,
            "utc_offset": utc_offset,
            "lat": lat, "lon": lon,
            "place": place,
        }

        # Generate all three readings in both English and Hindi
        week_en = generate_personalized_reading(birth_data, "week", lang="en")
        month_en = generate_personalized_reading(birth_data, "month", lang="en")
        year_en = generate_personalized_reading(birth_data, "year", lang="en")

        week_hi = generate_personalized_reading(birth_data, "week", lang="hi")
        month_hi = generate_personalized_reading(birth_data, "month", lang="hi")
        year_hi = generate_personalized_reading(birth_data, "year", lang="hi")

        return jsonify({
            "en": {"week": week_en, "month": month_en, "year": year_en},
            "hi": {"week": week_hi, "month": month_hi, "year": year_hi},
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
