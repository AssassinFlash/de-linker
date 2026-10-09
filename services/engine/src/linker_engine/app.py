"""HTTP entry point: `uvicorn linker_engine.app:app`."""

from fastapi import FastAPI

app = FastAPI(title="Solution Configurator engine")


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the service is up."""
    return {"status": "ok"}
