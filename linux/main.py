from typing import Literal
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import yaml

app = FastAPI()


@app.get("/")
def hello():
    return 'Hello!'


class AppStatus(BaseModel):
    name: Literal['tim', 'wechat']
    status: Literal['no_message', 'new_message', 'not_found', 'unknown_error']


@app.post("/status")
def status(app_status: AppStatus):
    print(app_status)
    return {"name": app_status.name, "status": app_status.status}


if __name__ == "__main__":
    with open(Path(__file__).parent.parent / 'config.yaml') as f:
        config = yaml.safe_load(f)
    uvicorn.run("main:app",
                host=config['linux']['host'],
                port=config['linux']['port'])
