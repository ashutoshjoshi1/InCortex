"""The InCortex API application (Design_Doc §19).

create_app(core) wraps one brain in a FastAPI app exposing the §19.2
endpoints. Three app-wide rules:

- every response uses the {"success", "data", "error"} envelope,
  including validation failures and unknown routes;
- errors carry readable messages, never stack traces;
- the fail-closed rule extends to HTTP — no approver is attached, so
  level-4 tools are denied on an unattended server.
"""

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from incortex.api.routes_chat import router as chat_router
from incortex.api.routes_feedback import router as feedback_router
from incortex.api.routes_memory import router as memory_router
from incortex.api.schemas import ToolExecuteRequest, envelope

MAX_LOG_COUNT = 200


def create_app(core=None, config=None):
    """Build the API around an existing brain, or one built from config."""
    if core is None:
        from incortex.core import CortexConfig, build_cortex
        core = build_cortex(config or CortexConfig())
    app = FastAPI(title="InCortex", version="0.1.0", docs_url="/docs")
    app.state.core = core
    app.include_router(chat_router)
    app.include_router(memory_router)
    app.include_router(feedback_router)
    _add_introspection_routes(app)
    _add_tool_route(app)
    _add_error_handlers(app)
    return app


def _add_introspection_routes(app):
    @app.get("/v1/health")
    def health(request: Request):
        return envelope(request.app.state.core.health_check())

    @app.get("/v1/organs")
    def organs(request: Request):
        report = request.app.state.core.health_check()
        summary = [{"name": organ["name"], "status": organ["status"],
                    "health": organ["health"]}
                   for organ in report["organs"]]
        return envelope({"organs": summary})

    @app.get("/v1/cells")
    def cells(request: Request):
        report = request.app.state.core.health_check()
        flattened = []
        for organ in report["organs"]:
            for component in organ["components"]:
                if "confidence" in component:  # a loose cell report
                    flattened.append({**component, "organ": organ["name"]})
                for cell in component.get("cells", []):
                    flattened.append({**cell, "organ": organ["name"]})
        return envelope({"cells": flattened})

    @app.get("/v1/logs")
    def logs(request: Request, count: int = Query(default=20, ge=1,
                                                  le=MAX_LOG_COUNT)):
        messages = [
            {
                "message_type": message.message_type,
                "source": message.source,
                "target": message.target,
                "session_id": message.session_id,
                "confidence": message.confidence,
                "created_at": message.created_at,
                "payload": _printable(message.payload),
            }
            for message in request.app.state.core.bus.history(count)
        ]
        return envelope({"messages": messages})


def _add_tool_route(app):
    @app.post("/v1/tools/execute")
    def tools_execute(request: Request, body: ToolExecuteRequest):
        core = request.app.state.core
        if core.tools is None:
            return JSONResponse(status_code=400, content=envelope(
                error="no tools are configured on this brain"))
        try:
            core.tools.registry.get(body.tool)
        except ValueError:
            return JSONResponse(status_code=404, content=envelope(
                error=f"no tool named '{body.tool}'"))
        out = core.tools.invoke(body.tool, body.request)
        return envelope(out.content)


def _add_error_handlers(app):
    @app.exception_handler(RequestValidationError)
    def on_validation_error(request, exc):
        details = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'] if part != 'body')}: "
            f"{error['msg']}"
            for error in exc.errors()
        )
        return JSONResponse(status_code=400, content=envelope(error=details))

    @app.exception_handler(ValueError)
    def on_value_error(request, exc):
        return JSONResponse(status_code=400, content=envelope(error=str(exc)))

    @app.exception_handler(StarletteHTTPException)
    def on_http_error(request, exc):
        return JSONResponse(status_code=exc.status_code,
                            content=envelope(error=str(exc.detail)))


def _printable(payload):
    """Payloads may be arbitrary objects; the log endpoint shows text."""
    if isinstance(payload, (str, int, float, bool, type(None))):
        return payload
    if isinstance(payload, dict):
        return {key: _printable(value) for key, value in payload.items()}
    if isinstance(payload, (list, tuple)):
        return [_printable(item) for item in payload]
    return str(payload)
