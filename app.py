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

Structure the memo with exactly these five sections and headers:

## Company Overview
Provide 2-3 paragraphs covering what the company does, its business model, key products or services,
competitive landscape, and industry context.

## Investment Thesis
Provide 2-3 paragraphs explaining why this could be a compelling investment opportunity and the
path to value creation.

## Key Risks
Provide a bulleted list of the 5-6 most important risks to the investment thesis.

## Diligence Questions
Provide a bulleted list of 6-8 specific questions that must be answered in due diligence.

## Recommendation
State clearly: PURSUE, WATCHLIST, or PASS — followed by 2-3 sentences of rationale."""


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
                max_tokens=2048,
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
