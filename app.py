import streamlit as st
import os
import asyncio
import edge_tts
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import AudioFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip
import numpy as np
import traceback
import re
import textwrap

# --- 1. SETUP ---
st.set_page_config(page_title="Dark Studio: Editor", layout="wide", page_icon="✂️")

# FOLDER SETUP
if "project_path" not in st.session_state:
    st.session_state.project_path = "/tmp/My_Dark_Project"
    if os.path.exists(st.session_state.project_path):
        import shutil
        shutil.rmtree(st.session_state.project_path) 
    os.makedirs(st.session_state.project_path)

def folder(): return st.session_state.project_path

# --- 2. CAPTION ENGINE (Burn-in Text) ---
def add_captions_to_image(img_path, text, is_short):
    """Draws professional subtitles at the bottom of the image."""
    try:
        img = Image.open(img_path).convert('RGB')
        width, height = img.size
        draw = ImageDraw.Draw(img)

        # Config
        font_size = int(height * 0.05) # 5% of screen height
        # Try to use a standard bold font, fallback to default
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except:
            font = ImageFont.load_default()

        # Wrap text
        char_width = 25 if is_short else 50
        lines = textwrap.wrap(text, width=char_width)

        # Box Dimensions
        text_h = len(lines) * (font_size * 1.2)
        box_h = text_h + (font_size) # Padding
        box_y = height - box_h - (height * 0.1) # 10% from bottom

        # Draw Semi-Transparent Background Box
        # We process this by creating a separate overlay
        overlay = Image.new('RGBA', img.size, (0,0,0,0))
        draw_overlay = ImageDraw.Draw(overlay)
        
        # Left/Right margins
        margin = width * 0.05
        draw_overlay.rectangle(
            [(margin, box_y), (width - margin, box_y + box_h)],
            fill=(0, 0, 0, 160) # Black with 160/255 opacity
        )
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        
        # Draw Text
        draw = ImageDraw.Draw(img)
        text_y = box_y + (font_size * 0.2)
        for line in lines:
            # Center text
            # bbox = draw.textbbox((0, 0), line, font=font)
            # w = bbox[2] - bbox[0]
            # x = (width - w) / 2
            
            # Simple centering calc for default font
            w = len(line) * (font_size * 0.5) 
            x = (width - w) / 2
            
            # Draw Shadow
            draw.text((x+2, text_y+2), line, font=font, fill=(0,0,0))
            # Draw White Text
            draw.text((x, text_y), line, font=font, fill=(255,255,255))
            text_y += (font_size * 1.2)
            
        img.save(img_path)
        return img_path
    except Exception as e:
        print(f"Caption Error: {e}")
        return img_path # Return original if caption fails

# --- 3. SCRIPT PARSER ---
def parse_script(raw_text):
    # Split by new lines for manual control
    lines = [l.strip() for l in raw_text.split('\n') if len(l.strip()) > 1]
    return [{"text": l, "image": None} for l in lines]

