import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def get_embedder():
    """
    Returns an OpenAI embedding client.
    """

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
    )

    return client.embeddings
