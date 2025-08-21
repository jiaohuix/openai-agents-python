import time
import asyncio
from openai import AsyncOpenAI, OpenAI
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

# 初始化 FastAPI 应用
app = FastAPI(title="Chat API")

# 配置信息
MODEL_NAME = "Qwen/Qwen3-8B"
api_key = "ms-"
base_url = "https://api-inference.modelscope.cn/v1/"

# 初始化异步和同步客户端
async_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
client = OpenAI(api_key=api_key, base_url=base_url)


# 同步聊天接口
@app.get("/chat/sync")
def chat_sync_endpoint(prompt: str):
    start_time = time.time()
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": prompt}
    ]
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0,
            extra_body={"enable_thinking": False},
        )
        content = response.choices[0].message.content
        end_time = time.time()
        return {
            "content": content,
            "execution_time": end_time - start_time,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 异步流式聊天接口
@app.get("/chat/stream")
async def chat_stream_endpoint(prompt: str):
    async def generate_stream():
        start_time = time.time()
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": prompt}
        ]
        try:
            stream = await async_client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0,
                extra_body={"enable_thinking": False},
                stream=True
            )
            first_token_received = False
            first_token_time = 0

            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    if not first_token_received:
                        first_token_time = time.time() - start_time
                        print(f"首次Token响应时间： {first_token_time} 秒")
                        first_token_received = True
                    yield content
        except Exception as e:
            yield f"Error: {str(e)}"

    return StreamingResponse(generate_stream(), media_type="text/plain")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)