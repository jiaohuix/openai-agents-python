'''
pip install openai==1.96.1
'''
import asyncio
from typing import List, Literal
from pydantic import BaseModel
from agents import Agent, Runner, RunConfig
from openai.types.responses import ResponseTextDeltaEvent

from config import MODEL_NAME, DEFAULT_MODEL_SETTINGS,CUSTOM_MODEL_PROVIDER


# class ResponseTextDeltaEvent(BaseModel):
#     content_index: int
#     """The index of the content part that the text delta was added to."""

#     delta: str
#     """The text delta that was added."""

#     item_id: str
#     """The ID of the output item that the text delta was added to."""

#     # logprobs: List[Logprob]
#     # """The log probabilities of the tokens in the delta."""

#     output_index: int
#     """The index of the output item that the text delta was added to."""

#     sequence_number: int
#     """The sequence number for this event."""

#     type: Literal["response.output_text.delta"]
#     """The type of the event. Always `response.output_text.delta`."""

async def chat_stream():
    agent = Agent(
        name = "故事大王",
        instructions = "你是一个讲科幻短故事的故事大王，擅长讲短小精悍的科幻故事。",
        model = MODEL_NAME,
        model_settings = DEFAULT_MODEL_SETTINGS,
    )
    query = "异形"
    print(query)
    result = Runner.run_streamed(agent, input = query,
                                    run_config=RunConfig(model_provider=CUSTOM_MODEL_PROVIDER))
    # print(result)
    async for event in result.stream_events():
        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent ):
            print(event.data.delta, end = "", flush = True)
            content = event.data.delta
            if content:
                print(content, end = "", flush = True)




# async def chat_stream():
#     agent = Agent(
#         name="Joker",
#         instructions="You are a helpful assistant.",
#         model = MODEL_NAME,
#         model_settings = DEFAULT_MODEL_SETTINGS,
#     )

#     result = Runner.run_streamed(agent, input="Please tell me 5 jokes.",
#                                  run_config=RunConfig(model_provider=CUSTOM_MODEL_PROVIDER))
#     async for event in result.stream_events():
#         if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
#             print(event.data.delta, end="", flush=True)


if __name__ == "__main__":
    asyncio.run(chat_stream())