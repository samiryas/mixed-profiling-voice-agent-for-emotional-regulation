import json
import logging
import os
from openai import AsyncOpenAI, BaseModel
from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError


BOT_TEMP = 1.0
OPENAI_KEY = os.environ.get('OPENAI_KEY')
OPENAI_MODEL = os.environ.get("OPENAI_MODEL")
URL = os.environ.get("OPENAI_URL")

# function to run messages (async)
async def runGPT(inputMessage):
    # openai async client and response creation
    client = AsyncOpenAI(api_key=OPENAI_KEY,base_url=URL, max_retries=50)
    response = await client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=BOT_TEMP,
        messages=inputMessage,
        stream=False
    )
    return response.choices[0].message.content



async def runGPTModel(inputMessage,model:BaseModel):
    client = AsyncOpenAI(api_key=OPENAI_KEY,base_url=URL, max_retries=5)
    schema = model.model_json_schema()

    parsed_correct=False
    while parsed_correct==False:
        if OPENAI_MODEL in ["kit.gpt-oss-120b", "kit.mixtral-8x22b-instruct"]:
            completion = await client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=BOT_TEMP,
                stream=False,
                messages = inputMessage,
                extra_body={
                    "guided_json": schema,
                }
            )
        else:
            completion = await client.chat.completions.create(
                model=OPENAI_MODEL,
                temperature=BOT_TEMP,
                stream=False,
                messages = inputMessage,
                response_format = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": model.__name__,
                        "strict": True,
                        "schema": schema,
                    },
                }
            )
        try:       
            parsed = model.model_validate_json(completion.choices[0].message.content)
            parsed_correct = True
        except ValidationError as e:
            logging.info(f"Parsing Model Error: {e}")        
    return parsed
