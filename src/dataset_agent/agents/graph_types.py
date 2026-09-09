from typing import TypedDict, Annotated
import operator

from langchain_core.messages import BaseMessage


class DatasetOutput(TypedDict):
    """Output schema for a discovered dataset observation."""
    entity_type: str
    title: str
    description: str
    doi: str
    license_: str
    publisher: str
    access_level: str
    keywords: list


class DiscoveryOutput(TypedDict):
    """Output schema for the discovery agent queries."""
    queries: list


def add_messages(left: list, right: list) -> list:
    if not isinstance(left, list):
        left = []
    if not isinstance(right, list):
        right = []
    return left + right


class StateGraphInput(TypedDict):
    messages: Annotated[list, add_messages]


class StateGraphOutput(TypedDict):
    structured_response: DatasetOutput
