from typing import Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, START, StateGraph
from langsmith import traceable

from app.config import get_settings


class AgentState(TypedDict):
    message: list[BaseMessage]
    model: str
    retry_cnt: int
    error: Optional[str]


class ProdAgent:
    """Current Gemini question-answering flow with a configured fallback model."""

    def __init__(self):
        settings = get_settings()
        common = {
            "temperature": 0.0,
            "timeout": settings.model_timeout_sec,
            "max_retries": settings.max_retry,
            "google_api_key": (
                settings.gemini_api_key.get_secret_value()
                if settings.gemini_api_key else None
            ),
        }
        self.primary_model_name = settings.primary_model
        self.fallback_model_name = settings.fallback_model
        self.max_retries = settings.max_retry
        self.model = ChatGoogleGenerativeAI(model=self.primary_model_name, **common)
        self.fallback_model = ChatGoogleGenerativeAI(model=self.fallback_model_name, **common)
        self.graph = self._build_graph()

    def _build_graph(self):
        def process_message(state: AgentState) -> dict:
            try:
                response = self.model.invoke(state["message"])
                return {"message": [response], "model": self.primary_model_name, "error": None}
            except Exception as exc:
                return {
                    "error": str(exc),
                    "retry_cnt": state["retry_cnt"] + 1,
                }

        def fallback_process_message(state: AgentState) -> dict:
            try:
                response = self.fallback_model.invoke(state["message"])
                return {"message": [response], "model": self.fallback_model_name, "error": None}
            except Exception as exc:
                return {"error": str(exc), "retry_cnt": state["retry_cnt"] + 1}

        def handle_error(state: AgentState) -> dict:
            return {
                "message": [AIMessage(content="There was an error processing your request. Please try again later.")],
                "model": "error_handler",
            }

        def route_after_process(state: AgentState) -> str:
            return "done" if state.get("error") is None else "fallback"

        def route_after_fallback(state: AgentState) -> str:
            return "done" if state.get("error") is None else "error_handler"

        graph = StateGraph(AgentState)
        graph.add_node("process", process_message)
        graph.add_node("fallback", fallback_process_message)
        graph.add_node("error_handler", handle_error)
        graph.add_edge(START, "process")
        graph.add_conditional_edges(
            "process", route_after_process,
            {"done": END, "fallback": "fallback", "error_handler": "error_handler"},
        )
        graph.add_conditional_edges(
            "fallback", route_after_fallback,
            {"done": END, "error_handler": "error_handler"},
        )
        graph.add_edge("error_handler", END)
        return graph.compile()

    @staticmethod
    def _text_content(message: AIMessage) -> str:
        content = message.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "".join(
                item.get("text", "") for item in content
                if isinstance(item, dict) and item.get("type", "text") == "text"
            )
        return str(content)

    @traceable(name="Agent Invoke")
    def invoke(self, message: str) -> dict:
        result = self.graph.invoke({
            "message": [HumanMessage(content=message)],
            "model": self.primary_model_name,
            "retry_cnt": 0,
            "error": None,
        })
        response_message = result["message"][-1]
        return {
            "response": self._text_content(response_message),
            "model": result.get("model", self.primary_model_name),
            "error": result.get("error"),
        }
