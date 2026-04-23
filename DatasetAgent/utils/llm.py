from langchain_openai import ChatOpenAI

def get_LLM(base_url, model_name, temperature)

    return ChatOpenAI(
        base_url=base_url,
        api_key="EMPTY",
        model=model_name,
        temperature=temperature,
    )