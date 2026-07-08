"""POST /v1/memory/add and /v1/memory/search (Design_Doc §19.2)."""

from fastapi import APIRouter, Request

from incortex.api.schemas import MemoryAddRequest, MemorySearchRequest, envelope

router = APIRouter()


@router.post("/v1/memory/add")
def memory_add(request: Request, body: MemoryAddRequest):
    core = request.app.state.core
    stored = core.memory.store(body.content, importance=body.importance)
    return envelope({**stored.content, "confidence": stored.confidence})


@router.post("/v1/memory/search")
def memory_search(request: Request, body: MemorySearchRequest):
    core = request.app.state.core
    found = core.memory.retrieve(body.query, top_k=body.top_k)
    return envelope({"results": found.content["results"],
                     "confidence": found.confidence})
