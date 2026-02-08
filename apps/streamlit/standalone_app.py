"""
ClaimeAI - Standalone Streamlit App
A complete fact-checking app that runs without LangGraph backend
"""

import streamlit as st
import os
import sys
import asyncio
import logging
import tempfile
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv

# Setup logger
logger = logging.getLogger(__name__)

# Add the agent directory to Python path
agent_path = os.path.join(os.path.dirname(__file__), '..', 'agent')
sys.path.insert(0, agent_path)

# Load environment variables
load_dotenv(os.path.join(agent_path, '.env'))

# Import Excel export module
try:
    from export_excel import generate_excel_report
    EXCEL_EXPORT_AVAILABLE = True
except ImportError:
    logger.warning("Excel export module not available")
    EXCEL_EXPORT_AVAILABLE = False

# Import the fact checker modules
try:
    # Import utilities first
    from utils.metrics import get_metrics_tracker, reset_metrics
    # Import agent creation functions (lazy load graphs when needed)
    from fact_checker.agent import create_graph
    from claim_extractor.agent import create_graph as create_claim_extractor_graph
    from claim_verifier.agent import create_graph as create_claim_verifier_graph
except ImportError as e:
    st.error(f"Could not import fact checker modules. Make sure dependencies are installed: {e}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="ClaimeAI - Fact Checker",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .claim-card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border-left: 5px solid;
    }
    .claim-supported {
        background-color: #d4edda;
        border-color: #28a745;
    }
    .claim-refuted {
        background-color: #f8d7da;
        border-color: #dc3545;
    }
    .claim-insufficient {
        background-color: #fff3cd;
        border-color: #ffc107;
    }
    .stProgress > div > div > div > div {
        background-color: #1f77b4;
    }
    </style>
    """, unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables"""
    if 'results' not in st.session_state:
        st.session_state.results = None
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'metrics_summary' not in st.session_state:
        st.session_state.metrics_summary = None
    if 'custom_tavily_key' not in st.session_state:
        st.session_state.custom_tavily_key = ''
    if 'use_custom_tavily' not in st.session_state:
        st.session_state.use_custom_tavily = False


def run_claim_extraction(text: str) -> Dict[str, Any]:
    """Extract claims from text without verification"""
    try:
        # Reset metrics for this run
        reset_metrics()
        
        # Create claim extractor graph
        claim_extractor_graph = create_claim_extractor_graph()
        
        # Create input state - claim extractor expects "answer_text" field
        input_state = {
            "answer_text": text
        }
        
        # Run the claim extractor graph
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(claim_extractor_graph.ainvoke(input_state))
        loop.close()
        
        # Log metrics summary
        tracker = get_metrics_tracker()
        logger.info("\n" + "="*50)
        logger.info("Claim Extraction Complete")
        tracker.log_summary()
        logger.info("="*50 + "\n")
        
        # Save metrics to session state
        st.session_state.metrics_summary = tracker.get_summary()
        
        # Return extracted claims
        return {
            "extracted_claims": result.get("validated_claims", []),
            "mode": "extraction_only"
        }
        
    except Exception as e:
        logger.error(f"Error in claim extraction: {str(e)}")
        st.error(f"Error: {str(e)}")
        return None


def run_single_fact_check(claim: str) -> Dict[str, Any]:
    """Verify a single fact directly without claim extraction"""
    try:
        # Reset metrics for this run
        reset_metrics()
        
        # Import claim verifier and schemas
        from claim_verifier.agent import graph as claim_verifier_graph
        from claim_extractor.schemas import ValidatedClaim
        
        # Create a ValidatedClaim object from the input string
        validated_claim = ValidatedClaim(
            claim_text=claim,
            is_complete_declarative=True,
            disambiguated_sentence=claim,
            original_sentence=claim,
            original_index=0
        )
        
        # Create input state for verifier
        input_state = {
            "claim": validated_claim
        }
        
        # Run the claim verifier graph directly
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(claim_verifier_graph.ainvoke(input_state))
        loop.close()
        
        # Log metrics summary
        tracker = get_metrics_tracker()
        logger.info("\n" + "="*50)
        logger.info("Single Fact Verification Complete")
        tracker.log_summary()
        logger.info("="*50 + "\n")
        
        # Save metrics to session state
        st.session_state.metrics_summary = tracker.get_summary()
        
        # Return in expected format
        return {
            "verified_claims": [result["verdict"]],
            "mode": "single_fact"
        }
        
    except Exception as e:
        logger.error(f"Error in single fact verification: {str(e)}")
        st.error(f"Error: {str(e)}")
        return None


