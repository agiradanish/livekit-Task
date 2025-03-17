import asyncio
import logging
import requests
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    metrics,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import deepgram, openai, silero

load_dotenv()
logger = logging.getLogger("voice-assistant")

# Flask API endpoint for audio validation
FLASK_API_URL = "https://7f01-27-4-44-174.ngrok-free.app/validate_audio"

async def stream_to_text(stream):
    """Helper to extract text from an async generator."""
    return "".join([chunk async for chunk in stream])

def calculate_audio_duration(text):
    """Estimate audio duration assuming 150 words per 60 seconds."""
    words_per_second = 150 / 60
    word_count = len(text.split())
    return word_count / words_per_second    

async def validate_text_before_tts(agent, text_stream):
    """
    Callback to process text before passing to TTS.
    Extract text, estimate duration, and validate via Flask API.
    """
    if isinstance(text_stream, str):
        text = text_stream  
    else:
        text = await stream_to_text(text_stream)  

    estimated_length = calculate_audio_duration(text)
    
    logger.debug(f"Text before validation: {text}")

    # Send text and length to Flask for validation
    response = requests.post(FLASK_API_URL, json={"length": estimated_length, "text": text})

    if response.ok:
        validated_text = response.json().get("message", text)
        logger.debug(f"Text after validation: {validated_text}")
        return validated_text
    return text  # Fallback to original text on failure

def initialize_job(proc: JobProcess):
    """Pre-warm the job process by loading necessary components."""
    proc.userdata["vad"] = silero.VAD.load()

async def run_voice_assistant(ctx: JobContext):
    """Main entry point for voice assistant."""
    initial_context = llm.ChatContext().append(
        role="system",
        text=(
            "You are a voice assistant created by LiveKit. Interact using voice responses. "
            "Be concise, and avoid unpronounceable punctuation."
        ),
    )

    logger.info(f"Connecting to room: {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()
    logger.info(f"Starting assistant for participant: {participant.identity}")

    dg_model = "nova-3-general" if participant.kind != rtc.ParticipantKind.PARTICIPANT_KIND_SIP else "nova-2-phonecall"

    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(model=dg_model),
        llm=openai.LLM(),
        tts=openai.TTS(),
        chat_ctx=initial_context,
        before_tts_cb=validate_text_before_tts,  # Validate before TTS
    )

    agent.start(ctx.room, participant)

    # Usage tracking
    usage_tracker = metrics.UsageCollector()

    @agent.on("metrics_collected")
    def handle_metrics_collection(metrics_data: metrics.AgentMetrics):
        metrics.log_metrics(metrics_data)
        usage_tracker.collect(metrics_data)

    async def log_usage_summary():
        summary = usage_tracker.get_summary()
        logger.info(f"Usage summary: ${summary}")

    ctx.add_shutdown_callback(log_usage_summary)

    # Manage incoming chat messages if needed
    chat_manager = rtc.ChatManager(ctx.room)

    async def handle_chat_message(txt: str):
        chat_context = agent.chat_ctx.copy().append(role="user", text=txt)
        response_stream = agent.llm.chat(chat_ctx=chat_context)
        await agent.say(response_stream)

    @chat_manager.on("message_received")
    def on_chat_message(msg: rtc.ChatMessage):
        if msg.message:
            asyncio.create_task(handle_chat_message(msg.message))

    await agent.say("Hey, how can I assist you today?", allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=run_voice_assistant,
            prewarm_fnc=initialize_job,
        ),
    )
