import json
import re


def parse_json_from_llm_output(text: str) -> dict:
    """
    Attempts to extract a JSON object from LLM output.
    Handles markdown code fences.
    """

    # Try to find JSON within code fences
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if json_match:
        text = json_match.group(1)

    # Try to find JSON object
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find start and end of JSON
    start = text.find('{')
    end = text.rfind('}') + 1

    if start != -1 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM output: {text[:200]}")
