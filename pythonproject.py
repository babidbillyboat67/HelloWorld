
import random
import fastapi
from fastapi.middleware.cors import CORSMiddleware

app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#this is the random number generator
@app.get("/api/roll")
def roll():
    return {"result": random.randint(1, 6)}




#this is the joke generator
@app.get("/api/joke")
def joke():
    jokes = [
        "67 mustard", "ohio", "doot doot"
    ]
    return {"joke": random.choice(jokes)}


@app.post("/api/add")
def add(data: dict):
    return {"result": data["a"] + data["b"]}


#this is the word reverser
@app.post("/api/reverse")
def reverse(data: dict):
    return {"reversed": data["text"][::-1]}

@app.post("/api/convert")
def convert(data: dict):
    return {"celsius": (data["fahrenheit"] - 32) * 5/9}

@app.get("/api/color")
def color():
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    color = f"#{r:02x}{g:02x}{b:02x}"
    return {"color": color}
