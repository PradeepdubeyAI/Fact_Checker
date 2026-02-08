"""Node configuration settings.

Contains settings for the pipeline nodes.
"""

# Node settings
PREPROCESSING_CONFIG = {
    "temperature": 0.0,  # Set to 0 for maximum determinism and to prevent hallucinations
}

# PHASE 2: Merged contextualization config (replaces preprocessing + disambiguation)
CONTEXT_CONFIG = {
    "completions": 2,  # Keep quality with 2 completions
    "min_successes": 2,
    "temperature": 0.2,  # Balanced for reasoning
}

SELECTION_CONFIG = {
    "completions": 1,  # OPTIMIZED: Reduced from 3 (Decomposition validates anyway)
    "min_successes": 1,
    "temperature": 0.2,  # Higher temp for diverse judgments
}

DISAMBIGUATION_CONFIG = {
    "completions": 2,  # OPTIMIZED: Reduced from 3 (keep quality with 2)
    "min_successes": 2,
    "temperature": 0.2,  # Higher temp for diverse judgments
}

DECOMPOSITION_CONFIG = {
    "completions": 1,
    "min_successes": 1,
    "temperature": 0.0,  # Zero temp for consistent results
}

VALIDATION_CONFIG = {
    "enabled": True,  # OPTIMIZED: Set to False to skip validation step
    "temperature": 0.0,  # Zero temp for consistent results
}

# Context windows
CONTEXT_WINDOWS = {
    "selection": {
        "preceding_sentences": 5,
        "following_sentences": 5,
    },
    "disambiguation": {
        "preceding_sentences": 5,
        "following_sentences": 0,  # No following sentences here
    },
    "decomposition": {
        "preceding_sentences": 5,
        "following_sentences": 0,  # No following sentences here
    },
}
