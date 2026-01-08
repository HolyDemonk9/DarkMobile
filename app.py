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
from PIL import Image, ImageOps
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeAudioClip, afx, vfx
import shutil

# CONFIG
st.set_page_config(page_title="Dark Studio: Cinematic", layout="centered", page_icon="🎥")

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
    st.write(f"🎨 gathering Cinematic Assets for: {topic}...")
    
    # We will FORCE 6 images to ensure fast pacing
    total_images = 6
    bar = st.progress(0)
    
    # Clean the topic for search
    search_term = urllib.parse.quote(topic)
    
    for i in range(total_images):
        filename = f"{i+1:03}.jpg"
        filepath = os.path.join(folder(), filename)
        
        # STRATEGY: High-Speed Stock Search (No Keys Required)
        # This uses different random seeds to get different photos of the SAME topic
        u_stock = f"https://image.pollinations.ai/prompt/{search_term}%20cinematic%20photography?width=1080&height=1920&nologo=true&seed={random.randint(0, 99999)}"
        
        try:
            # Add a random number to the request to trick the cache
            r = requests.get(u_stock, timeout=6)
            if r.status_code == 200 and len(r.content) > 2000:
                with open(filepath, "wb") as f: f.write(r.content)
            else:
                raise Exception("Image failed")
        except:
            # Backup: If Pollinations fails, use Picsum (Abstract/Dark)
            try:
                u_backup = f"https://picsum.photos/1080/1920?random={i}"
                r = requests.get(u_backup, timeout=5)
                with open(filepath, "wb") as f: f.write(r.content)
            except: 
                # Last Resort: Black Screen
                img = Image.new('RGB', (1080, 1920), color=(10, 10, 10))
                img.save(filepath)

        bar.progress((i + 1) / total_images)
        time.sleep(0.5) 
    
    st.success(f"✅ 6/6 Cinematic Assets Ready!")

def generate_ai_script(topic):
    st.info("🧠 AI is directing...")
    style = "suspenseful, fast-paced, documentary style"
    prompt = f"Write a 120 word viral YouTube script about '{topic}'. Style: {style}. No scene descriptions, just the voiceover."
    try:
        txt = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}").text
        st.session_state.generated_script = txt
        st.success("✅ Script Written!")
        st.rerun() 
    except: st.error("AI Script Failed")

def get_audio_from_text(text_script):
    st.write("🎙️ Recording Voice...")
    # Using a deeper, more storytelling voice
    voice = "en-US-ChristopherNeural" 
    async def _save():
        c = edge_tts.Communicate(text_script, voice)
        await c.save(os.path.join(folder(), "voice.mp3"))
    asyncio.run(_save())
    st.success("✅ Audio Ready!")

# --- THE MAGIC SAUCE: ZOOM EFFECT ---
def zoom_in_effect(clip, zoom_ratio=0.04):
    def effect(get_frame, t):
        img = Image.fromarray(get_frame(t))
        base_size = img.size
        new_size = [
            int(base_size[0] * (1 + (zoom_ratio * t))),
            int(base_size[1] * (1 + (zoom_ratio * t)))
        ]
        # High-quality resize
        img = img.resize(new_size, Image.LANCZOS)
        
        # Center Crop
        x = (new_size[0] - base_size[0]) // 2
        y = (new_size[1] - base_size[1]) // 2
        img = img.crop([x, y, x + base_size[0], y + base_size[1]])
        return np.array(img)
    return clip.fl(effect)

def render_video():
    st.write("🎬 Rendering (Adding Motion & Effects)...")
    p = folder()
    try:
        if not os.path.exists(os.path.join(p, "voice.mp3")): 
            st.error("❌ No Audio! Record voice first.")
            return
        
        vc = AudioFileClip(os.path.join(p, "voice.mp3"))
        files = sorted([os.path.join(p, f) for f in os.listdir(p) if f.endswith(".jpg")])
        
        if len(files) == 0:
            st.error("❌ No images found!")
            return

        # Calculate timing per image
        dur = vc.duration / len(files)
        clips = []
        
        # BUILD CLIPS WITH ANIMATION
        for i, f in enumerate(files):
            try:
                # 1. Load Image
                pil_img = Image.open(f).convert('RGB')
                pil_img = pil_img.resize((1080, 1920), Image.LANCZOS)
                
                # 2. Create Clip
                clip = ImageClip(np.array(pil_img)).set_duration(dur)
                
                # 3. APPLY "THE SHAKE" (Zoom Effect)
                # Alternating zoom direction could be complex, so we stick to Zoom IN
                # This makes it look alive!
                clip = zoom_in_effect(clip, zoom_ratio=0.04) 
                
                clips.append(clip)
            except Exception as e: 
                print(f"Skipped bad frame: {e}")

        if not clips:
            st.error("Critical Render Error.")
            return

        # SAFE MUSIC (Dark/Cinematic)
        final_audio = vc
        try:
            m_url = "https://ia800300.us.archive.org/17/items/TheSlenderManSong/Anxiety.mp3"
            r = requests.get(m_url, timeout=3)
            with open(os.path.join(p, "music.mp3"), "wb") as f: f.write(r.content)
            mc = AudioFileClip(os.path.join(p, "music.mp3"))
            
            # Loop music
            if mc.duration < vc.duration: 
                mc = afx.audio_loop(mc, duration=vc.duration)
            else: 
                mc = mc.subclip(0, vc.duration)
                
            # Lower music volume to 10% so voice is clear
            final_audio = CompositeAudioClip([vc, mc.volumex(0.10)])
        except: pass

        # FINAL RENDER
        final = concatenate_videoclips(clips, method="compose").set_audio(final_audio)
        output_path = os.path.join(p, "FINAL.mp4")
        
        # Ultrafast preset to prevent server timeout
        final.write_videofile(output_path, fps=24, preset="ultrafast", codec="libx264")
        
        st.balloons()
        st.success("DONE! VIDEO IS READY.")
        st.video(output_path)
        
        with open(output_path, "rb") as file:
            st.download_button("📥 DOWNLOAD MOVIE", file, "DarkVideo.mp4", "video/mp4")
        
    except Exception as e: st.error(f"Render Failed: {e}")

# --- UI LAYOUT ---
st.title("🎥 Dark Studio: Cinematic Mode")
st.caption("Auto-Motion Engine Active")

topic = st.text_input("Topic:", "The Mystery of the Ocean")

col1, col2 = st.columns(2)

if col1.button("1. Gather Assets"):
    get_images(topic)

if col2.button("2. Write Script"):
    generate_ai_script(topic)

st.subheader("Script Editor")
script_text = st.text_area("Review Script:", value=st.session_state.generated_script, height=150)

if st.button("3. Record Voice"):
    if len(script_text) < 5:
        st.error("Script is empty!")
    else:
        get_audio_from_text(script_text)

st.write("---")
st.caption("Status Check:")
img_count = len([f for f in os.listdir(folder()) if f.endswith(".jpg")])
st.write(f"🖼️ Images: {img_count}/6 | 🔊 Audio: {'Ready' if os.path.exists(os.path.join(folder(), 'voice.mp3')) else 'Not Ready'}")

if st.button("🔴 RENDER CINEMATIC VIDEO", type="primary"):
    render_video()

st.success("✅ SYSTEM READY")
