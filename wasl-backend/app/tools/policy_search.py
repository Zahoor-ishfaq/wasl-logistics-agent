"""
app/tools/policy_search.py

Agent tool: search the knowledge base for the policy that governs a
specific exception type.

This is different from the RAG answer service. The RAG service answers
a user's free-text question. This tool is called by the AGENT during an
investigation to pull the governing policy for the exception it found —
e.g. "what does our policy say about customs holds?" — so it can ground
its assessment and drafted action in the actual documented procedure.

It reuses the retriever you already built. The only twist is that it
biases toward the policy and SOP documents (where procedures live)
rather than, say, the SLA scorecard.

This tool does NOT call the LLM. It only retrieves policy chunks.
"""

from pydantic import BaseModel, Field

from app.models.answer import Citation
from app.models.shipment import ExceptionType
from app.rag.retriever import get_retriever

# Maps each exception type to a natural-language query that retrieves
# the most relevant policy for it. Written to match the language used
# in the policy documents so retrieval lands on the right sections.
_EXCEPTION_QUERIES: dict[ExceptionType, str] = {
    ExceptionType.customs_hold: (
        "customs hold documentation missing certificate HS code "
        "clearance procedure notification"
    ),
    ExceptionType.holiday_closure: (
        "public holiday closure Eid delay expected SLA exemption customs offices closed"
    ),
    ExceptionType.cross_border: (
        "cross border GCC delay escalation visibility notification border crossing hold"
    ),
    ExceptionType.supplier_delay: (
        "supplier vendor delivery failure delay notification vendor "
        "scorecard exception notice"
    ),
    ExceptionType.carrier_delay: (
        "carrier operational delay notification revised ETA escalation"
    ),
    ExceptionType.failed_delivery: (
        "failed delivery attempt re-delivery consignee unavailable policy"
    ),
    ExceptionType.none: "delivery procedure standard operating policy",
}


class PolicySearchInput(BaseModel):
    """Validated input for the policy search tool."""

    exception_type: ExceptionType = Field(
        ...,
        description="The exception type to find the governing policy for.",
    )
    extra_context: str = Field(
        default="",
        max_length=300,
        description="Optional extra keywords to refine the search "
        "(e.g. the specific missing document).",
    )
    top_k: int = Field(default=3, ge=1, le=10)


def policy_search(
    exception_type: ExceptionType,
    extra_context: str = "",
    top_k: int = 3,
) -> list[Citation]:
    """
    Retrieve the policy chunks that govern a given exception type.

    Use this tool during an investigation, after you've identified what
    kind of exception a shipment has, to pull the documented policy that
    tells you how to handle it. Ground your assessment and any drafted
    action in what these chunks say.

    Args:
        exception_type: The kind of exception found on the shipment.
        extra_context:  Optional extra keywords to sharpen the search,
                        e.g. "missing SASO certificate" or "Ghuwaifat border".
        top_k:          How many policy chunks to return. Default 3.

    Returns:
        A list of Citation objects (source, section, snippet, score),
        most relevant first. May be empty if nothing relevant is found.
    """
    validated = PolicySearchInput(
        exception_type=exception_type,
        extra_context=extra_context,
        top_k=top_k,
    )

    base_query = _EXCEPTION_QUERIES.get(
        validated.exception_type, _EXCEPTION_QUERIES[ExceptionType.none]
    )
    query = f"{base_query} {validated.extra_context}".strip()

    retriever = get_retriever()
    # We don't hard-filter to one source file here because the relevant
    # policy for one exception can legitimately span several documents
    # (e.g. delayed_shipments_policy + holiday_schedule for a holiday case).
    # The query wording already biases toward the right sections.
    return retriever.retrieve_as_citations(query=query, top_k=validated.top_k)
