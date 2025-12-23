"""MCP Server 主入口"""
from fastapi import FastAPI

from tools import system, file, folder

app = FastAPI(title="MCP Server", description="MCP 工具服务")

# 注册路由
app.include_router(system.router)
app.include_router(file.router)
app.include_router(folder.router)


@app.get("/")
async def root():
    return {"message": "MCP Server is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
