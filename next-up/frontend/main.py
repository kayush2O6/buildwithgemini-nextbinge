"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.

Why A2A: agents-cli 1.1.0 (GA) deploys ADK agents to Agent Runtime as A2A agents
and no longer registers the reasoning-engine operation schema the old
`agent_engines.get(...).stream_query()` path relied on (operation_schemas() comes
back empty). The container serves the A2A protocol over the Agent Engine HTTP
passthrough, so this proxy fetches the agent's card and sends messages with the
a2a-sdk client (the same path `agents-cli run --mode a2a` uses). This works for
both A2A and plain ADK 1.1.0 deployments (the container serves A2A either way).

Run:
  pip install -r requirements.txt
  export AGENT_ENGINE_RESOURCE_NAME="projects/.../locations/.../reasoningEngines/..."
  export AGENT_DIRECTORY="app"   # your agent's app directory (agents-cli-manifest.yaml)
  python main.py                 # -> http://localhost:8080
"""

import asyncio
import json
import os
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/539437831919/locations/us-east1/reasoningEngines/2864229989379735552",
)
# The agent's app directory (matches agent_directory in agents-cli-manifest.yaml).
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
# Location is embedded in the resource name: projects/<p>/locations/<loc>/reasoningEngines/<id>.
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

# A2A endpoint for an Agent Runtime deployment, via the Agent Engine HTTP
# passthrough. The card lives at the well-known path under this base.
A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

# The agent tags its A2UI data parts with this mime type.
_A2UI_MIME = "application/json+a2ui"

# One set of ADC credentials, refreshed per request (access tokens expire ~1h).
_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    # Always return JSON so the browser never receives a plain-text 500 page
    # (which shows up in the chat as "Unexpected token 'I', "Internal S"... is
    # not valid JSON"). Any server-side failure now surfaces as a readable
    # message in the chat bubble instead.
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}
# Cache the agent card after the first fetch.
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        try:
            resp = await client.get(A2A_CARD_URL, timeout=10.0)
            if resp.status_code == 200:
                card = AgentCard(**resp.json())
                card.url = A2A_BASE
                _card = card
                return _card
        except Exception:
            pass

        # Static fallback ensures cold starts / gateway hiccups don't break UI
        _card = AgentCard(
            name="next_up",
            description="An ADK Agent",
            url=A2A_BASE,
            version="0.1.0",
            protocol_version="0.3",
            preferred_transport="JSONRPC",
            capabilities={"streaming": True},
            default_input_modes=["text/plain"],
            default_output_modes=["text/plain"],
            skills=[],
        )
    return _card


def _extract_parts(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for the chat UI.

    Text parts pass through as {"kind": "text"}. A2UI data parts (tagged
    application/json+a2ui) become {"kind": "a2ui", "data": <message>} so the UI
    renders the card; each data part is one A2UI message (beginRendering or
    surfaceUpdate).
    """
    out: list[dict] = []
    for p in parts:
        root = getattr(p, "root", p)
        if isinstance(root, TextPart) and getattr(root, "text", None):
            text = root.text
            if text.startswith("<a2a_datapart_json>") and text.endswith("</a2a_datapart_json>"):
                json_str = text[len("<a2a_datapart_json>"):-len("</a2a_datapart_json>")]
                try:
                    data = json.loads(json_str)
                    if "beginRendering" in data:
                        out.append({"kind": "a2ui", "data": {"beginRendering": data["beginRendering"]}})
                    if "surfaceUpdate" in data:
                        out.append({"kind": "a2ui", "data": {"surfaceUpdate": data["surfaceUpdate"]}})
                    continue
                except Exception:
                    pass
            out.append({"kind": "text", "text": text})
        elif getattr(root, "data", None) is not None:
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            data_val = root.data
            if mime == _A2UI_MIME:
                out.append({"kind": "a2ui", "data": data_val})
            elif isinstance(data_val, dict):
                nested_meta = data_val.get("metadata") or {}
                if isinstance(nested_meta, dict) and nested_meta.get("mimeType") == _A2UI_MIME:
                    out.append({"kind": "a2ui", "data": data_val.get("data", data_val)})
                elif "beginRendering" in data_val or "surfaceUpdate" in data_val:
                    out.append({"kind": "a2ui", "data": data_val})
        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    last_error = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
                card = await _get_card(client)
                factory = ClientFactory(
                    ClientConfig(
                        supported_transports=[
                            TransportProtocol.jsonrpc,
                            TransportProtocol.http_json,
                        ],
                        httpx_client=client,
                    )
                )
                a2a_client = factory.create(card)

                msg = Message(
                    message_id=str(uuid.uuid4()),
                    role=Role.user,
                    parts=[Part(root=TextPart(text=message))],
                    context_id=_contexts.get(user_id),
                )

                last_task = None
                async for event in a2a_client.send_message(msg):
                    if not isinstance(event, tuple):
                        continue
                    task, update = event
                    if task is not None:
                        last_task = task
                        if getattr(task, "context_id", None):
                            _contexts[user_id] = task.context_id
                    if isinstance(update, TaskArtifactUpdateEvent):
                        parts.extend(_extract_parts(update.artifact.parts))

                # Fallback if streaming events did not produce user-facing parts:
                if not parts and last_task is not None:
                    for artifact in getattr(last_task, "artifacts", None) or []:
                        parts.extend(_extract_parts(artifact.parts))

                if parts:
                    break
        except Exception as e:
            last_error = e
            if attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))
            else:
                raise

    if not parts and last_error is None:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


# Serve the chat UI (keep this mount last so /chat wins).
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
