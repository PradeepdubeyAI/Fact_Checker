# AI Fact-Checking System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An advanced multi-agent fact-checking system built with LangGraph that automatically verifies the factual accuracy of text, video, and multilingual content. The system extracts individual claims, verifies them against real-world evidence, and generates professional Excel reports with cost tracking.

## 🏗️ System Architecture

The system is built on a modular, multi-agent architecture with three specialized agents orchestrated by LangGraph:

1.  **[Claim Extractor (`claim_extractor/`)](./apps/agent/claim_extractor/README.md)**: Extracts factual claims using the research-based Claimify methodology
2.  **[Claim Verifier (`claim_verifier/`)](./apps/agent/claim_verifier/README.md)**: Verifies each claim against online evidence via Tavily Search API
3.  **[Fact Checker (`fact_checker/`)](./apps/agent/fact_checker/README.md)**: Orchestrates the complete pipeline with parallel processing

### Three-Agent System

```
┌─────────────────────────────────────────────────────────────┐
│                    INPUT LAYER                              │
│  • Text Input (Direct/Translated)                           │
│  • Video Input → Whisper Transcription → Translation        │
│  • Single Claim (Quick Check Mode)                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               AGENT 1: CLAIM EXTRACTOR                      │
│  ┌──────────────────────────────────────┐                  │
│  │  Stage 1: Sentence Splitting         │                  │
│  │  • Identify fact-bearing sentences   │                  │
│  └──────────────────────────────────────┘                  │
│                     ↓                                       │
│  ┌──────────────────────────────────────┐                  │
│  │  Stage 2: Selection                  │                  │
│  │  • Filter verifiable statements      │                  │
│  └──────────────────────────────────────┘                  │
│                     ↓                                       │
│  ┌──────────────────────────────────────┐                  │
│  │  Stage 3: Disambiguation             │                  │
│  │  • Resolve pronouns & references     │                  │
│  │  • Multi-LLM consensus voting        │                  │
│  └──────────────────────────────────────┘                  │
│                     ↓                                       │
│  ┌──────────────────────────────────────┐                  │
│  │  Stage 4: Decomposition              │                  │
│  │  • Break complex → atomic claims     │                  │
│  └──────────────────────────────────────┘                  │
│                     ↓                                       │
│  ┌──────────────────────────────────────┐                  │
│  │  Stage 5: Validation                 │                  │
│  │  • Final checkability verification   │                  │
│  └──────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               AGENT 2: CLAIM VERIFIER                       │
│          (Runs in parallel for each claim)                  │
│                                                             │
│  ┌──────────────────────────────────────┐                  │
│  │  Node 1: Generate Search Query       │                  │
│  │  • Extract keywords from claim       │                  │
│  │  • Optimize for web search           │                  │
│  └──────────────────────────────────────┘                  │
│                     ↓                                       │
│  ┌──────────────────────────────────────┐                  │
│  │  Node 2: Retrieve Evidence           │                  │
│  │  • Tavily Search API (max 10/call)   │                  │
│  │  • Aggregate snippets + sources      │                  │
│  └──────────────────────────────────────┘                  │
│                     ↓                                       │
│  ┌──────────────────────────────────────┐                  │
│  │  Node 3: Search Decision             │                  │
│  │  • Check authoritative sources       │                  │
│  │  • Evaluate evidence sufficiency     │                  │
│  │  • Decide: CONTINUE or STOP          │                  │
│  └──────────────────────────────────────┘                  │
│           ↓                    ↓                            │
│      [Loop Back]          [Proceed]                         │
│           │                    │                            │
│  ┌────────┴────────────────────┘                           │
│  │                                                          │
│  ┌──────────────────────────────────────┐                  │
│  │  Node 4: Evaluate Evidence           │                  │
│  │  • Analyze all gathered evidence     │                  │
│  │  • Generate verdict:                 │                  │
│  │    - SUPPORTED                       │                  │
│  │    - REFUTED                         │                  │
│  │    - NOT_ENOUGH_INFO                 │                  │
│  │    - CONFLICTING_EVIDENCE            │                  │
│  │  • Provide detailed reasoning        │                  │
│  └──────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               AGENT 3: FACT CHECKER                         │
│             (Orchestrator & Aggregator)                     │
│                                                             │
│  • Manages overall workflow                                 │
│  • Coordinates parallel claim verification                  │
│  • Rate limiting (max 4 concurrent)                         │
│  • Aggregates all results                                   │
│  • Tracks costs & metrics                                   │
│  • Generates final report                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    OUTPUT LAYER                             │
│  • Professional Excel Report (4 sheets)                     │
│  • Real-time metrics dashboard                              │
│  • Downloadable results                                     │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- OpenAI API key
- Tavily API key (1,000 free searches/month)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/bharathxd/ClaimAI.git
cd ClaimAI
```

