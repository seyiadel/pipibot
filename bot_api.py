from fastapi import FastAPI


app = FastAPI(
    title="PipBot Version 1.0",
    version="1.0.0",
    description="Forex Trading Bot API - authored by seyiadel"
)

@app.get("/")
def intro():
    return "Welcome to Pipbot Trading Bot API v1.0"


def bot_api():
    return