def run_fact_check(question: str, answer: str) -> Dict[str, Any]:
    """Run the fact-checking process directly"""
    try:
        # Reset metrics for this run
        reset_metrics()
        
        # Create fact checker graph
        fact_checker_graph = create_graph()
        
        # Create input state
        input_state = {
            "answer": answer
        }
        
        # Run the fact checker graph asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(fact_checker_graph.ainvoke(input_state))
        loop.close()
        
        # Log metrics summary
        tracker = get_metrics_tracker()
        tracker.log_summary()
        
        # Save metrics to session state
        st.session_state.metrics_summary = tracker.get_summary()
        
        return result
        
    except Exception as e:
        st.error(f"Error during fact checking: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None


# ============================================================================
# VIDEO FACT-CHECKING FUNCTIONS
# ============================================================================

def extract_audio_from_video(video_file) -> str:
    """Extract audio track from uploaded video file"""
    try:
        # Import for moviepy v2.x (different from v1.x)
        try:
            from moviepy.editor import VideoFileClip
        except ImportError:
            # Fallback for newer moviepy versions
            from moviepy import VideoFileClip
        
        # Save uploaded video to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_video:
            tmp_video.write(video_file.read())
            video_path = tmp_video.name
        
        # Extract audio with compression to stay under Whisper's 25MB limit
        video = VideoFileClip(video_path)
        audio_path = video_path.replace(".mp4", ".mp3")
        
        # Use MP3 format with lower bitrate (64k) to reduce file size
        # This ensures we stay under Whisper API's 25MB limit
        video.audio.write_audiofile(
            audio_path, 
            codec='libmp3lame',
            bitrate='64k',
            logger=None
        )
        video.close()
        
        # Clean up video file
        os.unlink(video_path)
        
        return audio_path
        
    except Exception as e:
        logger.error(f"Error extracting audio: {str(e)}")
        raise

def transcribe_audio_whisper(audio_path: str) -> str:
    """Transcribe audio using OpenAI Whisper API"""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        with open(audio_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        # Clean up audio file
        os.unlink(audio_path)
        
        return transcript
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        raise


def detect_language(text: str) -> str:
    """Detect the language of the given text"""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a language detection expert. Identify the primary language of the given text. Respond with ONLY the language name (e.g., 'English', 'Hindi', 'Spanish', 'French', etc.). Be concise."
                },
                {
                    "role": "user",
                    "content": f"What language is this text in?\n\n{text[:500]}"
                }
            ],
            temperature=0.1
        )
        
        language = response.choices[0].message.content.strip()
        logger.info(f"Detected language: {language}")
        return language
        
    except Exception as e:
        logger.error(f"Error detecting language: {str(e)}")
        return "English"


def translate_to_english(text: str) -> str:
    """Translate non-English text to English for better claim extraction"""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional translator. Translate the given text to English. Preserve all facts, numbers, names, dates, and specific details accurately. If the text is already in English, return it unchanged."
                },
                {
                    "role": "user",
                    "content": f"Translate this text to English:\n\n{text}"
                }
            ],
            temperature=0.1
        )
        
        translation = response.choices[0].message.content.strip()
        logger.info(f"Translation completed: {len(text)} chars -> {len(translation)} chars")
        return translation
        
    except Exception as e:
        logger.error(f"Error translating text: {str(e)}")
        # If translation fails, return original text
        return text


def extract_claims_from_transcript(transcript: str) -> List[Dict]:
    """Extract claims from transcript using existing claim extractor"""
    try:
        # Reset metrics
        reset_metrics()
        
        # Translate to English for better claim extraction
        logger.info("Translating transcript to English for improved accuracy...")
        english_transcript = translate_to_english(transcript)
        
        # Store both versions in session state for display
        if 'video_original_transcript' not in st.session_state:
            st.session_state.video_original_transcript = transcript
        if 'video_english_transcript' not in st.session_state:
            st.session_state.video_english_transcript = english_transcript
        
        # Create claim extractor graph
        claim_extractor_graph = create_claim_extractor_graph()
        
        # Create input state - use English translation for claim extraction
        input_state = {"answer_text": english_transcript}
        
        # Run claim extraction
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(claim_extractor_graph.ainvoke(input_state))
        loop.close()
        
        # Convert to UI-friendly format
        claims = []
        for idx, claim in enumerate(result.get("validated_claims", [])):
            claims.append({
                "id": idx,
                "text": claim.claim_text if hasattr(claim, 'claim_text') else str(claim),
                "original": claim.original_sentence if hasattr(claim, 'original_sentence') else '',
                "claim_object": claim,
                "selected": True  # Default to selected
            })
        
        return claims
        
    except Exception as e:
        logger.error(f"Error extracting claims from transcript: {str(e)}")
        raise


def verify_selected_claims(claims: List, extracted_claims: List = None) -> Dict[str, Any]:
    """Verify only the selected claims"""
    try:
        # NOTE: Don't reset metrics here - we want cumulative cost (extraction + verification)
        # Metrics were already reset at the start of extraction
        
        # Create claim verifier graph
        claim_verifier_graph = create_claim_verifier_graph()
        
        async def verify_claim(claim):
            """Verify single claim"""
            result = await claim_verifier_graph.ainvoke({"claim": claim})
            return result["verdict"]
        
        # Run verification in parallel
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        tasks = [verify_claim(claim) for claim in claims]
        verdicts = loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
        
        loop.close()
        
        # Log metrics
        tracker = get_metrics_tracker()
        logger.info("\n" + "="*50)
        logger.info(f"Fact-Check Complete - Verified {len(claims)} claims")
        logger.info("📊 Cost shown below includes BOTH extraction + verification")
        tracker.log_summary()
        logger.info("="*50 + "\n")
        
        # Get final metrics summary with Tavily calls
        final_metrics = tracker.get_summary()
        logger.info(f"Final Tavily API calls tracked: {final_metrics.get('tavily_calls', 0)}")
        
        # Save metrics to session state
        st.session_state.metrics_summary = final_metrics
        
        return {
            "extracted_claims": extracted_claims if extracted_claims else claims,
            "verified_claims": verdicts,
            "verification_results": verdicts,
            "mode": "video"
        }
        
    except Exception as e:
        logger.error(f"Error verifying claims: {str(e)}")
        raise


