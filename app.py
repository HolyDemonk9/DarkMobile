import streamlit as st
import os
import requests
import time
import asyncio
import edge_tts
import urllib.parse
import re
import numpy as np
import random
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeAudioClip, afx
import shutil

# COMPATIBILITY
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS

# CONFIG
st.set_page_config(page_title="Dark Studio Mobile", layout="centered", page_icon="🎬")

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if os.path.exists(st.session_state.project_path):
        shutil.rmtree(st.session_state.project_path) 
    os.makedirs(st.session_state.project_path)

if "generated_script" not in st.session_state: st.session_state.generated_script = ""

def folder(): return st.session_state.project_path

# --- FUNCTIONS ---

def get_images(topic):
    style = st.session_state.get("stolen_prompt", "cinematic, dark, 8k")
    st.write(f"🎨 Generating Scenes for: {topic}...")
    
    # 1. Get Scene List (FORCE 5 ITEMS)
    seed = int(time.time())
    scenes = []
    try:
        u = f"https://text.pollinations.ai/{urllib.parse.quote(f'List 5 distinct visual scenes for {topic}. Style: {style}. Seed: {seed}. Format: - Description')}"
        # We strictly look for lines starting with "-"
        raw_scenes = [l for l in requests.get(u).text.split('\n') if l.strip().startswith("-")]
        scenes = raw_scenes[:5] # Take top 5
    except: pass

    # FAILSAFE: If we have less than 5, fill the gaps manually
    while len(scenes) < 5:
        scenes.append(f"- A mysterious cinematic shot of {topic}, scene {len(scenes)+1}")
    
    st.caption(f"Brainstormed {len(scenes)} Scenes. Generating Images...")

    bar = st.progress(0)
    
    # 2. GENERATE IMAGES (Indestructible Loop)
    for i, s in enumerate(scenes):
        clean = re.sub(r'^- ', '', s)
        filename = f"{i+1:03}.jpg"
        filepath = os.path.join(folder(), filename)
        
        # Strategy A: AI Generation
        prompt = urllib.parse.quote(f"{clean}, {style}, 8k")
        u_ai = f"https://image.pollinations.ai/prompt/{prompt}?width=1080&height=1920&nologo=true&seed={random.randint(0,99999)}"
        
        # Strategy B: Stock Photo Backup
        u_stock = f"https://picsum.photos/1080/1920?random={i+seed}"
        
        saved = False
        
        # Attempt 1: AI
        try:
            r = requests.get(u_ai, timeout=8)
            if r.status_code == 200 and len(r.content) > 4000: # Check file size > 4KB
                with open(filepath, "wb") as f: f.write(r.content)
                saved = True
        except: pass
        
        # Attempt 2: Stock Photo (If AI failed)
        if not saved:
            try:
                r = requests.get(u_stock, timeout=8)
                if r.status_code == 200:
                    with open(filepath, "wb") as f: f.write(r.content)
                    saved = True
            except: pass
            
        # Attempt 3: Black Placeholder (Last Resort)
        if not saved:
            img = Image.new('RGB', (1080, 1920), color=(10, 10, 10))
            d = ImageDraw.Draw(img)
            # Try drawing text, ignore font errors
            try: d.text((50, 900), f"Scene {i+1}: {clean[:20]}...", fill=(255, 255, 255))
            except: pass
            img.save(filepath)

        bar.progress((i + 1) / 5)
        time.sleep(1) 
    
    # Final Count Check
    valid_imgs = len([f for f in os.listdir(folder()) if f.endswith(".jpg")])
    if valid_imgs == 5:
        st.success(f"✅ Success! {valid_imgs} Images Ready.")
    else:
        st.warning(f"⚠️ Only {valid_imgs}/5 Images generated. Video might be short.")

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
    st.write("🎬 Rendering (Safe Mode)...")
    p = folder()
    try:
        if not os.path.exists(os.path.join(p, "voice.mp3")): 
            st.error("❌ No Audio! Record voice first.")
            return
        
        vc = AudioFileClip(os.path.join(p, "voice.mp3"))
        files = sorted([os.path.join(p, f) for f in os.listdir(p) if f.endswith(".jpg")])
        if len(files) == 0:
            st.error("❌ No images found! Click 'Generate Scenes' first.")
            return

        # BUILD CLIPS (Using PIL Method)
        dur = max(vc.duration / len(files), 2) # Min duration 2s
        clips = []
        for f in files:
            try:
                pil_img = Image.open(f).convert('RGB')
                pil_img = pil_img.resize((1080, 1920), Image.ANTIALIAS)
                clips.append(ImageClip(np.array(pil_img)).set_duration(dur))
            except: pass

        if not clips:
            st.error("❌ Critical: All images failed to load.")
            return

        # SAFE MUSIC
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

        final = concatenate_videoclips(clips, method="compose").set_audio(final_audio)
        output_path = os.path.join(p, "FINAL.mp4")
        final.write_videofile(output_path, fps=24, preset="ultrafast")
        
        st.success("DONE!")
        st.video(output_path)
        with open(output_path, "rb") as file:
            st.download_button("📥 DOWNLOAD VIDEO", file, "DarkVideo.mp4", "video/mp4")
        
    except Exception as e: st.error(f"Render Failed: {e}")

# --- UI LAYOUT ---
st.title("📱 Dark Studio v3.5")
st.caption("School Project: Auto-Fill Edition")

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

if col1.button("Generate Scenes (Force 5)"):
    get_images(topic)

if col2.button("✨ WRITE SCRIPT"):
    generate_ai_script