2. **Install dependencies**
```bash
cd apps/streamlit
pip install -r requirements.txt
```

3. **Set up API keys**

Create a `.streamlit/secrets.toml` file:
```toml
OPENAI_API_KEY = "your-openai-api-key"
TAVILY_API_KEY = "your-tavily-api-key"
```

Or set environment variables:
```bash
export OPENAI_API_KEY="your-openai-api-key"
export TAVILY_API_KEY="your-tavily-api-key"
```

4. **Launch the application**
```bash
streamlit run standalone_app.py
```

The app will open in your browser at `http://localhost:8501`

### Basic Usage

#### Mode 1: Full Text Analysis
1. Select "📄 Full Text Analysis" from sidebar
2. Enter or paste text to analyze
3. Click "🔍 Start Fact-Checking"
4. Review extracted claims and verification results
5. Download Excel report

#### Mode 2: Single Fact Verification
1. Select "✓ Single Fact Verification"
2. Enter a single claim to verify
3. Click "🔍 Verify This Fact"
4. Get instant verdict with evidence

#### Mode 3: Claim Extraction
1. Select "📋 Claim Extraction Only"
2. Input text for analysis
3. Click "🔍 Extract Claims"
4. Review list of extracted claims
5. Optionally select claims to verify

#### Mode 4: Video Fact-Checking
1. Select "🎥 Video Fact-Checking"
2. Upload video file (MP4/AVI/MOV)
3. System automatically:
   - Extracts audio
   - Transcribes speech (Whisper)
   - Detects and translates language
   - Extracts and verifies claims
4. Download comprehensive Excel report

## 📖 Usage Examples

### Example 1: Verifying a News Article

**Input Text:**
```
According to a White House statement, the US economy added 250,000 
jobs in January 2024. Tesla delivered over 1.8 million vehicles in 
2023, making it the world's best-selling EV manufacturer. The company's 
CEO stated they aim to produce 20 million cars annually by 2030.
```

**Output:**
```
✓ SUPPORTED: "Tesla delivered over 1.8 million vehicles in 2023"
  Evidence: Official Tesla Q4 2023 earnings report
  
✗ REFUTED: "The US economy added 250,000 jobs in January 2024"
  Evidence: Bureau of Labor Statistics reports 353,000 jobs added
  
✓ SUPPORTED: "Tesla is the world's best-selling EV manufacturer in 2023"
  Evidence: Multiple automotive industry reports
  
⚠️ NOT ENOUGH INFO: "Tesla aims to produce 20 million cars annually by 2030"
  Evidence: Various statements, but no official confirmation of 20M target
```

**Metrics:**
- 4 claims extracted
- 3 verified successfully
- Cost: ₹7.60 total
- Time: ~45 seconds

### Example 2: Quick Fact Check

**Mode:** Single Fact Verification

**Input:** "The Eiffel Tower was completed in 1889"

