import streamlit as st
import google.generativeai as genai
import os
import requests
import time
import urllib.parse
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeAudioClip, afx
import asyncio
import edge_tts
import shutil

# COMPATIBILITY
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS

st.set_page_config(page_title="Google AI Storyboard", layout="wide", page_icon="🤖")

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if os.path.exists(st.session_state.project_path):
        shutil.rmtree(st.session_state.project_path) 
    os.makedirs(st.session_state.project_path)

if "storyboard" not in st.session_state: st.session_state.storyboard = []

def folder(): return st.session_state.project_path

# --- GOOGLE GEMINI ROBOT ---
def run_google_director(api_key, topic):
    st.info("🤖 Google Gemini is directing the scene...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Ask Google to plan 6 visual panels
        prompt = (f"Act as a darker, cinematic film director. Create a 6-panel storyboard for a video about '{topic}'. "
                  f"For each panel, provide a vivid, highly detailed visual description suitable for image generation. "
                  f"Format: Panel 1: [Description] | Panel 2: [Description]...")
        
        response = model.generate_content(prompt)
        text = response.text
        
        # Parse the response into a list
        scenes = []
        for line in text.split('\n'):
            if "Panel" in line and ":" in line:
                # Clean up the text to get just the description
                desc = line.split(":", 1)[1].strip()
                scenes.append(desc)
        
        # Failsafe if parsing fails
        if len(scenes) < 6:
            scenes = [f"A cinematic shot of {topic}, scene {i+1}" for i in range(6)]
            
        return scenes[:6]
    except Exception as e:
        st.error(f"Google AI Error: {e}")
        return [f"A cinematic shot of {topic}, scene {i+1}" for i in range(6)]

# --- IMAGE GENERATOR ---
def generate_storyboard_images(scenes):
    st.write("🎨 Painting Storyboard...")
    generated_files = []
    
    my_bar = st.progress(0)
    
    for i, desc in enumerate(scenes):
        filename = f"panel_{i+1}.jpg"
        filepath = os.path.join(folder(), filename)
        
        # Use the "Smart Prompt" from Gemini to search for the perfect image
        # We clean it to keep it simple for the image engine
        search_prompt = urllib.parse.quote(desc[:100] + " cinematic lighting 8k")
        
        u = f"https://image.pollinations.ai/prompt/{search_prompt}?width=1080&height=1920&nologo=true&seed={random.randint(0,999)}"
        
        try:
            r = requests.get(u, timeout=6)
            if r.status_code == 200:
                with open(filepath, "wb") as f: f.write(r.content)
            else:
                raise Exception("Download failed")
        except:
            # Backup Black Image with Text
            img = Image.new('RGB', (1080, 1920), color=(15, 15, 20))
            d = ImageDraw.Draw(img)
            d.text((50, 900), f"Panel {i+1}\n{desc[:30]}...", fill=(255, 255, 255))
            img.save(filepath)
            
        generated_files.append(filepath)
        my_bar.progress((i+1)/6)
        
    return generated_files

# --- VIDEO RENDERER ---
def render_video_from_storyboard():
    st.write("🎬 Turning Storyboard into Video...")
    p = folder()
    
    # 1. Generate Voiceover
    text = f"This is the story of {st.session_state.topic}. " + " ".join(st.session_state.storyboard_text)
    voice = "en-US-ChristopherNeural"
    asyncio.run(edge_tts.Communicate(text[:500], voice).save(os.path.join(p, "voice.mp3")))
    
    try:
        vc = AudioFileClip(os.path.join(p, "voice.mp3"))
        files = sorted([os.path.join(p, f) for f in os.listdir(p) if f.startswith("panel")])
        
        if not files: return
        
        clips = []
        dur = vc.duration / len(files)
        
        for f in files:
            pil_img = Image.open(f).convert('RGB').resize((1080, 1920), Image.LANCZOS)
            clips.append(ImageClip(np.array(pil_img)).set_duration(dur))
            
        final = concatenate_videoclips(clips, method="compose").set_audio(vc)
        final.write_videofile(os.path.join(p, "FINAL.mp4"), fps=24, preset="ultrafast")
        
        st.video(os.path.join(p, "FINAL.mp4"))
        with open(os.path.join(p, "FINAL.mp4"), "rb") as f:
            st.download_button("📥 DOWNLOAD VIDEO", f, "Story.mp4")
            
    except Exception as e: st.error(f"Render Error: {e}")

# --- UI LAYOUT ---
st.title("🤖 Google AI Storyboarder")

# Sidebar for API Key
with st.sidebar:
    st.header("🔑 Settings")
    google_key = st.text_input("Google API Key:", type="password")
    st.caption("Get key from: aistudio.google.com")

st.header("1. The Concept")
topic = st.text_input("What is the story about?", "The lonely robot on Mars")
st.session_state.topic = topic

if st.button("🚀 Create Storyboard"):
    if len(google_key) < 10:
        st.error("Please enter your Google API Key first!")
    else:
        # 1. Ask Google to write the scenes
        scenes = run_google_director(google_key, topic)
        st.session_state.storyboard_text = scenes
        
        # 2. Generate the Images
        files = generate_storyboard_images(scenes)
        st.session_state.storyboard_images = files
        st.success("Storyboard Created!")

# DISPLAY THE STORYBOARD (Grid View)
if "storyboard_images" in st.session_state:
    st.header("2. The Visual Plan")
    
    # Display in columns of 3
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]
    
    for i, img_path in enumerate(st.session_state.storyboard_images):
        text = st.session_state.storyboard_text[i]
        with cols[i % 3]:
            st.image(img_path, caption=f"Panel {i+1}", use_container_width=True)
            st.caption(f"*{text[:60]}...*")

    st.header("3. Production")
    if st.button("🎥 Render Final Video"):
        render_video_from_storyboard()
