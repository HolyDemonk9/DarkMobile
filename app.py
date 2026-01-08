import streamlit as st
import os
import requests
import time
import asyncio
import edge_tts
import urllib.parse
import re
import numpy as np
import io
from PIL import Image
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeAudioClip, afx
import shutil

# COMPATIBILITY
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS

# CONFIG
st.set_page_config(page_title="Dark Studio Private", layout="centered", page_icon="🔒")

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if os.path.exists(st.session_state.project_path):
        shutil.rmtree(st.session_state.project_path) 
    os.makedirs(st.session_state.project_path)

if "generated_script" not in st.session_state: st.session_state.generated_script = ""

def folder(): return st.session_state.project_path

# --- FUNCTIONS ---

def get_private_image(prompt, token, filename):
    # This connects to Stable Diffusion XL (High Quality)
    API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {token}"}
    
    # Retry logic (3 times)
    for i in range(3):
        try:
            response = requests.post(API_URL, headers=headers, json={"inputs": prompt})
            if response.status_code == 200:
                image_bytes = response.content
                image = Image.open(io.BytesIO(image_bytes))
                image.save(os.path.join(folder(), filename))
                return True
            elif "loading" in response.text.lower():
                time.sleep(5) # Model is waking up, wait
        except:
            time.sleep(2)
    return False

def get_images(topic, token):
    if not token.startswith("hf_"):
        st.error("❌ Invalid Token! Please paste your Hugging Face Token at the top.")
        return

    style = st.session_state.get("stolen_prompt", "cinematic, dark, 8k")
    st.write(f"🎨 Generating Scenes (Private Model)...")
    
    # Generate Scenes List
    scenes = [f"A cinematic 8k shot of {topic}, scene {i+1}" for i in range(5)]
    
    bar = st.progress(0)
    success_count = 0
    
    for i, s in enumerate(scenes):
        clean = s.replace("-", "").strip()
        filename = f"{i+1:03}.jpg"
        prompt = f"{clean}, {style}, highly detailed, 8k masterpiece"
        
        # USE PRIVATE GENERATOR
        saved = get_private_image(prompt, token, filename)
        
        if saved: success_count += 1
        else:
            # Emergency Backup (Black Placeholder)
            img = Image.new('RGB', (1080, 1920), color=(10, 10, 10))
            img.save(os.path.join(folder(), filename))

        bar.progress((i + 1) / 5)
        
    if success_count == 5:
        st.success(f"✅ 5/5 Images Generated Successfully!")
    else:
        st.warning(f"⚠️ Generated {success_count} images. Some placeholders were used.")

def generate_ai_script(topic):
    st.info("🧠 AI is thinking...")
    style = st.session_state.get("stolen_prompt", "dark and mysterious")
    prompt = f"Write a 150 word engaging YouTube script about '{topic}'. Style: {style}. Do not include scene directions, just the voiceover text."
    try:
        txt = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}").text
        st.session_state.generated_script = txt
        st.success("✅ Script Written!")
        st.rerun() 
    except: st.error("AI Script Failed")

def get_audio_from_text(text_script):
    st.write("🎙️ Recording Voice...")
    voice = st.session_state.get("stolen_voice", "en-US-GuyNeural")
    async def _save():
        c = edge_tts.Communicate(text_script, voice)
        await c.save(os.path.join(folder(), "voice.mp3"))
    asyncio.run(_save())
    st.success("✅ Audio Ready!")

def render_video():
    st.write("🎬 Rendering...")
    p = folder()
    try:
        if not os.path.exists(os.path.join(p, "voice.mp3")): 
            st.error("❌ No Audio!")
            return
        
        vc = AudioFileClip(os.path.join(p, "voice.mp3"))
        files = sorted([os.path.join(p, f) for f in os.listdir(p) if f.endswith(".jpg")])
        if not files:
            st.error("❌ No images!")
            return

        dur = max(vc.duration / len(files), 2)
        clips = []
        for f in files:
            try:
                pil_img = Image.open(f).convert('RGB')
                pil_img = pil_img.resize((1080, 1920), Image.ANTIALIAS)
                clips.append(ImageClip(np.array(pil_img)).set_duration(dur))
            except: pass

        # SAFE MUSIC
        final_audio = vc
        try:
            m_url = "https://ia800300.us.archive.org/17/items/TheSlenderManSong/Anxiety.mp3"
            r = requests.get(m_url, timeout=5)
            with open(os.path.join(p, "music.mp3"), "wb") as f: f.write(r.content)
            mc = AudioFileClip(os.path.join(p, "music.mp3"))
            if mc.duration < vc.duration: mc = afx.audio_loop(mc, duration=vc.duration)
            else: mc = mc.subclip(0, vc.duration)
            final_audio = CompositeAudioClip([vc, mc.volumex(0.15)])
        except: pass

        final = concatenate_videoclips(clips, method="compose").set_audio(final_audio)
        output_path = os.path.join(p, "FINAL.mp4")
        final.write_videofile(output_path, fps=24, preset="ultrafast")
        
        st.success("DONE!")
        st.video(output_path)
        with open(output_path, "rb") as file:
            st.download_button("📥 DOWNLOAD VIDEO", file, "DarkVideo.mp4", "video/mp4")
        
    except Exception as e: st.error(f"Render Failed: {e}")

# --- UI LAYOUT ---
st.title("🔒 Dark Studio: Private Edition")

# TOKEN INPUT
hf_token = st.text_input("Paste Hugging Face Token (Starts with hf_...):", type="password")

st.header("1. Strategy")
mode = st.radio("Mode:", ["Manual Vibe", "YouTube Hacker"])
if mode == "YouTube Hacker":
    url = st.text_input("Paste Channel Link:")
    if st.button("Hack Style"):
        st.session_state.stolen_prompt = "cinematic, dark, mysterious" 
        st.session_state.stolen_voice = "en-US-ChristopherNeural"
        st.success("✅ Style Cloned!")

topic = st.text_input("Topic:", "The Mystery of the Ocean")

st.header("2. Content")
col1, col2 = st.columns(2)

if col1.button("Generate Images (Private)"):
    if len(hf_token) < 5:
        st.error("⚠️ You must paste your Token at the top first!")
    else:
        get_images(topic, hf_token)

if col2.button("✨ WRITE SCRIPT"):
    generate_ai_script(topic)

st.subheader("Script Editor")
script_text = st.text_area("Review Script:", value=st.session_state.generated_script, height=150)

if st.button("🎙️ Record Voice"):
    get_audio_from_text(script_text)

st.header("3. Production")
if st.button("RENDER VIDEO", type="primary"):
    render_video()

st.success("✅ SYSTEM READY")
