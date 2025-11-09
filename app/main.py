# app/main.py
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.rules import auto_approve_beyond_48h, deadline_meta
from app.rag import policy_lookup, normalize_reason, tag_reason
from app.precedent import record_precedent

app = FastAPI(title="EzExtender 2.0 (Local Demo)")
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "items": []})

@app.post("/request")
def submit_request(
    deadline_iso: str = Form(...),
    days_requested: int = Form(...),
    reason_text: str = Form(...)
):
    """
    - If deadline is >48h away -> auto-approve
    - Else -> RAG (policy + precedent)
    Always returns 'deadline_meta' for the UI.
    """
    try:
        dl_meta = deadline_meta(deadline_iso)
        beyond48, hours_left = auto_approve_beyond_48h(deadline_iso)
    except ValueError as e:
        return JSONResponse(
            {"error": "invalid_deadline_iso", "message": str(e)},
            status_code=400
        )

    if beyond48:
        return {
            "decision": "approve",
            "via": "rule_beyond_48h",
            "confidence": 1.0,
            "explanation": f"{hours_left:.1f}h to deadline (> 48h) → auto-approve.",
            "deadline_meta": dl_meta,
        }

    pol = policy_lookup(reason_text)
    pol["deadline_meta"] = dl_meta
    return JSONResponse(pol)

@app.post("/review")
def review_request(
    deadline_iso: str = Form(...),
    days_requested: int = Form(...),
    reason_text: str = Form(...),
    outcome: str = Form(...),          # "allow" or "deny"
    reviewer: str = Form("anonymous"),
):
    outcome = outcome.lower().strip()
    if outcome == "approve": outcome = "allow"
    if outcome == "reject":  outcome = "deny"
    if outcome not in ("allow", "deny"):
        return JSONResponse({"ok": False, "error": "Outcome must be allow/deny"}, status_code=400)

    norm = normalize_reason(reason_text)
    tag = tag_reason(reason_text)
    meta = {"deadline_iso": deadline_iso, "days_requested": days_requested, "reviewer": reviewer}

    record_precedent(
        reason_text_raw=reason_text,
        reason_text_norm=norm,
        outcome=outcome,
        tag=tag,
        meta=meta,
    )
    return {"ok": True, "stored": {"tag": tag, "outcome": outcome}}
