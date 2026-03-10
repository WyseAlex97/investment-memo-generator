import json
import os
from flask import Flask, render_template, request, Response, stream_with_context
import anthropic

app = Flask(__name__)

SYSTEM_PROMPT = """You are a managing director at a top-tier investment firm writing a concise,
professional investment screening memo. Be specific, balanced, and decisive. Write in clear prose
suitable for an investment committee. Use the exact section headers provided."""

MEMO_PROMPT = """Write an investment screening memo for the following company.

Company: {company_name}
{notes_line}

Structure the memo with exactly these four sections and headers. Each section must be 30 words or fewer.

## Company Overview
One or two sentences covering what the company does and its business model.

## Investment Thesis
One or two sentences on why this could be a compelling investment opportunity.

## Key Risks
A bulleted list of the 3 most important risks. Each bullet must be one short phrase.

## Recommendation
State clearly: PURSUE, WATCHLIST, or PASS — followed by one sentence of rationale."""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    company_name = (data.get("company_name") or "").strip()
    notes = (data.get("notes") or "").strip()

    if not company_name:
        return {"error": "Company name is required"}, 400

    notes_line = f"Additional context: {notes}" if notes else ""
    prompt = MEMO_PROMPT.format(company_name=company_name, notes_line=notes_line)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY environment variable is not set"}, 500

    def stream():
        client = anthropic.Anthropic(api_key=api_key)
        try:
            with client.messages.stream(
                model="claude-opus-4-6",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}]
            ) as s:
                for text in s.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001, threaded=True)
