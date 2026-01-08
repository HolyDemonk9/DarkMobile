import streamlit as st
import os
import requests
import random
import asyncio
import edge_tts
from PIL import Image
import shutil
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeAudioClip, afx
import numpy as np
import urllib.parse

# COMPATIBILITY
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS

st.set_page_config(page_title="Dark Studio: Safe Mode", layout="wide", page_icon="🛡️")

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if os.path.exists(st.session_state.project_path):
        shutil.rmtree(st.session_state.project_path) 
    os.makedirs(st.session_state.project_path)

def folder(): return st.session_state.project_path

# --- 1. LOGIC DIRECTOR ---
def run_logic_director(topic, n_scenes, is_short):
    st.info(f"🧠 Constructing Pro Script for '{topic}'...")
    
    visual_styles = [
        "Cinematic wide shot, establishing shot of {t}, golden hour lighting, 8k, hyper-realistic",
        "Macro close-up detail of {t}, intricate textures, depth of field, volumetric lighting, unreal engine 5",
        "Low angle dramatic shot of {t}, dark moody atmosphere, fog, silhouette, mysterious vibe",
        "Overhead drone view of {t}, symmetrical composition, high contrast, cinematic grading",
        "Action shot of {t} in motion, dynamic blur, particle effects, 4k resolution",
        "Abstract artistic representation of {t}, double exposure, dreamlike, surreal concept art"
    ]
    
    audio_intros = [
        "The story of {t} is one of the world's greatest mysteries.",
        "Few people truly understand the power and history of {t}.",
        "Hidden beneath the surface, {t} holds a secret that changes everything.",
    ]
    audio_middles = [
        "For centuries, experts have questioned its true origins.",
        "The evidence suggests something far darker is at play here.",
        "To understand the future, we must look at the hidden past.",
        "It is a phenomenon that defies all simple explanations.",
        "Every detail reveals a complex web of unanswered questions."
    ]
    audio_outros = [
        "This is why {t} remains an unforgettable legend.",
        "And that is the true secret hidden within the darkness.",
        "The legend of {t} is only just beginning."
    ]
    
    script_data = []
    
    for i in range(n_scenes):
        style_template = visual_styles[i % len(visual_styles)]
        visual_prompt = style_template.format(t=topic)
        
        if i == 0:
            audio_text = random.choice(audio_intros).format(t=topic)
        elif i == n_scenes - 1:
            audio_text = random.choice(audio_outros).format(t=topic)
        else:
            audio_text = random.choice(audio_middles).format(t=topic)
            
        script_data.append({
            "visual": visual_prompt,
            "audio": audio_text
        })
        
    return script_data

# --- 2. ARTIST ---
def generate_pro_images(script_data, is_short):
    st.write("🎨 Generating Professional Assets (Flux Engine)...")
    my_bar = st.progress(0)
    
    width, height = (1080, 1920) if is_short else (1920, 1080)
    
    for i, scene in enumerate(script_data):
        filename = f"scene_{i+1}.jpg"
        filepath = os.path.join(folder(), filename)
        
        safe_prompt = requests.utils.quote(scene['visual'])
        seed = random.randint(0, 99999)
        url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width={width}&height={height}&nologo=true&seed={seed}&model=flux"
        
        downloaded = False
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(filepath, "wb") as f: f.write(r.content)
                downloaded = True
        except: pass
        
        if not downloaded:
            img = Image.new('RGB', (width, height), color=(15, 15, 20))
            img.save(filepath)
            
        script_data[i]["image_path"] = filepath
        my_bar.progress((i+1)/len(script_data))
        
    return script_data

# --- 3. RENDERER (Safe vs Pro) ---
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

def render_video(project_data, is_short, safe_mode=False):
    st.write(f"⚙️ Rendering Video (Safe Mode: {safe_mode})...")
    p = folder()
    
    # 1. Voice
    full_text = " ".join([s['audio'] for s in project_data])
    voice_path = os.path.join(p, "voice.mp3")
    asyncio.run(edge_tts.Communicate(full_text, "en-US-ChristopherNeural").save(voice_path))
    
    vc = AudioFileClip(voice_path)
    clip_duration = vc.duration / len(project_data)
    
    # 2. Clips
    clips = []
    
    # In safe mode, we reduce resolution to ensure it finishes
    if safe_mode:
        target_size = (720, 1280) if is_short else (1280, 720)
    else:
        target_size = (1080, 1920) if is_short else (1920, 1080)
    
    for scene in project_data:
        try:
            img = Image.open(scene['image_path']).convert('RGB')
            img = img.resize(target_size, Image.LANCZOS)
            clip = ImageClip(np.array(img)).set_duration(clip_duration)
            
            # ONLY Apply heavy zoom if NOT in safe mode
            if not safe_mode:
                clip = zoom_in_effect(clip)
                
            clips.append(clip)
        except: pass
        
    # 3. Music
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
    
    # Write file
    final.write_videofile(output_path, fps=24, preset="ultrafast", codec="libx264")
    return output_path

# --- UI ---
st.title("💎 Dark Studio: Production")

with st.sidebar:
    st.header("Settings")
    format_choice = st.radio("Format:", ["📱 Shorts", "🖥️ Video"])
    is_short = "Short" in format_choice
    topic = st.text_input("Topic:", "The Deep Ocean")
    scenes = st.number_input("Scenes:", 3, 10, 5)
    
    if st.button("🚀 GENERATE DRAFT", type="primary"):
        data = run_logic_director(topic, scenes, is_short)
        final_data = generate_pro_images(data, is_short)
        st.session_state.project_data = final_data
        st.session_state.is_short = is_short
        st.rerun()

if "project_data" in st.session_state:
    st.header("Review & Edit")
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
                st.caption("Step 1: Copy Prompt")
                st.code(scene['visual'], language="text")
                st.caption("Step 2: Generate")
                st.markdown(f"[**👉 Open Gemini**](https://gemini.google.com/app)")
                
                new_text = st.text_area("Audio:", value=scene['audio'], key=f"txt_{i}")
                st.session_state.project_data[i]['audio'] = new_text

    st.divider()
    st.subheader("🏁 Final Production")
    
    col1, col2 = st.columns(2)
    
    # TWO BUTTONS FOR SAFETY
    with col1:
        if st.button("🟢 FAST RENDER (Safe Mode)", help="No Zoom, 720p. Use this if Pro crashes."):
            with st.spinner("Rendering Safe Video..."):
                try:
                    vid_path = render_video(st.session_state.project_data, st.session_state.get("is_short", True), safe_mode=True)
                    st.success("Success!")
                    st.video(vid_path)
                    with open(vid_path, "rb") as f:
                        st.download_button("📥 DOWNLOAD FAST", f, "Fast_Movie.mp4")
                except Exception as e:
                    st.error(f"Error: {e}")

    with col2:
        if st.button("🔴 PRO RENDER (High Quality)", help="Full HD + Zoom Effects. Might be slow."):
            with st.spinner("Rendering High Quality..."):
                try:
                    vid_path = render_video(st.session_state.project_data, st.session_state.get("is_short", True), safe_mode=False)
                    st.success("Success!")
                    st.video(vid_path)
                    with open(vid_path, "rb") as f:
                        st.download_button("📥 DOWNLOAD PRO", f, "Pro_Movie.mp4")
                except Exception as e:
                    st.error(f"Render Crashed: {e} (Try Fast Render instead)")
