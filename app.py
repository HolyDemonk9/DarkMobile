import streamlit as st
import os
import requests
import urllib.parse
import random
from duckduckgo_search import DDGS
from PIL import Image, ImageFilter
import shutil
import asyncio
import edge_tts
import numpy as np
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeAudioClip, afx

# COMPATIBILITY
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS

st.set_page_config(page_title="Dark Studio: Diverse", layout="wide", page_icon="🎨")

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
    total_words = int(duration * 2.5)
    return time_per_scene, total_words

# --- 2. DIRECTOR (FIXED VARIETY) ---
def run_director(topic, n_scenes, total_words, is_short):
    format_type = "Vertical (9:16)" if is_short else "Wide (16:9)"
    st.info(f"🧠 AI is writing {n_scenes} unique scenes...")
    
    try:
        ddgs = DDGS()
        prompt = (f"Write a documentary script about '{topic}'. "
                  f"List exactly {n_scenes} items. "
                  f"Format: VISUAL PROMPT | VOICEOVER TEXT. "
                  f"CRITICAL: Every VISUAL PROMPT must be completely different (e.g. Drone shot, Close up, Map view).")
        
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
        
        # Validation: Did we get enough scenes?
        if len(script_data) < 1: raise Exception("Empty AI response")
        return script_data[:n_scenes]

    except Exception as e:
        # --- THE FIX IS HERE ---
        # If AI fails, we use this "Smart Backup" that forces variety
        st.warning(f"AI Busy, using Smart Backup Director. ({e})")
        
        backup_angles = [
            f"Wide cinematic drone shot of {topic}, establishing shot",
            f"Extreme close up detail of {topic}, macro photography",
            f"Dark moody atmosphere of {topic}, fog and shadows",
            f"Historical diagram or map related to {topic}",
            f"Action shot of {topic} in motion, blur effect",
            f"Silhouette of {topic} against a sunset"
        ]
        
        backup_script = []
        for i in range(n_scenes):
            # Pick a unique angle for each scene using Modulo (%)
            angle = backup_angles[i % len(backup_angles)]
            backup_script.append({
                "visual": angle,
                "audio": f"Part {i+1} of the story reveals new secrets about {topic}."
            })
            
        return backup_script

# --- 3. SCOUT (VARIETY SEARCH) ---
def find_placeholder_images(script_data, is_short):
    st.write("⚡ Finding Diverse Images...")
    ddgs = DDGS()
    my_bar = st.progress(0)
    
    for i, scene in enumerate(script_data):
        filename = f"scene_{i+1}.jpg"
        filepath = os.path.join(folder(), filename)
        
        # We append a random seed to the search to ensure it doesn't get stuck
        orientation = "vertical portrait wallpaper" if is_short else "wide landscape wallpaper"
        keywords = f"cinematic art {scene['visual']} {orientation} 4k"
        
        found = False
        try:
            # Fetch 3 results, pick random one to ensure variety
            results = list(ddgs.images(keywords, max_results=3))
            if results:
                # Pick a random result from top 3
                best_img = random.choice(results)
                r = requests.get(best_img['image'], timeout=3)
                if r.status_code == 200:
                    with open(filepath, "wb") as f: f.write(r.content)
                    found = True
        except: pass
        
        if not found:
            img = Image.new('RGB', (1080, 1920) if is_short else (1920, 1080), color=(random.randint(20,50), 20, 30))
            img.save(filepath)
            
        script_data[i]["image_path"] = filepath
        my_bar.progress((i+1)/len(script_data))
        
    return script_data

# --- 4. RENDER ENGINE ---
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
    st.write("⚙️ Rendering...")
    p = folder()
    
    full_text = " ".join([s['audio'] for s in project_data])
    voice_path = os.path.join(p, "voice.mp3")
    asyncio.run(edge_tts.Communicate(full_text, "en-US-ChristopherNeural").save(voice_path))
    
    vc = AudioFileClip(voice_path)
    clip_duration = vc.duration / len(project_data)
    
    clips = []
    target_size = (1080, 1920) if is_short else (1920, 1080)
    
    for scene in project_data:
        img = Image.open(scene['image_path']).convert('RGB')
        img = img.resize(target_size, Image.LANCZOS)
        clip = ImageClip(np.array(img)).set_duration(clip_duration)
        clip = zoom_in_effect(clip, zoom_ratio=0.04)
        clips.append(clip)
        
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
    output_path = os.path.join(p, "FINAL_MOVIE.mp4")
    final.write_videofile(output_path, fps=24, preset="ultrafast", codec="libx264")
    return output_path

# --- UI ---
st.title("🔓 Dark Studio: Diverse Edition")

with st.sidebar:
    st.header("⚙️ Settings")
    format_choice = st.radio("📺 Format:", ["📱 YouTube Short", "🖥️ YouTube Video"])
    is_short = "Short" in format_choice
    topic = st.text_input("Topic:", "The Lost City of Atlantis")
    duration = st.slider("Duration (s):", 15, 90, 30, step=15)
    scene_count = st.number_input("Scenes:", 3, 12, 5)
    
    if st.button("🚀 GENERATE DRAFT", type="primary"):
        tps, words = calculate_pacing(duration, scene_count)
        data = run_director(topic, scene_count, words, is_short)
        if data:
            final_data = find_placeholder_images(data, is_short)
            st.session_state.project_data = final_data
            st.session_state.is_short = is_short
            st.rerun()

if "project_data" in st.session_state:
    st.header("🎞️ Storyboard Editor")
    for i, scene in enumerate(st.session_state.project_data):
        with st.expander(f"Scene {i+1}: {scene['visual'][:30]}...", expanded=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                if os.path.exists(scene["image_path"]):
                    st.image(scene["image_path"])
                up = st.file_uploader(f"Replace {i+1}", type=['jpg','png'], key=f"up_{i}")
                if up:
                    with open(scene["image_path"], "wb") as f: f.write(up.getbuffer())
                    st.rerun()
            with c2:
                st.info(scene['visual']) # Show the prompt so you know it changed!
                new_text = st.text_area("Voice:", value=scene['audio'], key=f"txt_{i}")
                st.session_state.project_data[i]['audio'] = new_text

    if st.button("🔴 RENDER FINAL VIDEO", type="primary"):
        with st.spinner("Rendering..."):
            vid_path = render_video(st.session_state.project_data, st.session_state.get("is_short", True))
            st.success("Done!")
            st.video(vid_path)
            with open(vid_path, "rb") as f:
                st.download_button("📥 DOWNLOAD", f, "Movie.mp4")
