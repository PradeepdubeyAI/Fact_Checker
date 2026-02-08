"""
Text preprocessing node - converts raw/structured input into claim-ready format.
Handles tables, lists, bullet points, and converts them to complete declarative sentences.
"""

import logging
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage
from utils import get_llm
from claim_extractor.schemas import ExtractionState

# Import prompts
from claim_extractor.prompts import (
    PREPROCESSING_SYSTEM_PROMPT,
    PREPROCESSING_HUMAN_PROMPT,
)

logger = logging.getLogger(__name__)


async def preprocess_text_node(state: ExtractionState) -> dict[str, Any]:
    """
    Preprocessing node that converts raw text into claim-ready format.
    
    Takes any input format (tables, lists, bullet points, paragraphs) and
    converts structured data into complete declarative sentences.
    
    Args:
        state: Current extraction state with answer_text
        
    Returns:
        Dictionary with preprocessed_text key
    """
    original_text = state.answer_text
    
    if not original_text or len(original_text.strip()) < 20:
        logger.warning("Text too short for preprocessing, using as-is")
        return {"preprocessed_text": original_text}
    
    logger.info(f"Preprocessing text ({len(original_text)} chars) - always run for universal context enhancement")
    
    try:
        llm = get_llm()
        
        messages = [
            SystemMessage(content=PREPROCESSING_SYSTEM_PROMPT),
            HumanMessage(content=PREPROCESSING_HUMAN_PROMPT.format(text=original_text))
        ]
        
        # Get LLM response
        response = await llm.ainvoke(messages)
        preprocessed_text = response.content.strip()
        
        logger.info(f"Preprocessed text: {len(original_text)} → {len(preprocessed_text)} chars")
        logger.debug(f"Preview: {preprocessed_text[:200]}...")
        
        return {"preprocessed_text": preprocessed_text}
        
    except Exception as e:
        logger.error(f"Error in text preprocessing: {e}, using original text")
        return {"preprocessed_text": original_text}
