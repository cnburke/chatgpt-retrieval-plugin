import logging
import os
from typing import Optional

import uvicorn
from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles

from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
)
from datastore.factory import get_datastore
from services.file import get_document_from_file

from models.models import DocumentMetadata, Source

# Configure logging before the application starts so every module can use it.
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer()
BEARER_TOKEN = os.environ.get("BEARER_TOKEN")
if BEARER_TOKEN is None:
    logger.error("BEARER_TOKEN environment variable must be set")
    raise RuntimeError("Missing BEARER_TOKEN environment variable")


def validate_token(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if credentials.scheme != "Bearer" or credentials.credentials != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return credentials


app = FastAPI(dependencies=[Depends(validate_token)])
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

# Create a sub-application, in order to access just the query endpoint in an OpenAPI schema, found at http://0.0.0.0:8000/sub/openapi.json when the app is running locally
sub_app = FastAPI(
    title="Retrieval Plugin API",
    description="A retrieval API for querying and filtering documents based on natural language queries and metadata",
    version="1.0.0",
    servers=[{"url": "https://your-app-url.com"}],
    dependencies=[Depends(validate_token)],
)
app.mount("/sub", sub_app)


@app.post(
    "/upsert-file",
    response_model=UpsertResponse,
)
async def upsert_file(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form(None),
):
    logger.info("Received /upsert-file request for filename '%s'", file.filename)
    try:
        metadata_obj = (
            DocumentMetadata.parse_raw(metadata)
            if metadata
            else DocumentMetadata(source=Source.file)
        )
    except Exception:
        logger.exception("Failed to parse metadata for /upsert-file request")
        metadata_obj = DocumentMetadata(source=Source.file)

    document = await get_document_from_file(file, metadata_obj)

    try:
        ids = await datastore.upsert([document])
        return UpsertResponse(ids=ids)
    except Exception:
        logger.exception("Failed to upsert document derived from file '%s'", file.filename)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.post(
    "/upsert",
    response_model=UpsertResponse,
)
async def upsert(
    request: UpsertRequest = Body(...),
):
    logger.info("Received /upsert request with %d documents", len(request.documents))
    try:
        ids = await datastore.upsert(request.documents)
        logger.debug("Upserted documents with ids: %s", ids)
        return UpsertResponse(ids=ids)
    except Exception:
        logger.exception("Failed to upsert documents via /upsert endpoint")
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.post(
    "/query",
    response_model=QueryResponse,
)
async def query_main(
    request: QueryRequest = Body(...),
):
    logger.info("Received /query request with %d queries", len(request.queries))
    try:
        results = await datastore.query(
            request.queries,
        )
        logger.debug("Query returned %d result sets", len(results))
        return QueryResponse(results=results)
    except Exception:
        logger.exception("Failed to process /query request")
        raise HTTPException(status_code=500, detail="Internal Service Error")


@sub_app.post(
    "/query",
    response_model=QueryResponse,
    # NOTE: We are describing the shape of the API endpoint input due to a current limitation in parsing arrays of objects from OpenAPI schemas. This will not be necessary in the future.
    description="Accepts search query objects array each with query and optional filter. Break down complex questions into sub-questions. Refine results by criteria, e.g. time / source, don't do this often. Split queries if ResponseTooLargeError occurs.",
)
async def query(
    request: QueryRequest = Body(...),
):
    logger.info("Received /sub/query request with %d queries", len(request.queries))
    try:
        results = await datastore.query(
            request.queries,
        )
        logger.debug("/sub/query returned %d result sets", len(results))
        return QueryResponse(results=results)
    except Exception:
        logger.exception("Failed to process /sub/query request")
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.delete(
    "/delete",
    response_model=DeleteResponse,
)
async def delete(
    request: DeleteRequest = Body(...),
):
    if not (request.ids or request.filter or request.delete_all):
        raise HTTPException(
            status_code=400,
            detail="One of ids, filter, or delete_all is required",
        )
    logger.info(
        "Received /delete request (ids=%s, filter_present=%s, delete_all=%s)",
        request.ids,
        bool(request.filter),
        request.delete_all,
    )
    try:
        success = await datastore.delete(
            ids=request.ids,
            filter=request.filter,
            delete_all=request.delete_all,
        )
        logger.debug("/delete operation success=%s", success)
        return DeleteResponse(success=success)
    except Exception:
        logger.exception("Failed to process /delete request")
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.on_event("startup")
async def startup():
    global datastore
    logger.info("Starting application and initialising datastore")
    datastore = await get_datastore()
    logger.info("Datastore initialised: %s", datastore.__class__.__name__)


def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
