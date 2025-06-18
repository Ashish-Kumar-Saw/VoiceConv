import streamlit as st
import os
from dotenv import load_dotenv
import speech_recognition as sr
from gtts import gTTS
import tempfile
import time
import pygame
import threading

# Try importing google.generativeai with error handling
try:
    import google.generativeai as genai
    USING_GEMINI = True
except ImportError:
    USING_GEMINI = False
    st.error("Oops! Something is missing.")

# Load environment variables securely
load_dotenv()

# Configure the page with minimal theme
st.set_page_config(
    page_title="Voice AI",
    page_icon="🎤",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Initialize pygame mixer for reliable audio playback
pygame.mixer.init()

# Custom CSS for minimal interface with improved button alignment
st.markdown("""
<style>
    .main {
        background-color: #ffffff;
        padding: 0;
        max-width: 100%;
    }
    
    /* Hide default header */
    header {
        visibility: hidden;
    }
    
    /* Animated pulsing circle */
    .ai-circle {
        width: 200px;
        height: 200px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(147,51,234,0.8) 0%, rgba(192,132,252,0.4) 70%, rgba(216,180,254,0) 100%);
        margin: 50px auto;
        display: flex;
        justify-content: center;
        align-items: center;
        animation: pulse 2s infinite ease-in-out;
        position: relative;
    }
    
    .ai-circle-inner {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(236,72,153,1) 0%, rgba(244,114,182,0.6) 70%, rgba(251,207,232,0) 100%);
        position: absolute;
    }
    
    @keyframes pulse {
        0% { transform: scale(0.95); }
        50% { transform: scale(1.05); }
        100% { transform: scale(0.95); }
    }
    
    .ai-circle.listening {
        animation: listen 1s infinite ease-in-out;
        background: radial-gradient(circle, rgba(59,130,246,0.8) 0%, rgba(96,165,250,0.4) 70%, rgba(191,219,254,0) 100%);
    }
    
    @keyframes listen {
        0% { transform: scale(0.95); opacity: 0.8; }
        50% { transform: scale(1.1); opacity: 1; }
        100% { transform: scale(0.95); opacity: 0.8; }
    }
    
    .ai-circle.thinking {
        animation: think 1.5s infinite ease-in-out;
        background: radial-gradient(circle, rgba(234,179,8,0.8) 0%, rgba(250,204,21,0.4) 70%, rgba(254,240,138,0) 100%);
    }
    
    @keyframes think {
        0% { transform: scale(0.95) rotate(0deg); }
        50% { transform: scale(1.05) rotate(10deg); }
        100% { transform: scale(0.95) rotate(0deg); }
    }
    
    .ai-circle.speaking {
        animation: speak 0.8s infinite ease-in-out;
        background: radial-gradient(circle, rgba(16,185,129,0.8) 0%, rgba(52,211,153,0.4) 70%, rgba(167,243,208,0) 100%);
    }
    
    @keyframes speak {
        0% { transform: scale(0.98); }
        25% { transform: scale(1.02); }
        50% { transform: scale(0.98); }
        75% { transform: scale(1.02); }
        100% { transform: scale(0.98); }
    }
    
    /* Chat bubble for response */
    .response-bubble {
        background: #f3e8ff;
        border-radius: 20px;
        padding: 15px;
        margin: 20px auto;
        max-width: 80%;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    /* IMPROVED BUTTON STYLING */
    .stButton > button {
        width: 70px !important;
        height: 70px !important;
        border-radius: 50% !important;
        border: 2px solid #a855f7 !important;
        background: #a855f7 !important;
        color: white !important;
        font-size: 30px !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        padding: 0 !important;
        margin: 0 auto !important; /* Center button in column */
        line-height: 1 !important;
        border: 3px solid #7e22ce !important;
    }
    
    .stButton > button:hover {
        background: #9333ea !important;
        transform: scale(1.05) !important;
    }
    
    /* Hide default footer */
    footer {
        visibility: hidden !important;
    }
    
    /* Custom button container */
    .button-container {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        margin: 20px auto !important;
        max-width: 300px !important;
    }
    
    /* Better column alignment for buttons */
    .button-row {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    
    /* Status text */
    .status-text {
        text-align: center;
        color: #a855f7;
        font-style: italic;
        margin-top: 10px;
        font-size: 18px;
    }
    
    /* Bilingual status text */
    .hindi-text {
        display: block;
        margin-top: 5px;
        font-size: 16px;
    }
    
    /* Hide all streamlit branding and extra elements */
    #MainMenu, .stDeployButton, footer, header {
        visibility: hidden !important;
        height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* Make sure the entire app fits well on mobile */
    .stApp {
        max-width: 100vw !important;
    }
    
    /* Adjust column width to ensure proper button alignment */
    [data-testid="column"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
</style>
""", unsafe_allow_html=True)

# Configure Gemini API if available
if USING_GEMINI:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)

# Initialize speech recognizer
recognizer = sr.Recognizer()

# Hindi translations for status messages
hindi_translations = {
    "listening": "सुन रहा हूँ...",
    "thinking": "सोच रहा हूँ...",
    "speaking": "बोल रहा हूँ...",
    "welcome": "नमस्ते! मुझसे बात करने के लिए माइक्रोफोन बटन पर टैप करें।"
}

