import streamlit as st
import os
import requests
import time
import asyncio
import edge_tts
import urllib.parse
import re
import numpy as np
from PIL import Image
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeAudioClip, afx
import shutil

# CONFIG
st.set_page_config(page_title="Dark Studio Mobile", layout="centered")

# FOLDER SETUP (For Cloud)
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if not os.path.exists(st.session_state.project_path): os.makedirs(st.session_state.project_path)

def folder(): return st.session_state.project_path

# --- FUNCTIONS ---
def get_images(topic, style):
    seed = int(time.time())
    st.write(f"🎨 Brainstorming {style} scenes...")
    
    # 1. Get Scene List
    try:
        u = f"https://text.pollinations.ai/{urllib.parse.quote(f'List 10 distinct visual scenes for {topic}. Style: {style}. Seed: {seed}. Format: - Description')}"
        scenes = [l for l in requests.get(u).text.split('\n') if l.strip().startswith("-")][:10]
        if len(scenes)<3: scenes = [f"{topic} scene {i}" for i in range(10)]
    except: scenes = [f"{topic} scene {i}" for i in range(10)]
    
    # 2. Generate Images
    bar = st.progress(0)
    for i, s in enumerate(scenes):
        clean = re.sub(r'^- ', '', s)
        prompt = urllib.parse.quote(f"{clean}, {style}, 8k, highly detailed")
        u2 = f"https://image.pollinations.ai/prompt/{prompt}?width=1080&height=1920&nologo=true"
        
        # Retry logic
        success = False
        for attempt in range(2):
            try:
                content = requests.get(u2, timeout=10).content
                if len(content) > 1000:
                    with open(os.path.join(folder(), f"{i+1:03}.jpg"), "wb") as f: f.write(content)
                    success = True
                    break
            except: time.sleep(2)
        
        bar.progress((i + 1) / len(scenes))
    st.success(f"✅ Generated {len(scenes)} Images!")

def get_script_and_audio(topic, style, voice):
    st.write("📝 Ghostwriting Script...")
    seed = int(time.time())
    prompt = f"Write a 100 word engaging script about '{topic}'. {style}. Seed: {seed}"
    
    # 1. Get Text
    try:
        txt = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}").text
    except: txt = f"This is a dark story about {topic}."
    
    st.info(f"Script: {txt[:100]}...")
    
    # 2. Convert to Audio
    st.write("🎙️ Recording Voice...")
    async def _save():
        c = edge_tts.Communicate(txt, voice)
        await c.save(os.path.join(folder(), "voice.mp3"))
    asyncio.run(_save())
    st.success("✅ Audio Ready!")

def render_video(music_vibe):
    st.write("🎬 Rendering Video (This happens on the Cloud Server!)...")
    p = folder()
    
    try:
        # Load Audio
        if not os.path.exists(os.path.join(p, "voice.mp3")): 
            st.error("No Audio found! Generate Audio first.")
            return
        
        vc = AudioFileClip(os.path.join(p, "voice.mp3"))
        
        # Download Music
        urls = {"horror": "https://ia800300.us.archive.org/17/items/TheSlenderManSong/Anxiety.mp3", "tech": "https://ia902808.us.archive.org/24/items/Synthwave-2016/Home%20-%20Decay.mp3"}
        m_path = os.path.join(p, "music.mp3")
        if not os.path.exists(m_path):
            with open(m_path, "wb") as f: f.write(requests.get(urls.get(music_vibe, urls["horror"])).content)
        
        # Mix Audio
        mc = AudioFileClip(m_path)
        if mc.duration < vc.duration: mc = afx.audio_loop(mc, duration=vc.duration)
        else: mc = mc.subclip(0, vc.duration)
        final_audio = CompositeAudioClip([vc, mc.volumex(0.15)])
        
        # Load Images
        files = sorted([os.path.join(p, f) for f in os.listdir(p) if f.endswith(".jpg")])
        if not files: 
            st.error("No images found!")
            return
            
        dur = vc.duration / len(files)
        clips = []
        for f in files:
            try: clips.append(ImageClip(np.array(Image.open(f).convert('RGB'))).resize(height=1920).crop(x1=0, y1=0, width=1080, height=1920).set_duration(dur))
            except: pass
            
        final = concatenate_videoclips(clips, method="compose").set_audio(final_audio)
        output_path = os.path.join(p, "FINAL_MOBILE.mp4")
        final.write_videofile(output_path, fps=24, preset="ultrafast")
        
        st.balloons()
        st.video(output_path)
        
        # Offer Download
        with open(output_path, "rb") as file:
            btn = st.download_button(
                label="📥 DOWNLOAD VIDEO TO PHONE",
                data=file,
                file_name="DarkStudio_Video.mp4",
                mime="video/mp4"
            )
        
    except Exception as e:
        st.error(f"Render Error: {e}")

# --- UI LAYOUT ---
st.title("📱 Dark Studio Remote")
st.caption("Running on Cloud Server")

style_opt = st.selectbox("Choose Style", ["Dark / Horror", "Tech / Future", "History / Vintage"])
topic = st.text_input("Video Topic", "The Mystery of the Ocean")

col1, col2 = st.columns(2)

if col1.button("1. Create Scenes"):
    vibe = "scary, dark" if "Horror" in style_opt else "futuristic" if "Tech" in style_opt else "vintage"
    get_images(topic, vibe)

if col2.button("2. Script & Audio"):
    voice = "en-US-GuyNeural" if "Horror" in style_opt else "en-US-ChristopherNeural"
    get_script_and_audio(topic, style_opt, voice)

if st.button("3. RENDER VIDEO", type="primary"):
    vibe = "tech" if "Tech" in style_opt else "horror"
    render_video(vibe)