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
# Fixes the "Pink Screen" crash on cloud servers
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS
if not hasattr(Image, 'BILINEAR'):
    Image.BILINEAR = Image.BICUBIC

st.set_page_config(page_title="Dark Studio: Stock Hunter", layout="wide", page_icon="📸")

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
    # Split text by punctuation (. ! ?) to make scenes
    sentences = re.split(r'(?<=[.!?])\s+', raw_text)
    script_data = []
    for s in sentences:
        clean_s = s.strip()
        if len(clean_s) > 5:
            script_data.append({
                "search_term": clean_s, 
                "audio": clean_s
            })
    return script_data

# --- 3. STOCK IMAGE HUNTER ---
def find_stock_images(script_data, is_short):
    st.write(f"📸 Hunting for Stock Photos (Unsplash/Pexels)...")
    prog_bar = st.progress(0)
    
    # Initialize Search Engine
    ddgs = DDGS()
    
    # Dimensions (High Res)
    width, height = (720, 1280) if is_short else (1280, 720)
    
    for i, scene in enumerate(script_data):
        filename = f"scene_{i+1}.jpg"
        filepath = os.path.join(folder(), filename)
        
        # KEY CHANGE: We force the search to look at Stock Sites
        # We strip common words to get the "Core Subject" (e.g. "The Ocean" -> "Ocean")
        core_subject = scene['search_term'].replace("The", "").replace(" is ", " ").replace(" a ", " ")
        
        # We search specifically on Unsplash or Pexels for high quality
        site = random.choice(["site:unsplash.com", "site:pexels.com"])
        query = f"{core_subject} {site}"
        
        found = False
        try:
            # Search for real images
            # We fetch 10 results to increase odds of finding a valid downloadable one
            results = list(ddgs.images(query, max_results=10))
            
            for res in results:
                try:
                    img_url = res['image']
                    # Try to download
                    r = requests.get(img_url, timeout=5)
                    if r.status_code == 200:
                        with open(filepath, "wb") as f: f.write(r.content)
                        # Verify it's a real image and not a broken file
                        with Image.open(filepath) as check:
                            check.verify()
                        found = True
                        break # Stop looking if we found one
                except:
                    continue
                    
        except Exception as e:
            print(f"Stock search failed: {e}")

        # Fallback: Create Black Placeholder if search fails
        if not found:
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
        
        # Resolution (480p Safe Mode to prevent crash)
        target_size = (480, 854) if is_short else (854, 480)
        
        clips = []
        for scene in project_data:
            try:
                img = Image.open(scene['image_path']).convert('RGB')
                img = img.resize(target_size, Image.LANCZOS)
                clips.append(ImageClip(np.array(img)).set_duration(clip_dur))
            except:
                pass # Skip broken images
            
        final = concatenate_videoclips(clips, method="compose").set_audio(vc)
        output_path = os.path.join(p, "FINAL.mp4")
        final.write_videofile(output_path, fps=24, preset="ultrafast", codec="libx264", audio_codec="aac")
        
        status.success("✅ Done!")
        return output_path

    except Exception as e:
        st.error(f"Render Error: {e}")
        st.code(traceback.format_exc())
        return None

# --- UI ---
st.title("📸 Dark Studio: Stock Hunter")

with st.sidebar:
    st.header("Settings")
    format_choice = st.radio("Format:", ["📱 Shorts (9:16)", "🖥️ Video (16:9)"])
    is_short = "Short" in format_choice
    
    st.info("💡 **Source:** This version searches Unsplash.com and Pexels.com for professional stock photography.")

# INPUT
raw_script = st.text_area("Paste your script here:", height=200, 
                          placeholder="The ocean is deep and mysterious. Giant whales swim in the blue water. Coral reefs are full of life.")

if st.button("🚀 FIND STOCK PHOTOS", type="primary"):
    if len(raw_script) < 5:
        st.error("Please write a script!")
    else:
        # 1. Parse
        data = parse_script_by_sentences(raw_script)
        st.success(f"Split into {len(data)} scenes.")
        
        # 2. Find Stock Images
        final_data = find_stock_images(data, is_short)
        
        st.session_state.project_data = final_data
        st.session_state.is_short = is_short
        st.rerun()

# EDITOR
if "project_data" in st.session_state:
    st.divider()
    st.header("🎞️ Timeline Review")
    
    for i, scene in enumerate(st.session_state.project_data):
        with st.expander(f"Scene {i+1}: \"{scene['audio'][:40]}...\"", expanded=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                if os.path.exists(scene["image_path"]):
                    # SAFE LOAD to prevent pink screen
                    st.image(scene["image_path"])
                
                # Upload Manual Replacement
                up = st.file_uploader(f"Replace Image {i+1}", type=['jpg','png'], key=f"up_{i}")
                if up:
                    with open(scene["image_path"], "wb") as f: f.write(up.getbuffer())
                    st.rerun()
            with c2:
                st.info(f"🗣️ **Voice:** {scene['audio']}")
                st.caption(f"🔍 **Search Query:** {scene['search_term']}")

    st.divider()
    if st.button("🔴 RENDER FINAL VIDEO", type="primary"):
        vid_path = render_video(st.session_state.project_data, st.session_state.get("is_short", True))
        if vid_path:
            st.video(vid_path)
            with open(vid_path, "rb") as f:
                st.download_button("📥 DOWNLOAD VIDEO", f, "Stock_Video.mp4")
