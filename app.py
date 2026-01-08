import streamlit as st
import os
import requests
import random
import asyncio
import edge_tts
from PIL import Image
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
import numpy as np
import traceback
import re
import time  # Added for the pause

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Dark Studio: Patient Mode", layout="wide", page_icon="⏳")

# PATCH IMAGE LIBRARY
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS
if not hasattr(Image, 'BILINEAR'): Image.BILINEAR = Image.BILINEAR

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if os.path.exists(st.session_state.project_path):
        import shutil
        shutil.rmtree(st.session_state.project_path) 
    os.makedirs(st.session_state.project_path)

def folder(): return st.session_state.project_path

# --- 2. SMART PARSER ---
def parse_script_by_sentences(raw_text):
    sentences = re.split(r'(?<=[.!?])\s+', raw_text)
    script_data = []
    for s in sentences:
        clean_s = s.strip()
        if len(clean_s) > 5:
            script_data.append({
                "visual": f"Cinematic shot, hyper-realistic, 8k, {clean_s}", 
                "audio": clean_s
            })
    return script_data

# --- 3. THE "PATIENT" IMAGE GENERATOR ---
def generate_images_with_pause(script_data, is_short):
    st.write(f"🎨 Generating {len(script_data)} scenes (with 15s safety pauses)...")
    
    # Create a container for the countdown so it updates in place
    status_box = st.empty()
    prog_bar = st.progress(0)
    
    width, height = (720, 1280) if is_short else (1280, 720)
    
    for i, scene in enumerate(script_data):
        filename = f"scene_{i+1}.jpg"
        filepath = os.path.join(folder(), filename)
        
        # 1. GENERATE
        status_box.info(f"⬇️ Downloading Scene {i+1}/{len(script_data)}...")
        
        safe_prompt = requests.utils.quote(scene['visual'])
        seed = random.randint(0, 99999)
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width={width}&height={height}&nologo=true&seed={seed}&model=flux"
        
        downloaded = False
        try:
            r = requests.get(url, timeout=15) # Increased timeout
            if r.status_code == 200:
                with open(filepath, "wb") as f: f.write(r.content)
                downloaded = True
        except: pass
        
        if not downloaded:
            # Fallback
            Image.new('RGB', (width, height), (30,30,30)).save(filepath)

        script_data[i]["image_path"] = filepath
        prog_bar.progress((i+1)/len(script_data))
        
        # 2. THE SAFETY PAUSE (Skip after the last image)
        if i < len(script_data) - 1:
            for seconds in range(15, 0, -1):
                status_box.warning(f"⏳ Cooling down API... {seconds}s remaining")
                time.sleep(1)
            status_box.empty() # Clear the countdown
            
    status_box.success("✅ All Images Ready!")
    return script_data

# --- 4. RENDERER ---
def render_video(project_data, is_short):
    p = folder()
    status = st.empty()
    
    try:
        # 1. Voice
        status.info("🎙️ Recording Voiceover...")
        full_text = " ".join([s['audio'] for s in project_data])
        voice_path = os.path.join(p, "voice.mp3")
        asyncio.run(edge_tts.Communicate(full_text, "en-US-ChristopherNeural").save(voice_path))
        
        # 2. Stitch
        status.info("🎬 Stitching Video...")
        vc = AudioFileClip(voice_path)
        clip_dur = vc.duration / len(project_data)
        
        target_size = (480, 854) if is_short else (854, 480)
        
        clips = []
        for scene in project_data:
            img = Image.open(scene['image_path']).convert('RGB')
            img = img.resize(target_size, Image.LANCZOS)
            clips.append(ImageClip(np.array(img)).set_duration(clip_dur))
            
        final = concatenate_videoclips(clips, method="compose").set_audio(vc)
        output_path = os.path.join(p, "FINAL.mp4")
        final.write_videofile(output_path, fps=24, preset="ultrafast", codec="libx264", audio_codec="aac")
        
        status.success("✅ Done!")
        return output_path

    except Exception as e:
        st.error(f"Error: {e}")
        return None

# --- UI ---
st.title("⏳ Dark Studio: Safety Mode")

with st.sidebar:
    st.header("Settings")
    format_choice = st.radio("Format:", ["📱 Shorts (9:16)", "🖥️ Video (16:9)"])
    is_short = "Short" in format_choice
    st.info("ℹ️ This mode waits 15 seconds between images to prevent server crashes.")

# INPUT
raw_script = st.text_area("Paste your story here:", height=150, 
                          placeholder="The deep ocean is a world of mystery. Strange creatures swim in the dark. Pressure here is immense.")

if st.button("🚀 START PRODUCTION", type="primary"):
    if len(raw_script) < 5:
        st.error("Empty script!")
    else:
        # 1. Parse
        data = parse_script_by_sentences(raw_script)
        st.success(f"Detected {len(data)} scenes.")
        
        # 2. Generate (WITH PAUSE)
        final_data = generate_images_with_pause(data, is_short)
        
        st.session_state.project_data = final_data
        st.session_state.is_short = is_short
        st.rerun()

# EDITOR
if "project_data" in st.session_state:
    st.divider()
    st.header("🎞️ Timeline")
    
    for i, scene in enumerate(st.session_state.project_data):
        with st.expander(f"Scene {i+1}: \"{scene['audio'][:30]}...\"", expanded=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                if os.path.exists(scene["image_path"]):
                    st.image(scene["image_path"])
                up = st.file_uploader(f"Replace {i+1}", type=['jpg','png'], key=f"up_{i}")
                if up:
                    with open(scene["image_path"], "wb") as f: f.write(up.getbuffer())
                    st.rerun()
            with c2:
                st.info(scene['audio'])
                st.caption(scene['visual'])

    st.divider()
    if st.button("🔴 RENDER FINAL VIDEO", type="primary"):
        vid_path = render_video(st.session_state.project_data, st.session_state.get("is_short", True))
        if vid_path:
            st.video(vid_path)
            with open(vid_path, "rb") as f:
                st.download_button("📥 DOWNLOAD", f, "My_Safe_Video.mp4")
