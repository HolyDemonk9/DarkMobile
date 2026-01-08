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
import time

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Dark Studio: Stealth", layout="wide", page_icon="🕵️")

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

# --- 2. STEALTH NETWORK ENGINE ---
def get_random_headers():
    # 1. Generate a random IP address
    fake_ip = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
    
    # 2. Pick a random browser (User-Agent)
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
        "Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
    ]
    
    headers = {
        "User-Agent": random.choice(user_agents),
        "X-Forwarded-For": fake_ip,
        "Client-IP": fake_ip,
        "Real-IP": fake_ip,
        "Referer": "https://www.google.com/"
    }
    return headers

# --- 3. SMART PARSER ---
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

# --- 4. THE STEALTH IMAGE GENERATOR ---
def generate_images_stealth(script_data, is_short):
    st.write(f"🕵️ Generating {len(script_data)} scenes (Stealth Mode)...")
    
    status_box = st.empty()
    prog_bar = st.progress(0)
    
    width, height = (720, 1280) if is_short else (1280, 720)
    
    for i, scene in enumerate(script_data):
        filename = f"scene_{i+1}.jpg"
        filepath = os.path.join(folder(), filename)
        
        status_box.info(f"🔄 Requesting Scene {i+1} with new Identity...")
        
        # Pollinations URL
        safe_prompt = requests.utils.quote(scene['visual'])
        seed = random.randint(0, 999999)
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width={width}&height={height}&nologo=true&seed={seed}&model=flux"
        
        downloaded = False
        try:
            # USE FAKE HEADERS HERE
            stealth_headers = get_random_headers()
            
            # 15s Timeout, verify=False (ignoring SSL helps sometimes with weird servers)
            r = requests.get(url, headers=stealth_headers, timeout=15)
            
            if r.status_code == 200 and len(r.content) > 1000:
                with open(filepath, "wb") as f: f.write(r.content)
                downloaded = True
        except Exception as e:
            print(f"Failed to download: {e}")
        
        # FAILSAFE: If it fails, create a placeholder so app doesn't crash
        if not downloaded:
            status_box.warning(f"⚠️ Scene {i+1} failed. Created placeholder.")
            # Create a simple colored background with text
            img = Image.new('RGB', (width, height), (random.randint(20,50), 20, 40))
            img.save(filepath)
            
        script_data[i]["image_path"] = filepath
        prog_bar.progress((i+1)/len(script_data))
        
        # Tiny pause to be safe
        time.sleep(2)
            
    status_box.success("✅ Generation Complete!")
    return script_data

# --- 5. RENDERER ---
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
            try:
                img = Image.open(scene['image_path']).convert('RGB')
                img = img.resize(target_size, Image.LANCZOS)
                clips.append(ImageClip(np.array(img)).set_duration(clip_dur))
            except:
                # If an image is broken, skip it or add black frame
                pass
            
        final = concatenate_videoclips(clips, method="compose").set_audio(vc)
        output_path = os.path.join(p, "FINAL.mp4")
        final.write_videofile(output_path, fps=24, preset="ultrafast", codec="libx264", audio_codec="aac")
        
        status.success("✅ Done!")
        return output_path

    except Exception as e:
        st.error(f"Render Error: {e}")
        return None

# --- UI ---
st.title("🕵️ Dark Studio: Stealth Mode")

with st.sidebar:
    st.header("Settings")
    format_choice = st.radio("Format:", ["📱 Shorts (9:16)", "🖥️ Video (16:9)"])
    is_short = "Short" in format_choice
    st.info("ℹ️ Uses Random IP Headers for every image request.")

# INPUT
raw_script = st.text_area("Paste your story here:", height=150, 
                          placeholder="The deep ocean is a world of mystery. Strange creatures swim in the dark. Pressure here is immense.")

if st.button("🚀 START STEALTH PRODUCTION", type="primary"):
    if len(raw_script) < 5:
        st.error("Empty script!")
    else:
        # 1. Parse
        data = parse_script_by_sentences(raw_script)
        st.success(f"Detected {len(data)} scenes.")
        
        # 2. Generate (STEALTH)
        final_data = generate_images_stealth(data, is_short)
        
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
                st.download_button("📥 DOWNLOAD", f, "My_Stealth_Video.mp4")
