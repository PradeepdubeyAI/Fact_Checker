"""Data models for claim verification.

All the structured types used throughout the verification workflow.
"""

from enum import Enum
from typing import Annotated, List, Optional
from pydantic import BaseModel, Field
from claim_extractor.schemas import ValidatedClaim
from operator import add


class VerificationResult(str, Enum):
    """Possible outcomes of a fact-checking verification."""

    SUPPORTED = "Supported"
    REFUTED = "Refuted"
    NOT_ENOUGH_INFO = "Insufficient Information"
    CONFLICTING_EVIDENCE = "Conflicting Evidence"


class Evidence(BaseModel):
    """A single piece of evidence retrieved from a search."""

    url: str = Field(description="The URL of the evidence source")
    text: str = Field(description="The text snippet of the evidence")
    title: Optional[str] = Field(
        default=None, description="The title of the source page"
    )
    is_influential: bool = Field(
        default=False, description="Whether this source was marked as influential by the LLM during evaluation"
    )


class Verdict(BaseModel):
    """The result of fact-checking a single claim."""

    claim_text: str = Field(description="The text of the claim that was checked")
    disambiguated_sentence: str = Field(
        description="The disambiguated sentence from which the claim was derived"
    )
    original_sentence: str = Field(
        description="The original sentence from which the claim was derived"
    )
    original_index: int = Field(
        description="The index of the original sentence in the source text"
    )
    result: VerificationResult = Field(
        description="The fact-checking verdict (Supported, Refuted, etc.)"
    )
    reasoning: str = Field(description="Brief explanation of the verdict")
    corrected_claim: Optional[str] = Field(
        default=None, 
        description="For REFUTED claims: the correct version based on evidence. For SUPPORTED: confirmation of accuracy."
    )
    detailed_explanation: str = Field(
        default="", 
        description="Detailed analysis explaining the verdict with specific evidence details, data points, and source credibility assessment"
    )
    sources: List[Evidence] = Field(
        default_factory=list, description="List of evidence sources"
    )
    search_queries: List[str] = Field(
        default_factory=list, description="All search queries used to find evidence"
    )
    # Insufficient info reason fields (only populated when result=NOT_ENOUGH_INFO)
    insufficient_info_reason: Optional[str] = Field(
        default=None,
        description="Category explaining why verification failed (PROPRIETARY_DATA, TOO_SPECIFIC, REGIONAL_DATA, etc.)"
    )
    insufficient_info_explanation: Optional[str] = Field(
        default=None,
        description="Detailed explanation of why this specific claim couldn't be verified"
    )
    insufficient_info_suggestions: Optional[List[str]] = Field(
        default=None,
        description="Actionable suggestions for alternative verification methods"
    )


class IntermediateAssessment(BaseModel):
    """Assessment of evidence sufficiency during iterative searching."""

    needs_more_evidence: bool = Field(description="Whether more evidence is needed")
    missing_aspects: List[str] = Field(
        default_factory=list, description="Aspects that need more evidence"
    )


class ClaimVerifierState(BaseModel):
    """The workflow graph state for claim verification."""

    claim: ValidatedClaim = Field(description="The claim being verified")
    query: Optional[str] = Field(default=None, description="Current search query")
    all_queries: List[str] = Field(
        default_factory=list, description="All queries used across iterations"
    )
    evidence: Annotated[List[Evidence], add] = Field(default_factory=list)
    verdict: Optional[Verdict] = Field(
        default=None, description="Final verification result"
    )
    iteration_count: int = Field(default=0, description="Current iteration number")
    intermediate_assessment: Optional[IntermediateAssessment] = Field(
        default=None, description="Assessment of evidence sufficiency"
    )
