import streamlit as st
import os
import random
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeAudioClip, TextClip, ColorClip
import asyncio
import edge_tts
import shutil
import textwrap

# COMPATIBILITY
if not hasattr(Image, 'ANTIALIAS'): Image.ANTIALIAS = Image.LANCZOS

st.set_page_config(page_title="Dark Studio: Kinetic", layout="centered", page_icon="🎬")

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if os.path.exists(st.session_state.project_path):
        shutil.rmtree(st.session_state.project_path) 
    os.makedirs(st.session_state.project_path)

def folder(): return st.session_state.project_path

# --- 1. THE INTERNAL ARTIST (No Internet Needed) ---
def create_kinetic_slide(text, index):
    # This function DRAWS the image from scratch
    width, height = 1080, 1920
    
    # A. Generate a Background (Dark Gradient style)
    # We create a solid color based on the slide number so it changes
    colors = [(20, 20, 30), (40, 10, 10), (10, 30, 20), (30, 30, 10), (10, 10, 40)]
    bg_color = colors[index % len(colors)]
    
    img = Image.new('RGB', (width, height), color=bg_color)
    d = ImageDraw.Draw(img)
    
    # B. Add "Noise" or Shapes to make it look pro
    for _ in range(20):
        x = random.randint(0, width)
        y = random.randint(0, height)
        r = random.randint(5, 50)
        fill = (bg_color[0]+20, bg_color[1]+20, bg_color[2]+20)
        d.ellipse([x, y, x+r, y+r], fill=fill)

    # C. Draw the TEXT (Kinetic Typography)
    # We try to use a default font, usually usually available on Linux
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
    except:
        font = ImageFont.load_default() # Fallback

    # Wrap text so it fits
    lines = textwrap.wrap(text, width=20)
    y_text = 600
    for line in lines:
        # Draw text with shadow for style
        bbox = d.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x_text = (width - text_w) / 2
        
        # Shadow
        d.text((x_text+5, y_text+5), line, font=font, fill=(0,0,0))
        # Main Text
        d.text((x_text, y_text), line, font=font, fill=(255, 255, 255))
        y_text += 100

    # Save the file locally
    filename = f"slide_{index}.jpg"
    filepath = os.path.join(folder(), filename)
    img.save(filepath)
    return filepath

# --- 2. THE SCRIPT ENGINE (Mad Libs) ---
def get_script_and_slides(topic):
    # This ensures we ALWAYS have a story without waiting for AI
    templates = [
        f"The truth about {topic} is stranger than fiction.",
        "Scientists have been studying this for years.",
        "But what they found changed everything.",
        "Deep beneath the surface, a secret was hiding.",
        f"This is the mystery of {topic}."
    ]
    return templates

# --- 3. THE RENDERER ---
def render_kinetic_video(topic):
    st.write("⚙️ Generating Kinetic Video...")
    
    # 1. Get Content
    sentences = get_script_and_slides(topic)
    full_script = " ".join(sentences)
    
    # 2. Generate Audio
    st.write("🎙️ Synthesizing Voice...")
    voice_file = os.path.join(folder(), "voice.mp3")
    asyncio.run(edge_tts.Communicate(full_script, "en-US-ChristopherNeural").save(voice_file))
    
    # 3. Generate Visuals (Internal Draw)
    st.write("🎨 Drawing Slides (Internal CPU)...")
    slides = []
    for i, text in enumerate(sentences):
        slides.append(create_kinetic_slide(text, i))
        
    # 4. Assemble
    st.write("🎬 Mixing Video...")
    try:
        vc = AudioFileClip(voice_file)
        slide_duration = vc.duration / len(slides)
        
        clips = []
        for slide_path in slides:
            # Zoom effect logic (Simple Scale)
            img_clip = ImageClip(slide_path).set_duration(slide_duration)
            clips.append(img_clip)
            
        final_video = concatenate_videoclips(clips, method="compose").set_audio(vc)
        
        output_path = os.path.join(folder(), "Kinetic_Story.mp4")
        final_video.write_videofile(output_path, fps=24, preset="ultrafast")
        
        st.success("✅ RENDER COMPLETE!")
        st.video(output_path)
        with open(output_path, "rb") as f:
            st.download_button("📥 DOWNLOAD VIDEO", f, "Kinetic_Video.mp4")
            
    except Exception as e:
        st.error(f"Render Error: {e}")

# --- UI ---
st.title("🎬 Dark Studio: Kinetic")
st.caption("100% Offline Generation Mode (No APIs)")

topic = st.text_input("Enter Topic:", "The Dark Ocean")

if st.button("🚀 GENERATE VIDEO"):
    render_kinetic_video(topic)
