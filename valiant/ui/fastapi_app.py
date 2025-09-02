from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
from pathlib import Path
import sys
from typing import Dict, Any, List, Optional

# Add project root to Python path
current_dir = Path(__file__).parent
project_root = current_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import after setting path
from valiant.framework.api import ValiantAPI
from valiant.ui.logger import fastapi_logger

app = FastAPI(
    title="Valiant Workflow API",
    version="1.0.0",
    description="REST API for executing Valiant validation workflows",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    fastapi_logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    fastapi_logger.info(f"Response status: {response.status_code}")
    return response


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Valiant Workflow API",
        "version": "1.0.0",
        "endpoints": {
            "workflows": "/workflows",
            "workflow_schema": "/workflows/{workflow_name}/schema",
            "run_workflow": "/run/{workflow_name}"
        },
        "documentation": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "valiant-api"}


@app.get("/workflows")
async def list_workflows():
    """Get all available workflows"""
    try:
        workflows = ValiantAPI.list_workflows()
        return {
            "success": True,
            "data": workflows,
            "count": len(workflows)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")


@app.get("/workflows/{workflow_name}")
async def get_workflow_info(workflow_name: str):
    """Get information about a specific workflow"""
    try:
        workflows = ValiantAPI.list_workflows()
        if workflow_name not in workflows:
            raise HTTPException(status_code=404, detail=f"Workflow '{workflow_name}' not found")

        return {
            "success": True,
            "data": {
                "name": workflow_name,
                "class_path": workflows[workflow_name],
                "schema_endpoint": f"/workflows/{workflow_name}/schema",
                "run_endpoint": f"/run/{workflow_name}"
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow info: {str(e)}")


@app.get("/workflows/{workflow_name}/schema")
async def get_workflow_schema(workflow_name: str):
    """Get input schema for a specific workflow"""
    try:
        schema = ValiantAPI.get_workflow_input_schema(workflow_name)
        return {
            "success": True,
                            "data": schema,
            "workflow": workflow_name,
            "field_count": len(schema)
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get workflow schema: {str(e)}")


@app.post("/run/{workflow_name}")
async def run_workflow(workflow_name: str, config: Optional[Dict[str, Any]] = None):
    """Execute a workflow with provided configuration"""
    config = config or {}

    try:
        # Extract parameters with defaults
        environment = config.get('environment', 'dev')
        timeout = config.get('timeout', 30.0)
        retries = config.get('retries', 1)
        context_overrides = config.get('context', {})

        # Use provided context or defaults
        if not context_overrides:
            context_overrides = {
                'demo_text': 'Hello Enhanced Framework!',
                'demo_number': 42,
                'demo_select': 'option1',
                'enable_advanced': False
            }

        # Validate parameters
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise HTTPException(status_code=400, detail="Timeout must be a positive number")

        if not isinstance(retries, int) or retries < 0:
            raise HTTPException(status_code=400, detail="Retries must be a non-negative integer")

        # Execute workflow
        result = await ValiantAPI.run_workflow(
            workflow_name=workflow_name,
            environment=environment,
            timeout=timeout,
            retries=retries,
            context_overrides=context_overrides
        )

        # Process the results to ensure metrics and tags are included
        formatted_results = []
        for r in result["results"]:
            step_result = {
                "name": str(r["name"]),
                "success": bool(r["success"]),
                "message": str(r["message"]),
                "skipped": bool(r["skipped"]),
                "executed": bool(r["executed"]),
                "time_taken": float(r["time_taken"]),
                "attempts": int(r["attempts"]),
                "metadata": {},  # We're not using metadata anymore
                "derived_metrics": r.get("derived_metrics", {}),
                "step_config": r.get("_step_config", {}),
                "tags": r.get("tags", [])
            }
            formatted_results.append(step_result)

        return {
            "success": True,
            "workflow": workflow_name,
            "environment": environment,
            "execution_summary": {
                "overall_success": result["success"],
                "total_steps": len(result["results"]),
                "executed_steps": sum(1 for r in result["results"] if r["executed"]),
                "successful_steps": sum(1 for r in result["results"] if r["success"] and r["executed"]),
                "failed_steps": sum(1 for r in result["results"] if not r["success"] and r["executed"]),
                "skipped_steps": sum(1 for r in result["results"] if r["skipped"]),
                "total_time": sum(r["time_taken"] for r in result["results"] if r["executed"])
            },
            "results": formatted_results,
            "context": result["context"]
        }
            
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute workflow: {str(e)}")


@app.post("/run/{workflow_name}/sync")
async def run_workflow_sync(workflow_name: str, config: Optional[Dict[str, Any]] = None):
    """
    Execute a workflow synchronously with simplified response
    """
    config = config or {}

    try:
        result = await ValiantAPI.run_workflow(
            workflow_name=workflow_name,
            environment=config.get('environment', 'dev'),
            timeout=config.get('timeout', 30.0),
            retries=config.get('retries', 1),
            context_overrides=config.get('context', {})
        )

        # Simplified response
        return {
            "workflow": workflow_name,
            "status": "success" if result["success"] else "failed",
            "steps": {
                "total": len(result["results"]),
                "executed": sum(1 for r in result["results"] if r["executed"]),
                "successful": sum(1 for r in result["results"] if r["success"] and r["executed"]),
                "failed": sum(1 for r in result["results"] if not r["success"] and r["executed"])
            },
            "failed_steps": [
                {
                    "name": r["name"],
                    "message": r["message"]
                }
                for r in result["results"] if not r["success"] and r["executed"]
            ]
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get API statistics"""
    try:
        workflows = ValiantAPI.list_workflows()
        return {
            "workflows_count": len(workflows),
            "workflows": list(workflows.keys()),
            "api_version": "1.0.0",
            "status": "operational"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"success": False, "error": "Not Found", "message": str(exc)}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal Server Error", "message": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="Valiant FastAPI Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    args = parser.parse_args()

    print(f"Starting Valiant API server on {args.host}:{args.port}")
    print(f"Documentation: http://{args.host}:{args.port}/docs")
    print(f"Health check: http://{args.host}:{args.port}/health")

    uvicorn.run(
        "fastapi_app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )
