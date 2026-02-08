"""
Insufficient Info Reason Analyzer

Provides context-aware categorization and explanations for NOT_ENOUGH_INFO verdicts.
Helps users understand why verification failed and suggests alternative approaches.
"""

import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Taxonomy of insufficient info reasons
INSUFFICIENT_INFO_REASONS = {
    "PROPRIETARY_DATA": {
        "label": "Proprietary/Paywalled Data",
        "explanation_template": "This claim requires access to paid or proprietary data sources that are not publicly searchable. The specific data mentioned (like keyword search volumes, paid analytics, or subscription-based research) is only available through specialized paid tools or subscriptions.",
        "patterns": [
            r'\b\d+[,\d]*\s*(searches?|search volume|monthly searches?)\b',
            r'\b(google\s*(ads|keyword\s*planner)|semrush|ahrefs|moz)\b',
            r'\bkeyword\s*(data|research|analysis)\b',
            r'\bsearch\s*volume\s*data\b',
            r'\bpaid\s*(tool|analytics|subscription)\b',
            r'\b(cpc|cost\s*per\s*click|keyword\s*difficulty)\b',
        ],
        "keywords": ["search volume", "monthly searches", "keyword data", "google ads", "semrush", "ahrefs", "keyword planner", "paid tool", "subscription data", "analytics platform"],
        "suggestions": [
            "Try accessing Google Keyword Planner (requires Google Ads account)",
            "Check if your organization has SEMrush, Ahrefs, or similar SEO tool subscriptions",
            "Consider rephrasing as general statements (e.g., 'high search volume' instead of exact numbers)",
            "Look for publicly available trend data that shows relative popularity without exact figures",
            "Verify if the claim source has shared their methodology or raw data publicly"
        ]
    },
    
    "TOO_SPECIFIC": {
        "label": "Overly Specific/Exact Figures",
        "explanation_template": "This claim contains very specific numbers, percentages, or exact figures that are difficult to verify through public sources. While the general trend or concept may be verifiable, the precise values stated require access to specific research studies, proprietary databases, or detailed reports that aren't freely available.",
        "patterns": [
            r'\b\d+\.\d+%\b',  # Exact percentages with decimals
            r'\bexactly\s+\d+\b',
            r'\b\d+[,\d]*\s*(dollars?|rupees?|USD|INR)\s*per\b',
            r'\bincreased?\s+by\s+\d+\.\d+%\b',
        ],
        "keywords": ["exact figure", "precise number", "specific percentage", "detailed breakdown", "exact amount"],
        "suggestions": [
            "Look for the original research report or study that contains this data",
            "Check if there are publicly available summaries or press releases with the key findings",
            "Consider verifying the general trend rather than the exact figure",
            "Contact the organization that published the original research",
            "Search for similar studies that might corroborate the general magnitude"
        ]
    },
    
    "REGIONAL_DATA": {
        "label": "Regional/Country-Specific Data",
        "explanation_template": "This claim pertains to specific regional, country-level, or local market data that may not be well-covered in international or general public sources. Regional data often requires access to local reports, government databases, or region-specific research that might not be indexed in standard search engines.",
        "patterns": [
            r'\b(india|indian|delhi|mumbai|bangalore|hyderabad)\b',
            r'\bin\s+(india|china|japan|korea|brazil|mexico)\b',
            r'\b(asian|european|african|latin\s*american)\s+(market|region|countries?)\b',
            r'\blocal\s+(market|data|statistics)\b',
        ],
        "keywords": ["in India", "Indian market", "local data", "regional statistics", "country-specific", "market in", "specific to"],
        "suggestions": [
            "Check government statistical agencies or ministries from the specific country/region",
            "Look for market research firms specializing in that geographic area",
            "Search using local language terms or regional search engines",
            "Check international organizations' regional reports (World Bank, IMF, UN agencies)",
            "Contact local universities or research institutions that study the region"
        ]
    },
    
    "RECENT_DATA": {
        "label": "Very Recent/Current Data",
        "explanation_template": "This claim references very recent information (from the last few months or current year) that may not yet be widely published, indexed, or publicly available. Recent data often has a lag time before it appears in searchable databases, academic publications, or comprehensive reports.",
        "patterns": [
            r'\b(2025|2026)\b',
            r'\b(this\s+year|current\s+year|recently|latest)\b',
            r'\b(last\s+few\s+months|past\s+quarter)\b',
            r'\b(as\s+of\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+20(2[5-6]))\b',
        ],
        "keywords": ["2025", "2026", "this year", "current year", "recently", "latest", "as of 2025", "in 2026"],
        "suggestions": [
            "Wait for official reports or publications to be released (there's often a 1-6 month lag)",
            "Check press releases or announcements from the relevant organizations",
            "Look for real-time data dashboards if available for this topic",
            "Monitor industry news sites and trade publications",
            "Consider whether preliminary or estimated figures would be acceptable"
        ]
    },
    
    "INTERNAL_DATA": {
        "label": "Internal/Unpublished Research",
        "explanation_template": "This claim appears to reference internal company data, proprietary research, unpublished studies, or confidential information that is not publicly available. Such data is typically only accessible to employees, stakeholders, or subscribers of specific services.",
        "patterns": [
            r'\b(internal\s+(data|research|study|report|analysis))\b',
            r'\b(proprietary|confidential|private)\s+(data|research)\b',
            r'\b(unpublished|not\s+yet\s+published)\b',
            r'\b(company\s+internal|our\s+(research|data|findings))\b',
        ],
        "keywords": ["internal data", "proprietary research", "unpublished study", "confidential information", "private data", "company internal"],
        "suggestions": [
            "Contact the organization directly to request access or a public summary",
            "Check if any findings have been shared in press releases or blog posts",
            "Look for similar publicly available research on the same topic",
            "Ask if there are any published case studies or white papers based on this data",
            "Consider whether third-party analyses or reviews exist"
        ]
    },
    
    "CONTRADICTORY_SOURCES": {
        "label": "Contradictory Sources",
        "explanation_template": "Multiple sources provide conflicting information about this claim, making it impossible to definitively verify. The available evidence presents different numbers, dates, or facts that contradict each other, requiring deeper investigation or access to primary sources to resolve the discrepancy.",
        "patterns": [
            # This pattern is harder to detect automatically - mainly identified through context
        ],
        "keywords": ["contradictory", "conflicting", "different sources", "varies by source", "disputed"],
        "suggestions": [
            "Look for the most authoritative or primary source (original research, government data, etc.)",
            "Check the dates of conflicting sources - more recent may be more accurate",
            "Investigate the methodology used by different sources",
            "Consider whether the contradiction is due to different definitions or measurement methods",
            "Acknowledge the uncertainty and present multiple perspectives if appropriate"
        ]
    },
    
    "SOURCE_NOT_ACCESSIBLE": {
        "label": "Cited Source Not Accessible",
        "explanation_template": "The claim cites or references a specific source (research paper, report, article) that is behind a paywall, requires subscription access, has been removed, or is otherwise not publicly accessible. While the source exists, we cannot access its content to verify the claim.",
        "patterns": [
            r'\b(according\s+to|cited\s+in|from|source:)\b.*\b(journal|study|report|paper)\b',
            r'\b(paywall|subscription\s+required|access\s+restricted)\b',
            r'\b(doi:|arxiv:|published\s+in)\b',
        ],
        "keywords": ["according to", "cited in", "published in", "journal article", "research paper", "paywall", "subscription required"],
        "suggestions": [
            "Check if the author or institution has made a pre-print or public version available",
            "Look for press coverage or summaries of the research",
            "Try accessing through academic databases if you have institutional access",
            "Search for the authors' other publicly available work on the same topic",
            "Contact the authors directly - many are willing to share their work"
        ]
    },
    
    "GENERAL_UNAVAILABLE": {
        "label": "Information Not Publicly Available",
        "explanation_template": "The specific information in this claim is not currently available through public web sources. This could be because it's too niche, not well-documented online, requires specialized databases, or hasn't been digitized or published in accessible formats.",
        "patterns": [
            # Default/fallback category
        ],
        "keywords": [],
        "suggestions": [
            "Consult specialized databases or libraries relevant to this topic",
            "Contact subject matter experts or organizations in this field",
            "Check if there are alternative ways to verify the underlying concept",
            "Consider whether the claim needs this level of specificity or if a general statement would suffice",
            "Look for related or adjacent information that might provide indirect verification"
        ]
    }
}


