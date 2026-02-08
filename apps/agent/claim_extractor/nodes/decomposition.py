"""Decomposition node - extracts factual claims from sentences.

Breaks complex sentences into simple, standalone factual claims.
"""

import asyncio
import itertools
import logging
from typing import Dict, List

from pydantic import BaseModel, Field

from claim_extractor.config import DECOMPOSITION_CONFIG
from claim_extractor.prompts import DECOMPOSITION_SYSTEM_PROMPT, HUMAN_PROMPT
from claim_extractor.schemas import DisambiguatedContent, PotentialClaim, State
from utils import call_llm_with_structured_output, get_llm, remove_following_sentences

logger = logging.getLogger(__name__)

# Use only one completion here - we've already filtered and disambiguated
COMPLETIONS = DECOMPOSITION_CONFIG["completions"]
MIN_SUCCESSES = DECOMPOSITION_CONFIG["min_successes"]


class DecompositionOutput(BaseModel):
    """Response schema for decomposition LLM calls."""

    claims: List[str] = Field(
        default_factory=list, description="List of extracted factual claims"
    )
    no_claims: bool = Field(
        description="Flag indicating if no verifiable claims were found"
    )


async def _decomposition_stage(
    disambiguated_item: DisambiguatedContent,
) -> List[PotentialClaim]:
    """Extract atomic claims from a disambiguated sentence.

    Args:
        disambiguated_item: Disambiguated content to process

    Returns:
        List of potential claims
    """
    sentence = disambiguated_item.disambiguated_sentence
    logger.debug(f"Processing decomposition for: '{sentence}'")

    # Get zero-temp LLM for consistent results
    llm = get_llm(completions=COMPLETIONS, stage="claim_extractor.decomposition")

    # Get context without following sentences
    original_context = (
        disambiguated_item.original_selected_item.original_context_item.context_for_llm
    )
    modified_context = remove_following_sentences(original_context)

    # Prep the prompt
    messages = [
        ("system", DECOMPOSITION_SYSTEM_PROMPT),
        (
            "human",
            HUMAN_PROMPT.format(
                excerpt=modified_context,
                sentence=sentence,
            ),
        ),
    ]

    # Call the LLM to extract claims
    response = await call_llm_with_structured_output(
        llm=llm,
        output_class=DecompositionOutput,
        messages=messages,
        context_desc=f"decomposition stage for sentence '{sentence}'",
    )

    # If no claims were found
    if not response or response.no_claims or not response.claims:
        logger.info(f"No claims found in: '{sentence}'")
        return []

    logger.debug(f"Decomposition response: {response}")

    # Clean up claims and convert to objects
    claims_texts = [claim.strip() for claim in response.claims if claim.strip()]

    # Get original sentence and index
    original_sentence = disambiguated_item.original_selected_item.original_context_item.original_sentence
    original_index = disambiguated_item.original_selected_item.original_context_item.original_index

    potential_claims = [
        PotentialClaim(
            claim_text=claim_text, 
            disambiguated_sentence=sentence,
            original_sentence=original_sentence,
            original_index=original_index
        )
        for claim_text in claims_texts
    ]

    logger.info(
        f"Extracted {len(potential_claims)} potential claims from: '{sentence}'"
    )
    return potential_claims


async def decomposition_node(state: State) -> Dict[str, List[PotentialClaim]]:
    """Break sentences into self-contained factual claims.

    Supports three modes:
    1. Standard pipeline: with disambiguated_contents (from disambiguation node)
    2. Phase 2 optimized: with selected_contents (contextualization already did disambiguation)
    3. Phase 3 aggressive: with contextual_sentences (no selection)

    Args:
        state: Current workflow state

    Returns:
        Dictionary with potential_claims key
    """
    disambiguated_contents = state.disambiguated_contents or []
    selected_contents = state.selected_contents or []
    contextual_sentences = state.contextual_sentences or []

    # Phase 2 optimized mode: Convert selected_contents to disambiguated format
    # (contextualization already did the disambiguation work)
    if not disambiguated_contents and selected_contents:
        logger.info(
            f"PHASE 2 MODE: Processing {len(selected_contents)} selected items "
            "(contextualization already resolved references)"
        )
        from claim_extractor.schemas import DisambiguatedContent
        disambiguated_contents = [
            DisambiguatedContent(
                disambiguated_sentence=item.processed_sentence,
                original_selected_item=item
            )
            for item in selected_contents
        ]
    
    # Phase 3 aggressive mode: Work directly with contextual_sentences if no disambiguated content
    elif not disambiguated_contents and contextual_sentences:
        logger.info(
            f"PHASE 3 AGGRESSIVE MODE: Processing {len(contextual_sentences)} sentences directly "
            "(skipping selection - decomposition will filter)"
        )
        # Convert contextual sentences to pseudo-disambiguated format
        from claim_extractor.schemas import DisambiguatedContent, SelectedContent
        disambiguated_contents = [
            DisambiguatedContent(
                disambiguated_sentence=sent.original_sentence,
                original_selected_item=SelectedContent(
                    processed_sentence=sent.original_sentence,
                    original_context_item=sent
                )
            )
            for sent in contextual_sentences
        ]

    if not disambiguated_contents:
        logger.warning("Nothing to decompose")
        return {"potential_claims": []}

    # Process all contents in parallel for speed
    potential_claims = await asyncio.gather(
        *(
            _decomposition_stage(disambiguated_content)
            for disambiguated_content in disambiguated_contents
        )
    )

    potential_claims = list(itertools.chain.from_iterable(potential_claims))

    # Check if any claims were found
    if not potential_claims:
        logger.info("No potential claims found after processing")
        return {"potential_claims": []}

    logger.info(f"Extracted a total of {len(potential_claims)} potential claims")
    return {"potential_claims": potential_claims}
