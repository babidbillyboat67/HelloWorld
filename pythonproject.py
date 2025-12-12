from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/hello")
def hello(data: dict):
    return {"message": f"Hello, {data['name' + "doot doot skrilla"]}!"}
