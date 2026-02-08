"""
FastAPI server that wraps the existing LangGraph agents for the Electron desktop app.
This server provides REST API endpoints for all fact-checking operations.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List
import configparser

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Load API keys from config file
config = configparser.ConfigParser()
config_path = Path(__file__).parent / "config.ini"
if config_path.exists():
    config.read(config_path)
    os.environ['OPENAI_API_KEY'] = config.get('API_KEYS', 'OPENAI_API_KEY', fallback='')
    os.environ['TAVILY_API_KEY'] = config.get('API_KEYS', 'TAVILY_API_KEY', fallback='')
    print(f"Loaded API keys from {config_path}")
else:
    print(f"Config file not found at {config_path}")

# Add parent directories to path to import existing agents
agent_path = Path(__file__).parent.parent.parent / "agent"
sys.path.insert(0, str(agent_path))

# Import existing agent modules
try:
    from claim_extractor.agent import create_graph as create_extractor_graph
    from claim_verifier.agent import create_graph as create_verifier_graph
    
    # Create graph instances
    extractor_graph = create_extractor_graph()
    verifier_graph = create_verifier_graph()
    print("Successfully loaded claim extractor and verifier agents")
except ImportError as e:
    print(f"Warning: Could not import agents: {e}")
    extractor_graph = None
    verifier_graph = None

# Pydantic models
class HealthResponse(BaseModel):
    status: str
    version: str

class DetectLanguageRequest(BaseModel):
    text: str

class DetectLanguageResponse(BaseModel):
    language: str
    confidence: float

class TranslateRequest(BaseModel):
    text: str

class TranslateResponse(BaseModel):
    original: str
    translated: str
    source_language: str

class ExtractClaimsRequest(BaseModel):
    text: str
    translation: Optional[str] = None

class Claim(BaseModel):
    id: int
    text: str
    selected: bool = True

class ExtractClaimsResponse(BaseModel):
    claims: List[Claim]
    total_count: int

class VerifyClaimsRequest(BaseModel):
    claims: List[str]

class Evidence(BaseModel):
    url: str
    title: str
    snippet: str

class ClaimVerification(BaseModel):
    claim: str
    verdict: str
    explanation: str
    evidence: List[Evidence]
    confidence: float

class VerifyClaimsResponse(BaseModel):
    results: List[ClaimVerification]
    summary: dict

class VerifySingleFactRequest(BaseModel):
    fact: str

class ConfigRequest(BaseModel):
    openai_api_key: Optional[str] = None
    tavily_api_key: Optional[str] = None

# Initialize FastAPI app
app = FastAPI(title="ClaimAI Backend API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global configuration
config = {
    "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
    "tavily_api_key": os.getenv("TAVILY_API_KEY", "")
}

# Helper functions
async def detect_language_llm(text: str) -> dict:
    """Detect language using OpenAI"""
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=config["openai_api_key"])
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Detect the language. Respond with ONLY the language name.\n\nText: {text[:500]}\n\nLanguage:"}],
            temperature=0
        )
        
        return {"language": response.choices[0].message.content.strip(), "confidence": 0.95}
    except Exception as e:
        return {"language": "English", "confidence": 0.5}

async def translate_text_llm(text: str) -> dict:
    """Translate text to English"""
    try:
        lang_result = await detect_language_llm(text)
        if lang_result["language"].lower() == "english":
            return {"original": text, "translated": text, "source_language": "English"}
        
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=config["openai_api_key"])
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Translate to English. Preserve facts.\n\nText: {text}\n\nTranslation:"}],
            temperature=0
        )
        
        return {"original": text, "translated": response.choices[0].message.content.strip(), "source_language": lang_result["language"]}
    except Exception as e:
        return {"original": text, "translated": text, "source_language": "Unknown"}

# API Endpoints
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}

@app.post("/api/config")
async def update_config(request: ConfigRequest):
    if request.openai_api_key:
        config["openai_api_key"] = request.openai_api_key
        os.environ["OPENAI_API_KEY"] = request.openai_api_key
    if request.tavily_api_key:
        config["tavily_api_key"] = request.tavily_api_key
        os.environ["TAVILY_API_KEY"] = request.tavily_api_key
    return {"status": "success"}

@app.post("/api/detect-language")
async def detect_language(request: DetectLanguageRequest):
    return await detect_language_llm(request.text)

@app.post("/api/translate")
async def translate_text(request: TranslateRequest):
    return await translate_text_llm(request.text)

@app.post("/api/extract-claims")
async def extract_claims(request: ExtractClaimsRequest):
    try:
        if not extractor_graph:
            raise HTTPException(503, "Extractor not available")
        
        text = request.translation or request.text
        result = await extractor_graph.ainvoke({"text": text})
        
        claims_list = result.get("claims", [])
        if isinstance(claims_list, str):
            claims_list = [c.strip() for c in claims_list.split('\n') if c.strip()]
        
        claims = [{"id": i+1, "text": c, "selected": True} for i, c in enumerate(claims_list)]
        return {"claims": claims, "total_count": len(claims)}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/verify-claims")
async def verify_claims(request: VerifyClaimsRequest):
    try:
        if not verifier_graph:
            raise HTTPException(503, "Verifier not available")
        
        results = []
        for claim in request.claims:
            try:
                v = await verifier_graph.ainvoke({"claim": claim, "search_queries": [], "search_attempts": 0, "evidence": []})
                results.append({
                    "claim": claim,
                    "verdict": v.get("verdict", "Unverifiable"),
                    "explanation": v.get("justification", "No explanation"),
                    "evidence": [{"url": e.get("url", ""), "title": e.get("title", ""), "snippet": e.get("content", "")[:200]} for e in v.get("evidence", [])[:3]],
                    "confidence": 0.8
                })
            except Exception as e:
                results.append({"claim": claim, "verdict": "Error", "explanation": str(e), "evidence": [], "confidence": 0.0})
        
        verdicts = [r["verdict"] for r in results]
        summary = {
            "total": len(results),
            "true": verdicts.count("True"),
            "false": verdicts.count("False"),
            "partially_true": verdicts.count("Partially True"),
            "unverifiable": verdicts.count("Unverifiable"),
            "error": verdicts.count("Error")
        }
        return {"results": results, "summary": summary}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/verify-single")
async def verify_single(request: VerifySingleFactRequest):
    try:
        if not verifier_graph:
            raise HTTPException(503, "Verifier not available")
        
        # Create a ValidatedClaim object with required fields
        claim_obj = {
            "claim_text": request.fact,
            "is_complete_declarative": True,
            "disambiguated_sentence": request.fact,
            "original_sentence": request.fact,
            "original_index": 0
        }
        
        v = await verifier_graph.ainvoke({
            "claim": claim_obj,
            "search_queries": [],
            "search_attempts": 0,
            "evidence": []
        })
        
        # Debug: Print keys in response
        print(f"Verifier response keys: {list(v.keys())}")
        
        # Get verdict - it returns VerificationResult enum, need to get string value
        verdict_obj = v.get("verdict", "Unverifiable")
        if hasattr(verdict_obj, 'value'):
            verdict = verdict_obj.value.lower()
        elif isinstance(verdict_obj, str):
            verdict = verdict_obj.lower()
        else:
            verdict = str(verdict_obj).lower()
        
        # Get the explanation - try multiple fields
        explanation = (
            v.get("detailed_explanation") or 
            v.get("justification") or 
            v.get("reasoning") or 
            "The claim has been verified against available evidence."
        )
        
        # Clean up the explanation if it's too long
        if isinstance(explanation, str) and len(explanation) > 500:
            explanation = explanation[:500] + "..."
        
        # Format evidence properly
        evidence_list = []
        for e in v.get("evidence", [])[:3]:
            if hasattr(e, '__dict__'):
                # It's an Evidence object
                evidence_list.append({
                    "url": getattr(e, 'url', ''),
                    "title": getattr(e, 'title', 'Source'),
                    "snippet": (getattr(e, 'text', '') or getattr(e, 'content', ''))[:300]
                })
            elif isinstance(e, dict):
                evidence_list.append({
                    "url": e.get("url", ""),
                    "title": e.get("title", "Source"),
                    "snippet": (e.get("text", "") or e.get("content", ""))[:300]
                })
        
        # Return ONLY clean data - do not include claim object
        result = {
            "claim": str(request.fact),  # Force string conversion
            "verdict": verdict,
            "explanation": str(explanation),  # Force string conversion
            "evidence": evidence_list
        }
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8765))
    print(f"ClaimAI Backend starting on port {port}...")
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
