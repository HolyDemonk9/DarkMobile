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
import urllib.parse
import time

# COMPATIBILITY
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS

st.set_page_config(page_title="Dark Studio: Progress", layout="wide", page_icon="⏳")

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if os.path.exists(st.session_state.project_path):
        shutil.rmtree(st.session_state.project_path) 
    os.makedirs(st.session_state.project_path)

def folder(): return st.session_state.project_path

# --- 1. CALCULATOR ---
def calculate_pacing(duration, scenes):
    time_per_scene = duration / scenes
    total_words = int(duration * 2.2) 
    return time_per_scene, total_words

# --- 2. LOGIC DIRECTOR ---
def run_logic_director(topic, n_scenes, total_words, is_short):
    st.info(f"🧠 Writing {total_words}-word script for '{topic}'...")
    
    visual_styles = [
        "Cinematic wide shot of {t}, golden hour, 8k, hyper-realistic",
        "Extreme close-up details of {t}, macro photography, unreal engine 5",
        "Dark atmospheric shot of {t}, silhouette, fog, mysterious lighting",
        "Drone overhead view of {t}, symmetrical, high contrast",
        "Action shot of {t}, dynamic motion blur, 4k",
        "Abstract concept art of {t}, dreamlike, surreal, double exposure"
    ]
    
    script_data = []
    
    intros = [f"The story of {topic} is a mystery.", f"{topic} has changed the world.", f"We explore the truth of {topic}."]
    middles = [f"Deep inside {topic}, secrets remain.", f"Experts are baffled by {topic}.", f"The evidence for {topic} is clear."]
    outros = [f"This is the legend of {topic}.", f"{topic} will never be forgotten.", f"The end of {topic} is near."]
    
    for i in range(n_scenes):
        style = visual_styles[i % len(visual_styles)].format(t=topic)
        if i == 0: text = random.choice(intros)
        elif i == n_scenes - 1: text = random.choice(outros)
        else: text = random.choice(middles)
        script_data.append({"visual": style, "audio": text})
        
    return script_data

# --- 3. ARTIST ---
def generate_pro_images(script_data, is_short):
    st.write("🎨 Generating Assets...")
    # Add a visible progress bar for image generation
    my_bar = st.progress(0, text="Downloading Images...")
    
    width, height = (1080, 1920) if is_short else (1920, 1080)
    
    for i, scene in enumerate(script_data):
        filename = f"scene_{i+1}.jpg"
        filepath = os.path.join(folder(), filename)
        
        safe_prompt = requests.utils.quote(scene['visual'])
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width={width}&height={height}&nologo=true&seed={random.randint(0,999)}&model=flux"
        
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                with open(filepath, "wb") as f: f.write(r.content)
            else:
                Image.new('RGB', (width, height), (20,20,20)).save(filepath)
        except:
            Image.new('RGB', (width, height), (20,20,20)).save(filepath)
            
        script_data[i]["image_path"] = filepath
        # Update bar
        percent = int(((i+1)/len(script_data))*100)
        my_bar.progress((i+1)/len(script_data), text=f"Downloading Image {i+1}/{len(script_data)} ({percent}%)")
        
    return script_data

# --- 4. RENDERER WITH PROGRESS ---
def render_with_progress(project_data, is_short):
    p = folder()
    
    # We use a Status Container to show steps
    with st.status("🚀 Starting Render Engine...", expanded=True) as status:
        
        # STEP 1: AUDIO
        status.write("🎙️ Step 1/4: Generating Voiceover...")
        full_text = " ".join([s['audio'] for s in project_data])
        voice_path = os.path.join(p, "voice.mp3")
        asyncio.run(edge_tts.Communicate(full_text, "en-US-ChristopherNeural").save(voice_path))
        
        # STEP 2: IMAGES
        status.write("🎨 Step 2/4: Processing & Resizing Images...")
        target_size = (720, 1280) if is_short else (1280, 720)
        vc = AudioFileClip(voice_path)
        clip_dur = vc.duration / len(project_data)
        
        clips = []
        # Create a mini progress bar inside the status for image processing
        proc_bar = st.progress(0)
        for i, scene in enumerate(project_data):
            try:
                img = Image.open(scene['image_path']).convert('RGB')
                img = img.resize(target_size, Image.LANCZOS)
                clips.append(ImageClip(np.array(img)).set_duration(clip_dur))
            except: pass
            proc_bar.progress((i+1)/len(project_data))
            
        # STEP 3: STITCHING
        status.write("🎬 Step 3/4: Stitching Video Timeline...")
        final = concatenate_videoclips(clips, method="compose").set_audio(vc)
        
        # STEP 4: WRITING FILE
        status.write("💾 Step 4/4: Saving Final File (Please Wait)...")
        output_path = os.path.join(p, "FINAL.mp4")
        # We cannot get a % bar for this specific function in Streamlit easily, 
        # but the status shows we are in the final stage.
        final.write_videofile(output_path, fps=24, preset="ultrafast", codec="libx264", audio_codec="aac")
        
        status.update(label="✅ Render Complete!", state="complete", expanded=False)
        
    return output_path

# --- UI ---
st.title("⚡ Dark Studio: Progress Edition")

with st.sidebar:
    st.header("1. Settings")
    
    # MOVED TO TOP
    st.subheader("⏱️ Time Controls")
    duration = st.number_input("Total Duration (Seconds):", min_value=10, max_value=300, value=30, help="Type the exact seconds you want.")
    scenes = st.number_input("Number of Scenes:", 3, 20, 5)
    
    st.divider()
    
    st.subheader("📺 Format")
    format_choice = st.radio("Style:", ["📱 Shorts (9:16)", "🖥️ Video (16:9)"])
    is_short = "Short" in format_choice
    topic = st.text_input("Topic:", "The Deep Ocean")
    
    if st.button("🚀 GENERATE DRAFT", type="primary"):
        tps, words = calculate_pacing(duration, scenes)
        data = run_logic_director(topic, scenes, words, is_short)
        final_data = generate_pro_images(data, is_short)
        st.session_state.project_data = final_data
        st.session_state.is_short = is_short
        st.rerun()

if "project_data" in st.session_state:
    st.header("2. Review")
    
    # Progress Bar for Review
    review_bar = st.progress(100, text="Draft Ready for Review")
    
    for i, scene in enumerate(st.session_state.project_data):
        with st.expander(f"Scene {i+1}", expanded=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                if os.path.exists(scene["image_path"]):
                    st.image(scene["image_path"])
                up = st.file_uploader(f"Replace {i+1}", type=['jpg','png'], key=f"up_{i}")
                if up:
                    with open(scene["image_path"], "wb") as f: f.write(up.getbuffer())
                    st.rerun()
            with c2:
                st.code(scene['visual'])
                st.markdown(f"[👉 Open Gemini](https://gemini.google.com/app)")
                new_text = st.text_area("Audio:", value=scene['audio'], key=f"txt_{i}")
                st.session_state.project_data[i]['audio'] = new_text

    st.divider()
    
    if st.button("🟢 RENDER VIDEO NOW", type="primary"):
        try:
            vid_path = render_with_progress(st.session_state.project_data, st.session_state.get("is_short", True))
            st.success("Video Ready!")
            st.video(vid_path)
            with open(vid_path, "rb") as f:
                st.download_button("📥 DOWNLOAD VIDEO", f, "My_Video.mp4")
        except Exception as e:
            st.error(f"Error: {e}")
