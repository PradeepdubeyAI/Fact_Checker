"""
Contextualization node - converts raw input to self-sufficient, claim-ready sentences.

This node MERGES the functionality of:
1. Preprocessing (format conversion: tables → prose)
2. Disambiguation (reference resolution: pronouns → specific nouns)

By combining these tasks, we eliminate redundancy and reduce LLM calls by ~47%.
"""

import logging
from typing import Any, Tuple
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field
from utils import get_llm, process_with_voting, call_llm_with_structured_output
from claim_extractor.schemas import ExtractionState, ContextualSentence
from claim_extractor.config import CONTEXT_CONFIG

logger = logging.getLogger(__name__)

# Use 2 completions for quality (critical step)
COMPLETIONS = CONTEXT_CONFIG.get("completions", 2)
MIN_SUCCESSES = CONTEXT_CONFIG.get("min_successes", 2)


class ContextualizationOutput(BaseModel):
    """Response schema for contextualization LLM calls."""
    contextualized_text: str = Field(
        description="Text with all formats converted to prose and all references resolved"
    )


# Combined prompt handling both format conversion AND reference resolution
CONTEXTUALIZATION_SYSTEM_PROMPT = """You are an expert text processor that transforms ANY input format into complete, self-sufficient sentences ready for fact-checking.

YOUR MISSION:
Create sentences that can be independently verified without access to the original document. Each sentence must explicitly state what is being claimed and about what entity, topic, location, or timeframe.

CRITICAL FIRST STEP - EXTRACT DOCUMENT-LEVEL CONTEXT:
Before processing individual sentences, analyze the entire input to identify:

1. MAIN SUBJECT/TOPIC: What is this document primarily about?
   - Look for: document titles, section headings, repeated themes, central entities
   - Identify: industry, domain, product, event, research area, geographic focus

2. CONTEXTUAL QUALIFIERS that define scope:
   - Geographic: country, region, city, market
   - Temporal: year, quarter, time period, date range
   - Demographic: population segment, age group, profession, user type
   - Institutional: organization, company, department, study name
   - Categorical: industry sector, product category, service type

3. SCOPE INDICATORS that narrow the subject:
   - Who is the target population or entity being measured?
   - Where is this occurring or applicable?
   - When is this data from or relevant to?
   - What specific domain or category does this fall under?

MANDATORY ENRICHMENT TASKS:

1. **Enrich vague subjects with document topic**:
   When data lacks explicit subject (percentages, statistics, counts without clear reference):
   - Identify what entity/population the data describes using document context
   - Add the full subject specification including relevant qualifiers
   - Ensure geographic, temporal, or categorical context is included

2. **Resolve ALL pronouns and vague references**:
   Replace "he", "she", "it", "they", "this", "that", "the content", "the product", "users", "individuals" with:
   - Specific entity names from document
   - Full subject specification with qualifiers

3. **Add temporal context systematically**:
   If dates, years, quarters, or timeframes appear in surrounding text, include them in relevant sentences

4. **Convert structured data with full context**:
   Transform tables, bullets, key-values into complete prose sentences where each includes:
   - Explicit subject (what entity/topic)
   - Relevant qualifiers (location, timeframe, source)
   - Complete predicate (action or measurement)

5. **Expand acronyms and abbreviations** if definitions provided in text

6. **Preserve factual content only**:
   - Keep: facts ABOUT capabilities, features, measurements, relationships
   - Remove: procedural instructions (HOW TO USE), calls to action

SELF-SUFFICIENCY VERIFICATION:
For every output sentence, test:
- Can someone verify this through research without reading anything else?
- Does it explicitly state WHAT is being measured/claimed?
- Does it specify WHO/WHAT entity or population?
- Does it include WHERE (location) if geographically specific?
- Does it include WHEN (timeframe) if temporally specific?
- If answer is NO to any → enrich with missing context from document

UNIVERSAL PRINCIPLE:
Treat the document topic and qualifiers as essential context that must be embedded into every sentence containing data or claims. A fact-checker receiving one sentence should understand its full scope without needing to read the document title or other sentences.

OUTPUT: Complete prose where every sentence is independently fact-checkable with all necessary context embedded.
"""


async def _single_contextualization_attempt(
    text: str, llm: BaseChatModel
) -> Tuple[bool, str]:
    """Make a single contextualization attempt.

    Args:
        text: Raw input text
        llm: LLM instance

    Returns:
        (success, contextualized_text)
    """
    messages = [
        ("system", CONTEXTUALIZATION_SYSTEM_PROMPT),
        ("human", f"Text to contextualize:\n\n{text}")
    ]

    response = await call_llm_with_structured_output(
        llm=llm,
        output_class=ContextualizationOutput,
        messages=messages,
        context_desc=f"contextualization of text ({len(text)} chars)",
    )

    if not response or not response.contextualized_text:
        return False, ""

    return True, response.contextualized_text.strip()


def _create_contextualized_result(contextualized_text: str, original_text: str) -> str:
    """Package the contextualized result.
    
    Args:
        contextualized_text: The processed text from LLM
        original_text: The original input text (unused but required by voting interface)
        
    Returns:
        The contextualized text
    """
    return contextualized_text


async def contextualization_node(state: ExtractionState) -> dict[str, Any]:
    """
    Contextualization node that performs BOTH format conversion AND reference resolution.
    
    Replaces the sequential preprocessing → disambiguation pipeline with a single step.
    
    Args:
        state: Current extraction state with answer_text
        
    Returns:
        Dictionary with preprocessed_text key
    """
    original_text = state.answer_text
    
    if not original_text or len(original_text.strip()) < 20:
        logger.warning("Text too short for contextualization, using as-is")
        return {"preprocessed_text": original_text}
    
    logger.info(
        f"Contextualizing text ({len(original_text)} chars) - "
        f"converting formats AND resolving references in one step"
    )
    
    try:
        # Use voting with 2 completions for quality
        llm = get_llm(completions=COMPLETIONS, stage="claim_extractor.contextualization")
        
        results = await process_with_voting(
            items=[original_text],
            processor=lambda txt, llm_inst: _single_contextualization_attempt(txt, llm_inst),
            llm=llm,
            completions=COMPLETIONS,
            min_successes=MIN_SUCCESSES,
            result_factory=_create_contextualized_result,
            description="text contextualization",
        )
        
        if results and len(results) > 0:
            contextualized_text = results[0]
            logger.info(
                f"Contextualized text: {len(original_text)} → {len(contextualized_text)} chars"
            )
            logger.debug(f"Preview: {contextualized_text[:200]}...")
            return {"preprocessed_text": contextualized_text}
        else:
            logger.warning("Contextualization produced no results, using original")
            return {"preprocessed_text": original_text}
        
    except Exception as e:
        logger.error(f"Error in contextualization: {e}, using original text")
        return {"preprocessed_text": original_text}
