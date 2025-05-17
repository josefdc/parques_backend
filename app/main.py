from fastapi import FastAPI

app = FastAPI(title="Parqués Backend")

@app.get("/")
async def read_root():
    return {"message": "Bienvenido al Backend de Parqués"}

# Aquí es donde más adelante incluirás los routers de game_routes.py, etc.
# from app.api.routers import game_routes
# app.include_router(game_routes.router, prefix="/api/v1")