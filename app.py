from flask import Flask, render_template, request, jsonify, Response
import asyncio
import json
import sys
import os

app = Flask(__name__)

# ─── Import migration pipeline from notebook (converted to .py) ──────────────
from migration_pipeline import run_migration

# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/migrate", methods=["POST"])
def migrate():
    data = request.get_json()
    sql_input = data.get("sql", "").strip()

    if not sql_input:
        return jsonify({"error": "No SQL provided"}), 400

    # Run the async migration pipeline
    try:
        # Capture print logs by redirecting stdout
        import io
        from contextlib import redirect_stdout

        log_buffer = io.StringIO()

        async def run():
            with redirect_stdout(log_buffer):
                # result = await run_migration(sql_input)
                from migration_pipeline import run_migration
                result = await run_migration(sql_input)
            return result

        result = asyncio.run(run())
        logs = log_buffer.getvalue()

        return jsonify({
            "success": True,
            "result": result if result is not None else "Migration executed in DB (validation inconclusive — check logs)",
            "logs": logs
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

"""
# ─── Mock migration (remove once real pipeline is connected) ──────────────────
def mock_migration(sql: str) -> str:
    Placeholder — replace with actual run_migration() call.
    return sql.replace("IDENTITY(1,1)", "GENERATED ALWAYS AS IDENTITY") \
              .replace("NVARCHAR", "VARCHAR") \
              .replace("DATETIME", "TIMESTAMP") \
              .replace("GETDATE()", "NOW()") \
              .replace("BIT", "BOOLEAN") \
              .replace("MONEY", "NUMERIC(19,4)") \
              .replace("[", "").replace("]", "") \
              .replace("dbo.", "")
"""


if __name__ == "__main__":
    app.run(debug=True, port=5000)