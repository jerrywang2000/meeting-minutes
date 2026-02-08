from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
from typing import Optional, List
import logging
from dotenv import load_dotenv
from db import DatabaseManager
import json
from threading import Lock
from transcript_processor import TranscriptProcessor, SummaryResponse
from incremental_summarizer import IncrementalSummarizer
import time

# Load environment variables
load_dotenv()

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d - %(funcName)s()] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(console_handler)

app = FastAPI(
    title="Meeting Summarizer API",
    description="API for processing and summarizing meeting transcripts",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# Global instances
db = DatabaseManager()
active_summarizers = {}

# --- Pydantic Models ---

class Transcript(BaseModel):
    id: str
    text: str
    timestamp: str
    audio_start_time: Optional[float] = None
    audio_end_time: Optional[float] = None
    duration: Optional[float] = None

class MeetingResponse(BaseModel):
    id: str
    title: str

class MeetingDetailsResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    transcripts: List[Transcript]

class MeetingTitleUpdate(BaseModel):
    meeting_id: str
    title: str

class DeleteMeetingRequest(BaseModel):
    meeting_id: str

class SaveTranscriptRequest(BaseModel):
    meeting_title: str
    transcripts: List[Transcript]
    folder_path: Optional[str] = None

class SaveModelConfigRequest(BaseModel):
    provider: str
    model: str
    whisperModel: str
    apiKey: Optional[str] = None

class SaveTranscriptConfigRequest(BaseModel):
    provider: str
    model: str
    apiKey: Optional[str] = None

class TranscriptRequest(BaseModel):
    text: str
    model: str
    model_name: str
    meeting_id: str
    chunk_size: Optional[int] = 5000
    overlap: Optional[int] = 1000
    custom_prompt: Optional[str] = "Generate a summary of the meeting transcript."

class IncrementalStartRequest(BaseModel):
    meeting_id: str
    model_provider: str
    model_name: str
    custom_prompt: Optional[str] = ""
    api_key: Optional[str] = None

class IncrementalAddChunkRequest(BaseModel):
    meeting_id: str
    text_chunk: str

class IncrementalEndRequest(BaseModel):
    meeting_id: str

class MeetingSummaryUpdate(BaseModel):
    meeting_id: str
    summary: dict

class SearchRequest(BaseModel):
    query: str

class GetApiKeyRequest(BaseModel):
    provider: str


# --- V2 Incremental Summarization Endpoints ---

@app.post("/v2/summarize/start")
async def api_v2_start_summarization(request: IncrementalStartRequest):
    meeting_id = request.meeting_id
    logger.info(f"🚀 [Start] Received summary start request for {meeting_id}. Provider: {request.model_provider}, Model: {request.model_name}")
    if meeting_id in active_summarizers:
        logger.warning(f"⚠️ [Start] Summarization already in progress for {meeting_id}")
        raise HTTPException(status_code=409, detail=f"Summarization for meeting {meeting_id} is already in progress.")
    try:
        summarizer = IncrementalSummarizer(
            meeting_id=meeting_id,
            model_provider=request.model_provider,
            model_name=request.model_name,
            custom_prompt=request.custom_prompt,
            db_manager=db
        )
        await summarizer.initialize(api_key=request.api_key)
        active_summarizers[meeting_id] = summarizer
        logger.info(f"✅ [Start] Initialized summarizer for {meeting_id} using {request.model_provider}/{request.model_name}")
        return JSONResponse(status_code=200, content={"message": "Summarization session started successfully."})
    except Exception as e:
        logger.error(f"❌ [Start] Failed to start for {meeting_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v2/summarize/add_chunk", response_model=SummaryResponse)
async def api_v2_add_chunk(request: IncrementalAddChunkRequest):
    meeting_id = request.meeting_id
    summarizer = active_summarizers.get(meeting_id)
    if not summarizer:
        logger.error(f"❌ [AddChunk] 404 Not Found: {meeting_id}. Active sessions: {list(active_summarizers.keys())}")
        raise HTTPException(status_code=404, detail=f"No active summarization session found for meeting {meeting_id}.")
    try:
        logger.debug(f"📥 [AddChunk] Adding chunk to {meeting_id} (Length: {len(request.text_chunk)})")
        updated_summary = await summarizer.add_transcript_chunk(request.text_chunk)
        
        # Debug: Print the data structure being sent
        from fastapi.encoders import jsonable_encoder
        json_data = jsonable_encoder(updated_summary)
        logger.debug(f"📤 [AddChunk] Returning JSON structure (keys): {list(json_data.keys())}")
        
        return updated_summary
    except Exception as e:
        logger.error(f"❌ [AddChunk] Failed for {meeting_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v2/summarize/end")
async def api_v2_end_summarization(request: IncrementalEndRequest):
    meeting_id = request.meeting_id
    summarizer = active_summarizers.get(meeting_id)
    if not summarizer:
        logger.info(f"ℹ️ [End] Session {meeting_id} not found in memory. It may have already been closed.")
        # Attempt to return successful status if the process is already in DB
        return JSONResponse(status_code=200, content={"message": "Summarization session already ended or not found.", "status": "already_closed"})
    try:
        logger.info(f"🏁 [End] Ending summarization for {meeting_id}")
        final_summary = await summarizer.get_final_summary()
        
        # Debug: Print final summary content
        logger.info(f"📊 [End] Final Summary for {meeting_id}:")
        logger.info(f"  - Title: {final_summary.meeting_name}")
        logger.info(f"  - Summary Blocks: {len(final_summary.session_summary.blocks)}")
        if final_summary.session_summary.blocks:
            for i, block in enumerate(final_summary.session_summary.blocks):
                logger.info(f"    [{i}] {block.content[:100]}...")

        process_id = await db.create_process(meeting_id)
        await db.update_process(process_id, status="completed", result=final_summary.model_dump_json())
        summarizer.cleanup()
        if meeting_id in active_summarizers:
            del active_summarizers[meeting_id]
        logger.info(f"💾 [End] Saved final summary for {meeting_id}")
        return JSONResponse(status_code=200, content={"message": "Summarization session ended successfully.", "final_summary": final_summary.model_dump()})
    except Exception as e:
        logger.error(f"❌ [End] Failed for {meeting_id}: {e}", exc_info=True)
        if meeting_id in active_summarizers:
            active_summarizers[meeting_id].cleanup()
            del active_summarizers[meeting_id]
        raise HTTPException(status_code=500, detail=str(e))


# --- Other Endpoints ---

@app.get("/get-meetings", response_model=List[MeetingResponse])
async def get_meetings():
    try:
        meetings = await db.get_all_meetings()
        return [{"id": meeting["id"], "title": meeting["title"]} for meeting in meetings]
    except Exception as e:
        logger.error(f"Error getting meetings: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-meeting/{meeting_id}", response_model=MeetingDetailsResponse)
async def get_meeting(meeting_id: str):
    try:
        meeting = await db.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        return meeting
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting meeting: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save-meeting-title")
async def save_meeting_title(data: MeetingTitleUpdate):
    try:
        await db.update_meeting_title(data.meeting_id, data.title)
        return {"message": "Meeting title saved successfully"}
    except Exception as e:
        logger.error(f"Error saving meeting title: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/delete-meeting")
async def delete_meeting(data: DeleteMeetingRequest):
    try:
        success = await db.delete_meeting(data.meeting_id)
        if success:
            return {"message": "Meeting deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete meeting")
    except Exception as e:
        logger.error(f"Error deleting meeting: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-transcript")
async def process_transcript_api(transcript: TranscriptRequest, background_tasks: BackgroundTasks):
    # This is the old endpoint. It is now disabled to prevent conflicts.
    logger.warning("The old /process-transcript endpoint is disabled.")
    raise HTTPException(status_code=410, detail="This endpoint is deprecated. Please use the v2 endpoints.")

@app.get("/get-summary/{meeting_id}")
async def get_summary(meeting_id: str):
    # This is the old endpoint for polling. It should still work for summaries saved by the v2/end endpoint.
    try:
        result = await db.get_transcript_data(meeting_id)
        if not result:
            return JSONResponse(status_code=404, content={"status": "error", "error": "Meeting ID not found"})
        # ... (The rest of the logic can stay as it reads from the DB)
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        logger.error(f"Error getting summary for {meeting_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/save-transcript")
async def save_transcript(request: SaveTranscriptRequest):
    try:
        logger.info(f"Received save-transcript request for meeting: {request.meeting_title}")
        meeting_id = f"meeting-{int(time.time() * 1000)}"
        await db.save_meeting(meeting_id, request.meeting_title, folder_path=request.folder_path)
        for transcript in request.transcripts:
            await db.save_meeting_transcript(
                meeting_id=meeting_id,
                transcript=transcript.text,
                timestamp=transcript.timestamp,
                summary="", action_items="", key_points="",
                audio_start_time=transcript.audio_start_time,
                audio_end_time=transcript.audio_end_time,
                duration=transcript.duration
            )
        return {"status": "success", "message": "Transcript saved successfully", "meeting_id": meeting_id}
    except Exception as e:
        logger.error(f"Error saving transcript: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ... (other non-conflicting endpoints like /get-model-config, etc. can be kept) ...

@app.get("/get-model-config")
async def get_model_config():
    """Get the current model configuration"""
    model_config = await db.get_model_config()
    if model_config:
        api_key = await db.get_api_key(model_config["provider"])
        if api_key != None:
            model_config["apiKey"] = api_key
    return model_config

@app.post("/save-model-config")
async def save_model_config(request: SaveModelConfigRequest):
    """Save the model configuration"""
    await db.save_model_config(request.provider, request.model, request.whisperModel)
    if request.apiKey != None:
        await db.save_api_key(request.apiKey, request.provider)
    return {"status": "success", "message": "Model configuration saved successfully"}  

@app.get("/get-transcript-config")
async def get_transcript_config():
    """Get the current transcript configuration"""
    transcript_config = await db.get_transcript_config()
    if transcript_config:
        transcript_api_key = await db.get_transcript_api_key(transcript_config["provider"])
        if transcript_api_key != None:
            transcript_config["apiKey"] = transcript_api_key
    return transcript_config

@app.post("/save-transcript-config")
async def save_transcript_config(request: SaveTranscriptConfigRequest):
    """Save the transcript configuration"""
    await db.save_transcript_config(request.provider, request.model)
    if request.apiKey != None:
        await db.save_transcript_api_key(request.apiKey, request.provider)
    return {"status": "success", "message": "Transcript configuration saved successfully"}

@app.post("/get-api-key")
async def get_api_key(request: GetApiKeyRequest):
    try:
        return await db.get_api_key(request.provider)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get-transcript-api-key")
async def get_transcript_api_key(request: GetApiKeyRequest):
    try:
        return await db.get_transcript_api_key(request.provider)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/save-meeting-summary")
async def save_meeting_summary(data: MeetingSummaryUpdate):
    try:
        await db.update_meeting_summary(data.meeting_id, data.summary)
        return {"message": "Meeting summary saved successfully"}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search-transcripts")
async def search_transcripts(request: SearchRequest):
    try:
        results = await db.search_transcripts(request.query)
        return JSONResponse(content=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("API shutting down.")
    # No processor to clean up

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    uvicorn.run("main:app", host="0.0.0.0", port=5167)