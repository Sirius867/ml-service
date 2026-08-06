from fastapi import FastAPI


app = FastAPI(title="ML Service", version="0.1.0")


@app.get("/")
async def index() -> dict[str, str]:
    return {"message": "ML service is running"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
