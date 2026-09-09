import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_LLM(base_url, model_name, temperature=0.0):
    """
    Returns a ChatOpenAI LLM instance.
    """

    return ChatOpenAI(
        model=model_name,
        temperature=temperature,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base=base_url,
    )
