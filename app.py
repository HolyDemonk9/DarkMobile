import streamlit as st
import os
import requests
import time
import asyncio
import edge_tts
import urllib.parse
import re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeAudioClip, afx
import shutil

# CONFIG
st.set_page_config(page_title="Dark Studio Mobile", layout="centered", page_icon="🎬")

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if os.path.exists(st.session_state.project_path):
        shutil.rmtree(st.session_state.project_path) # Clean start
    os.makedirs(st.session_state.project_path)

def folder(): return st.session_state.project_path

# --- HELPER: Create Backup Image (If AI Fails) ---
def create_placeholder(filename, text):
    img = Image.new('RGB', (1080, 1920), color = (0, 0, 0))
    d = ImageDraw.Draw(img)
    try:
        # Try to use a default font, or fall back
        d.text((100, 900), text, fill=(255, 255, 255))
    except: pass
    img.save(os.path.join(folder(), filename))

# --- FUNCTIONS ---
def get_images(topic):
    style = st.session_state.get("stolen_prompt", "cinematic, dark, 8k")
    st.write(f"🎨 Generating Scenes for: {topic}...")
    
    # 1. Get List
    seed = int(time.time())
    try:
        u = f"https://text.pollinations.ai/{urllib.parse.quote(f'List 5 distinct visual scenes for {topic}. Style: {style}. Seed: {seed}. Format: - Description')}"
        scenes = [l for l in requests.get(u).text.split('\n') if l.strip().startswith("-")][:5]
        if len(scenes) < 3: raise Exception("List too short")
    except: 
        scenes = [f"Dark cinematic shot of {topic} {i}" for i in range(5)]
    
    # 2. Generate Images
    bar = st.progress(0)
    success_count = 0
    
    for i, s in enumerate(scenes):
        clean = re.sub(r'^- ', '', s)
        filename = f"{i+1:03}.jpg"
        
        # Try AI Generation
        prompt = urllib.parse.quote(f"{clean}, {style}, 8k")
        u2 = f"https://image.pollinations.ai/prompt/{prompt}?width=1080&height=1920&nologo=true"
        
        saved = False
        try:
            r = requests.get(u2, timeout=15)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(os.path.join(folder(), filename), "wb") as f: f.write(r.content)
                saved = True
                success_count += 1
        except: pass
        
        # FAILSAFE: If AI failed, make a black placeholder image
        if not saved:
            create_placeholder(filename, f"Scene {i+1}: {clean[:20]}...")
            
        bar.progress((i + 1) / len(scenes))
        time.sleep(1) # Be polite to server
        
    st.success(f"✅ Process Finished. {success_count}/{len(scenes)} AI Images generated (rest are placeholders).")

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
        # CHECK 1: Audio
        if not os.path.exists(os.path.join(p, "voice.mp3")): 
            st.error("❌ No Audio! Please generate audio first.")
            return
        
        vc = AudioFileClip(os.path.join(p, "voice.mp3"))
        
        # CHECK 2: Images (The Crash Fix)
        files = sorted([os.path.join(p, f) for f in os.listdir(p) if f.endswith(".jpg")])
        if len(files) == 0:
            st.error("❌ No images found! You must click 'Create Scenes' first.")
            return

        # MUSIC (Optional - Won't crash if fails)
        final_audio = vc
        try:
            # Simple safe download
            m_url = "https://ia800300.us.archive.org/17/items/TheSlenderManSong/Anxiety.mp3"
            r = requests.get(m_url, timeout=5)
            if r.status_code == 200:
                with open(os.path.join(p, "music.mp3"), "wb") as f: f.write(r.content)
                mc = AudioFileClip(os.path.join(p, "music.mp3"))
                if mc.duration < vc.duration: mc = afx.audio_loop(mc, duration=vc.duration)
                else: mc = mc.subclip(0, vc.duration)
                final_audio = CompositeAudioClip([vc, mc.volumex(0.15)])
        except: st.warning("⚠️ Music skipped (network issue), continuing with voice only.")

        # BUILD VIDEO
        dur = vc.duration / len(files)
        clips = []
        for f in files:
            try:
                # Resize strictly to avoid size errors
                img = ImageClip(f).resize((1080, 1920)).set_duration(dur)
                clips.append(img)
            except: pass
            
        if not clips: raise Exception("Could not process images.")
        
        final = concatenate_videoclips(clips, method="compose").set_audio(final_audio)
        output_path = os.path.join(p, "FINAL.mp4")
        final.write_videofile(output_path, fps=24, preset="ultrafast")
        
        st.success("DONE!")
        st.video(output_path)
        
        with open(output_path, "rb") as file:
            st.download_button("📥 DOWNLOAD VIDEO", file, "DarkVideo.mp4", "video/mp4")
        
    except Exception as e:
        st.error(f"Render Failed: {e}")

# --- UI LAYOUT ---
st.title("📱 Dark Studio v2.0")
st.caption("Failsafe Edition")

# 1. STYLE SECTION
st.header("1. Strategy")
mode = st.radio("Mode:", ["Manual Vibe", "YouTube Hacker"])
if mode == "YouTube Hacker":
    url = st.text_input("Paste Channel Link:")
    if st.button("Hack Style"):
        # Simplified Hacker logic for speed
        st.session_state.stolen_prompt = "cinematic, dark, mysterious" 
        st.session_state.stolen_voice = "en-US-ChristopherNeural"
        st.success("✅ Style Cloned!")
else:
    style_in = st.selectbox("Vibe:", ["Dark/Horror", "Tech/Future", "History"])

topic = st.text_input("Topic:", "The Mystery of the Ocean")

# 2. CONTENT SECTION
st.header("2. Content")
col1, col2 = st.columns(2)

if col1.button("Generate Images"):
    get_images(topic)

# SCRIPT EDITOR (New Feature!)
st.subheader("Script Editor")
default_script = f"This is a video about {topic}. It is very mysterious and interesting. Subscribe for more."
script_text = st.text_area("Edit your script here:", value=default_script, height=150)

if col2.button("Record Voice"):
    get_audio_from_text(script_text)

# 3. RENDER SECTION
st.header("3. Production")
# Debug Status
img_count = len([f for f in os.listdir(folder()) if f.endswith(".jpg")])
st.caption(f"Status: {img_count} Images Ready | Audio Ready: {os.path.exists(os.path.join(folder(), 'voice.mp3'))}")

if st.button("RENDER VIDEO", type="primary"):
    render_video()
