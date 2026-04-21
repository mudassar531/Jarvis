"""
JARVIS Voice Agent — FastAPI WebSocket Server
Exposes the voice agent pipeline over WebSocket for browser clients.
"""

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.transports.network.fastapi_websocket import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams,
)

from bot import create_pipeline

load_dotenv()

app = FastAPI(title="JARVIS Voice Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Minimal test page
TEST_PAGE = """
<!DOCTYPE html>
<html>
<head><title>JARVIS Voice Agent</title></head>
<body style="font-family: sans-serif; max-width: 600px; margin: 50px auto; text-align: center;">
    <h1>🎙️ JARVIS Voice Agent</h1>
    <p>WebSocket server is running at <code>ws://localhost:8080/ws</code></p>
    <p>Connect a Pipecat client or the React frontend to start talking.</p>
    <p style="color: #666;">Status: <span style="color: green;">● Online</span></p>
</body>
</html>
"""


@app.get("/")
async def root():
    return HTMLResponse(TEST_PAGE)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.info("New WebSocket connection")

    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    pipeline = await create_pipeline(transport)
    task = PipelineTask(
        pipeline,
        PipelineParams(allow_interruptions=True),
    )
    runner = PipelineRunner()

    try:
        await runner.run(task)
    except Exception as e:
        logger.error(f"Pipeline error: {e}")
    finally:
        logger.info("WebSocket connection closed")


if __name__ == "__main__":
    logger.info("Starting JARVIS server on http://localhost:8080")
    uvicorn.run(app, host="0.0.0.0", port=8080)