def analyze_insufficient_info(
    claim: str,
    evidence_list: List[Dict],
    search_queries: List[str],
    verdict_reasoning: str
) -> Tuple[str, str, List[str]]:
    """
    Analyze why a claim couldn't be verified and categorize the reason.
    
    Args:
        claim: The claim that couldn't be verified
        evidence_list: List of evidence items retrieved (may be empty or irrelevant)
        search_queries: Queries used to search for evidence
        verdict_reasoning: The reasoning for the NOT_ENOUGH_INFO verdict
        
    Returns:
        Tuple of (reason_category, detailed_explanation, suggestions_list)
    """
    
    # Normalize claim for pattern matching
    claim_lower = claim.lower()
    
    # Score each category based on pattern matching
    category_scores = {}
    
    for category, config in INSUFFICIENT_INFO_REASONS.items():
        score = 0
        
        # Check regex patterns
        for pattern in config["patterns"]:
            if re.search(pattern, claim_lower, re.IGNORECASE):
                score += 2
        
        # Check keywords
        for keyword in config["keywords"]:
            if keyword.lower() in claim_lower:
                score += 1
        
        category_scores[category] = score
    
    # Additional context-based scoring
    
    # Check for proprietary data indicators
    if any(term in claim_lower for term in ["search volume", "monthly searches", "keyword"]):
        category_scores["PROPRIETARY_DATA"] = category_scores.get("PROPRIETARY_DATA", 0) + 3
    
    # Check for specific numbers (too specific)
    if re.search(r'\b\d{3,}[,\d]*\b', claim):  # Large specific numbers
        category_scores["TOO_SPECIFIC"] = category_scores.get("TOO_SPECIFIC", 0) + 1
    
    # Check for regional indicators
    if any(term in claim_lower for term in ["india", "indian", "asia", "regional", "local"]):
        category_scores["REGIONAL_DATA"] = category_scores.get("REGIONAL_DATA", 0) + 2
    
    # Check for recency
    current_year = datetime.now().year
    if str(current_year) in claim or str(current_year - 1) in claim:
        category_scores["RECENT_DATA"] = category_scores.get("RECENT_DATA", 0) + 1
    
    # Check evidence count - if no evidence found at all, might be too specific or unavailable
    if not evidence_list or len(evidence_list) == 0:
        category_scores["TOO_SPECIFIC"] = category_scores.get("TOO_SPECIFIC", 0) + 1
        category_scores["GENERAL_UNAVAILABLE"] = category_scores.get("GENERAL_UNAVAILABLE", 0) + 1
    
    # Check if evidence exists but doesn't contain the specific data
    if evidence_list and len(evidence_list) > 0:
        if any(term in verdict_reasoning.lower() for term in ["does not contain specific", "does not provide", "lack specific"]):
            category_scores["TOO_SPECIFIC"] = category_scores.get("TOO_SPECIFIC", 0) + 2
    
    # Select the category with the highest score
    if max(category_scores.values()) > 0:
        selected_category = max(category_scores, key=category_scores.get)
    else:
        # Default to GENERAL_UNAVAILABLE if no patterns matched
        selected_category = "GENERAL_UNAVAILABLE"
    
    # Build the explanation
    config = INSUFFICIENT_INFO_REASONS[selected_category]
    
    # Start with the template
    explanation = config["explanation_template"]
    
    # Add context-specific details
    if selected_category == "PROPRIETARY_DATA":
        # Identify specific tools mentioned or implied
        tools = []
        if "search volume" in claim_lower or "monthly search" in claim_lower:
            tools.extend(["Google Keyword Planner", "SEMrush", "Ahrefs"])
        if tools:
            explanation += f" Common tools for this type of data include: {', '.join(tools)}."
    
    elif selected_category == "TOO_SPECIFIC":
        # Mention the specific numbers
        numbers = re.findall(r'\b\d+[,\d]*\b', claim)
        if numbers:
            explanation += f" The claim references specific figures ({', '.join(numbers[:3])}) that require access to detailed source data."
    
    elif selected_category == "REGIONAL_DATA":
        # Identify the region
        regions = []
        if "india" in claim_lower or "indian" in claim_lower:
            regions.append("India")
        if regions:
            explanation += f" This data is specific to {', '.join(regions)}, which may require local or regional sources."
    
    elif selected_category == "RECENT_DATA":
        years = re.findall(r'\b20(2[5-6])\b', claim)
        if years:
            explanation += f" The claim references {', '.join(set(years))}, which is very recent and may not yet be widely published."
    
    # Add information about search attempts
    if search_queries:
        explanation += f" We attempted {len(search_queries)} search quer{'y' if len(search_queries) == 1 else 'ies'} but could not find publicly accessible sources with this specific information."
    
    # Get suggestions
    suggestions = config["suggestions"].copy()
    
    return selected_category, explanation, suggestions


def get_reason_label(category: str) -> str:
    """Get the user-friendly label for a reason category."""
    return INSUFFICIENT_INFO_REASONS.get(category, {}).get("label", "Information Not Available")


def get_short_explanation(category: str) -> str:
    """Get a brief one-line explanation for a reason category."""
    explanations = {
        "PROPRIETARY_DATA": "Requires paid/subscription data sources",
        "TOO_SPECIFIC": "Exact figures not in public sources",
        "REGIONAL_DATA": "Region-specific data not widely available",
        "RECENT_DATA": "Too recent to be published/indexed",
        "INTERNAL_DATA": "Internal/unpublished research",
        "CONTRADICTORY_SOURCES": "Conflicting information in sources",
        "SOURCE_NOT_ACCESSIBLE": "Cited source behind paywall",
        "GENERAL_UNAVAILABLE": "Not found in public sources"
    }
    return explanations.get(category, "Information not publicly available")
