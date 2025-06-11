from fastapi import FastAPI, HTTPException, Body
from mp_api.client import MPRester
from pydantic import BaseModel, Field
from typing import List, Optional
import os

app = FastAPI(
    title="MateriaScout MCP Server",
    description="A server to interact with the Materials Project API.",
    version="1.0.0",
)

class SearchCriteria(BaseModel):
    elements: List[str] = Field(..., example=["Fe", "O"], description="A list of element symbols to search for.")
    properties: List[str] = Field(..., example=["band_gap", "density"], description="A list of material properties to return.")
    api_key: str = Field(..., description="Your Materials Project API key.")
    max_results: int = Field(20, ge=1, le=200, description="Maximum number of results to return.")

class ApiKeyModel(BaseModel):
    api_key: str

@app.post("/properties")
async def get_available_properties(criteria: ApiKeyModel):
    """
    Returns a list of available material summary properties.
    """
    try:
        with MPRester(api_key=criteria.api_key) as mpr:
            available_fields = mpr.materials.summary.available_fields
            return {"properties": available_fields}
    except Exception as e:
        if "API_KEY" in str(e) or "query for key" in str(e):
            raise HTTPException(status_code=401, detail=f"Authentication error with Materials Project API: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching properties: {e}")

@app.post("/search")
async def search_materials(criteria: SearchCriteria):
    """
    Searches for materials based on the provided criteria.
    """
    try:
        with MPRester(api_key=criteria.api_key) as mpr:
            docs = mpr.materials.summary.search(
                elements=criteria.elements,
                fields=criteria.properties
            )
            # Manually limit the number of results, as the API does not support a direct limit parameter.
            limited_docs = docs[:criteria.max_results]
            data = [doc.dict() for doc in limited_docs]
            return {"data": data}
            
    except Exception as e:
        if "API_KEY" in str(e) or "query for key" in str(e):
            raise HTTPException(status_code=401, detail=f"Authentication error with Materials Project API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "MateriaScout MCP Server is running."}

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 