def render_claim_card(claim: Any, index: int):
    """Render a claim card with verdict and evidence"""
    # Handle both dict and Pydantic Verdict object
    if isinstance(claim, dict):
        claim_text = claim.get('claim_text', claim.get('claim', ''))
        verdict = str(claim.get('result', claim.get('verdict', 'INSUFFICIENT_EVIDENCE')))
        evidence_list = claim.get('sources', claim.get('evidence', []))
        reasoning = claim.get('reasoning', '')
        corrected_claim = claim.get('corrected_claim', None)
        detailed_explanation = claim.get('detailed_explanation', '')
        insufficient_info_reason = claim.get('insufficient_info_reason', None)
        insufficient_info_explanation = claim.get('insufficient_info_explanation', None)
        insufficient_info_suggestions = claim.get('insufficient_info_suggestions', None)
    else:
        # Pydantic Verdict object
        claim_text = claim.claim_text if hasattr(claim, 'claim_text') else ''
        verdict = str(claim.result) if hasattr(claim, 'result') else 'INSUFFICIENT_EVIDENCE'
        evidence_list = claim.sources if hasattr(claim, 'sources') else []
        reasoning = claim.reasoning if hasattr(claim, 'reasoning') else ''
        corrected_claim = claim.corrected_claim if hasattr(claim, 'corrected_claim') else None
        detailed_explanation = claim.detailed_explanation if hasattr(claim, 'detailed_explanation') else ''
        insufficient_info_reason = claim.insufficient_info_reason if hasattr(claim, 'insufficient_info_reason') else None
        insufficient_info_explanation = claim.insufficient_info_explanation if hasattr(claim, 'insufficient_info_explanation') else None
        insufficient_info_suggestions = claim.insufficient_info_suggestions if hasattr(claim, 'insufficient_info_suggestions') else None
    
    # Determine card style - handle enum format like "VerificationResult.SUPPORTED"
    if 'SUPPORTED' in verdict:
        emoji = '✅'
        color = 'green'
        verdict_display = 'SUPPORTED'
    elif 'REFUTED' in verdict:
        emoji = '❌'
        color = 'red'
        verdict_display = 'REFUTED'
    else:
        emoji = '⚠️'
        color = 'orange'
        verdict_display = 'INSUFFICIENT_EVIDENCE'
    
    # Render claim card
    with st.expander(f"{emoji} **Claim {index + 1}:** {claim_text[:100]}{'...' if len(claim_text) > 100 else ''}", expanded=False):
        st.markdown(f"**Full Claim:**")
        st.write(claim_text)
        
        st.markdown(f"**Verdict:** :{color}[**{verdict_display}**]")
        
        # Show insufficient info reason prominently if available
        if insufficient_info_reason and 'INSUFFICIENT' in verdict_display:
            try:
                from claim_verifier.insufficient_info_analyzer import get_reason_label, get_short_explanation
                reason_label = get_reason_label(insufficient_info_reason)
                short_explanation = get_short_explanation(insufficient_info_reason)
                
                st.markdown("---")
                st.markdown(f"### 🔍 Why We Couldn't Verify")
                st.warning(f"**{reason_label}**")
                st.caption(short_explanation)
                
                # Show detailed explanation in expandable section
                if insufficient_info_explanation:
                    with st.expander("📖 Detailed Explanation", expanded=False):
                        st.write(insufficient_info_explanation)
                
                # Show actionable suggestions
                if insufficient_info_suggestions and len(insufficient_info_suggestions) > 0:
                    with st.expander("💡 Verification Suggestions", expanded=False):
                        st.markdown("**Alternative ways to verify this claim:**")
                        for suggestion in insufficient_info_suggestions:
                            st.markdown(f"• {suggestion}")
            except Exception as e:
                # Fallback if analyzer not available
                pass
        
        # Show corrected claim prominently for REFUTED verdicts
        if corrected_claim and 'REFUTED' in verdict:
            st.markdown("---")
            st.markdown("### ✏️ Corrected Information")
            st.success(corrected_claim)
        elif corrected_claim and 'SUPPORTED' in verdict:
            st.markdown("---")
            st.markdown("### ✅ Confirmation")
            st.info(corrected_claim)
        
        # Show detailed explanation
        if detailed_explanation:
            st.markdown("---")
            st.markdown("**Detailed Analysis:**")
            st.write(detailed_explanation)
        
        # Show brief reasoning if no detailed explanation
        if reasoning and not detailed_explanation:
            st.markdown("**Reasoning:**")
            st.write(reasoning)
        
        if evidence_list:
            st.markdown("**Evidence:**")
            for i, evidence in enumerate(evidence_list, 1):
                with st.container():
                    st.markdown(f"**Source {i}:**")
                    # Handle both dict and object
                    if isinstance(evidence, dict):
                        title = evidence.get('title', 'Source')
                        url = evidence.get('url', '#')
                        content = evidence.get('content', '')
                    else:
                        # Pydantic object
                        title = evidence.title if hasattr(evidence, 'title') else 'Source'
                        url = evidence.url if hasattr(evidence, 'url') else '#'
                        content = evidence.text if hasattr(evidence, 'text') else ''
                    
                    st.markdown(f"📄 [{title}]({url})")
                    if content:
                        st.caption(content[:300] + "..." if len(content) > 300 else content)
                    st.divider()


def render_summary_stats(results: Dict[str, Any]):
    """Render summary statistics"""
    # Try different possible keys for claims
    claims = results.get('verification_results', results.get('verified_claims', []))
    
    if not claims:
        st.info("No verifiable claims were found in the provided text.")
        return
    
    # Handle both dict and Pydantic object formats
    supported = 0
    refuted = 0
    insufficient = 0
    
    for c in claims:
        # Get verdict - handle both dict and Pydantic Verdict object
        if isinstance(c, dict):
            verdict = str(c.get('result', c.get('verdict', '')))
        elif hasattr(c, 'result'):
            verdict = str(c.result)
        elif hasattr(c, 'verdict'):
            verdict = str(c.verdict)
        else:
            verdict = str(c)
        
        if 'SUPPORTED' in verdict.upper() or 'Supported' in verdict:
            supported += 1
        elif 'REFUTED' in verdict.upper() or 'Refuted' in verdict:
            refuted += 1
        else:
            insufficient += 1
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Claims", len(claims))
    with col2:
        st.metric("✅ Supported", supported)
    with col3:
        st.metric("❌ Refuted", refuted)
    with col4:
        st.metric("⚠️ Insufficient", insufficient)


