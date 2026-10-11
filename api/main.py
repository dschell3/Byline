"""OverClock API entry point."""

from fastapi import FastAPI

app = FastAPI(title="OverClock API")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe used by Render. Must never touch the database."""
    return {"status": "ok"}
