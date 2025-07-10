# app.py
import streamlit as st
from chatbot import Chatbot
import base64
from io import BytesIO
from st_audiorec import st_audiorec
import os


# --- MODIFIED: A more robust CSS loader ---
def load_css():
    # Helper function to encode images for CSS
    def get_image_as_base64(path):
        if not os.path.exists(path):
            return None
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode()

    # Get the background image as a Base64 string
    bg_base64 = get_image_as_base64("background.png")

    # CSS remains the same if background.png is not found
    background_style = ""
    if bg_base64:
        # This more robust CSS targets the main app container with higher specificity
        background_style = f"""
        <style>
        [data-testid="stAppViewContainer"] > .main {{
            background-image: linear-gradient(rgba(26, 26, 46, 0.9), rgba(26, 26, 46, 0.9)), url("data:image/png;base64,{bg_base64}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        /* Also apply a base background color to the app itself for consistency */
        .stApp {{
             background-color: var(--background-color);
        }}
        </style>
        """

    # Combine all CSS into one markdown block
    st.markdown(
        f"""
        {background_style}
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600&display=swap');

            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}

            :root{{
                --primary-color:#FF69B4;
                --secondary-color:#C71585;
                --background-color:#1a1a2e; /* Used for the overlay and fallback */
                --text-color:#e0e0e0;
                --user-bubble-bg:#2e2e4f;
                --assistant-bubble-bg:#4a0e38;
            }}
            html,body,[class*="st-"]{{
                font-family:'Montserrat',sans-serif;
                color:var(--text-color);
            }}

            header,#MainMenu,footer{{visibility:hidden;}}
            ::-webkit-scrollbar{{width:8px;}}
            ::-webkit-scrollbar-track{{background:var(--user-bubble-bg);}}
            ::-webkit-scrollbar-thumb{{background:var(--primary-color);border-radius:4px;}}
            ::-webkit-scrollbar-thumb:hover{{background:var(--secondary-color);}}
            div[data-testid="stChatInput"]{{background-color:transparent; border-top:1px solid var(--primary-color);}}
            .stButton > button{{border:2px solid var(--primary-color);background-color:transparent;color:var(--primary-color);border-radius:25px;transition:all 0.3s ease-in-out;width:100%;}}
            .stButton > button:hover{{background-color:var(--primary-color);color:white;box-shadow:0 0 15px var(--primary-color);}}
            div[data-testid="stChatMessage"]{{
                border-radius:15px;
                padding:1rem;
                margin-bottom:1rem;
                animation: fadeIn 0.5s ease-in-out;
            }}
            div[data-testid="stChatMessage"]:has(div[aria-label="user message"]){{background-color:var(--user-bubble-bg);border:1px solid var(--secondary-color);}}
            div[data-testid="stChatMessage"]:has(div[aria-label="assistant message"]){{background-image:linear-gradient(135deg,var(--assistant-bubble-bg),var(--secondary-color));border:1px solid var(--primary-color);}}
            div[data-testid="stFileUploader"]{{border-color:var(--primary-color);}}
            div[data-testid="stInfo"]{{background-color:rgba(255,105,180,0.1);border:1px dashed var(--primary-color);border-radius:10px;}}

            /* Style the chat avatars to be circular */
            .st-emotion-cache-12fmjuu {{ /* This targets the avatar image container */
                border-radius: 50%;
                box-shadow: 0 0 10px var(--primary-color);
            }}

            .main .block-container {{
                max-width: 800px;
                padding-top: 2rem;
            }}
        </style>
        """,
        unsafe_allow_html=True)


# --- Start of your existing code (word-for-word) ---

st.set_page_config(page_title="Chat with Ava", page_icon="💋", layout="wide")

load_css()  # Call the enhanced CSS loader

# --- HEADER ---
col_header_1, col_header_2 = st.columns([1, 4])
with col_header_1:
    st.image("ava_avatar.png", width=120)
with col_header_2:
    st.title("Chat with Ava ❤️")
    st.markdown("_Your witty, flirty, and fun companion_")
