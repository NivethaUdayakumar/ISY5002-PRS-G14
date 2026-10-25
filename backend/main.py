from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.video_route import router as video_router
from services.sighting_store import reset_runtime_sightings, seed_species

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(video_router)


@app.on_event("startup")
def clear_previous_runtime_sightings():
    reset_runtime_sightings()
    seed_species()

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}