# --- 4. RENDERER ---
def render_project(scenes, is_short):
    p = folder()
    status = st.empty()
    prog = st.progress(0)
    
    try:
        clips = []
        target_size = (720, 1280) if is_short else (1280, 720)
        
        for i, scene in enumerate(scenes):
            status.info(f"⚙️ Processing Scene {i+1}/{len(scenes)}...")
            
            # 1. Generate Voice (Per Scene for perfect sync)
            voice_file = os.path.join(p, f"voice_{i}.mp3")
            asyncio.run(edge_tts.Communicate(scene['text'], "en-US-ChristopherNeural").save(voice_file))
            
            audio_clip = AudioFileClip(voice_file)
            duration = audio_clip.duration + 0.5 # Add small pause
            
            # 2. Process Image (Resize + Caption)
            img_path = scene['image']
            if not img_path: 
                # Create Black Placeholder if user forgot to upload
                img_path = os.path.join(p, f"black_{i}.jpg")
                Image.new('RGB', target_size, (0,0,0)).save(img_path)
                
            # Resize
            with Image.open(img_path) as pil_img:
                pil_img = pil_img.convert('RGB')
                pil_img = pil_img.resize(target_size, Image.LANCZOS)
                pil_img.save(img_path)
            
            # Add Caption
            final_img_path = add_captions_to_image(img_path, scene['text'], is_short)
            
            # 3. Create Clip
            video_clip = ImageClip(final_img_path).set_duration(duration)
            video_clip = video_clip.set_audio(audio_clip)
            
            # 4. Crossfade Transition (Professional Touch)
            if i > 0:
                video_clip = video_clip.crossfadein(0.5)
                
            clips.append(video_clip)
            prog.progress((i+1)/len(scenes))
            
        # Stitch
        status.info("🎬 Final Stitching...")
        final_video = concatenate_videoclips(clips, method="compose", padding=-0.5) # Negative padding overlaps transitions
        
        output_path = os.path.join(p, "FINAL_CUT.mp4")
        final_video.write_videofile(output_path, fps=24, preset="ultrafast", codec="libx264", audio_codec="aac")
        
        status.success("✅ Video Complete!")
        return output_path
        
    except Exception as e:
        st.error(f"Render Error: {e}")
        st.code(traceback.format_exc())
        return None

# --- UI ---
st.title("✂️ Dark Studio: Editor's Cut")

# SESSION STATE INIT
if "editor_scenes" not in st.session_state:
    st.session_state.editor_scenes = []

with st.sidebar:
    st.header("Project Settings")
    format_choice = st.radio("Format:", ["📱 Shorts (9:16)", "🖥️ Video (16:9)"])
    is_short = "Short" in format_choice

# STEP 1: SCRIPT INPUT
if not st.session_state.editor_scenes:
    st.subheader("Step 1: The Script")
    st.info("Paste your script line-by-line. Each line will correspond to ONE image.")
    raw_script = st.text_area("Script:", height=200, placeholder="The ocean is deep.\nIt is full of mystery.\nDivers explore the unknown.")
    
    if st.button("🚀 START EDITING", type="primary"):
        if len(raw_script) > 5:
            st.session_state.editor_scenes = parse_script(raw_script)
            st.session_state.is_short = is_short
            st.rerun()

# STEP 2: ASSET MANAGER
else:
    st.subheader("Step 2: Asset Manager")
    
    if st.button("⬅️ Restart Project"):
        st.session_state.editor_scenes = []
        st.rerun()
    
    # Loop through scenes
    for i, scene in enumerate(st.session_state.editor_scenes):
        with st.expander(f"Scene {i+1}: \"{scene['text'][:50]}...\"", expanded=True):
            c1, c2 = st.columns([2, 1])
            
            with c1:
                st.markdown(f"**Subtitle:** {scene['text']}")
                
            with c2:
                # File Uploader for this specific scene
                uploaded_file = st.file_uploader(f"Image for Scene {i+1}", type=['jpg', 'png', 'jpeg'], key=f"up_{i}")
                
                if uploaded_file:
                    # Save uploaded file
                    ext = uploaded_file.name.split('.')[-1]
                    save_path = os.path.join(folder(), f"user_upload_{i}.{ext}")
                    with open(save_path, "wb") as f: f.write(uploaded_file.getbuffer())
                    
                    # Update session state
                    st.session_state.editor_scenes[i]['image'] = save_path
                    st.success("✅ Loaded")
                
                elif scene['image']:
                    st.info("✅ Image Loaded")

    st.divider()
    
    # RENDER
    if st.button("🔴 RENDER VIDEO WITH CAPTIONS", type="primary"):
        # Check if all images exist
        missing = [i+1 for i, s in enumerate(st.session_state.editor_scenes) if not s['image']]
        
        if missing:
            st.warning(f"⚠️ You haven't uploaded images for scenes: {missing}. Black screens will be used.")
            
        vid_path = render_project(st.session_state.editor_scenes, st.session_state.get("is_short", True))
        
        if vid_path:
            st.video(vid_path)
            with open(vid_path, "rb") as f:
                st.download_button("📥 DOWNLOAD VIDEO", f, "My_Edit.mp4")
