from flask import Flask, request, jsonify
from transformers import pipeline

app = Flask(__name__)

# Load the summarization model
summarizer = pipeline("summarization", model="t5-small")

def trim_text_middle(text, ratio=0.5):
    """
    Trims the middle of the text based on the specified ratio.
    Returns the shortened version.
    """
    words = text.split()
    total_words = len(words)
    
    if total_words <= 150:
        return text
    
    trim_size = int(total_words * ratio)
    start = (total_words - trim_size) // 2
    end = start + trim_size 

    return " ".join(words[start:end])

@app.route('/validate_audio', methods=['POST'])
def handle_audio_validation():
    """
    Endpoint to accept a JSON with 'text' and 'length' fields.
    If the text exceeds 60 seconds, trims and summarizes it.
    """
    data = request.json or {}
    text = data.get("text", "")
    length = data.get("length", 0)

    if not text:
        return jsonify({"error": "The 'text' field is missing."}), 400

    # If the length is less than or equal to 60 seconds, return original text
    if length <= 60:
        return jsonify({"message": text})

    # Trim and summarize the text if the length exceeds the threshold
    trimmed_text = trim_text_middle(text)
    summary = summarizer(trimmed_text, max_length=100, min_length=50, do_sample=False)[0]['summary_text']

    return jsonify({"message": summary})

if __name__ == '__main__':
    app.run(debug=True)