**Output:**
```
✓ SUPPORTED

Reasoning: Multiple authoritative sources including official Eiffel Tower 
website and historical records confirm completion in 1889 for the World's 
Fair in Paris.

Sources:
- https://www.toureiffel.paris/en/the-monument/history
- https://www.britannica.com/topic/Eiffel-Tower-Paris-France
```

**Metrics:**
- 1 claim verified
- Cost: ₹1.90
- Time: ~8 seconds

### Example 3: Video Fact-Checking

**Input:** Political speech video (5 minutes, MP4)

**Process:**
1. Audio extracted → 4.8 MB WAV
2. Transcribed with Whisper → 1,247 words
3. Language detected → English
4. 12 claims extracted
5. 12 claims verified in parallel

**Sample Results:**
```
✓ SUPPORTED: "Unemployment is at a 50-year low" (8 claims supported)
⚠️ NOT ENOUGH INFO: "Our economy is the strongest in the world" (2 claims insufficient)
✗ REFUTED: "We've created more jobs than any previous administration" (2 claims refuted)
```

**Final Report:**
- Accuracy: 66.7% (8/12 supported)
- Total cost: ₹22.80
- Processing time: 2 min 15 sec
- Excel report: 4 sheets, 38 rows of evidence

### Example 4: Multi-Language Content

**Input:** Spanish article about climate change

**Process:**
1. Language auto-detected → Spanish
2. Auto-translated to English for processing
3. 7 claims extracted
4. Verified against English sources

**Output:**
All claims verified with proper context preservation. Original Spanish 
claims shown in Excel report alongside English translations.

## 🎯 How It Works

### Step 1: Claim Extraction
The system analyzes input text and extracts verifiable claims through a 4-stage pipeline:

- **Selection**: Identifies sentences containing factual information
- **Disambiguation**: Resolves ambiguous references and pronouns using multi-LLM consensus voting
- **Decomposition**: Breaks compound statements into atomic, independently verifiable claims
- **Validation**: Ensures each extracted claim is clear, self-contained, and checkable

**Example:**
```
Input: "He founded SpaceX in 2002. The company launched Falcon 9."

After extraction:
✓ "Elon Musk founded SpaceX in 2002"
✓ "SpaceX launched the Falcon 9 rocket"
```

### Step 2: Claim Verification
Each extracted claim is independently verified:

1. **Query Generation**: Constructs optimal search queries using LLM
2. **Evidence Retrieval**: Gathers supporting/refuting evidence via Tavily Search
3. **Iterative Search**: Continues searching until sufficient evidence or confidence threshold
4. **Smart Stopping**: Early termination when authoritative sources found (gov/edu/org domains)
5. **Verdict Generation**: Analyzes all evidence to determine:
   - **SUPPORTED**: Claim backed by reliable evidence
   - **REFUTED**: Claim contradicted by evidence
   - **NOT ENOUGH INFO**: Insufficient evidence to verify

### Step 3: Report Generation
The system produces a comprehensive report including:
- Original text and extracted claims
- Per-claim verdicts with confidence levels
- Supporting/refuting evidence with sources
- Summary statistics (accuracy rate, claim breakdown)
- Token usage and cost metrics

## ✨ Features Overview

### 🎯 Four Operation Modes

#### 1. **Full Text Analysis** (Complete Fact-Checking)
Extract all claims from text and verify each one against online evidence. Perfect for:
- Analyzing articles, blog posts, social media content
- Validating quoted statistics and figures
- Comprehensive fact-checking of long-form content

**Workflow**: Text Input → Claim Extraction → Parallel Verification → Excel Report

#### 2. **Single Fact Verification** (Quick Check)
Instantly verify a single statement without extraction overhead. Ideal for:
- Quick spot-checks of specific claims
- Verifying quotes or statistics in real-time
- Fast fact-checking during conversations

**Workflow**: Single Claim Input → Direct Verification → Instant Verdict

#### 3. **Claim Extraction Only** (Content Analysis)
Extract verifiable claims without verification - analyze what's being stated. Great for:
- Content auditing and analysis
- Identifying fact-bearing statements
- Planning verification work

