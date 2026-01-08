import streamlit as st
import os
import requests
import random
from duckduckgo_search import DDGS
from PIL import Image
import shutil
import asyncio
import edge_tts
import numpy as np
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeAudioClip, afx

# COMPATIBILITY
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS

st.set_page_config(page_title="Dark Studio: Pro", layout="wide", page_icon="💎")

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if os.path.exists(st.session_state.project_path):
        shutil.rmtree(st.session_state.project_path) 
    os.makedirs(st.session_state.project_path)

def folder(): return st.session_state.project_path

# --- 1. THE CALCULATOR (Custom Duration) ---
def calculate_pacing(duration, scenes):
    # Precise math for pacing
    time_per_scene = duration / scenes
    # Speaking rate (approx 2.5 words per second for a calm documentary voice)
    total_words = int(duration * 2.5)
    return time_per_scene, total_words

# --- 2. THE PRO DIRECTOR (Smart Prompting) ---
def run_pro_director(topic, n_scenes, total_words, is_short):
    format_type = "Vertical 9:16 Portrait" if is_short else "Wide 16:9 Cinematic"
    
    st.info(f"💎 AI is crafting a professional script & art prompts ({total_words} words)...")
    
    try:
        ddgs = DDGS()
        # WE USE "MAGIC KEYWORDS" IN THE SYSTEM PROMPT TO FORCE QUALITY
        magic_style = "hyper-realistic, 8k resolution, volumetric lighting, dark moody atmosphere, highly detailed, Unreal Engine 5 render"
        
        prompt = (f"Act as an award-winning documentary director. Write a script about '{topic}'."
                  f"\n\nRULES:"
                  f"\n1. List exactly {n_scenes} scenes."
                  f"\n2. Total voiceover word count must be approx {total_words} words."
                  f"\n3. VISUAL PROMPT: Describe a {format_type} image. MUST include these style keywords: {magic_style}."
                  f"\n4. FORMAT: EXACTLY 'VISUAL PROMPT | VOICEOVER TEXT'"
                  f"\n5. Do not number the lines. Just the content.")
        
        # Using GPT-4o-mini via DuckDuckGo (Smartest Free Model)
        response = ddgs.chat(prompt, model='gpt-4o-mini')
        
        script_data = []
        for line in response.split('\n'):
            if "|" in line:
                parts = line.split("|")
                if len(parts) >= 2:
                    script_data.append({
                        "visual": parts[0].strip(),
                        "audio": parts[1].strip()
                    })
        
        return script_data[:n_scenes]

    except Exception as e:
        st.error(f"Director Error: {e}")
        return []

# --- 3. THE PRO ARTIST (High-Quality Generator) ---
def generate_pro_images(script_data, is_short):
    st.write("🎨 Generating Professional Assets...")
    my_bar = st.progress(0)
    
    width, height = (1080, 1920) if is_short else (1920, 1080)
    
    for i, scene in enumerate(script_data):
        filename = f"scene_{i+1}.jpg"
        filepath = os.path.join(folder(), filename)
        
        # CLEAN THE PROMPT FOR URL
        # We take the AI's detailed description and encode it safely
        safe_prompt = requests.utils.quote(scene['visual'])
        
        # POLLINATIONS AI (Best Free High-Quality Generator)
        # We add a random seed so every image is unique
        seed = random.randint(0, 99999)
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width={width}&height={height}&nologo=true&seed={seed}&model=flux"
        
        # RETRY LOOP (Reliability Fix)
        # If it fails, try 3 times before giving up
        downloaded = False
        for attempt in range(3):
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200 and len(r.content) > 5000:
                    with open(filepath, "wb") as f: f.write(r.content)
                    downloaded = True
                    break
            except:
                pass
        
        # Backup: Black Screen with Text if ALL fails
        if not downloaded:
            img = Image.new('RGB', (width, height), color=(10, 10, 20))
            img.save(filepath)
            
        script_data[i]["image_path"] = filepath
        my_bar.progress((i+1)/len(script_data))
        
    return script_data

# --- 4. RENDER ENGINE (Ken Burns Zoom) ---
def zoom_in_effect(clip, zoom_ratio=0.04):
    def effect(get_frame, t):
        img = Image.fromarray(get_frame(t))
        base_size = img.size
        new_size = [
            int(base_size[0] * (1 + (zoom_ratio * t))),
            int(base_size[1] * (1 + (zoom_ratio * t)))
        ]
        img = img.resize(new_size, Image.LANCZOS)
        x = (new_size[0] - base_size[0]) // 2
        y = (new_size[1] - base_size[1]) // 2
        img = img.crop([x, y, x + base_size[0], y + base_size[1]])
        return np.array(img)
    return clip.fl(effect)

