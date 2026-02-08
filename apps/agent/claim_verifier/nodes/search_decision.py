"""Search decision node - determines whether to continue searching or make final evaluation.

Assesses evidence sufficiency and confidence to decide next steps.
"""

import logging
from typing import Literal

from langgraph.graph.state import Command
from pydantic import BaseModel, Field
from utils import call_llm_with_structured_output, get_llm

from claim_verifier.config import ITERATIVE_SEARCH_CONFIG
from claim_verifier.prompts import (
    SEARCH_DECISION_HUMAN_PROMPT,
    SEARCH_DECISION_SYSTEM_PROMPT,
    get_current_timestamp,
)
from claim_verifier.schemas import ClaimVerifierState, IntermediateAssessment

logger = logging.getLogger(__name__)


# Authoritative source domains for heuristic early stopping
AUTHORITATIVE_DOMAINS = [
    "gov",  # Government sites
    "edu",  # Educational institutions
    ".org",  # Official organizations
    "who.int",
    "imf.org",
    "worldbank.org",
    "un.org",
    "nasa.gov",
    "cdc.gov",
    "nih.gov",
    "nature.com",
    "science.org",
    "nejm.org",
    "wikipedia.org",
    "britannica.com",
]


def has_authoritative_source(evidence: list) -> bool:
    """Check if evidence includes authoritative sources.
    
    Args:
        evidence: List of Evidence objects
        
    Returns:
        True if at least one authoritative source present
    """
    for ev in evidence:
        url_lower = ev.url.lower()
        if any(domain in url_lower for domain in AUTHORITATIVE_DOMAINS):
            return True
    return False


class SearchDecisionOutput(BaseModel):
    """Evidence sufficiency assessment for claim verification.

    Evaluates whether the current evidence is sufficient to make a confident
    fact-checking determination or if additional evidence gathering is needed.
    Should be conservative - only recommend stopping when evidence is comprehensive
    and conclusive.
    """

    needs_more_evidence: bool = Field(
        description="Whether additional evidence is needed before making a final determination. Return True if: evidence is limited (1-2 pieces), evidence is contradictory or unclear, evidence lacks authoritative sources, or claim requires more specific verification. Return False only when evidence is comprehensive, clear, and from reliable sources."
    )
    missing_aspects: list[str] = Field(
        default_factory=list,
        description="Specific aspects that need more evidence coverage. Examples: 'official statements from organization X', 'statistical data from authoritative source', 'expert opinion on technical claims', 'contradictory evidence from reliable sources', 'more recent information'. Be specific about what type of evidence would strengthen the verification.",
    )


async def search_decision_node(
    state: ClaimVerifierState,
) -> Command[Literal["generate_search_query", "evaluate_evidence"]]:
    """Decide whether to continue searching or proceed to final evaluation."""

    claim = state.claim
    evidence = state.evidence
    iteration_count = state.iteration_count

    max_iterations = ITERATIVE_SEARCH_CONFIG["max_iterations"]

    # Check stopping conditions
    if iteration_count >= max_iterations:
        logger.info(
            f"Reached maximum iterations ({max_iterations}), proceeding to final evaluation"
        )
        return Command(goto="evaluate_evidence")

    # Heuristic early stopping: if we have good evidence from authoritative sources
    # With max 3 iterations, be slightly more lenient on early stopping
    if len(evidence) >= 3 and has_authoritative_source(evidence):
        logger.info(
            f"Early stop: Found {len(evidence)} evidence items including authoritative sources"
        )
        return Command(goto="evaluate_evidence")
    
    # Additional early stop: 2+ authoritative sources is also sufficient
    authoritative_count = sum(1 for ev in evidence if any(domain in ev.url.lower() for domain in AUTHORITATIVE_DOMAINS))
    if authoritative_count >= 2 and len(evidence) >= 2:
        logger.info(
            f"Early stop: Found {authoritative_count} authoritative sources out of {len(evidence)} total"
        )
        return Command(goto="evaluate_evidence")

    # Assess evidence sufficiency with LLM
    llm = get_llm(stage="claim_verifier.search_decision")

    evidence_summary = "\n".join(
        [
            f"- {ev.title}: {ev.text[:200]}..." if ev.title else f"- {ev.text[:200]}..."
            for ev in evidence[:10]
        ]
    )

    current_time = get_current_timestamp()

    system_prompt = SEARCH_DECISION_SYSTEM_PROMPT.format(current_time=current_time)
    human_prompt = SEARCH_DECISION_HUMAN_PROMPT.format(
        claim_text=claim.claim_text,
        evidence_count=len(evidence),
        evidence_summary=evidence_summary,
    )

    messages = [
        ("system", system_prompt),
        ("human", human_prompt),
    ]

    response = await call_llm_with_structured_output(
        llm=llm,
        output_class=SearchDecisionOutput,
        messages=messages,
        context_desc=f"search decision for claim '{claim.claim_text}'",
    )

    if not response:
        logger.warning(
            "Failed to assess evidence sufficiency, proceeding to final evaluation"
        )
        return Command(goto="evaluate_evidence")

    assessment = IntermediateAssessment(
        needs_more_evidence=response.needs_more_evidence,
        missing_aspects=response.missing_aspects,
    )

    # Decision logic based on LLM assessment
    should_continue = response.needs_more_evidence and iteration_count < max_iterations

    if should_continue:
        logger.info(
            f"Continuing search - more evidence needed, "
            f"iteration: {iteration_count + 1}/{max_iterations}, "
            f"current evidence: {len(evidence)} pieces"
        )
        return Command(
            goto="generate_search_query",
            update={
                "iteration_count": iteration_count + 1,
                "intermediate_assessment": assessment,
            },
        )
    else:
        logger.info(
            f"Proceeding to final evaluation - evidence sufficient, "
            f"total evidence: {len(evidence)} pieces"
        )
        return Command(
            goto="evaluate_evidence", update={"intermediate_assessment": assessment}
        )
