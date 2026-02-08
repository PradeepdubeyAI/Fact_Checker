import logging

from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph

from claim_extractor.nodes import (
    decomposition_node,
    disambiguation_node,
    selection_node,
    sentence_splitter_node,
    validation_node,
)
from claim_extractor.nodes.preprocessing import preprocess_text_node
from claim_extractor.nodes.contextualization import contextualization_node
from claim_extractor.schemas import State

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_graph(use_optimized_pipeline: bool = True, aggressive_mode: bool = False) -> CompiledStateGraph:
    """Set up the claim extraction workflow graph.

    Args:
        use_optimized_pipeline: If True, use Phase 2 optimized pipeline (merged contextualization).
                               If False, use original pipeline (preprocessing → disambiguation).
        aggressive_mode: If True, use Phase 3 ultra-optimized pipeline (NO selection step).
                        Requires use_optimized_pipeline=True.

    Pipeline modes:
    
    ORIGINAL (Phase 1 - 136 calls):
    preprocessing → sentence_splitter → selection → disambiguation → decomposition → validation
    
    OPTIMIZED (Phase 2 - 76 calls, 44% reduction):
    contextualization → sentence_splitter → selection → decomposition → validation
    (Merges preprocessing + disambiguation)
    
    AGGRESSIVE (Phase 3 - 60 calls, 56% reduction):
    contextualization → sentence_splitter → decomposition → validation
    (Also removes selection - decomposition filters instead)
    """
    workflow = StateGraph(State)

    if aggressive_mode:
        if not use_optimized_pipeline:
            raise ValueError("aggressive_mode requires use_optimized_pipeline=True")
        
        logger.info("Using AGGRESSIVE pipeline (Phase 3): Contextualization + NO Selection step")
        # Add nodes for aggressive pipeline
        workflow.add_node("contextualization", contextualization_node)
        workflow.add_node("sentence_splitter", sentence_splitter_node)
        workflow.add_node("decomposition", decomposition_node)
        workflow.add_node("validation", validation_node)

        # Set entry point
        workflow.set_entry_point("contextualization")

        # Connect the nodes in sequence (NO selection, NO disambiguation)
        workflow.add_edge("contextualization", "sentence_splitter")
        workflow.add_edge("sentence_splitter", "decomposition")  # Direct to decomposition
        workflow.add_edge("decomposition", "validation")
        
    elif use_optimized_pipeline:
        logger.info("Using OPTIMIZED pipeline (Phase 2): Contextualization merges preprocessing + disambiguation, selection feeds decomposition")
        # Add nodes for optimized pipeline
        workflow.add_node("contextualization", contextualization_node)
        workflow.add_node("sentence_splitter", sentence_splitter_node)
        workflow.add_node("selection", selection_node)
        workflow.add_node("decomposition", decomposition_node)
        workflow.add_node("validation", validation_node)

        # Set entry point
        workflow.set_entry_point("contextualization")

        # Connect the nodes in sequence
        # Contextualization does BOTH preprocessing AND disambiguation
        # Selection filters to verifiable content
        # Decomposition breaks into atomic claims
        workflow.add_edge("contextualization", "sentence_splitter")
        workflow.add_edge("sentence_splitter", "selection")
        workflow.add_edge("selection", "decomposition")
        workflow.add_edge("decomposition", "validation")
    else:
        logger.info("Using ORIGINAL pipeline: Separate preprocessing → disambiguation steps")
        # Add nodes for original pipeline
        workflow.add_node("preprocessing", preprocess_text_node)
        workflow.add_node("sentence_splitter", sentence_splitter_node)
        workflow.add_node("selection", selection_node)
        workflow.add_node("disambiguation", disambiguation_node)
        workflow.add_node("decomposition", decomposition_node)
        workflow.add_node("validation", validation_node)

        # Set entry point
        workflow.set_entry_point("preprocessing")

        # Connect the nodes in sequence (WITH disambiguation step)
        workflow.add_edge("preprocessing", "sentence_splitter")
        workflow.add_edge("sentence_splitter", "selection")
        workflow.add_edge("selection", "disambiguation")
        workflow.add_edge("disambiguation", "decomposition")
        workflow.add_edge("decomposition", "validation")

    # Set finish point
    workflow.set_finish_point("validation")

    return workflow.compile()


# Default to optimized pipeline (Phase 2) - change aggressive_mode=True for Phase 3
graph = create_graph(use_optimized_pipeline=True, aggressive_mode=False)
