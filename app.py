import streamlit as st
import google.generativeai as genai
import os
import requests
import time
import urllib.parse
import random
import numpy as np
from PIL import Image, ImageDraw
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeAudioClip
import asyncio
import edge_tts
import shutil
from duckduckgo_search import DDGS

# COMPATIBILITY
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS

st.set_page_config(page_title="Story Robot: Instant Mode", layout="wide", page_icon="⚡")

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if os.path.exists(st.session_state.project_path):
        shutil.rmtree(st.session_state.project_path) 
    os.makedirs(st.session_state.project_path)

if "storyboard_text" not in st.session_state: st.session_state.storyboard_text = []

def folder(): return st.session_state.project_path

# --- 1. THE DIRECTOR (Google Gemini) ---
def run_google_director(api_key, topic):
    st.info("🧠 Gemini is writing the story...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = (f"Write a 6-sentence dark, cinematic story about '{topic}'. "
                  f"Format as a list of 6 distinct visual sentences.")
        
        response = model.generate_content(prompt)
        text = response.text
        
        # Clean up text
        scenes = [line.strip().replace("*", "") for line in text.split('\n') if len(line) > 10]
        return scenes[:6]
    except Exception as e:
        st.error(f"Gemini Error: {e}")
        return [f"The mystery of {topic} begins now.", f"Deep in the shadows, something moves.", 
                f"The world changed forever.", f"Nobody expected what happened next.",
                f"The truth was hidden in plain sight.", f"This is the end of the beginning."]

# --- 2. THE ARTIST (DuckDuckGo Search) ---
def find_cinematic_images(scenes):
    st.write("⚡ Finding Cinematic Assets (No Keys, No Lag)...")
    generated_files = []
    my_bar = st.progress(0)
    ddgs = DDGS()
    
    for i, desc in enumerate(scenes):
        filename = f"panel_{i+1}.jpg"
        filepath = os.path.join(folder(), filename)
        
        # The Search Query: We ask for "Concept Art" to match the AI vibe
        keywords = f"cinematic concept art {desc[:20]} vertical wallpaper 4k dark moody"
        
        found = False
        try:
            # Search for images
            results = list(ddgs.images(keywords, max_results=5))
            if results:
                # Try to download the first valid image
                for res in results:
                    img_url = res['image']
                    try:
                        r = requests.get(img_url, timeout=3)
                        if r.status_code == 200:
                            with open(filepath, "wb") as f: f.write(r.content)
                            # Verify it's a real image
                            try: 
                                Image.open(filepath).verify()
                                found = True
                                break
                            except: pass
                    except: pass
        except: pass
        
        # Backup if search fails: Create a Text Card
        if not found:
            img = Image.new('RGB', (1080, 1920), color=(10, 10, 20))
            d = ImageDraw.Draw(img)
            d.text((100, 800), f"SCENE {i+1}", fill=(255, 255, 255))
            img.save(filepath)
            
        generated_files.append(filepath)
        my_bar.progress((i+1)/6)
        
    return generated_files

# --- 3. THE EDITOR (Video Render) ---
def render_video():
    st.write("🎬 Assembling Video...")
    p = folder()
    
    # Voiceover
    full_text = " ".join(st.session_state.storyboard_text)
    asyncio.run(edge_tts.Communicate(full_text, "en-US-ChristopherNeural").save(os.path.join(p, "voice.mp3")))
    
    try:
        vc = AudioFileClip(os.path.join(p, "voice.mp3"))
        files = st.session_state.storyboard_images
        
        clips = []
        dur = max(vc.duration / len(files), 2)
        
        for f in files:
            # Resize image to fit screen
            pil_img = Image.open(f).convert('RGB')
            # Crop to center 9:16
            width, height = pil_img.size
            target_ratio = 1080/1920
            
            if width/height > target_ratio:
                # Too wide, crop width
                new_width = int(height * target_ratio)
                left = (width - new_width) // 2
                pil_img = pil_img.crop((left, 0, left + new_width, height))
            else:
                # Too tall, crop height
                new_height = int(width / target_ratio)
                top = (height - new_height) // 2
                pil_img = pil_img.crop((0, top, width, top + new_height))
                
            pil_img = pil_img.resize((1080, 1920), Image.LANCZOS)
            clips.append(ImageClip(np.array(pil_img)).set_duration(dur))
            
        final = concatenate_videoclips(clips, method="compose").set_audio(vc)
        final.write_videofile(os.path.join(p, "FINAL.mp4"), fps=24, preset="ultrafast")
        
        st.video(os.path.join(p, "FINAL.mp4"))
        with open(os.path.join(p, "FINAL.mp4"), "rb") as f:
            st.download_button("📥 DOWNLOAD VIDEO", f, "Story.mp4")
            
    except Exception as e: st.error(f"Render Error: {e}")

# --- UI ---
st.title("⚡ Instant Story Robot")
st.caption("Using Search Engine Assets (No Keys Required for Images)")

with st.sidebar:
    google_key = st.text_input("Google API Key (For Script):", type="password")

topic = st.text_input("Topic:", "The Mystery of the Deep Ocean")

if st.button("🚀 GO!"):
    if len(google_key) < 5:
        st.error("Please enter Google Key for the script!")
    else:
        # 1. Script
        scenes = run_google_director(google_key, topic)
        st.session_state.storyboard_text = scenes
        st.success("Script Written!")
        
        # 2. Images (Search)
        files = find_cinematic_images(scenes)
        st.session_state.storyboard_images = files
        
        # Show Preview
        cols = st.columns(3)
        for i, f in enumerate(files):
            with cols[i%3]:
                st.image(f, caption=f"Scene {i+1}")
        
        # 3. Render Button
        st.button("🎥 RENDER FINAL VIDEO", on_click=render_video)