**Workflow**: Text Input → Claim Extraction → Claim List Output

#### 4. **Video Fact-Checking** (Multimedia Analysis)
Upload video files (MP4, AVI, MOV, etc.) for automatic transcription and fact-checking. Features:
- Automatic audio extraction using MoviePy
- Speech-to-text with OpenAI Whisper
- Multi-language transcription and translation
- Full fact-checking pipeline on video content

**Workflow**: Video Upload → Audio Extraction → Transcription → Translation (if needed) → Claim Extraction → Verification → Excel Report

### 🌍 Multi-Language Support
- **Auto-Detection**: Automatically identifies input language
- **Auto-Translation**: Translates non-English content to English for processing
- **Supported Languages**: 100+ languages via OpenAI's detection
- **Preserved Context**: Maintains original meaning during translation

### 📊 Professional Excel Reports
Generate beautifully formatted reports with:
- **Summary Sheet**: Overall accuracy metrics, verdict breakdown, total costs
- **Extracted Facts Sheet**: Numbered list of all claims found
- **Fact-Check Results**: Detailed verdicts with confidence scores
- **Evidence Details**: Sources with clickable URLs
- **Visual Formatting**: Color-coded verdicts, alternating rows, professional styling

### 🚀 Core Capabilities
- ✅ **Multi-stage Claim Extraction** - Research-based methodology (Claimify)
- ✅ **Iterative Evidence Gathering** - Continues until confidence threshold met
- ✅ **Authoritative Source Detection** - Prioritizes .gov, .edu, .org domains
- ✅ **Parallel Processing** - Verifies multiple claims concurrently (rate-limited)
- ✅ **Real-Time Metrics** - Live tracking of API costs and token usage
- ✅ **Video Processing** - MP4/AVI/MOV support with Whisper transcription
- ✅ **Multi-Language** - Auto-detect and translate 100+ languages

### ⚡ Optimizations
- ✅ **Rate Limiting** - Semaphore-based concurrency control (max 4 concurrent)
- ✅ **Circuit Breaker** - Auto-pauses on API errors to prevent retry storms
- ✅ **Search Heuristics** - Early stopping with authoritative sources saves 30% API calls
- ✅ **Smart Retries** - 3 retries with exponential backoff, 60s timeout
- ✅ **Token Tracking** - Real-time cost monitoring per pipeline stage
- ✅ **Session State** - Preserves metrics across UI interactions

### 💰 Cost Metrics Dashboard
- 📊 **Live Tracking** - Real-time OpenAI and Tavily API usage
- 📊 **Per-claim costs** - LLM tokens, search calls, estimated costs
- 📊 **Stage breakdown** - Extraction vs verification costs
- 📊 **Session totals** - Cumulative metrics for entire analysis

## 💰 Cost Analysis

### Current Configuration (GPT-4o-mini + Tavily)

**Per-Claim Breakdown:**
- **LLM Costs**: ₹0.54 per claim
  - Claim extraction: ₹0.18
  - Query generation: ₹0.08
  - Evidence evaluation: ₹0.28
- **Tavily Search**: ₹1.36 per claim (avg 2 searches)
- **Total**: ₹1.90 per claim

**Real-World Scenarios:**
- **Short article** (5 claims): ₹9.50
- **Long article** (15 claims): ₹28.50
- **5-minute video** (12 claims): ₹22.80
- **Monthly usage** (1,000 claims): ₹1,220 (after free tier)

**Free Tier Coverage:**
- ✅ **OpenAI**: Pay-as-you-go (no free tier)
- ✅ **Tavily**: 1,000 free searches/month
  - Covers ~500 verified claims
  - Additional searches: $0.005 each

**Cost Optimization Tips:**
1. Use "Claim Extraction Only" mode for content analysis (no Tavily costs)
2. Enable early stopping for authoritative sources (saves ~30% Tavily calls)
3. Use Single Fact Verification for spot checks
4. Batch process multiple videos to amortize extraction costs

