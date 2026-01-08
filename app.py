import streamlit as st
import google.generativeai as genai
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

st.set_page_config(page_title="Dark Studio: Final", layout="wide", page_icon="🎬")

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

# --- 2. DIRECTOR (GEMINI) ---
def run_director(api_key, topic, n_scenes, total_words, is_short):
    format_type = "Vertical (9:16) for YouTube Shorts" if is_short else "Wide (16:9) for YouTube Video"
    
    st.info(f"🧠 Gemini is writing script for {format_type}...")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = (f"Act as a documentary director. Write a script about '{topic}'. "
                  f"Strictly format it as a list of exactly {n_scenes} items. "
                  f"Total word count should be approx {total_words} words. "
                  f"The video format is {format_type}, so describe visual composition accordingly. "
                  f"Format each line as: VISUAL PROMPT | VOICEOVER TEXT")
        
        response = model.generate_content(prompt)
        
        script_data = []
        for line in response.text.split('\n'):
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

# --- 3. SCOUT (DUCKDUCKGO) ---
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
            results = list(ddgs.images(keywords, max_results=2))
            if results:
                r = requests.get(results[0]['image'], timeout=3)
                if r.status_code == 200:
                    with open(filepath, "wb") as f: f.write(r.content)
                    found = True
        except: pass
        
        if not found:
            img = Image.new('RGB', (1080, 1920) if is_short else (1920, 1080), color=(20, 20, 30))
            img.save(filepath)
            
        script_data[i]["image_path"] = filepath
        my_bar.progress((i+1)/len(script_data))
        
    return script_data

# --- 4. RENDER ENGINE (EFFECTS) ---
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
    
    # 1. Generate Voiceover
    full_text = " ".join([s['audio'] for s in project_data])
    voice_path = os.path.join(p, "voice.mp3")
    asyncio.run(edge_tts.Communicate(full_text, "en-US-ChristopherNeural").save(voice_path))
    
    # 2. Build Video Clips
    vc = AudioFileClip(voice_path)
    # Calculate exact duration per scene based on audio length
    # This is smarter than fixed timing: it ensures video matches voice length
    clip_duration = vc.duration / len(project_data)
    
    clips = []
    target_size = (1080, 1920) if is_short else (1920, 1080)
    
    for scene in project_data:
        # Load & Resize Image Smartly
        img = Image.open(scene['image_path']).convert('RGB')
        img = img.resize(target_size, Image.LANCZOS)
        
        # Create Clip
        clip = ImageClip(np.array(img)).set_duration(clip_duration)
        
        # APPLY KEN BURNS ZOOM
        clip = zoom_in_effect(clip, zoom_ratio=0.04)
        clips.append(clip)
        
    # 3. Add Music (Cinematic Background)
    st.write("🎵 Mixing Audio...")
    try:
        m_path = os.path.join(p, "music.mp3")
        # Download dark cinematic music
        if not os.path.exists(m_path):
            u = "https://ia800300.us.archive.org/17/items/TheSlenderManSong/Anxiety.mp3"
            r = requests.get(u, timeout=5)
            with open(m_path, "wb") as f: f.write(r.content)
            
        music = AudioFileClip(m_path)
        # Loop music to fit video
        if music.duration < vc.duration:
            music = afx.audio_loop(music, duration=vc.duration)
        else:
            music = music.subclip(0, vc.duration)
            
        # Fade out music at the end
        music = music.audio_fadeout(2)
        # Mix Voice (100%) and Music (15%)
        final_audio = CompositeAudioClip([vc, music.volumex(0.15)])
    except:
        final_audio = vc

    # 4. Final Export
    st.write("🎬 Exporting Final MP4...")
    final = concatenate_videoclips(clips, method="compose").set_audio(final_audio)
    output_path = os.path.join(p, "FINAL_MOVIE.mp4")
    
    # Ultrafast preset for cloud performance
    final.write_videofile(output_path, fps=24, preset="ultrafast", codec="libx264")
    
    return output_path

# --- UI LAYOUT ---
st.title("🎬 Dark Studio: Production")

with st.sidebar:
    st.header("⚙️ Settings")
    google_key = st.text_input("Google API Key:", type="password")
    st.divider()
    format_choice = st.radio("📺 Format:", ["📱 YouTube Short (9:16)", "🖥️ YouTube Video (16:9)"])
    is_short = True if "Short" in format_choice else False
    topic = st.text_input("Topic:", "The Lost City of Atlantis")
    duration = st.slider("Duration (s):", 15, 90, 30, step=15)
    scene_count = st.number_input("Scenes:", min_value=3, max_value=12, value=5)
    
    tps, words = calculate_pacing(duration, scene_count)
    st.caption(f"Stats: ~{tps:.1f} sec/scene | ~{words} words")
    
    if st.button("🚀 GENERATE DRAFT", type="primary"):
        if len(google_key) < 5: st.error("Need API Key!")
        else:
            data = run_director(google_key, topic, scene_count, words, is_short)
            if data:
                final_data = find_placeholder_images(data, is_short)
                st.session_state.project_data = final_data
                st.session_state.is_short = is_short
                st.success("Draft Created!")
                st.rerun()

# MAIN EDITOR
if "project_data" in st.session_state:
    st.header("🎞️ Storyboard Editor")
    fmt = "Vertical" if st.session_state.get("is_short", True) else "Horizontal"
    st.info(f"Format: {fmt}. Edit prompt or upload images below.")
    
    for i, scene in enumerate(st.session_state.project_data):
        with st.expander(f"🎬 Scene {i+1}: {scene['visual'][:40]}...", expanded=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                if os.path.exists(scene["image_path"]):
                    st.image(scene["image_path"], use_container_width=True)
                up = st.file_uploader(f"Replace Image {i+1}", type=['jpg','png'], key=f"up_{i}")
                if up:
                    with open(scene["image_path"], "wb") as f: f.write(up.getbuffer())
                    st.rerun()
            with c2:
                st.code(scene['visual'])
                # Helper Link
                q_type = "Vertical Wallpaper" if st.session_state.get("is_short", True) else "Wide Wallpaper"
                link = f"https://www.google.com/search?q={urllib.parse.quote(scene['visual'] + ' ' + q_type)}&tbm=isch"
                st.markdown(f"[🔎 Search Google Images for Replacement]({link})")
                
                # Update script logic
                new_text = st.text_area("Voiceover:", value=scene['audio'], key=f"txt_{i}")
                st.session_state.project_data[i]['audio'] = new_text

    st.divider()
    st.header("🏁 Final Production")
    if st.button("🔴 RENDER FINAL VIDEO", type="primary"):
        with st.spinner("Rendering Video... (This takes about 30 seconds)"):
            vid_path = render_video(st.session_state.project_data, st.session_state.get("is_short", True))
            st.success("Render Complete!")
            st.video(vid_path)
            with open(vid_path, "rb") as f:
                st.download_button("📥 DOWNLOAD MOVIE", f, "DarkStudio_Movie.mp4")
