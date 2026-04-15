from fapi import FastAPI
import uvicorn

# 创建应用实例
app = FastAPI()

# 定义路由
@app.get("/")
def root():
    return {"message": "Hello World"}

# 启动入口（直接传入 app 对象，避免字符串导入问题）
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