st.divider()

# --- Session State Initialization ---
if 'chatbot' not in st.session_state:
    st.session_state.user_name = ""
    st.session_state.chatbot_initialized = False
    st.session_state.messages = [
        {"role": "assistant", "content": "Hey there! Before we start, what should I call you?"}]
    st.session_state.uploaded_image_data = None
    st.session_state.recorded_audio_data = None

# --- Media Uploader Section ---
if st.session_state.chatbot_initialized:
    with st.sidebar:
        st.markdown("### Share something with me")
        uploaded_file = st.file_uploader(
            "Share a picture...",
            type=["jpg", "jpeg", "png"]
        )
        if uploaded_file is not None:
            st.image(uploaded_file, caption="You shared this image.")
            st.session_state.uploaded_image_data = {
                "mime_type": uploaded_file.type,
                "data": base64.b64encode(uploaded_file.getvalue()).decode()
            }
            st.info("Great! Now, what do you want to say about this picture?")
        st.markdown("---")
        st.markdown("Or, just talk to me:")
        wav_audio_data = st_audiorec()

        if wav_audio_data is not None:
            st.audio(wav_audio_data, format='audio/wav')
            st.session_state.recorded_audio_data = {
                "mime_type": "audio/wav",
                "data": base64.b64encode(wav_audio_data).decode()
            }
            st.info("I've got your message! Just hit send in the chat to let me listen.")

# --- Display Chat History ---
ava_avatar_path = "ava_avatar.png" if os.path.exists("ava_avatar.png") else "🤖"
user_avatar_path = "khushal.png" if os.path.exists("khushal.png") else "👤"

for message in st.session_state.messages:
    avatar_to_use = ava_avatar_path if message["role"] == "assistant" else user_avatar_path
    with st.chat_message(message["role"], avatar=avatar_to_use):
        if "audio" in message:
            st.audio(base64.b64decode(message["audio"]["data"]), format=message["audio"]["mime_type"])
        if "image" in message:
            st.image(f"data:{message['image']['mime_type']};base64,{message['image']['data']}", width=150)

        st.write(message["content"])

# --- User Input Handling (Unchanged) ---
if prompt := st.chat_input("What's on your mind?"):
    if not st.session_state.chatbot_initialized:
        user_name = prompt.strip()
        if user_name:
            st.session_state.user_name = user_name
            st.session_state.chatbot = Chatbot(user_name=st.session_state.user_name)
            st.session_state.chatbot_initialized = True
            st.session_state.messages.append({"role": "user", "content": user_name})
            initial_greeting = f"It's so great to meet you, {user_name}! 😊 What would you like to talk about?"
            st.session_state.messages.append({"role": "assistant", "content": initial_greeting})
            st.rerun()
        else:
            st.warning("Please tell me your name so we can get to know each other!")

    else:
        user_message = {"role": "user", "content": prompt}
        if st.session_state.uploaded_image_data:
            user_message["image"] = st.session_state.uploaded_image_data
        if st.session_state.recorded_audio_data:
            user_message["audio"] = st.session_state.recorded_audio_data

        st.session_state.messages.append(user_message)
        st.rerun()

if st.session_state.chatbot_initialized and (
        "image" in st.session_state.messages[-1] or "audio" in st.session_state.messages[-1] or
        st.session_state.messages[-1].get("content")):
    last_message = st.session_state.messages[-1]
    if last_message["role"] == "user" and len(st.session_state.messages) % 2 == 0:
        with st.chat_message("assistant", avatar=ava_avatar_path):
            with st.spinner("Ava is thinking..."):
                prompt_text = last_message.get("content", "")
                image_data = last_message.get("image")
                audio_data = last_message.get("audio")

                response = st.session_state.chatbot.talk(
                    user_input=prompt_text,
                    image_data=image_data,
                    audio_data=audio_data
                )

                st.session_state.uploaded_image_data = None
                st.session_state.recorded_audio_data = None

                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()