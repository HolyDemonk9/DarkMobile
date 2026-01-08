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
from duckduckgo_search import DDGS

# --- 1. CRITICAL PATCHES ---
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS
if not hasattr(Image, 'BILINEAR'):
    Image.BILINEAR = Image.BICUBIC

st.set_page_config(page_title="Dark Studio: Director", layout="wide", page_icon="🎬")

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if os.path.exists(st.session_state.project_path):
        import shutil
        shutil.rmtree(st.session_state.project_path) 
    os.makedirs(st.session_state.project_path)

def folder(): return st.session_state.project_path

# --- 2. SCRIPT PARSER ---
def parse_script_by_sentences(raw_text):
    sentences = re.split(r'(?<=[.!?])\s+', raw_text)
    script_data = []
    for s in sentences:
        clean_s = s.strip()
        if len(clean_s) > 5:
            # Default the prompt to be the same as the audio, but user can change it later
            script_data.append({
                "search_term": clean_s, 
                "audio": clean_s,
                "image_path": None
            })
    return script_data

# --- 3. STOCK IMAGE HUNTER ---
def find_stock_images(script_data, is_short):
    st.write(f"📸 Hunting for Stock Photos...")
    prog_bar = st.progress(0)
    ddgs = DDGS()
    
    width, height = (720, 1280) if is_short else (1280, 720)
    
    for i, scene in enumerate(script_data):
        filename = f"scene_{i+1}.jpg"
        filepath = os.path.join(folder(), filename)
        
        # USE THE MANUAL PROMPT PROVIDED BY USER
        user_prompt = scene['search_term']
        
        # Force high quality stock sites
        site = random.choice(["site:unsplash.com", "site:pexels.com"])
        query = f"{user_prompt} {site}"
        
        found = False
        try:
            results = list(ddgs.images(query, max_results=5))
            for res in results:
                try:
                    r = requests.get(res['image'], timeout=5)
                    if r.status_code == 200:
                        with open(filepath, "wb") as f: f.write(r.content)
                        with Image.open(filepath) as check: check.verify()
                        found = True
                        break
                except: continue
        except: pass

        if not found:
            # Fallback
            Image.new('RGB', (width, height), (20, 20, 30)).save(filepath)

        script_data[i]["image_path"] = filepath
        prog_bar.progress((i+1)/len(script_data))
        
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
            try:
                img = Image.open(scene['image_path']).convert('RGB')
                img = img.resize(target_size, Image.LANCZOS)
                clips.append(ImageClip(np.array(img)).set_duration(clip_dur))
            except: pass
            
        final = concatenate_videoclips(clips, method="compose").set_audio(vc)
        output_path = os.path.join(p, "FINAL.mp4")
        final.write_videofile(output_path, fps=24, preset="ultrafast", codec="libx264", audio_codec="aac")
        
        status.success("✅ Done!")
        return output_path

    except Exception as e:
        st.error(f"Render Error: {e}")
        return None

# --- UI LOGIC ---
st.title("🎬 Dark Studio: Director Mode")

if "step" not in st.session_state: st.session_state.step = 1

with st.sidebar:
    st.header("Settings")
    format_choice = st.radio("Format:", ["📱 Shorts (9:16)", "🖥️ Video (16:9)"])
    is_short = "Short" in format_choice
    st.info("Step 1: Write Script\nStep 2: Define Visuals\nStep 3: Generate")

# --- STEP 1: SCRIPT ---
if st.session_state.step == 1:
    st.header("Step 1: The Script")
    raw_script = st.text_area("Paste your story:", height=200, placeholder="The ocean is deep. Creatures swim in the dark.")
    
    if st.button("NEXT: PLAN VISUALS ➡️", type="primary"):
        if len(raw_script) > 5:
            st.session_state.project_data = parse_script_by_sentences(raw_script)
            st.session_state.is_short = is_short
            st.session_state.step = 2
            st.rerun()
        else:
            st.error("Script is too short!")

# --- STEP 2: PROMPTING ---
elif st.session_state.step == 2:
    st.header("Step 2: The Visuals")
    st.info("Describe what image you want for each sentence. Be specific!")
    
    # Create a form so we can edit all prompts at once
    with st.form("prompt_form"):
        updated_data = []
        for i, scene in enumerate(st.session_state.project_data):
            st.subheader(f"Scene {i+1}")
            st.caption(f"🗣️ Audio: \"{scene['audio']}\"")
            
            # Here is where you type your manual prompt
            new_prompt = st.text_input(f"Visual Prompt for Scene {i+1}:", value=scene['search_term'], key=f"p_{i}")
            
            scene['search_term'] = new_prompt
            updated_data.append(scene)
            st.divider()
            
        if st.form_submit_button("🚀 LAUNCH PRODUCTION"):
            st.session_state.project_data = updated_data
            # Run the search now
            final_data = find_stock_images(st.session_state.project_data, st.session_state.is_short)
            st.session_state.project_data = final_data
            st.session_state.step = 3
            st.rerun()

# --- STEP 3: REVIEW & RENDER ---
elif st.session_state.step == 3:
    st.header("Step 3: Final Review")
    
    if st.button("⬅️ Back to Script"):
        st.session_state.step = 1
        st.rerun()
    
    for i, scene in enumerate(st.session_state.project_data):
        with st.expander(f"Scene {i+1}", expanded=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                if scene["image_path"] and os.path.exists(scene["image_path"]):
                    st.image(scene["image_path"])
                up = st.file_uploader(f"Replace {i+1}", type=['jpg','png'], key=f"up_{i}")
                if up:
                    with open(scene["image_path"], "wb") as f: f.write(up.getbuffer())
                    st.rerun()
            with c2:
                st.info(f"🗣️ {scene['audio']}")
                st.caption(f"🔍 Used Prompt: {scene['search_term']}")

    st.divider()
    if st.button("🔴 RENDER VIDEO", type="primary"):
        vid_path = render_video(st.session_state.project_data, st.session_state.is_short)
        if vid_path:
            st.video(vid_path)
            with open(vid_path, "rb") as f:
                st.download_button("📥 DOWNLOAD", f, "Director_Cut.mp4")
