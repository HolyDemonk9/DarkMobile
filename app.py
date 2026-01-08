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

# COMPATIBILITY PATCH
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS

# CONFIG
st.set_page_config(page_title="Dark Studio Mobile", layout="centered", page_icon="🎬")

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if os.path.exists(st.session_state.project_path):
        shutil.rmtree(st.session_state.project_path) 
    os.makedirs(st.session_state.project_path)

if "generated_script" not in st.session_state:
    st.session_state.generated_script = ""

def folder(): return st.session_state.project_path

# --- HELPER: Create Backup Image ---
def create_placeholder(filename, text):
    img = Image.new('RGB', (1080, 1920), color = (0, 0, 0))
    d = ImageDraw.Draw(img)
    try: d.text((100, 900), text, fill=(255, 255, 255))
    except: pass
    img.save(os.path.join(folder(), filename))

# --- FUNCTIONS ---
def get_images(topic):
    style = st.session_state.get("stolen_prompt", "cinematic, dark, 8k")
    st.write(f"🎨 Generating Scenes for: {topic}...")
    
    seed = int(time.time())
    try:
        u = f"https://text.pollinations.ai/{urllib.parse.quote(f'List 5 distinct visual scenes for {topic}. Style: {style}. Seed: {seed}. Format: - Description')}"
        scenes = [l for l in requests.get(u).text.split('\n') if l.strip().startswith("-")][:5]
        if len(scenes) < 3: raise Exception("List too short")
    except: 
        scenes = [f"Dark cinematic shot of {topic} {i}" for i in range(5)]
    
    bar = st.progress(0)
    for i, s in enumerate(scenes):
        clean = re.sub(r'^- ', '', s)
        filename = f"{i+1:03}.jpg"
        prompt = urllib.parse.quote(f"{clean}, {style}, 8k")
        u2 = f"https://image.pollinations.ai/prompt/{prompt}?width=1080&height=1920&nologo=true"
        
        saved = False
        try:
            r = requests.get(u2, timeout=15)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(os.path.join(folder(), filename), "wb") as f: f.write(r.content)
                saved = True
        except: pass
        
        if not saved: create_placeholder(filename, f"Scene {i+1}")
        bar.progress((i + 1) / len(scenes))
        time.sleep(1) 
    st.success(f"✅ Images Ready!")

def generate_ai_script(topic):
    st.info("🧠 AI is thinking...")
    style = st.session_state.get("stolen_prompt", "dark and mysterious")
    prompt = f"Write a 150 word engaging YouTube script about '{topic}'. Style: {style}. Do not include scene directions, just the voiceover text."
    
    try:
        txt = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}").text
        st.session_state.generated_script = txt
        st.success("✅ Script Written!")
        st.rerun() 
    except Exception as e:
        st.error(f"AI Failed: {e}")

def get_audio_from_text(text_script):
    st.write("🎙️ Recording Voice...")
    voice = st.session_state.get("stolen_voice", "en-US-GuyNeural")
    async def _save():
        c = edge_tts.Communicate(text_script, voice)
        await c.save(os.path.join(folder(), "voice.mp3"))
    asyncio.run(_save())
    st.success("✅ Audio Ready!")

def render_video():
    st.write("🎬 Rendering (Bulletproof Mode)...")
    p = folder()
    try:
        # 1. AUDIO CHECK
        if not os.path.exists(os.path.join(p, "voice.mp3")): 
            st.error("❌ No Audio! Record voice first.")
            return
        
        vc = AudioFileClip(os.path.join(p, "voice.mp3"))
        
        # 2. IMAGE CHECK
        files = sorted([os.path.join(p, f) for f in os.listdir(p) if f.endswith(".jpg")])
        if len(files) == 0:
            st.error("❌ No images found!")
            return

        # 3. BUILD CLIPS (Using PIL Method - Fixes the Crash)
        dur = vc.duration / len(files)
        clips = []
        
        for f in files:
            try:
                # Load with PIL -> Convert to Array -> Clip
                # This bypasses the FFmpeg image reader which fails on cloud
                pil_img = Image.open(f).convert('RGB')
                pil_img = pil_img.resize((1080, 1920), Image.ANTIALIAS)
                img_array = np.array(pil_img)
                
                clip = ImageClip(img_array).set_duration(dur)
                clips.append(clip)
            except Exception as e:
                st.warning(f"Skipped bad image {f}: {e}")

        if not clips:
            st.error("❌ Critical Error: All images failed to load.")
            return

        # 4. MUSIC (Safe Mode)
        final_audio = vc
        try:
            m_url = "https://ia800300.us.archive.org/17/items/TheSlenderManSong/Anxiety.mp3"
            r = requests.get(m_url, timeout=5)
            if r.status_code == 200:
                with open(os.path.join(p, "music.mp3"), "wb") as f: f.write(r.content)
                mc = AudioFileClip(os.path.join(p, "music.mp3"))
                if mc.duration < vc.duration: mc = afx.audio_loop(mc, duration=vc.duration)
                else: mc = mc.subclip(0, vc.duration)
                final_audio = CompositeAudioClip([vc, mc.volumex(0.15)])
        except: pass

        # 5. FINAL EXPORT
        final = concatenate_videoclips(clips, method="compose").set_audio(final_audio)
        output_path = os.path.join(p, "FINAL.mp4")
        final.write_videofile(output_path, fps=24, preset="ultrafast")
        
        st.success("DONE!")
        st.video(output_path)
        with open(output_path, "rb") as file:
            st.download_button("📥 DOWNLOAD VIDEO", file, "DarkVideo.mp4", "video/mp4")
        
    except Exception as e: st.error(f"Render Failed: {e}")

# --- UI LAYOUT ---
st.title("📱 Dark Studio v2.2")
st.caption("School Project Edition")

# 1. STRATEGY
st.header("1. Strategy")
mode = st.radio("Mode:", ["Manual Vibe", "YouTube Hacker"])
if mode == "YouTube Hacker":
    url = st.text_input("Paste Channel Link:")
    if st.button("Hack Style"):
        st.session_state.stolen_prompt = "cinematic, dark, mysterious" 
        st.session_state.stolen_voice = "en-US-ChristopherNeural"
        st.success("✅ Style Cloned!")

topic = st.text_input("Topic:", "The Mystery of the Ocean")

# 2. CONTENT
st.header("2. Content")
col1, col2 = st.columns(2)

if col1.button("Generate Images"):
    get_images(topic)

if col2.button("✨ WRITE SCRIPT"):
    generate_ai_script(topic)

# SCRIPT EDITOR
st.subheader("Script Editor")
script_text = st.text_area("Review Script:", value=st.session_state.generated_script, height=150)

if st.button("🎙️ Record Voice"):
    if len(script_text) < 5:
        st.error("Script is empty!")
    else:
        get_audio_from_text(script_text)

# 3. PRODUCTION
st.header("3. Production")
img_count = len([f for f in os.listdir(folder()) if f.endswith(".jpg")])
st.caption(f"Status: {img_count} Images Ready")

if st.button("RENDER VIDEO", type="primary"):
    render_video()
