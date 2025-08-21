import time
import asyncio
from openai import AsyncOpenAI,OpenAI
MODEL_NAME="Qwen/Qwen3-8B"
api_key = "ms-
base_url = "https://api-inference.modelscope.cn/v1/"

# 初始化客户端
async_client = AsyncOpenAI(api_key=api_key, base_url= base_url)
client = OpenAI(api_key=api_key, base_url= base_url)

def chat_sync(prompt: str):
    """ 同步的对话函数 
        接口文档：https://platform.openai.com/docs/api-reference/chat_streaming/streaming
    """
    start_time = time.time()
    messages = [{"role":"system","content": "You are a helpful assistant"},
                    {"role":"user","content": prompt}]
    response = client.chat.completions.create(
        model = MODEL_NAME,
        messages = messages,
        temperature = 0,
        extra_body = {"enable_thinking": False},

    )
    print("response", response)
    content = response.choices[0].message.content
    
    end_time = time.time()
    print(f"执行时间: {end_time - start_time} 秒")
    return content


async def chat_stream(prompt: str):
    """ 异步流式的对话服务 
        接口文档：https://platform.openai.com/docs/api-reference/chat_streaming/streaming
    """
    start_time = time.time()
    messages = [{"role":"system","content": "You are a helpful assistant"},
                    {"role":"user","content": prompt}]
    
    stream = await async_client.chat.completions.create(
        model = MODEL_NAME,
        messages = messages,
        temperature = 0,
        extra_body = {"enable_thinking": False},
        stream = True # <==
    )
    full_response = ""
    first_token_received = False
    first_token_time = 0

    # 迭代每个chunk
    async for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            if not first_token_received:
                first_token_time = time.time() - start_time
                print(f"首次Token响应时间： {first_token_time} 秒")
                first_token_received = True

            full_response += content
            # print(content, end = "\n", flush = True) # print的时候会把信息存到缓冲区，出现\n会输出；flush=True后强制每次输出刷新，实现打字机的效果
            print(content, end = "", flush = True) # print的时候会把信息存到缓冲区，出现\n会输出；flush=True后强制每次输出刷新，实现打字机的效果
        

    end_time = time.time()
    print(f"执行时间: {end_time - start_time} 秒")

    return full_response


if __name__ == "__main__":
    prompt = "如何才能恢复精力和专注力"
    # content = chat_sync(prompt)
    # print("content", content)

    asyncio.run(chat_stream(prompt))