**Detailed Cost Documentation:**
* **[Claim Extractor Cost Analysis](./apps/agent/claim_extractor/README.md)** - Token usage breakdown
* **[Claim Verifier Cost Analysis](./apps/agent/claim_verifier/README.md)** - Search and evaluation costs
* **[Full Pipeline Analysis](./CLAIM_EXTRACTOR_COST_ANALYSIS.md)** - Comprehensive cost study

## 📚 Technical Details

### Technology Stack
- **Framework**: LangGraph for multi-agent orchestration
- **LLM**: OpenAI GPT-4o-mini (configurable)
- **Search**: Tavily Search API for evidence retrieval
- **Transcription**: OpenAI Whisper for video audio
- **Frontend**: Streamlit (web) + Electron (desktop)
- **Excel**: openpyxl with advanced formatting
- **Video**: MoviePy for audio extraction
- **Language**: Python 3.11+
- **Core Libraries**:
  - `langchain` - LLM framework
  - `langchain-openai` - OpenAI integrations
  - `langgraph` - Agent workflow orchestration
  - `streamlit` - Web UI
  - `openpyxl` - Excel generation
  - `moviepy` - Video processing
  - `pydantic` - Data validation
  - `asyncio` - Parallel processing

### State Management
The system uses LangGraph's state management approach:

```python
# Claim Extractor State
@dataclass
class ClaimExtractorState:
    input_text: str
    sentences: List[str]
    selected_sentences: List[Sentence]
    disambiguated_claims: List[Claim]
    decomposed_claims: List[Claim]
    validated_claims: List[ValidatedClaim]
    metadata: Dict[str, Any]
```

```python
# Claim Verifier State
@dataclass
class ClaimVerifierState:
    claim: str
    search_queries: List[str]
    evidence: List[Evidence]
    search_iterations: int
    max_iterations: int
    verdict: Verdict
    reasoning: str
```

### Parallel Processing
Claims are verified in parallel with rate limiting:

```python
async def verify_claims_parallel(claims, max_concurrent=4):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def verify_with_limit(claim):
        async with semaphore:
            return await verify_claim(claim)
    
    tasks = [verify_with_limit(claim) for claim in claims]
    return await asyncio.gather(*tasks)
```

### Cost Tracking
Real-time metrics tracked via `MetricsTracker`:

```python
tracker = get_metrics_tracker()

# Track LLM usage
tracker.record_llm_call(
    model="gpt-4o-mini",
    prompt_tokens=150,
    completion_tokens=50,
    total_tokens=200
)

# Track Tavily searches
tracker.record_tavily_call(num_results=10)

# Get summary
summary = tracker.get_summary()
# Returns: {
#     "llm_calls": 25,
#     "total_tokens": 5000,
#     "estimated_cost": 0.15,
#     "tavily_calls": 8
# }
```

### Configuration
Each agent has customizable settings:

**Claim Extractor** (`claim_extractor/llm/config.py`):
```python
LLM_CONFIG = {
    "model": "gpt-4o-mini",
    "temperature": 0.0,  # Deterministic
    "max_tokens": 2000
}
```

**Claim Verifier** (`claim_verifier/llm/config.py`):
```python
VERIFIER_CONFIG = {
    "model": "gpt-4o-mini",
    "temperature": 0.1,
    "max_search_iterations": 3,
    "max_results_per_search": 10,
    "timeout_seconds": 60
}
```

### Excel Report Structure

Generated reports include 4 sheets:

1. **Summary** - Accuracy metrics and cost breakdown
   - Overall accuracy percentage
   - Verdict distribution (Supported/Refuted/Not Enough Info)
   - Total OpenAI/Tavily costs
   - Generation timestamp

