from fastapi import FastAPI
from routes.video_route import router as video_router

app = FastAPI()
app.include_router(video_router)

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}