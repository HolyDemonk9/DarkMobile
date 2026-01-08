import streamlit as st
import os
import requests
import random
import asyncio
import edge_tts
from PIL import Image
import shutil
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips
import numpy as np
import traceback

# COMPATIBILITY
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS

st.set_page_config(page_title="Dark Studio: Visible", layout="wide", page_icon="👀")

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if os.path.exists(st.session_state.project_path):
        shutil.rmtree(st.session_state.project_path) 
    os.makedirs(st.session_state.project_path)

def folder(): return st.session_state.project_path

# --- 1. SETTINGS & CALCULATOR ---
def calculate_pacing(duration, scenes):
    time_per_scene = duration / scenes
    total_words = int(duration * 2.2) 
    return time_per_scene, total_words

# --- 2. LOGIC DIRECTOR ---
def run_logic_director(topic, n_scenes, total_words, is_short):
    st.info(f"🧠 Writing Script...")
    
    visual_styles = [
        "Cinematic wide shot of {t}, 8k",
        "Close-up detail of {t}, highly detailed",
        "Dark atmospheric shot of {t}, silhouette",
        "Drone view of {t}, high contrast",
        "Action shot of {t}, motion blur",
        "Abstract art of {t}, dreamlike"
    ]
    
    script_data = []
    
    intros = [f"The story of {topic} begins here.", f"{topic} is a mystery to many.", f"Let us explore {topic}."]
    middles = [f"Deep inside {topic}, secrets remain.", f"We are learning more about {topic}.", f"The truth of {topic} is revealing."]
    outros = [f"This concludes the story of {topic}.", f"{topic} will never be forgotten.", f"The legend of {topic} lives on."]
    
    for i in range(n_scenes):
        style = visual_styles[i % len(visual_styles)].format(t=topic)
        if i == 0: text = random.choice(intros)
        elif i == n_scenes - 1: text = random.choice(outros)
        else: text = random.choice(middles)
        script_data.append({"visual": style, "audio": text})
        
    return script_data

# --- 3. ARTIST ---
def generate_pro_images(script_data, is_short):
    st.write("🎨 Setting up Placeholders...")
    width, height = (720, 1280) if is_short else (1280, 720)
    
    for i, scene in enumerate(script_data):
        filename = f"scene_{i+1}.jpg"
        filepath = os.path.join(folder(), filename)
        # Create Black Placeholder
        Image.new('RGB', (width, height), (30,30,40)).save(filepath)
        script_data[i]["image_path"] = filepath
        
    return script_data

# --- UI START ---
st.title("👀 Dark Studio: High Visibility Mode")

with st.sidebar:
    st.header("1. Settings")
    
    # DURATION BAR
    duration = st.number_input("⏱️ Total Duration (Seconds):", min_value=10, max_value=300, value=20)
    scenes = st.number_input("🎬 Scenes:", 3, 20, 4)
    
    format_choice = st.radio("Style:", ["📱 Shorts (9:16)", "🖥️ Video (16:9)"])
    is_short = "Short" in format_choice
    topic = st.text_input("Topic:", "Test Video")
    
    if st.button("🚀 START NEW PROJECT", type="primary"):
        tps, words = calculate_pacing(duration, scenes)
        data = run_logic_director(topic, scenes, words, is_short)
        final_data = generate_pro_images(data, is_short)
        st.session_state.project_data = final_data
        st.session_state.is_short = is_short
        st.rerun()

# --- MAIN AREA ---
if "project_data" in st.session_state:
    st.header("2. Image Manager")
    
    for i, scene in enumerate(st.session_state.project_data):
        c1, c2 = st.columns([1, 2])
        with c1:
            if os.path.exists(scene["image_path"]):
                st.image(scene["image_path"])
            
            up = st.file_uploader(f"Upload Image {i+1}", type=['jpg','png','jpeg'], key=f"up_{i}")
            if up:
                with open(scene["image_path"], "wb") as f: f.write(up.getbuffer())
                st.success(f"Image {i+1} Saved!")
                st.rerun()
                
        with c2:
            st.text_area("Voice Text:", value=scene['audio'], key=f"txt_{i}")
            st.session_state.project_data[i]['audio'] = scene['audio']

    st.divider()
    
    # --- RENDER LOGIC (DIRECTLY IN UI) ---
    st.header("3. Final Export")
    
    # STATUS PLACEHOLDERS (These will update visibly)
    status_text = st.empty()
    progress_bar = st.progress(0)
    
    if st.button("🔴 RENDER VIDEO NOW", type="primary"):
        try:
            p = folder()
            project_data = st.session_state.project_data
            
            # STEP 1: AUDIO
            status_text.markdown("### 🎙️ Step 1/4: Generating Audio...")
            progress_bar.progress(10)
            
            full_text = " ".join([s['audio'] for s in project_data])
            if not full_text: full_text = "Audio generation test."
            
            voice_path = os.path.join(p, "voice.mp3")
            asyncio.run(edge_tts.Communicate(full_text, "en-US-ChristopherNeural").save(voice_path))
            
            if not os.path.exists(voice_path): raise Exception("Audio file missing!")
            vc = AudioFileClip(voice_path)
            clip_dur = vc.duration / len(project_data)
            
            # STEP 2: IMAGES
            status_text.markdown("### 🎨 Step 2/4: Processing Images...")
            progress_bar.progress(30)
            
            target_size = (480, 854) if st.session_state.is_short else (854, 480)
            clips = []
            
            for i, scene in enumerate(project_data):
                # Update status for every image
                status_text.write(f"Processing Image {i+1}...")
                img = Image.open(scene['image_path']).convert('RGB')
                img = img.resize(target_size, Image.LANCZOS)
                clips.append(ImageClip(np.array(img)).set_duration(clip_dur))
                
                # Increment bar
                current_prog = 30 + int((i / len(project_data)) * 40)
                progress_bar.progress(current_prog)

            # STEP 3: STITCHING
            status_text.markdown("### 🎬 Step 3/4: Stitching Video...")
            progress_bar.progress(80)
            
            final = concatenate_videoclips(clips, method="compose")
            final = final.set_audio(vc)
            
            # STEP 4: SAVING
            status_text.markdown("### 💾 Step 4/4: Saving (Please Wait)...")
            progress_bar.progress(90)
            
            output_path = os.path.join(p, "FINAL_DEBUG.mp4")
            final.write_videofile(output_path, fps=15, preset="ultrafast", codec="libx264", audio_codec="aac")
            
            progress_bar.progress(100)
            status_text.success("✅ DONE! Video is ready below.")
            
            st.video(output_path)
            with open(output_path, "rb") as f:
                st.download_button("📥 DOWNLOAD RESULT", f, "final_video.mp4")

        except Exception as e:
            st.error("❌ ERROR:")
            st.code(traceback.format_exc())
