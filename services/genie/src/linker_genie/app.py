"""HTTP entry point: `uvicorn linker_genie.app:app`."""

from fastapi import FastAPI

app = FastAPI(title="Genie - Linker's AI assistant")


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the service is up."""
    return {"status": "ok"}
