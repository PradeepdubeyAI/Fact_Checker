"""Evaluate evidence node - determines claim validity based on evidence.

Analyzes evidence snippets to assess if a claim is supported, refuted, or inconclusive.
"""

import logging
from typing import List, Optional

from pydantic import BaseModel, Field
from utils import (
    call_llm_with_structured_output,
    get_llm,
    truncate_evidence_for_token_limit,
)

from claim_verifier.prompts import (
    EVIDENCE_EVALUATION_HUMAN_PROMPT,
    EVIDENCE_EVALUATION_SYSTEM_PROMPT,
    get_current_timestamp,
)
from claim_verifier.schemas import (
    ClaimVerifierState,
    Evidence,
    Verdict,
    VerificationResult,
)
from claim_verifier.insufficient_info_analyzer import analyze_insufficient_info

logger = logging.getLogger(__name__)


class EvidenceEvaluationOutput(BaseModel):
    verdict: VerificationResult = Field(
        description="The final fact-checking verdict. Use 'Supported' only when evidence clearly and consistently supports the claim from reliable sources. Use 'Refuted' when evidence clearly contradicts the claim with authoritative sources. Use 'Insufficient Information' when evidence is limited, unclear, or not comprehensive enough for a definitive conclusion. Use 'Conflicting Evidence' when reliable sources provide contradictory information about the claim."
    )
    reasoning: str = Field(
        description="Brief summary of the verdict (1-2 sentences max). State the key finding concisely."
    )
    corrected_claim: Optional[str] = Field(
        default=None,
        description="REQUIRED for REFUTED verdicts: Provide the accurate version of the claim based on evidence (e.g., if claim says 'India is 1st economy', provide 'India is the 5th largest economy by GDP as of 2024'). For SUPPORTED verdicts: Optionally provide confirmation with specific data. For NOT_ENOUGH_INFO: Set to null."
    )
    detailed_explanation: str = Field(
        description="Comprehensive analysis (3-5 sentences) that includes: (1) Specific data points from evidence (numbers, dates, names), (2) Assessment of source credibility and authority, (3) Why the evidence supports the verdict, (4) Any relevant context or caveats. Be factual and educational."
    )
    influential_source_indices: List[int] = Field(
        description="1-based indices of the evidence sources that were most important in reaching this verdict. These sources will be marked for prominent display in the user interface while all sources remain visible. For 'Supported' and 'Refuted' verdicts, include sources that directly support the decision. For 'Insufficient Information' and 'Conflicting Evidence' verdicts, include the most relevant sources that were considered. Select 2-4 of the most critical sources.",
        default_factory=list,
    )


def _format_evidence_snippets(snippets: List[Evidence]) -> str:
    if not snippets:
        return "No relevant evidence snippets were found."

    return "\n\n".join(
        [
            f"Source {i + 1}: {s.url}\n"
            + (f"Title: {s.title}\n" if s.title else "")
            + f"Snippet: {s.text.strip()}\n---"
            for i, s in enumerate(snippets)
        ]
    )


