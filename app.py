"""
Flask web app for Vedic Kundali Generator.
Accepts birth details via a form, generates a PDF report, and serves it.

Designed for PythonAnywhere free-tier deployment.
"""

from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from datetime import datetime
import io
import os

from vedic_kundali import generate_chart, generate_pdf_to_buffer

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
            flash(f"Could not find '{place}'. Try a major city name like 'Mumbai' or 'New York'.", "error")
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
