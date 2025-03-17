 # LiveKit Voice Assistant with Audio Validation & Summarization
## Overview
This project implements a voice assistant using LiveKit's Voice Pipeline Agent, integrating audio length validation and text summarization. It ensures audio does not exceed 60 seconds by sending length validation to a Flask server, which trims and summarizes long responses using Hugging Face's BART model.

# Features

LiveKit Voice Assistant for real-time interaction

Pre-TTS Validation to check estimated audio length

Flask Backend API to handle validation & processing

Text Summarization for long responses (using Hugging Face)

Ngrok Integration for easy backend exposure

# How It Works

User interacts with the LiveKit Voice Agent.

Before text is sent to TTS, its estimated audio length is calculated.

The estimated length is sent to the Flask API for validation.

If the duration exceeds 60 seconds, the middle portion of the text is trimmed and summarized.

The modified text is returned and processed by TTS.

### Note This repository only includes task file modifications for integrating audio validation and summarization.  please refer to the official GitHub repository:

#### LiveKit Agents GitHub: https://github.com/livekit/agents/tree/main/examples/voice-pipeline-agent