def render_metrics_summary():
    """Render LLM usage metrics summary in a collapsible expander."""
    # Try to get metrics from session state first (more accurate after verification)
    summary = st.session_state.get('metrics_summary')
    
    if not summary:
        # Fallback to current tracker
        tracker = get_metrics_tracker()
        summary = tracker.get_summary()
    
    if summary['total_calls'] == 0:
        return
    
    # Get stage summary from current tracker
    tracker = get_metrics_tracker()
    stage_summary = tracker.get_stage_summary()
    
    # Wrap everything in an expander (collapsed by default)
    with st.expander("📊 API Usage Metrics", expanded=False):
        st.caption("💡 Shows cumulative cost for all operations (extraction + verification)")
        
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.metric("LLM API Calls", summary['total_calls'])
        with col2:
            tavily_calls = summary.get('tavily_calls', 0)
            st.metric("Tavily API Calls", tavily_calls)
        with col3:
            st.metric("Input Tokens", f"{summary['total_input_tokens']:,}")
        with col4:
            st.metric("Output Tokens", f"{summary['total_output_tokens']:,}")
        with col5:
            st.metric("Duration", f"{summary['duration_seconds']:.1f}s")
        with col6:
            st.metric("💰 Total Cost", f"${summary['total_cost']:.4f}")
        
        # Stage breakdown (no nested expander - just show directly)
        tracker = get_metrics_tracker()
        stage_summary = tracker.get_stage_summary()
        if stage_summary:
            st.markdown("---")
            st.markdown("### 📈 Per-Stage Breakdown (Extraction vs Verification)")
            
            # Separate extraction and verification stages
            extraction_stages = {k: v for k, v in stage_summary.items() if 'extractor' in k}
            verification_stages = {k: v for k, v in stage_summary.items() if 'verifier' in k}
            
            if extraction_stages:
                st.markdown("**🔍 Claim Extraction:**")
                extraction_total = sum(m['cost'] for m in extraction_stages.values())
                for stage, metrics in sorted(extraction_stages.items()):
                    st.markdown(
                        f"  • {stage}: {metrics['calls']} calls, "
                        f"{metrics['input_tokens']:,} in, {metrics['output_tokens']:,} out, "
                        f"${metrics['cost']:.4f}"
                    )
                st.markdown(f"  **Extraction Subtotal: ${extraction_total:.4f}**")
                st.markdown("")
            
            if verification_stages:
                st.markdown("**✓ Fact Verification:**")
                verification_total = sum(m['cost'] for m in verification_stages.values())
                for stage, metrics in sorted(verification_stages.items()):
                    st.markdown(
                        f"  • {stage}: {metrics['calls']} calls, "
                        f"{metrics['input_tokens']:,} in, {metrics['output_tokens']:,} out, "
                        f"${metrics['cost']:.4f}"
                    )
                st.markdown(f"  **Verification Subtotal: ${verification_total:.4f}**")
                st.markdown("")
            
            # Show other stages if any
            other_stages = {k: v for k, v in stage_summary.items() 
                          if 'extractor' not in k and 'verifier' not in k}
            if other_stages:
                st.markdown("**Other:**")
                for stage, metrics in sorted(other_stages.items()):
                    st.markdown(
                        f"  • {stage}: {metrics['calls']} calls, "
                        f"{metrics['input_tokens']:,} in, {metrics['output_tokens']:,} out, "
                        f"${metrics['cost']:.4f}"
                    )


def check_api_keys():
    """Check if required API keys are configured"""
    openai_key = os.getenv('OPENAI_API_KEY')
    tavily_key = os.getenv('TAVILY_API_KEY')
    
    # Default Tavily API key (fallback)
    DEFAULT_TAVILY_KEY = "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"
    
    # Use custom Tavily key if provided in UI
    if st.session_state.get('use_custom_tavily') and st.session_state.get('custom_tavily_key'):
        tavily_key = st.session_state.custom_tavily_key
        os.environ['TAVILY_API_KEY'] = tavily_key
    elif not tavily_key:
        # Use default if no key in environment
        tavily_key = DEFAULT_TAVILY_KEY
        os.environ['TAVILY_API_KEY'] = tavily_key
    
    if not openai_key:
        st.error("⚠️ OpenAI API key not configured!")
        st.markdown("""
        Please set up your OpenAI API key:
        
        **Option 1:** Set in `apps/agent/.env`:
        ```
        OPENAI_API_KEY=sk-proj-your-key-here
        ```
        
        **Option 2:** Add in Streamlit secrets (`.streamlit/secrets.toml`):
        ```
        OPENAI_API_KEY = "sk-proj-your-key-here"
        ```
        
        Get API key from: https://platform.openai.com/api-keys
        """)
        return False
    
    return True


