from fastapi import FastAPI
from api.stt import routes as stt_routes
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.include_router(stt_routes.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