# Function to convert speech to text
def speech_to_text(animation_placeholder):
    # Update UI to listening state
    animation_placeholder.markdown("""
    <div class="ai-circle listening">
        <div class="ai-circle-inner"></div>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
        
        # Update UI to thinking state
        animation_placeholder.markdown("""
        <div class="ai-circle thinking">
            <div class="ai-circle-inner"></div>
        </div>
        """, unsafe_allow_html=True)
        
        text = recognizer.recognize_google(audio)
        return text
    except Exception as e:
        # Return to idle state on error
        animation_placeholder.markdown("""
        <div class="ai-circle">
            <div class="ai-circle-inner"></div>
        </div>
        """, unsafe_allow_html=True)
        return None

# Function to get response from Gemini AI
def get_ai_response(prompt):
    if not USING_GEMINI:
        return "I'm having trouble thinking right now."
    
    try:
        model = genai.GenerativeModel("models/gemini-1.5-flash")
        
        # System prompt for simple, friendly responses
        system_prompt = """
        You are a friendly voice assistant. Keep your responses concise, simple, and helpful.
        Use simple language that anyone can understand.
        """
        
        full_prompt = f"{system_prompt}\n\nUser: {prompt}\n\nAssistant:"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return "I didn't understand that. Can you try again?"

# Function to convert text to speech and play it automatically
def text_to_speech_and_play(text, lang='en'):
    # Update the animation to speaking state
    animation_placeholder.markdown("""
    <div class="ai-circle speaking">
        <div class="ai-circle-inner"></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Convert text to speech
    tts = gTTS(text=text, lang=lang, slow=False)
    
    # Save to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
        temp_filename = fp.name
        tts.save(temp_filename)
    
    # Play using pygame (more reliable than browser autoplay)
    pygame.mixer.music.load(temp_filename)
    pygame.mixer.music.play()
    
    # Wait for audio to finish playing
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    
    # Return to idle state
    animation_placeholder.markdown("""
    <div class="ai-circle">
        <div class="ai-circle-inner"></div>
    </div>
    """, unsafe_allow_html=True)

# Initialize session state
if 'conversation' not in st.session_state:
    st.session_state.conversation = []
if 'current_state' not in st.session_state:
    st.session_state.current_state = "idle"
if 'is_processing' not in st.session_state:
    st.session_state.is_processing = False

# Create placeholder for animation
animation_placeholder = st.empty()

# Show animation based on current state
if not st.session_state.is_processing:
    animation_placeholder.markdown("""
    <div class="ai-circle">
        <div class="ai-circle-inner"></div>
    </div>
    """, unsafe_allow_html=True)

# Display the latest response in a bubble
response_placeholder = st.empty()
if st.session_state.conversation:
    latest_response = st.session_state.conversation[-1][1]
    response_placeholder.markdown(f"""
    <div class="response-bubble">
        {latest_response}
    </div>
    """, unsafe_allow_html=True)

# Status indicator with Hindi translation
status_placeholder = st.empty()

# Function to handle the voice input process
def process_voice_input():
    if st.session_state.is_processing:
        return
        
    st.session_state.is_processing = True
    
    # Update status with English and Hindi
    status_placeholder.markdown(f"""
    <p class="status-text">
        Listening...
        <span class="hindi-text">{hindi_translations['listening']}</span>
    </p>
    """, unsafe_allow_html=True)
    
    # Get user input
    user_input = speech_to_text(animation_placeholder)
    
    if user_input:
        # Add user input to conversation
        st.session_state.conversation.append(("user", user_input))
        
        # Update status with English and Hindi
        status_placeholder.markdown(f"""
        <p class="status-text">
            Thinking...
            <span class="hindi-text">{hindi_translations['thinking']}</span>
        </p>
        """, unsafe_allow_html=True)
        
        # Get AI response
        response = get_ai_response(user_input)
        st.session_state.conversation.append(("assistant", response))
        
        # Display response in bubble
        response_placeholder.markdown(f"""
        <div class="response-bubble">
            {response}
        </div>
        """, unsafe_allow_html=True)
        
        # Update status with English and Hindi
        status_placeholder.markdown(f"""
        <p class="status-text">
            Speaking...
            <span class="hindi-text">{hindi_translations['speaking']}</span>
        </p>
        """, unsafe_allow_html=True)
        
        # Convert and play the response
        text_to_speech_and_play(response)
        
        # Clear status
        status_placeholder.markdown("", unsafe_allow_html=True)
    
    st.session_state.is_processing = False

# Custom function to handle initial welcome message with autoplay
def play_welcome_message():
    if len(st.session_state.conversation) == 0:
        # English welcome text
        welcome_text_en = "Hello! Tap the microphone button and speak to ask me a question."
        st.session_state.conversation.append(("assistant", welcome_text_en))
        
        # Display welcome message
        response_placeholder.markdown(f"""
        <div class="response-bubble">
            {welcome_text_en}
            <br><br>
            <span style="font-style: italic;">{hindi_translations['welcome']}</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Play welcome message in English
        text_to_speech_and_play(welcome_text_en)
        
        # Play welcome message in Hindi
        text_to_speech_and_play(hindi_translations['welcome'], lang='hi')

# Single microphone button centered
st.markdown('<div class="button-row">', unsafe_allow_html=True)
if st.button("🎤", key="mic_button"):
    process_voice_input()
st.markdown('</div>', unsafe_allow_html=True)

# Play welcome message on first load
if 'welcomed' not in st.session_state:
    st.session_state.welcomed = True
    play_welcome_message()