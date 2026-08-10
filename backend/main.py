from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.video_route import router as video_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(video_router)

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}