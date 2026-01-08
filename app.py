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

st.set_page_config(page_title="Dark Studio: No-Key Edition", layout="wide", page_icon="🔓")

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

# --- 2. DIRECTOR (DUCKDUCKGO CHAT - NO KEY) ---
def run_director(topic, n_scenes, total_words, is_short):
    format_type = "Vertical (9:16) for YouTube Shorts" if is_short else "Wide (16:9) for YouTube Video"
    
    st.info(f"🧠 AI (DuckDuckGo) is writing script for {format_type}...")
    
    # We use the 'chat' function which is free and smart
    try:
        ddgs = DDGS()
        
        prompt = (f"Act as a documentary director. Write a script about '{topic}'. "
                  f"Strictly format it as a list of exactly {n_scenes} items. "
                  f"Total word count should be approx {total_words} words. "
                  f"The video format is {format_type}, so describe visual composition accordingly. "
                  f"Format each line EXACTLY as: VISUAL PROMPT | VOICEOVER TEXT")
        
        # We ask GPT-4o-mini (via DuckDuckGo)
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
        
        # FAILSAFE: If AI talks too much, take top N scenes
        return script_data[:n_scenes]

    except Exception as e:
        st.error(f"AI Director Error: {e}")
        # Emergency Backup (Mad Libs) if AI blocks us
        return [{
            "visual": f"Cinematic shot of {topic}", 
            "audio": f"This is the story of {topic}. It is a mystery that has puzzled us for years."
        }] * n_scenes

# --- 3. SCOUT (DUCKDUCKGO IMAGES - NO KEY) ---
def find_placeholder_images(script_data, is_short):
    st.write("⚡ Finding Draft Images...")
    ddgs = DDGS()
    my_bar = st.progress(0)
    
    for i, scene in enumerate(script_data):
        filename = f"scene_{i+1}.jpg"
        filepath = os.path.join(folder(), filename)
        
        if is_short:
            keywords = f"cinematic concept art {scene['visual']} vertical wallpaper 4k"
        else:
            keywords = f"cinematic concept art {scene['visual']} wide landscape wallpaper 4k"
        
        found = False
        try:
            # Fetch 2 results to be safe
            results = list(ddgs.images(keywords, max_results=2))
            if results:
                # Try first result
                r = requests.get(results[0]['image'], timeout=3)
                if r.status_code == 200:
                    with open(filepath, "wb") as f: f.write(r.content)
                    found = True
        except: pass
        
        if not found:
            # Create Blank Placeholder if search fails
            img = Image.new('RGB', (1080, 1920) if is_short else (1920, 1080), color=(20, 20, 30))
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
    st.write("⚙️ Starting Render Engine...")
    p = folder()
    
    # 1. Voiceover
    full_text = " ".join([s['audio'] for s in project_data])
    voice_path = os.path.join(p, "voice.mp3")
    asyncio.run(edge_tts.Communicate(full_text, "en-US-ChristopherNeural").save(voice_path))
    
    # 2. Build Clips
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
        
    # 3. Music
    st.write("🎵 Mixing Audio...")
    try:
        m_path = os.path.join(p, "music.mp3")
        if not os.path.exists(m_path):
            u = "https://ia800300.us.archive.org/17/items/TheSlenderManSong/Anxiety.mp3"
            r = requests.get(u, timeout=5)
            with open(m_path, "wb") as f: f.write(r.content)
            
        music = AudioFileClip(m_path)
        if music.duration < vc.duration:
            music = afx.audio_loop(music, duration=vc.duration)
        else:
            music = music.subclip(0, vc.duration)
        
        music = music.audio_fadeout(2)
        final_audio = CompositeAudioClip([vc, music.volumex(0.15)])
    except:
        final_audio = vc

    # 4. Export
    st.write("🎬 Exporting Final MP4...")
    final = concatenate_videoclips(clips, method="compose").set_audio(final_audio)
    output_path = os.path.join(p, "FINAL_MOVIE.mp4")
    final.write_videofile(output_path, fps=24, preset="ultrafast", codec="libx264")
    
    return output_path

# --- UI LAYOUT ---
st.title("🔓 Dark Studio: No-Key Edition")

with st.sidebar:
    st.header("⚙️ Settings")
    
    format_choice = st.radio("📺 Format:", ["📱 YouTube Short (9:16)", "🖥️ YouTube Video (16:9)"])
    is_short = True if "Short" in format_choice else False
    
    topic = st.text_input("Topic:", "The Lost City of Atlantis")
    duration = st.slider("Duration (s):", 15, 90, 30, step=15)
    scene_count = st.number_input("Scenes:", min_value=3, max_value=12, value=5)
    
    if st.button("🚀 GENERATE DRAFT", type="primary"):
        tps, words = calculate_pacing(duration, scene_count)
        # No API Key needed here!
        data = run_director(topic, scene_count, words, is_short)
        if data:
            final_data = find_placeholder_images(data, is_short)
            st.session_state.project_data = final_data
            st.session_state.is_short = is_short
            st.success("Draft Created!")
            st.rerun()

# MAIN EDITOR
if "project_data" in st.session_state:
    st.header("🎞️ Storyboard Editor")
    
    for i, scene in enumerate(st.session_state.project_data):
        with st.expander(f"🎬 Scene {i+1}", expanded=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                if os.path.exists(scene["image_path"]):
                    st.image(scene["image_path"], use_container_width=True)
                up = st.file_uploader(f"Replace Image {i+1}", type=['jpg','png'], key=f"up_{i}")
                if up:
                    with open(scene["image_path"], "wb") as f: f.write(up.getbuffer())
                    st.rerun()
            with c2:
                # Updated Google Link (Just for manual help)
                st.code(scene['visual'])
                q_type = "Vertical Wallpaper" if st.session_state.get("is_short", True) else "Wide Wallpaper"
                link = f"https://www.google.com/search?q={urllib.parse.quote(scene['visual'] + ' ' + q_type)}&tbm=isch"
                st.markdown(f"[🔎 Find Image on Google]({link})")
                
                new_text = st.text_area("Voiceover:", value=scene['audio'], key=f"txt_{i}")
                st.session_state.project_data[i]['audio'] = new_text

    st.divider()
    if st.button("🔴 RENDER FINAL VIDEO", type="primary"):
        with st.spinner("Rendering Video..."):
            vid_path = render_video(st.session_state.project_data, st.session_state.get("is_short", True))
            st.success("Done!")
            st.video(vid_path)
            with open(vid_path, "rb") as f:
                st.download_button("📥 DOWNLOAD MOVIE", f, "Movie.mp4")
