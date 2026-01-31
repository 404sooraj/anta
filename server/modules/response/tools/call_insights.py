"""Tool for retrieving similar past call scenarios, response patterns, and policy from Pinecone."""

import logging
import os
from typing import Any, Dict, List, Optional

from langchain_aws import BedrockEmbeddings
from pinecone import Pinecone
from pydantic import BaseModel, Field

from .base import BaseTool

logger = logging.getLogger(__name__)

# Same as data-ingestion pipeline; switch model by changing BEDROCK_EMBEDDING_MODEL_ID or using another LangChain embeddings class
BEDROCK_EMBED_MODEL = os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v1:0")
TOP_K = int(os.getenv("PINECONE_TOP_K", "5"))


def _normalize_index_name(name: str) -> str:
    """Pinecone index names must be lowercase alphanumeric or hyphen only (e.g. call_scenarios → call-scenarios)."""
    return name.replace("_", "-").lower()


def _get_embeddings() -> BedrockEmbeddings:
    """LangChain Bedrock embeddings; switch to OpenAIEmbeddings etc. to change provider."""
    return BedrockEmbeddings(
        region_name=os.getenv("AWS_REGION", "us-west-2"),
        model_id=BEDROCK_EMBED_MODEL,
    )


def _get_embedding(text: str) -> List[float]:
    """Embed text using LangChain embeddings (Bedrock by default)."""
    embeddings = _get_embeddings()
    return embeddings.embed_query(text)


def _query_index(
    pc: Pinecone,
    index_name: str,
    vector: List[float],
    top_k: int = TOP_K,
    filter_metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    try:
        index = pc.Index(name=_normalize_index_name(index_name))
        kwargs: Dict[str, Any] = {
            "vector": vector,
            "top_k": top_k,
            "include_metadata": True,
        }
        if filter_metadata:
            kwargs["filter"] = filter_metadata
        result = index.query(**kwargs)
        matches = getattr(result, "matches", None) or []
        out = []
        for m in matches:
            meta = getattr(m, "metadata", None) or {}
            text = meta.get("text", "") if isinstance(meta, dict) else ""
            meta_clean = {k: v for k, v in (meta if isinstance(meta, dict) else {}).items() if k != "text"}
            out.append({"text": text, "metadata": meta_clean})
        return out
    except Exception as e:
        logger.warning("Pinecone query failed for %s: %s", index_name, e)
        return []


class GetCallInsightsInput(BaseModel):
    """Input schema for getCallInsights tool."""

    situation_summary: str = Field(
        ...,
        description="Short description of the current situation or issue (e.g. customer wants penalty removed after late battery return).",
    )
    issue_type: Optional[str] = Field(
        default=None,
        description="Optional normalized issue type if known (e.g. penalty_dispute, battery_swap) to bias results.",
    )


class GetCallInsightsTool(BaseTool):
    """Retrieve similar past call scenarios, response patterns, and policy from Pinecone for AI guidance."""

    name: str = "getCallInsights"
    description: str = (
        "Use this when you need to know if a similar situation has happened before, what worked or failed, or what the company policy says. "
        "Returns similar past scenarios, response patterns (best practices and anti-patterns), and policy snippets. "
        "Provide a short situation_summary of the current issue; optionally provide issue_type (e.g. penalty_dispute, battery_swap)."
    )
    args_schema = GetCallInsightsInput

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute getCallInsights: embed query, query Pinecone indexes, return insights.
        """
        situation_summary = kwargs.get("situation_summary", "").strip()
        issue_type = (kwargs.get("issue_type") or "").strip() or None

        if not situation_summary:
            return {
                "status": "error",
                "data": {"message": "situation_summary is required"},
            }

        pinecone_key = os.getenv("PINECONE_API_KEY")
        index_scenarios = os.getenv("PINECONE_INDEX_CALL_SCENARIOS", "call_scenarios")
        index_patterns = os.getenv("PINECONE_INDEX_RESPONSE_PATTERNS", "response_patterns")
        index_policy = os.getenv("PINECONE_INDEX_POLICY_KNOWLEDGE", "policy_knowledge")

        if not pinecone_key:
            return {
                "status": "error",
                "data": {"message": "PINECONE_API_KEY not configured"},
            }

        query_text = situation_summary
        if issue_type:
            query_text = f"{issue_type}: {situation_summary}"

        try:
            vector = _get_embedding(query_text)
        except Exception as e:
            logger.exception("Embedding failed")
            return {"status": "error", "data": {"message": str(e)}}

        pc = Pinecone(api_key=pinecone_key)
        filter_meta = {"issue_type": {"$eq": issue_type}} if issue_type else None

        similar_scenarios = _query_index(pc, index_scenarios, vector, TOP_K, filter_meta)
        response_patterns = _query_index(pc, index_patterns, vector, TOP_K, filter_meta)
        policy_snippets = _query_index(pc, index_policy, vector, TOP_K)

        if not similar_scenarios and not response_patterns and not policy_snippets:
            return {
                "status": "success",
                "data": {
                    "similar_scenarios": [],
                    "response_patterns": [],
                    "policy_snippets": [],
                    "message": "No similar past cases or policy found for this situation.",
                },
            }

        return {
            "status": "success",
            "data": {
                "similar_scenarios": similar_scenarios,
                "response_patterns": response_patterns,
                "policy_snippets": policy_snippets,
            },
        }