async def evaluate_evidence_node(state: ClaimVerifierState) -> dict:
    claim = state.claim
    evidence_snippets = state.evidence
    iteration_count = state.iteration_count

    logger.info(
        f"Final evaluation for claim '{claim.claim_text}' "
        f"with {len(evidence_snippets)} evidence snippets "
        f"after {iteration_count} iterations"
    )

    system_prompt = EVIDENCE_EVALUATION_SYSTEM_PROMPT.format(
        current_time=get_current_timestamp()
    )

    truncated_evidence = truncate_evidence_for_token_limit(
        evidence_items=evidence_snippets,
        claim_text=claim.claim_text,
        system_prompt=system_prompt,
        human_prompt_template=EVIDENCE_EVALUATION_HUMAN_PROMPT,
        max_tokens=128000,  # gpt-4o-mini has 128k context window
        format_evidence_func=_format_evidence_snippets,
    )
    
    # Critical safeguard: If no evidence after truncation, return NOT_ENOUGH_INFO
    if not truncated_evidence or len(truncated_evidence) == 0:
        logger.warning(f"No evidence available after truncation for claim: '{claim.claim_text}'")
        verdict = Verdict(
            claim_text=claim.claim_text,
            disambiguated_sentence=claim.disambiguated_sentence,
            original_sentence=claim.original_sentence,
            original_index=claim.original_index,
            result=VerificationResult.NOT_ENOUGH_INFO,
            reasoning="Evidence was gathered but could not be processed due to technical constraints.",
            corrected_claim=None,
            detailed_explanation="Multiple evidence sources were found, but technical limitations prevented their analysis. This claim requires manual review with the available sources.",
            sources=[Evidence(url=e.url, text=e.text[:200], title=e.title) for e in evidence_snippets[:5]],
            search_queries=state.all_queries,
        )
        logger.info(
            f"Verdict '{verdict.result}' for '{claim.claim_text}': {verdict.reasoning} "
            f"({len(verdict.sources)} sources listed)"
        )
        return {"verdict": verdict}


    messages = [
        ("system", system_prompt),
        (
            "human",
            EVIDENCE_EVALUATION_HUMAN_PROMPT.format(
                claim_text=claim.claim_text,
                evidence_snippets=_format_evidence_snippets(truncated_evidence),
            ),
        ),
    ]

    llm = get_llm(model_name="openai:gpt-4o-mini", stage="claim_verifier.evaluate_evidence")

    response = await call_llm_with_structured_output(
        llm=llm,
        output_class=EvidenceEvaluationOutput,
        messages=messages,
        context_desc=f"evidence evaluation for claim '{claim.claim_text}'",
    )

    if not response:
        logger.warning(f"Failed to evaluate evidence for claim: '{claim.claim_text}'")
        
        # Create verdict with insufficient info analysis
        verdict = Verdict(
            claim_text=claim.claim_text,
            disambiguated_sentence=claim.disambiguated_sentence,
            original_sentence=claim.original_sentence,
            original_index=claim.original_index,
            result=VerificationResult.NOT_ENOUGH_INFO,
            reasoning="Verification could not be completed due to API rate limits or technical issues.",
            sources=[Evidence(url=e.url, text=e.text[:200], title=e.title) for e in evidence_snippets[:3]],
            search_queries=state.all_queries,
        )
        
        # Try to analyze why verification failed
        try:
            reason_category, explanation, suggestions = analyze_insufficient_info(
                claim=claim.claim_text,
                evidence_list=[{"url": e.url, "text": e.text, "title": e.title} for e in evidence_snippets],
                search_queries=state.all_queries,
                verdict_reasoning="API call failed after retries - likely rate limiting or service issues"
            )
            verdict.insufficient_info_reason = reason_category
            verdict.insufficient_info_explanation = f"{explanation} Additionally, the verification process was interrupted by API rate limits. Please try verifying fewer claims at once (10-15 recommended) to stay within rate limits."
            verdict.insufficient_info_suggestions = suggestions + [
                "Try verifying this claim separately or in a smaller batch (10-15 claims)",
                "Wait a few minutes before retrying to avoid rate limits",
                "Check OpenAI API status if issues persist: https://status.openai.com/"
            ]
        except Exception as e:
            logger.warning(f"Failed to analyze insufficient info for failed verification: {e}")
    else:
        try:
            result = VerificationResult(response.verdict)
        except ValueError:
            logger.warning(
                f"Invalid verdict '{response.verdict}', defaulting to NOT_ENOUGH_INFO"
            )
            result = VerificationResult.NOT_ENOUGH_INFO

        influential_urls = (
            {
                truncated_evidence[idx - 1].url
                for idx in response.influential_source_indices
                if 1 <= idx <= len(truncated_evidence)
            }
            if response.influential_source_indices
            else set()
        )

        sources = [
            Evidence(
                url=source.url,
                text=source.text,
                title=source.title,
                is_influential=source.url in influential_urls,
            )
            for source in {source.url: source for source in evidence_snippets}.values()
        ]

        verdict = Verdict(
            claim_text=claim.claim_text,
            disambiguated_sentence=claim.disambiguated_sentence,
            original_sentence=claim.original_sentence,
            original_index=claim.original_index,
            result=result,
            reasoning=response.reasoning,
            corrected_claim=response.corrected_claim if hasattr(response, 'corrected_claim') else None,
            detailed_explanation=response.detailed_explanation if hasattr(response, 'detailed_explanation') else response.reasoning,
            sources=sources,
            search_queries=state.all_queries,
        )
        
        # If verdict is NOT_ENOUGH_INFO, analyze the reason
        if result == VerificationResult.NOT_ENOUGH_INFO:
            try:
                reason_category, explanation, suggestions = analyze_insufficient_info(
                    claim=claim.claim_text,
                    evidence_list=[{"url": e.url, "text": e.text, "title": e.title} for e in evidence_snippets],
                    search_queries=state.all_queries,
                    verdict_reasoning=response.reasoning
                )
                verdict.insufficient_info_reason = reason_category
                verdict.insufficient_info_explanation = explanation
                verdict.insufficient_info_suggestions = suggestions
                logger.info(f"NOT_ENOUGH_INFO reason: {reason_category}")
            except Exception as e:
                logger.warning(f"Failed to analyze insufficient info reason: {e}")

    # Log final result
    influential_count = sum(source.is_influential for source in verdict.sources)
    logger.info(
        f"Verdict '{verdict.result}' for '{claim.claim_text}': {verdict.reasoning} "
        f"({len(verdict.sources)} sources, {influential_count} influential)"
    )

    return {"verdict": verdict}
 