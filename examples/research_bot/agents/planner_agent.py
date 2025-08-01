from pydantic import BaseModel

from agents import Agent

from .config import MODEL_NAME, DEFAULT_MODEL_SETTINGS, get_model_structure

PROMPT = (
    "You are a helpful research assistant. Given a query, come up with a set of web searches "
    "to perform to best answer the query. Output between 5 and 20 terms to query for."
    "IMPORTANT: If the query is in Chinese, generate search terms in BOTH Chinese and English "
    "to get comprehensive results from different sources. If the query is in English, generate "
    "search terms only in English."
    "Please respond in JSON format with the required structure."
)


class WebSearchItem(BaseModel):
    reason: str
    "Your reasoning for why this search is important to the query."

    query: str
    "The search term to use for the web search."


class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem]
    """A list of web searches to perform to best answer the query."""

output_structure = get_model_structure(WebSearchPlan)
# print("output_structure",output_structure)
PROMPT += "\n\nRequired JSON structure:\n" + output_structure

planner_agent = Agent(
    name="PlannerAgent",
    instructions=PROMPT,
    # model="gpt-4o",
    model = MODEL_NAME,
    model_settings=DEFAULT_MODEL_SETTINGS,
    output_type=WebSearchPlan,
)