2. **Extracted Facts** - All claims found
   - Sequential numbering (#1, #2, etc.)
   - One claim per row
   - Clean, readable format

3. **Fact-Check Results** - Detailed verdicts
   - Original claim text
   - Corrected/clarified version
   - Verdict (color-coded)
   - Detailed reasoning
   - Search queries used

4. **Evidence Details** - Source information
   - Claim reference
   - Evidence snippets
   - Clickable source URLs
   - Website names

**Formatting Features**:
- Color-coded verdicts (green=supported, red=refuted, yellow=insufficient)
- Alternating row colors for readability
- Bold headers with background colors
- Auto-sized columns
- Hyperlinked URLs
- Professional borders and styling

## � A Bit About the Research

The `claim_extractor` is built on the **Claimify** methodology from Metropolitansky & Larson's 2025 paper. It's pretty fascinating stuff - they figured out how to handle ambiguity and extract verifiable claims. I spent a good week just implementing their pipeline, and it was worth it. The full citation and details are in the [`claim_extractor/README.md`](./apps/agent/claim_extractor/README.md).

For the `claim_verifier`, the evidence retrieval approach draws some inspiration from the Search-Augmented Factuality Evaluator (SAFE) methodology in ["Long-form factuality in large language models"](https://arxiv.org/abs/2403.18802) by Wei et al. (2024). Just the basic idea of using search results to verify individual claims.

## ⚠️ A Quick Note on the Implementation

Look, I've tried my best to faithfully implement everything described in the research papers, especially Claimify. But let's be real - there's always room for improvement and I might have missed some minor details along the way. I also took some creative liberties to enhance what was in the papers, adding features like the voting mechanism for disambiguation and the multi-retry approach for verification.

What you're seeing here is my interpretation of these research methods, with some practical additions that I found helpful when implementing in the real world. If you spot something that doesn't align perfectly with the papers, that's probably intentional - I was aiming for a working system that captured the spirit of the research while being practically useful.

The beauty of building on research is that we get to stand on the shoulders of giants AND add our own twist. I believe this implementation represents the core ideas faithfully while adding practical enhancements that make it even more effective.

## 🧪 Development Setup

### Running from Source

1. **Clone and navigate**
```bash
git clone https://github.com/bharathxd/ClaimAI.git
cd ClaimAI/apps/streamlit
```

2. **Create virtual environment** (recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure API keys** (choose one method)

**Method A: Streamlit Secrets** (recommended)
```bash
mkdir .streamlit
echo 'OPENAI_API_KEY = "sk-..."' > .streamlit/secrets.toml
echo 'TAVILY_API_KEY = "tvly-..."' >> .streamlit/secrets.toml
```

**Method B: Environment Variables**
```bash
export OPENAI_API_KEY="sk-..."
export TAVILY_API_KEY="tvly-..."
```

5. **Launch**
```bash
streamlit run standalone_app.py
```

### Desktop App

The desktop version uses Electron + Python backend:

```bash
cd apps/desktop

# Windows
START.bat

# Unix/Mac
chmod +x START.sh
./START.sh
```

### Running Individual Agents

Test agents independently:

```bash
cd apps/agent

# Extract claims only
python scripts/run_claim_extractor.py "Your text here"

# Verify single claim
python scripts/run_claim_verifier.py "Claim to verify"

# Full pipeline
python scripts/run_fact_checker.py "Complete text to analyze"
```

### Component Documentation

For detailed information on each agent:
* **[Claim Extractor](./apps/agent/claim_extractor/README.md)** - Claimify methodology implementation
* **[Claim Verifier](./apps/agent/claim_verifier/README.md)** - Evidence retrieval and evaluation
* **[Fact Checker](./apps/agent/fact_checker/README.md)** - Pipeline orchestration


## 📂 Repository Structure

```
ClaimeAI-main/
├── apps/
│   ├── agent/                    # Core fact-checking agents
│   │   ├── claim_extractor/      # Agent 1: Extract claims from text
│   │   │   ├── agent.py          # Main orchestration logic
│   │   │   ├── prompts.py        # LLM prompts for each stage
│   │   │   ├── schemas.py        # Pydantic models for state
│   │   │   ├── config/           # Configuration
│   │   │   │   └── nodes.py      # Node definitions
│   │   │   ├── llm/              # LLM configuration
│   │   │   │   └── config.py     # Model settings
│   │   │   └── nodes/            # Processing nodes
│   │   │       ├── sentence_splitter.py
│   │   │       ├── selection.py
│   │   │       ├── disambiguation.py
│   │   │       ├── decomposition.py
│   │   │       ├── contextualization.py
│   │   │       ├── preprocessing.py
│   │   │       └── validation.py
│   │   │
│   │   ├── claim_verifier/       # Agent 2: Verify individual claims
│   │   │   ├── agent.py          # Verification orchestration
│   │   │   ├── prompts.py        # Verification prompts
│   │   │   ├── schemas.py        # State models
│   │   │   ├── insufficient_info_analyzer.py  # Analyze missing info
│   │   │   ├── config/
│   │   │   │   └── nodes.py
│   │   │   ├── llm/
│   │   │   │   └── config.py
│   │   │   └── nodes/
│   │   │       ├── generate_search_query.py
│   │   │       ├── retrieve_evidence.py
│   │   │       ├── search_decision.py
│   │   │       └── evaluate_evidence.py
│   │   │
│   │   ├── fact_checker/         # Agent 3: Orchestrate full pipeline
│   │   │   ├── agent.py          # Main orchestrator
│   │   │   ├── schemas.py        # Pipeline state models
│   │   │   └── nodes/
│   │   │       ├── claim_verifier.py
│   │   │       └── ...
│   │   │
│   │   ├── utils/                # Shared utilities
│   │   │   ├── callbacks.py      # LangGraph callbacks
│   │   │   ├── llm.py            # LLM helper functions
│   │   │   ├── metrics.py        # Cost & usage tracking
│   │   │   ├── models.py         # Shared data models
│   │   │   ├── rate_limiter.py   # Concurrency control
│   │   │   ├── redis.py          # Redis utilities
│   │   │   ├── settings.py       # Configuration settings
│   │   │   └── text.py           # Text processing helpers
│   │   │
│   │   ├── security/             # API key management
│   │   │   ├── api_keys.py       # Key storage
│   │   │   └── auth.py           # Authentication
│   │   │
│   │   └── scripts/              # Utility scripts
│   │       ├── run_claim_extractor.py
│   │       ├── run_claim_verifier.py
│   │       ├── run_fact_checker.py
│   │       └── dev.py
│   │
│   ├── streamlit/                # Streamlit web interface
│   │   ├── standalone_app.py     # Main application (1,446 lines)
│   │   ├── export_excel.py       # Excel report generator (431 lines)
│   │   ├── requirements.txt      # Python dependencies
│   │   └── requirements_standalone.txt
│   │
│   └── desktop/                  # Desktop application (Electron)
│       ├── electron/             # Electron frontend
│       │   ├── main.js           # Electron main process
│       │   ├── preload.js        # Preload script
│       │   ├── package.json
│       │   └── src/
│       ├── python-backend/       # Python backend server
│       │   ├── server.py
│       │   ├── config.ini
│       │   └── requirements.txt
│       ├── START.bat             # Windows launcher
│       ├── START.sh              # Unix launcher
│       ├── START_BACKEND.bat
│       └── START_ELECTRON.bat
│
├── docs/                         # Documentation
│   ├── README.md                 # This file
│   ├── ARCHITECTURE.md           # System architecture
│   └── CLAIM_EXTRACTOR_COST_ANALYSIS.md
│
└── pyproject.toml                # Project configuration
```

### Key Files

- **`apps/streamlit/standalone_app.py`** - Main Streamlit application with 4 modes
- **`apps/streamlit/export_excel.py`** - Professional Excel report generator
- **`apps/agent/claim_extractor/agent.py`** - Claimify-based extraction pipeline
- **`apps/agent/claim_verifier/agent.py`** - Evidence-based verification logic
- **`apps/agent/fact_checker/agent.py`** - Main orchestrator with parallel processing
- **`apps/agent/utils/metrics.py`** - Real-time cost and usage tracking

## 🙏 Thanks to the Giants

This project wouldn't have been possible without:

* Dasha Metropolitansky & Jonathan Larson from Microsoft Research - their Claimify methodology is brilliant
* Jerry Wei and team at Google DeepMind - their SAFE paper had some useful ideas for evidence retrieval
* The LangChain team - LangGraph made the complex workflows so much easier
* OpenAI - for the LLMs that power the text understanding
* Tavily AI - their search API is perfect for this use case

I've learned a ton working on this project. If you use it or have ideas for improvements, I'd love to hear about it! Contributions are always welcome - whether it's code, suggestions, or even just sharing how you're using it. Let's make this thing even better together.

## 🛣️ Roadmap

### Completed ✅
- ✅ Multi-agent architecture with LangGraph
- ✅ 4 operation modes (Full Text, Single Fact, Claim Extraction, Video)
- ✅ Video fact-checking with Whisper transcription
- ✅ Multi-language support (100+ languages)
- ✅ Professional Excel reports with formatting
- ✅ Real-time cost tracking dashboard
- ✅ Parallel claim verification with rate limiting
- ✅ Authoritative source detection
- ✅ Desktop app (Electron + Python)
- ✅ Streamlit web interface

### In Progress 🔄
- 🔄 **Evaluation agent** - Assess fact-checking accuracy and reliability
- 🔄 **Performance benchmarks** - Compare against human fact-checkers
- 🔄 **Caching layer** - Redis-based result caching

### Planned 📋
- 📋 **Public API service** - RESTful API for external integrations
- 📋 **Batch processing** - Handle multiple files/videos at once
- 📋 **Custom model support** - Allow local LLMs (Ollama, LLaMA)
- 📋 **Web scraping fallback** - Direct crawling when Tavily unavailable
- 📋 **Citation graph** - Visualize evidence connections
- 📋 **Real-time mode** - Process streaming text/audio
- 📋 **Browser extension** - Fact-check while browsing
- 📋 **Mobile app** - iOS/Android support

## � Contributing

Contributions are welcome! Here's how you can help:

### Getting Started
1. **Fork** the repository
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Test thoroughly** - run all agents, check Excel export, verify metrics
5. **Commit**: `git commit -m 'Add amazing feature'`
6. **Push**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Contribution Guidelines
- ✅ **Code Style**: Follow existing patterns and PEP 8
- ✅ **Documentation**: Update README/docstrings for new features
- ✅ **Testing**: Add tests for new functionality
- ✅ **Dependencies**: Minimize new dependencies when possible
- ✅ **Compatibility**: Ensure Python 3.11+ compatibility

### Areas for Contribution
- 🔧 **Performance**: Optimize LLM calls, reduce latency
- 🌐 **Languages**: Improve translation accuracy
- 📊 **Analytics**: Enhanced metrics and visualizations
- 🧪 **Testing**: Unit tests, integration tests
- 📝 **Documentation**: Tutorials, examples, API docs
- 🐛 **Bug Fixes**: Always appreciated!

### Reporting Issues
Use the [GitHub Issue Tracker](https://github.com/bharathxd/ClaimAI/issues):
- 🐛 **Bugs**: Include steps to reproduce, error messages, environment details
- 💡 **Feature Requests**: Describe use case and expected behavior
- ❓ **Questions**: Ask about usage, implementation, or architecture

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.

## � Contact & Support

- **Issues**: Please use the [GitHub Issue Tracker](https://github.com/bharathxd/agent/issues) to report bugs or request features
- **Email**: [bharathxxd@gmail.com](mailto:bharathxxd@gmail.com)
- **Twitter**: [@Bharath_uwu](https://twitter.com/bharath_uwu)