def render_video(project_data, is_short):
    st.write("⚙️ Rendering Video...")
    p = folder()
    
    # Voiceover
    full_text = " ".join([s['audio'] for s in project_data])
    voice_path = os.path.join(p, "voice.mp3")
    asyncio.run(edge_tts.Communicate(full_text, "en-US-ChristopherNeural").save(voice_path))
    
    vc = AudioFileClip(voice_path)
    # Smart Calculation: Ensure video matches audio length perfectly
    clip_duration = vc.duration / len(project_data)
    
    clips = []
    target_size = (1080, 1920) if is_short else (1920, 1080)
    
    for scene in project_data:
        img = Image.open(scene['image_path']).convert('RGB')
        img = img.resize(target_size, Image.LANCZOS)
        
        clip = ImageClip(np.array(img)).set_duration(clip_duration)
        clip = zoom_in_effect(clip) # Apply Pro Zoom
        clips.append(clip)
        
    # Music Mix
    try:
        m_path = os.path.join(p, "music.mp3")
        if not os.path.exists(m_path):
            u = "https://ia800300.us.archive.org/17/items/TheSlenderManSong/Anxiety.mp3"
            r = requests.get(u, timeout=5)
            with open(m_path, "wb") as f: f.write(r.content)
            
        music = AudioFileClip(m_path)
        if music.duration < vc.duration: music = afx.audio_loop(music, duration=vc.duration)
        else: music = music.subclip(0, vc.duration)
        
        final_audio = CompositeAudioClip([vc, music.audio_fadeout(2).volumex(0.15)])
    except: final_audio = vc

    final = concatenate_videoclips(clips, method="compose").set_audio(final_audio)
    output_path = os.path.join(p, "PRO_MOVIE.mp4")
    final.write_videofile(output_path, fps=24, preset="ultrafast", codec="libx264")
    
    return output_path

# --- UI LAYOUT ---
st.title("💎 Dark Studio: Pro Edition")

with st.sidebar:
    st.header("⚙️ Studio Settings")
    
    # 1. FORMAT
    format_choice = st.radio("📺 Format:", ["📱 Shorts (9:16)", "🖥️ Video (16:9)"])
    is_short = "Short" in format_choice
    
    # 2. TOPIC
    topic = st.text_input("Topic:", "The Lost City of Atlantis")
    
    # 3. NEW: CUSTOM DURATION INPUT
    # You can type ANY number here now!
    duration = st.number_input("⏱️ Video Duration (Seconds):", min_value=10, max_value=300, value=60, step=1)
    
    # 4. SCENE COUNT
    scene_count = st.number_input("🎬 Scene Count:", min_value=3, max_value=20, value=6)
    
    if st.button("🚀 GENERATE PRO DRAFT", type="primary"):
        tps, words = calculate_pacing(duration, scene_count)
        data = run_pro_director(topic, scene_count, words, is_short)
        
        if data:
            final_data = generate_pro_images(data, is_short)
            st.session_state.project_data = final_data
            st.session_state.is_short = is_short
            st.success("Draft Created!")
            st.rerun()

# MAIN EDITOR
if "project_data" in st.session_state:
    st.header("🎞️ Director's Board")
    
    for i, scene in enumerate(st.session_state.project_data):
        with st.expander(f"Scene {i+1}", expanded=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                if os.path.exists(scene["image_path"]):
                    st.image(scene["image_path"])
                # Manual Replace Option
                up = st.file_uploader(f"Replace {i+1}", type=['jpg','png'], key=f"up_{i}")
                if up:
                    with open(scene["image_path"], "wb") as f: f.write(up.getbuffer())
                    st.rerun()
            with c2:
                st.info(f"🎨 **AI Prompt:** {scene['visual']}")
                new_text = st.text_area("🎙️ **Voiceover:**", value=scene['audio'], key=f"txt_{i}")
                st.session_state.project_data[i]['audio'] = new_text

    st.divider()
    if st.button("🔴 RENDER FINAL VIDEO", type="primary"):
        with st.spinner("Rendering High-Quality Video..."):
            vid_path = render_video(st.session_state.project_data, st.session_state.get("is_short", True))
            st.success("Render Complete!")
            st.video(vid_path)
            with open(vid_path, "rb") as f:
                st.download_button("📥 DOWNLOAD VIDEO", f, "Pro_Movie.mp4")