def main():
    """Main application"""
    initialize_session_state()
    
    # Header
    st.markdown('<div class="main-header">🔍 AI Fact Checker</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Standalone AI-Powered Fact Checking System</div>', unsafe_allow_html=True)
    
    # Check API keys
    if not check_api_keys():
        st.stop()
    
    # Sidebar
    with st.sidebar:
        st.header("ℹ️ About")
        st.markdown("""
        **AI Fact Checker** has three modes:
        
        **📝 Full Text Analysis:**
        - Extracts multiple claims from text
        - Verifies each claim independently
        - Generates comprehensive report
        
        **⚡ Single Fact Verification:**
        - Quick check for one specific fact
        - Direct verification without extraction
        - Faster results
        
        **🎯 Claim Extraction Only:**
        - Just extract facts from text
        - No verification (fastest & cheapest)
        - Perfect for content analysis
        
        **Powered by:**
        - OpenAI for language understanding
        - Tavily for web search (verification modes)
        - LangGraph for orchestration
        
        **Mode:** Standalone (no backend required)
        """)
        
        st.divider()
        
        st.header("⚙️ Settings")
        
        # OpenAI API Key Status
        if os.getenv('OPENAI_API_KEY'):
            st.success("✅ OpenAI API Key configured")
        else:
            st.error("❌ OpenAI API Key missing")
        
        st.divider()
        
        # Tavily API Key Configuration
        st.subheader("🔑 Tavily API Settings")
        
        # Check if Tavily key exists in environment
        env_tavily_key = os.getenv('TAVILY_API_KEY')
        
        if env_tavily_key:
            st.success("✅ Tavily API Key (from environment)")
            st.caption(f"Key: {env_tavily_key[:8]}...{env_tavily_key[-4:]}")
        else:
            st.info("ℹ️ Using default Tavily API Key")
        
        # Option to use custom Tavily key
        use_custom = st.checkbox(
            "Use Custom Tavily API Key",
            value=st.session_state.use_custom_tavily,
            key="use_custom_tavily_checkbox",
            help="Check this to enter your own Tavily API key. Otherwise, default key will be used."
        )
        
        if use_custom:
            custom_key = st.text_input(
                "Enter your Tavily API Key",
                value=st.session_state.custom_tavily_key,
                type="password",
                placeholder="tvly-...",
                help="Get your free API key from https://tavily.com (1,000 searches/month free)"
            )
            
            if st.button("💾 Save Tavily Key"):
                if custom_key and custom_key.startswith('tvly-'):
                    st.session_state.custom_tavily_key = custom_key
                    st.session_state.use_custom_tavily = True
                    os.environ['TAVILY_API_KEY'] = custom_key
                    st.success("✅ Custom Tavily API Key saved!")
                    st.rerun()
                else:
                    st.error("❌ Invalid Tavily API key format. Should start with 'tvly-'")
        else:
            st.session_state.use_custom_tavily = False
            if not env_tavily_key:
                st.caption("💡 Default key provided - no action needed")
        
        st.divider()
        
        if st.button("🔄 Clear Results"):
            st.session_state.results = None
            st.session_state.metrics_summary = None
            st.rerun()
    
    # Main content
    st.header("Enter Content to Fact-Check")
    
    # Mode selection
    mode = st.radio(
        "Select Mode:",
        options=["📝 Full Text Analysis", "⚡ Single Fact Verification", "🎯 Claim Extraction Only", "🎬 Video Fact-Checking"],
        help="Choose between full analysis, quick fact check, claim extraction, or video fact-checking",
        horizontal=True
    )
    
    st.divider()
    
    # Input form based on mode
    if mode == "🎯 Claim Extraction Only":
        # Extraction only mode
        with st.form("extraction_form"):
            st.info("🎯 **Extraction Mode**: Extract all factual claims from text without verification. Fast & cheap!")
            
            text = st.text_area(
                "Text to Extract Claims From *",
                placeholder="Enter text to extract claims...\n\nExample:\n\"India's Chandrayaan-3 successfully landed on the moon in 2023. This made India the fourth country to achieve a lunar landing. The mission cost approximately $75 million.\"",
                height=200,
                help="Enter text containing multiple factual statements"
            )
            
            col1, col2 = st.columns([1, 4])
            with col1:
                submit_button = st.form_submit_button("🎯 Extract Claims", type="primary", use_container_width=True)
        
        if submit_button:
            if not text.strip():
                st.error("Please enter text to extract claims from.")
            else:
                st.session_state.processing = True
                
                with st.spinner("🎯 Extracting claims from text..."):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("📝 Analyzing text structure...")
                    progress_bar.progress(25)
                    
                    status_text.text("🔍 Identifying factual statements...")
                    progress_bar.progress(50)
                    
                    results = run_claim_extraction(text)
                    
                    if results:
                        status_text.text("✅ Extraction complete!")
                        progress_bar.progress(100)
                        
                        import time
                        time.sleep(0.5)
                        
                        st.session_state.results = results
                        status_text.empty()
                        progress_bar.empty()
                    else:
                        status_text.empty()
                        progress_bar.empty()
                        st.error("Failed to extract claims. Please check the error message above.")
        
        st.session_state.processing = False
    
    elif mode == "⚡ Single Fact Verification":
        # Single fact mode
        with st.form("single_fact_form"):
            st.info("💡 **Quick Check Mode**: Enter a single factual statement to verify directly without claim extraction.")
            
            claim = st.text_area(
                "Fact to Verify *",
                placeholder="Enter a single factual statement...\n\nExample: \"India's Chandrayaan-3 landed on the moon in August 2023\"",
                height=120,
                help="Enter one clear, specific factual claim to verify"
            )
            
            col1, col2 = st.columns([1, 4])
            with col1:
                submit_button = st.form_submit_button("⚡ Verify Fact", type="primary", use_container_width=True)
        
        if submit_button:
            if not claim.strip():
                st.error("Please enter a fact to verify.")
            else:
                st.session_state.processing = True
                
                with st.spinner("⚡ Verifying fact and gathering evidence..."):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("🔍 Searching for evidence...")
                    progress_bar.progress(50)
                    
                    results = run_single_fact_check(claim)
                    
                    if results:
                        status_text.text("✅ Verification complete!")
                        progress_bar.progress(100)
                        
                        import time
                        time.sleep(0.5)
                        
                        st.session_state.results = results
                        status_text.empty()
                        progress_bar.empty()
                    else:
                        status_text.empty()
                        progress_bar.empty()
                        st.error("Failed to verify fact. Please check the error message above.")
    
    elif mode == "🎬 Video Fact-Checking":
        # Video fact-checking mode
        st.info("🎬 **Video Mode**: Upload video → Transcribe with Whisper → Translate to English → Extract claims → Verify selected facts.")
        
        # Video upload
        uploaded_video = st.file_uploader(
            "Upload Video File",
            type=["mp4", "avi", "mov", "mkv", "webm"],
            help="Supported formats: MP4, AVI, MOV, MKV, WebM. Max size: 1GB"
        )
        
        if uploaded_video:
            # Check file size
            file_size_mb = uploaded_video.size / (1024 * 1024)
            if file_size_mb > 1000:
                st.error(f"❌ File too large ({file_size_mb:.1f}MB). Maximum size is 1GB (1000MB).")
            else:
                st.success(f"✅ Video uploaded: {uploaded_video.name} ({file_size_mb:.1f}MB)")
                
                # Initialize session state for video processing
                if 'video_transcript' not in st.session_state:
                    st.session_state.video_transcript = None
                if 'video_claims' not in st.session_state:
                    st.session_state.video_claims = None
                
                # Step 1: Extract Audio & Transcribe
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🎤 Transcribe Video", type="primary", use_container_width=True):
                        with st.spinner("⏳ Extracting audio from video..."):
                            try:
                                audio_path = extract_audio_from_video(uploaded_video)
                                st.success("✅ Audio extracted!")
                                
                                with st.spinner("🎤 Transcribing audio with Whisper AI..."):
                                    transcript = transcribe_audio_whisper(audio_path)
                                    st.session_state.video_transcript = transcript
                                    st.success("✅ Transcription complete!")
                                    
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                                logger.error(f"Video processing error: {str(e)}")
                
                # Show transcript if available
                if st.session_state.video_transcript:
                    # Show both original and English transcripts if translation occurred
                    if st.session_state.get('video_english_transcript') and st.session_state.get('video_original_transcript'):
                        col_orig, col_eng = st.columns(2)
                        with col_orig:
                            with st.expander("📄 Original Transcript", expanded=False):
                                st.text_area(
                                    "Original",
                                    st.session_state.video_original_transcript,
                                    height=200,
                                    disabled=True,
                                    label_visibility="collapsed",
                                    key="video_original_transcript_1"
                                )
                        with col_eng:
                            with st.expander("🌐 English Translation", expanded=False):
                                st.text_area(
                                    "English",
                                    st.session_state.video_english_transcript,
                                    height=200,
                                    disabled=True,
                                    label_visibility="collapsed",
                                    key="video_english_transcript_1"
                                )
                    else:
                        with st.expander("📄 View Transcript", expanded=False):
                            st.text_area(
                                "Transcript",
                                st.session_state.video_transcript,
                                height=200,
                                disabled=True,
                                key="video_transcript_single"
                            )
                    
                    # Step 2: Extract Claims
                    with col2:
                        if st.button("🔍 Extract Claims", type="primary", use_container_width=True):
                            try:
                                with st.spinner("🌐 Translating to English..."):
                                    st.caption("Translating transcript for better accuracy...")
                                
                                with st.spinner("🔍 Extracting claims..."):
                                    claims = extract_claims_from_transcript(st.session_state.video_transcript)
                                    st.session_state.video_claims = claims
                                    st.success(f"✅ Found {len(claims)} claims!")
                                    st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
                                logger.error(f"Claim extraction error: {str(e)}")
                    
                    # Step 3: Display Claims for Selection
                    if st.session_state.video_claims:
                        st.divider()
                        st.subheader(f"📋 Extracted Claims ({len(st.session_state.video_claims)} found)")
                        st.info("✅ Select which claims you want to verify. Deselect opinions or irrelevant statements.")
                        
                        # Select All / Deselect All buttons
                        col1, col2, col3 = st.columns([1, 1, 3])
                        with col1:
                            if st.button("✓ Select All"):
                                for claim in st.session_state.video_claims:
                                    claim['selected'] = True
                                st.rerun()
                        with col2:
                            if st.button("✗ Deselect All"):
                                for claim in st.session_state.video_claims:
                                    claim['selected'] = False
                                st.rerun()
                        
                        # Display claims with checkboxes
                        for claim in st.session_state.video_claims:
                            claim_id = claim['id']
                            claim_text = claim['text']
                            
                            # Create checkbox for each claim
                            is_selected = st.checkbox(
                                f"**Claim {claim_id + 1}:** {claim_text[:150]}{'...' if len(claim_text) > 150 else ''}",
                                value=claim.get('selected', True),
                                key=f"video_claim_{claim_id}"
                            )
                            
                            # Update selection state
                            claim['selected'] = is_selected
                            
                            # Show full text in expander
                            if len(claim_text) > 150:
                                with st.expander("View full claim"):
                                    st.write(claim_text)
                        
                        # Count selected claims
                        selected_count = sum(1 for c in st.session_state.video_claims if c.get('selected', True))
                        
                        st.divider()
                        
                        # Step 4: Verify Selected Claims
                        if selected_count > 0:
                            if st.button(f"✅ Verify {selected_count} Selected Claims", type="primary", use_container_width=True):
                                # Get selected claim objects
                                selected_claims = [
                                    c['claim_object'] 
                                    for c in st.session_state.video_claims 
                                    if c.get('selected', True)
                                ]
                                
                                with st.spinner(f"🔍 Verifying {selected_count} claims..."):
                                    progress_bar = st.progress(0)
                                    status_text = st.empty()
                                    
                                    try:
                                        for i, claim in enumerate(selected_claims):
                                            status_text.text(f"Verifying claim {i+1}/{selected_count}...")
                                            progress_bar.progress((i + 1) / selected_count)
                                        
                                        results = verify_selected_claims(selected_claims)
                                        
                                        if results:
                                            status_text.text("✅ Verification complete!")
                                            progress_bar.progress(1.0)
                                            
                                            import time
                                            time.sleep(0.5)
                                            
                                            st.session_state.results = results
                                            status_text.empty()
                                            progress_bar.empty()
                                            st.success(f"✅ Verified {selected_count} claims!")
                                        
                                    except Exception as e:
                                        status_text.empty()
                                        progress_bar.empty()
                                        st.error(f"❌ Error: {str(e)}")
                                        logger.error(f"Verification error: {str(e)}")
                        else:
                            st.warning("⚠️ No claims selected. Please select at least one claim to verify.")
    
    else:
        # Full text analysis mode with multi-step workflow (like video mode)
        st.info("📝 **Full Text Analysis**: Paste any text (English/Hindi/etc.) → Auto-translate → Extract claims → Select which to verify → Get results")
        
        # Initialize session state for text mode
        if 'text_transcript' not in st.session_state:
            st.session_state.text_transcript = None
        if 'text_detected_language' not in st.session_state:
            st.session_state.text_detected_language = None
        if 'text_english_version' not in st.session_state:
            st.session_state.text_english_version = None
        if 'text_claims' not in st.session_state:
            st.session_state.text_claims = None
        
        # Step 1: Input Text
        st.markdown("### Step 1: Paste Your Text")
        
        text_input = st.text_area(
            "Paste your text or transcript here",
            placeholder="Paste any text (English, Hindi, Spanish, etc.)...\n\nExample:\n'भारत का चंद्रयान-3 मिशन 2023 में चंद्रमा पर सफलतापूर्वक उतरा। यह भारत को चंद्र दक्षिणी ध्रुव पर उतरने वाला पहला देश बना देता है।'",
            height=200,
            key="text_input_area"
        )
        
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🔍 Analyze & Extract Claims", type="primary", use_container_width=True):
                if not text_input.strip():
                    st.error("❌ Please enter some text first!")
                else:
                    # Store input in session state
                    st.session_state.last_input_text = text_input
                    
                    with st.spinner("🌐 Detecting language..."):
                        detected_lang = detect_language(text_input)
                        st.session_state.text_detected_language = detected_lang
                        st.session_state.text_transcript = text_input
                        
                        # Check if translation needed
                        if detected_lang.lower() != 'english':
                            with st.spinner(f"🔤 Translating from {detected_lang} to English..."):
                                english_text = translate_to_english(text_input)
                                st.session_state.text_english_version = english_text
                                st.success(f"✅ Detected: {detected_lang} → Translated to English")
                        else:
                            st.session_state.text_english_version = text_input
                            st.success("✅ Detected: English (no translation needed)")
                    
                    with st.spinner("📝 Extracting claims from text..."):
                        try:
                            # Use English version for claim extraction
                            text_for_extraction = st.session_state.text_english_version
                            claims = extract_claims_from_transcript(text_for_extraction)
                            st.session_state.text_claims = claims
                            
                            if claims:
                                st.success(f"✅ Extracted {len(claims)} claims!")
                                st.rerun()
                            else:
                                st.warning("No verifiable claims found in the text.")
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                            logger.error(f"Claim extraction error: {str(e)}")
        
        # Step 2: Show Transcripts (if available)
        if st.session_state.text_transcript and st.session_state.text_english_version:
            st.divider()
            st.markdown("### Step 2: Review Text")
            
            # Show both versions if translation occurred
            if st.session_state.text_detected_language and st.session_state.text_detected_language.lower() != 'english':
                col1, col2 = st.columns(2)
                
                with col1:
                    with st.expander(f"📄 Original Text ({st.session_state.text_detected_language})", expanded=False):
                        st.text_area(
                            "Original",
                            st.session_state.text_transcript,
                            height=250,
                            key="text_original_display",
                            label_visibility="collapsed"
                        )
                
                with col2:
                    with st.expander("📄 English Translation", expanded=True):
                        st.text_area(
                            "English",
                            st.session_state.text_english_version,
                            height=250,
                            key="text_english_display",
                            label_visibility="collapsed"
                        )
            else:
                with st.expander("📄 Text", expanded=False):
                    st.text_area(
                        "Text",
                        st.session_state.text_english_version,
                        height=250,
                        key="text_single_display",
                        label_visibility="collapsed"
                    )
        
        # Step 3: Claim Selection (if claims extracted)
        if st.session_state.text_claims:
            st.divider()
            st.markdown("### Step 3: Select Claims to Verify")
            
            st.info(f"💡 Found **{len(st.session_state.text_claims)} claims**. Select which ones you want to verify (saves cost by verifying only what matters).")
            
            # Select All / Deselect All buttons
            col1, col2, col3, col4 = st.columns([1, 1, 1, 3])
            with col1:
                if st.button("✅ Select All", use_container_width=True):
                    for claim in st.session_state.text_claims:
                        claim['selected'] = True
                    st.rerun()
            with col2:
                if st.button("❌ Deselect All", use_container_width=True):
                    for claim in st.session_state.text_claims:
                        claim['selected'] = False
                    st.rerun()
            with col3:
                if st.button("🔝 Select Top 10", use_container_width=True):
                    for i, claim in enumerate(st.session_state.text_claims):
                        claim['selected'] = i < 10
                    st.rerun()
            
            st.markdown("---")
            
            # Display claims with checkboxes
            for idx, claim in enumerate(st.session_state.text_claims):
                col1, col2 = st.columns([0.1, 0.9])
                
                with col1:
                    is_selected = st.checkbox(
                        "Select",
                        value=claim.get('selected', True),
                        key=f"text_claim_checkbox_{idx}",
                        label_visibility="collapsed"
                    )
                    claim['selected'] = is_selected
                
                with col2:
                    st.markdown(f"**Claim {idx + 1}:**")
                    st.info(claim['text'])
            
            # Count selected claims
            selected_count = sum(1 for c in st.session_state.text_claims if c.get('selected', False))
            
            st.markdown("---")
            st.markdown(f"**Selected: {selected_count}/{len(st.session_state.text_claims)} claims**")
            
            # Verify button
            if selected_count > 0:
                if st.button(f"✅ Verify {selected_count} Selected Claims", type="primary", use_container_width=True):
                    # Get selected claims
                    selected_claims = [
                        claim['claim_object'] 
                        for claim in st.session_state.text_claims 
                        if claim.get('selected', False)
                    ]
                    
                    with st.spinner(f"🔍 Verifying {selected_count} claims..."):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        try:
                            for i, claim in enumerate(selected_claims):
                                status_text.text(f"Verifying claim {i+1}/{selected_count}...")
                                progress_bar.progress((i + 1) / selected_count)
                            
                            # Pass the full extracted claims for reporting
                            results = verify_selected_claims(
                                selected_claims,
                                extracted_claims=[c['claim_object'] for c in st.session_state.text_claims]
                            )
                            
                            if results:
                                status_text.text("✅ Verification complete!")
                                progress_bar.progress(1.0)
                                
                                import time
                                time.sleep(0.5)
                                
                                st.session_state.results = results
                                status_text.empty()
                                progress_bar.empty()
                                st.success(f"✅ Verified {selected_count} claims!")
                                st.rerun()
                            
                        except Exception as e:
                            status_text.empty()
                            progress_bar.empty()
                            st.error(f"❌ Error: {str(e)}")
                            logger.error(f"Verification error: {str(e)}")
            else:
                st.warning("⚠️ No claims selected. Please select at least one claim to verify.")

    
    # Display results
    if st.session_state.results:
        st.divider()
        
        results = st.session_state.results
        is_single_fact = results.get("mode") == "single_fact"
        is_extraction_only = results.get("mode") == "extraction_only"
        is_video_mode = results.get("mode") == "video"
        
        # Header based on mode
        if is_extraction_only:
            st.header("🎯 Extracted Claims")
        elif is_single_fact:
            st.header("⚡ Fact Verification Result")
        elif is_video_mode:
            st.header("🎬 Video Fact-Check Results")
        else:
            st.header("📊 Fact-Check Results")
        
        # Add Download Excel Report button
        if EXCEL_EXPORT_AVAILABLE:
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("📥 Download Excel Report", type="secondary", use_container_width=True):
                    try:
                        # Prepare metadata
                        input_metadata = {
                            'type': 'Video' if is_video_mode else 'Text',
                            'preprocessed': results.get('preprocessed_text') is not None
                        }
                        
                        # Add video-specific metadata
                        if is_video_mode:
                            input_metadata['language'] = st.session_state.get('video_language', 'Unknown')
                            input_metadata['translated'] = st.session_state.get('video_english_transcript') is not None
                            input_metadata['transcript'] = st.session_state.get('video_original_transcript', '')
                            input_metadata['english_transcript'] = st.session_state.get('video_english_transcript', '')
                        
                        # Get original input
                        original_input = st.session_state.get('last_input_text', '')
                        if is_video_mode:
                            original_input = st.session_state.get('video_transcript', original_input)
                        
                        # Get metrics summary from session state (saved during verification)
                        metrics_summary = st.session_state.get('metrics_summary')
                        if not metrics_summary:
                            tracker = get_metrics_tracker()
                            metrics_summary = tracker.get_summary()
                        
                        # Generate Excel report
                        excel_buffer = generate_excel_report(
                            original_input=original_input,
                            results=results,
                            input_metadata=input_metadata,
                            metrics_summary=metrics_summary
                        )
                        
                        # Create filename with timestamp
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"fact_check_report_{timestamp}.xlsx"
                        
                        # Offer download
                        st.download_button(
                            label="💾 Download Report",
                            data=excel_buffer,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                        
                    except Exception as e:
                        st.error(f"Error generating report: {str(e)}")
                        logger.error(f"Excel export error: {str(e)}")
        
        st.divider()
        
        # Handle extraction-only mode
        if is_extraction_only:
            extracted_claims = results.get('extracted_claims', [])
            
            if extracted_claims:
                st.success(f"✅ Found {len(extracted_claims)} factual claims")
                
                st.subheader("📝 Extracted Claims")
                
                for idx, claim in enumerate(extracted_claims, 1):
                    # Display claim object
                    claim_text = claim.claim_text if hasattr(claim, 'claim_text') else str(claim)
                    confidence = claim.confidence if hasattr(claim, 'confidence') else None
                    
                    with st.container():
                        st.markdown(f"**Claim {idx}:**")
                        st.info(claim_text)
                        
                        if confidence:
                            st.caption(f"Confidence: {confidence:.1%}")
                        
                        st.markdown("---")
                
                # Offer to verify
                st.divider()
                st.info("💡 **Want to verify these claims?** Switch to '📝 Full Text Analysis' mode to verify all claims automatically.")
                
            else:
                st.warning("No factual claims were extracted from the text.")
                st.info("Try entering text with clear factual statements like dates, numbers, names, or events.")
        
        # Handle verification modes
        else:
            # Show video transcripts for video mode (both original and translated)
            if is_video_mode and st.session_state.get('video_transcript'):
                if st.session_state.get('video_english_transcript') and st.session_state.get('video_original_transcript'):
                    # Show both transcripts side by side
                    st.subheader("📄 Transcripts")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        with st.expander("📄 Original Transcript (Detected Language)", expanded=False):
                            st.text_area(
                                "Original",
                                st.session_state.video_original_transcript,
                                height=250,
                                key="video_original_transcript_2",
                                label_visibility="collapsed"
                            )
                    
                    with col2:
                        with st.expander("📄 English Translation", expanded=False):
                            st.text_area(
                                "English",
                                st.session_state.video_english_transcript,
                                height=250,
                                key="video_english_transcript_2",
                                label_visibility="collapsed"
                            )
                    
                    st.divider()
                else:
                    # Show single transcript
                    with st.expander("📄 Video Transcript", expanded=False):
                        st.text_area(
                            "Transcript",
                            st.session_state.video_transcript,
                            height=250,
                            key="video_transcript_results",
                            label_visibility="collapsed"
                        )
                    st.divider()
            
            # Summary statistics
            render_summary_stats(results)
            
            st.divider()
            
            # Individual claim results
            st.subheader("🔍 Detailed Claim Analysis")
            
            # Get claims from results
            claims = results.get('verification_results', results.get('verified_claims', []))
            
            if not claims:
                st.info("No claims to display.")
            else:
                for idx, claim in enumerate(claims):
                    render_claim_card(claim, idx)
        
        # API Usage Metrics at the bottom
        st.divider()
        render_metrics_summary()


if __name__ == "__main__":
    main()