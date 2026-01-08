import streamlit as st
import os
import requests
import time
import asyncio
import edge_tts
import urllib.parse
import re
import numpy as np
from PIL import Image
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeAudioClip, afx
import shutil

# CONFIG
st.set_page_config(page_title="Dark Studio Mobile", layout="centered", page_icon="🎬")

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if not os.path.exists(st.session_state.project_path): os.makedirs(st.session_state.project_path)

# SESSION STATE (MEMORY)
if "stolen_prompt" not in st.session_state: st.session_state.stolen_prompt = ""
if "stolen_voice" not in st.session_state: st.session_state.stolen_voice = "en-US-GuyNeural"
if "music_vibe" not in st.session_state: st.session_state.music_vibe = "horror"

def folder(): return st.session_state.project_path

# --- FUNCTIONS ---

def steal_style(url):
    st.info(f"🕵️ Hacking metadata from: {url}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        html = requests.get(url, headers=headers).text
        
        # Regex to find hidden data
        title = re.search(r'<title>(.*?) - YouTube</title>', html)
        desc = re.search(r'<meta name="description" content="(.*?)">', html)
        
        if title and desc:
            name = title.group(1)
            description = desc.group(1)[:300]
            
            # Save to Memory
            st.session_state.stolen_prompt = f"in the style of '{name}', {description}. Mimic their visual style."
            st.success(f"✅ HACKED: {name}")
            
            # Auto-Detect Vibe
            desc_lower = description.lower()
            if any(x in desc_lower for x in ['tech', 'review', 'future']):
                st.session_state.music_vibe = "tech"
                st.session_state.stolen_voice = "en-US-ChristopherNeural"
            elif any(x in desc_lower for x in ['history', 'documentary']):
                st.session_state.music_vibe = "history"
                st.session_state.stolen_voice = "en-GB-RyanNeural"
            elif any(x in desc_lower for x in ['horror', 'scary', 'dark']):
                st.session_state.music_vibe = "horror"
                st.session_state.stolen_voice = "en-US-GuyNeural"
            else:
                st.session_state.music_vibe = "bright"
                st.session_state.stolen_voice = "en-US-AriaNeural"
                
            st.write(f"**Detected Vibe:** {st.session_state.music_vibe.upper()}")
            st.write(f"**Voice Selected:** {st.session_state.stolen_voice}")
        else:
            st.error("Could not read channel data. Is the link correct?")
    except Exception as e:
        st.error(f"Hack Failed: {e}")

def get_images(topic):
    style = st.session_state.stolen_prompt if st.session_state.stolen_prompt else "cinematic, 8k, mysterious"
    st.write(f"🎨 Generating Scenes ({style[:50]}...)...")
    
    seed = int(time.time())
    try:
        u = f"https://text.pollinations.ai/{urllib.parse.quote(f'List 10 distinct visual scenes for {topic}. Style: {style}. Seed: {seed}. Format: - Description')}"
        scenes = [l for l in requests.get(u).text.split('\n') if l.strip().startswith("-")][:10]
        if len(scenes)<3: scenes = [f"{topic} scene {i}" for i in range(10)]
    except: scenes = [f"{topic} scene {i}" for i in range(10)]
    
    bar = st.progress(0)
    for i, s in enumerate(scenes):
        clean = re.sub(r'^- ', '', s)
        prompt = urllib.parse.quote(f"{clean}, {style}, 8k, highly detailed")
        u2 = f"https://image.pollinations.ai/prompt/{prompt}?width=1080&height=1920&nologo=true"
        
        for attempt in range(2):
            try:
                content = requests.get(u2, timeout=10).content
                if len(content) > 1000:
                    with open(os.path.join(folder(), f"{i+1:03}.jpg"), "wb") as f: f.write(content)
                    break
            except: time.sleep(1)
        bar.progress((i + 1) / len(scenes))
    st.success(f"✅ Generated {len(scenes)} Images!")

def get_script_and_audio(topic):
    st.write("📝 Ghostwriting Script...")
    style = st.session_state.stolen_prompt if st.session_state.stolen_prompt else "dark and mysterious"
    prompt = f"Write a 100 word engaging script about '{topic}'. {style}."
    
    try:
        txt = requests.get(f"https://text.pollinations.ai/{urllib.parse.quote(prompt)}").text
    except: txt = f"This is a video about {topic}."
    
    st.info(f"Script: {txt[:100]}...")
    
    st.write("🎙️ Recording Voice...")
    async def _save():
        c = edge_tts.Communicate(txt, st.session_state.stolen_voice)
        await c.save(os.path.join(folder(), "voice.mp3"))
    asyncio.run(_save())
    st.success("✅ Audio Ready!")

def render_video():
    st.write("🎬 Rendering Video...")
    p = folder()
    
    try:
        # 1. LOAD VOICE
        if not os.path.exists(os.path.join(p, "voice.mp3")): 
            st.error("No Audio found! Generate Audio first.")
            return
        vc = AudioFileClip(os.path.join(p, "voice.mp3"))
        
        # 2. SAFE MUSIC DOWNLOAD (Fixes the crash!)
        urls = {
            "horror": "https://ia800300.us.archive.org/17/items/TheSlenderManSong/Anxiety.mp3",
            "tech": "https://ia902808.us.archive.org/24/items/Synthwave-2016/Home%20-%20Decay.mp3",
            "history": "https://ia800302.us.archive.org/24/items/BachCelloSuiteNo.1InGMinor/01-Bach_Cello_Suite_No.1_in_G_Major_Prelude.mp3",
            "bright": "https://ia800504.us.archive.org/11/items/UkuleleSong/UkuleleSong-320bit.mp3"
        }
        
        m_path = os.path.join(p, "music.mp3")
        target_url = urls.get(st.session_state.music_vibe, urls["horror"])
        
        # Only download if we don't have it, and check if it's valid
        try:
            r = requests.get(target_url, timeout=10)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(m_path, "wb") as f: f.write(r.content)
            else:
                st.warning("⚠️ Music download failed (bad file). Rendering without music.")
        except:
            st.warning("⚠️ Music download timed out. Rendering without music.")

        # 3. MIX AUDIO
        final_audio = vc
        if os.path.exists(m_path) and os.path.getsize(m_path) > 1000:
            try:
                mc = AudioFileClip(m_path)
                # Loop music to match voice
                if mc.duration < vc.duration: mc = afx.audio_loop(mc, duration=vc.duration)
                else: mc = mc.subclip(0, vc.duration)
                final_audio = CompositeAudioClip([vc, mc.volumex(0.15)])
            except:
                st.warning("⚠️ Music file was corrupt. Skipping music.")
        
        # 4. BUILD VIDEO
        files = sorted([os.path.join(p, f) for f in os.listdir(p) if f.endswith(".jpg")])
        if not files: 
            st.error("No images found!")
            return
            
        dur = vc.duration / len(files)
        clips = []
        for f in files:
            try: clips.append(ImageClip(np.array(Image.open(f).convert('RGB'))).resize(height=1920).crop(x1=0, y1=0, width=1080, height=1920).set_duration(dur))
            except: pass
            
        final = concatenate_videoclips(clips, method="compose").set_audio(final_audio)
        output_path = os.path.join(p, "FINAL_MOBILE.mp4")
        final.write_videofile(output_path, fps=24, preset="ultrafast")
        
        st.balloons()
        st.video(output_path)
        
        with open(output_path, "rb") as file:
            st.download_button("📥 DOWNLOAD VIDEO", file, "DarkStudio_Video.mp4", "video/mp4")
        
    except Exception as e:
        st.error(f"Render Error: {e}")

# --- UI LAYOUT ---
st.title("📱 Dark Studio Mobile")
st.caption("Running on Cloud Server")

# MODE SELECTION
mode = st.radio("Select Mode:", ["Manual Style", "YouTube Copycat (Hacker)"])

if mode == "YouTube Copycat (Hacker)":
    url = st.text_input("Paste Channel Link:")
    if st.button("Analyze Channel"):
        steal_style(url)
    if st.session_state.stolen_prompt:
        st.success(f"Active Style: {st.session_state.stolen_prompt[:40]}...")

else:
    # Manual Fallback
    style_opt = st.selectbox("Choose Style", ["Dark / Horror", "Tech / Future", "History / Vintage"])
    if "Horror" in style_opt: st.session_state.music_vibe = "horror"
    elif "Tech" in style_opt: st.session_state.music_vibe = "tech"
    else: st.session_state.music_vibe = "history"

topic = st.text_input("Video Topic", "The Mystery of the Ocean")

col1, col2 = st.columns(2)
if col1.button("1. Create Scenes"): get_images(topic)
if col2.button("2. Script & Audio"): get_script_and_audio(topic)

if st.button("3. RENDER VIDEO", type="primary"):
    render_video()
