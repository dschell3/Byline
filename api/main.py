"""OverClock API entry point."""

from fastapi import FastAPI

from routers import auth, invites, me

app = FastAPI(title="OverClock API")
app.include_router(auth.router)
app.include_router(invites.router)
app.include_router(me.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe used by Render. Must never touch the database."""
    return {"status": "ok"}
