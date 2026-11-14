#!/usr/bin/env python3
"""
Demo Video Generator for nexjobs.in (FindJobs)
Simple reliable scenes matching the website's forest green theme.
Uses fixed x-coordinates to avoid FFmpeg expression parsing issues.
"""

import os
import subprocess
import requests
import shutil

BASE_URL = "http://127.0.0.1:5000"
PROJECT_DIR = "/opt/sandbox/workspace/demo-video-saas"
RECORDINGS_DIR = os.path.join(PROJECT_DIR, "recordings")
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "output")

SESSION_ID = "nexjobs_real_demo"

# Colors matching the real website (forest green theme)
GREEN = "0x2d6a4f"
DARK_GREEN = "0x1b4332"
WHITE = "white"
GRAY = "0x6c757d"

# Scenes matching the actual website UI from the screenshot
SCENES = [
    {
        "duration": 6,
        "narration": "Welcome to FindJobs, also known as NexJobs. This is a live job search platform built for freshers, with no login required.",
        "bg": WHITE,
        "title": "FindJobs",
        "subtitle": "Live jobs. Real matches. Built for freshers.",
        "annotation": "FindJobs - nexjobs.in",
        "annotation_pos": "center",
        "annotation_color": "0xFFD700"
    },
    {
        "duration": 6,
        "narration": "The navigation bar gives you quick access to Home, Find Jobs, your Saved jobs, and your personal profile. There are currently one thousand seven hundred and eighty six jobs available.",
        "bg": DARK_GREEN,
        "title": "Navigation",
        "subtitle": "Home - Find Jobs - Saved - My Profile",
        "annotation": "Home | Find Jobs | Saved | My Profile",
        "annotation_pos": "top-left",
        "annotation_color": "0x00FF00"
    },
    {
        "duration": 6,
        "narration": "Use the powerful search bar to find jobs by title, skill, or company. You can also filter by location or choose remote positions. Just click Search live jobs to get started.",
        "bg": GREEN,
        "title": "Search Jobs",
        "subtitle": "Search by title, skill, company or location",
        "annotation": "Search live jobs easily",
        "annotation_pos": "bottom-left",
        "annotation_color": "0x00FFFF"
    },
    {
        "duration": 6,
        "narration": "FindJobs aggregates live openings from over five trusted sources including RemoteOK, Remotive, and Arbeitnow. Jobs are updated every hour so you always see fresh opportunities.",
        "bg": DARK_GREEN,
        "title": "Trusted Sources",
        "subtitle": "RemoteOK - Remotive - Arbeitnow - Stripe - Ramp",
        "annotation": "5+ Sources Updated Hourly",
        "annotation_pos": "top-right",
        "annotation_color": "0xFF69B4"
    },
    {
        "duration": 6,
        "narration": "Browse across seventeen different categories to find the perfect role. Whether you are looking for remote work or local positions, FindJobs has you covered.",
        "bg": GREEN,
        "title": "17 Categories",
        "subtitle": "Find your perfect role across 17 job categories",
        "annotation": "17 Job Categories",
        "annotation_pos": "bottom-right",
        "annotation_color": "0x90EE90"
    },
    {
        "duration": 6,
        "narration": "With one thousand seven hundred and eighty six live jobs and no login required, finding your dream job has never been easier. Visit NexJobs dot in and start your search today.",
        "bg": DARK_GREEN,
        "title": "Start Your Journey",
        "subtitle": "1786 live jobs - No login required",
        "annotation": "Visit nexjobs.in - 1786 Live Jobs",
        "annotation_pos": "center",
        "annotation_color": "0xFFD700"
    }
]


def create_scene_video(scene, index):
    """Create a scene with background color, title, and subtitle text using filter_complex."""
    output_path = os.path.join(RECORDINGS_DIR, f"nexjobs_scene_{index}.mp4")
    duration = scene["duration"]
    bg = scene["bg"]
    title = scene["title"].replace(":", "").replace("'", "").replace("(", "").replace(")", "")
    subtitle = scene["subtitle"].replace(":", "").replace("'", "").replace("(", "").replace(")", "")

    # Replace spaces and commas with underscores to avoid filter parsing issues
    # (commas are FFmpeg filter separators)
    title_clean = title.replace(" ", "_").replace(",", "_")
    subtitle_clean = subtitle.replace(" ", "_").replace(",", "_")

    # Use filter_complex with proper input/output labeling
    filter_str = (
        f"[0:v]drawtext=text={title_clean}:x=500:y=280:fontsize=64:fontcolor=white:font=DejaVu-Sans[v1];"
        f"[v1]drawtext=text={subtitle_clean}:x=500:y=380:fontsize=28:fontcolor=0xcccccc:font=DejaVu-Sans[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={bg}:s=1280x720:d={duration}:rate=30",
        "-filter_complex", filter_str,
        "-map", "[out]",
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  Scene {index} FFmpeg stderr: {result.stderr[-200:]}")
        return None
    return output_path


def generate_voice(narration, index):
    """Generate voice narration using gTTS via the app's API."""
    output_path = os.path.join(ASSETS_DIR, f"nexjobs_voice_{index}.wav")
    try:
        r = requests.post(f"{BASE_URL}/api/tts/generate", json={
            "text": narration,
            "session_id": SESSION_ID,
            "language": "en"
        }, timeout=60)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "ok":
                src = data["audio_path"]
                if os.path.exists(src):
                    shutil.copy2(src, output_path)
                    return output_path
    except Exception as e:
        print(f"  Voice generation failed for scene {index}: {e}")
    return None


def merge_video_audio(video_path, audio_path, output_path):
    """Merge video with audio using FFmpeg."""
    if audio_path and os.path.exists(audio_path):
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-pix_fmt", "yuv420p",
            output_path
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-an",
            "-pix_fmt", "yuv420p",
            output_path
        ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def concat_videos(video_paths, output_path):
    """Concatenate multiple videos using FFmpeg concat demuxer."""
    list_file = os.path.join(RECORDINGS_DIR, "concat_list.txt")
    with open(list_file, "w") as f:
        for v in video_paths:
            f.write(f"file '{v}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", list_file,
        "-c", "copy",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def add_final_annotations(video_path, output_path, annotations):
    """Add timed text annotations to the final video."""
    prev = "0:v"
    filters = []
    for i, ann in enumerate(annotations):
        out = f"ann_{i}"
        pos_map = {
            "center": (540, 650),
            "top-left": (40, 100),
            "top-right": (1060, 100),
            "bottom-left": (40, 620),
            "bottom-right": (1060, 620),
        }
        x, y = pos_map.get(ann["position"], (40, 620))
        text = ann["text"].replace(":", "\\:").replace("'", "'\\''").replace("|", "PIPE")
        color = ann["color"]
        font_size = ann.get("font_size", 32)
        start = ann["start_time"]
        end = ann["end_time"]

        filter_str = (
            f"[{prev}]drawtext=text='{text}':x={x}:y={y}:"
            f"fontsize={font_size}:fontcolor={color}:"
            f"font=DejaVu-Sans:box=1:boxcolor=0x00000080:boxborderw=12:"
            f"enable='between(t,{start},{end})'[{out}]"
        )
        filters.append(filter_str)
        prev = out

    if filters:
        filter_complex = ";".join(filters)
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-filter_complex", filter_complex,
            "-map", f"[{prev}]",
            "-map", "0:a",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-c", "copy",
            output_path
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stderr


def main():
    print("=" * 60)
    print("  Demo Video Generator - nexjobs.in (FindJobs)")
    print("  Matching actual website UI")
    print("=" * 60)
    print()

    # Step 1: Create scene videos matching the real website
    print("Step 1: Creating scenes matching nexjobs.in UI...")
    scene_videos = []
    for i, scene in enumerate(SCENES):
        print(f"  Creating scene {i+1}/{len(SCENES)}: {scene['title']}")
        path = create_scene_video(scene, i)
        scene_videos.append(path)
        if path and os.path.exists(path):
            print(f"    -> {os.path.getsize(path)} bytes")
        else:
            print(f"    -> FAILED")

    # Step 2: Generate voice narration
    print("\nStep 2: Generating voice narration...")
    voice_files = []
    for i, scene in enumerate(SCENES):
        print(f"  Generating voice for scene {i+1}/{len(SCENES)}")
        path = generate_voice(scene["narration"], i)
        voice_files.append(path)
        if path and os.path.exists(path):
            print(f"    -> {os.path.getsize(path)} bytes")

    # Step 3: Merge scenes with voice
    print("\nStep 3: Merging scenes with voice...")
    merged_videos = []
    for i, (scene, video, voice) in enumerate(zip(SCENES, scene_videos, voice_files)):
        output = os.path.join(RECORDINGS_DIR, f"nexjobs_merged_{i}.mp4")
        if not video or not os.path.exists(video):
            print(f"  Scene {i+1} no video - skipping")
            continue
        success, err = merge_video_audio(video, voice, output)
        if success and os.path.exists(output):
            merged_videos.append(output)
            print(f"  Scene {i+1} merged ({os.path.getsize(output)} bytes)")
        elif os.path.exists(video):
            merged_videos.append(video)
            print(f"  Scene {i+1} no audio ({os.path.getsize(video)} bytes)")
        else:
            print(f"  Scene {i+1} FAILED")

    if not merged_videos:
        print("  No merged videos created!")
        return None

    # Step 4: Concatenate all scenes
    print("\nStep 4: Concatenating scenes...")
    concat_path = os.path.join(RECORDINGS_DIR, "nexjobs_concat.mp4")
    success, err = concat_videos(merged_videos, concat_path)
    if success and os.path.exists(concat_path):
        print(f"  Concatenated ({os.path.getsize(concat_path)} bytes)")
    else:
        print(f"  Concat error: {err[-300:]}")
        return None

    # Step 5: Add timed annotations
    print("\nStep 5: Adding timed annotations...")
    annotations = [
        {"text": "FindJobs - nexjobs.in", "start_time": 0, "end_time": 6, "position": "center", "color": "0xFFD700", "font_size": 36},
        {"text": "Home | Find Jobs | Saved | My Profile", "start_time": 6, "end_time": 12, "position": "top-left", "color": "0x00FF00", "font_size": 28},
        {"text": "Search by title, skill, or location", "start_time": 12, "end_time": 18, "position": "bottom-left", "color": "0x00FFFF", "font_size": 28},
        {"text": "5+ Sources Updated Hourly", "start_time": 18, "end_time": 24, "position": "top-right", "color": "0xFF69B4", "font_size": 28},
        {"text": "17 Job Categories", "start_time": 24, "end_time": 30, "position": "bottom-right", "color": "0x90EE90", "font_size": 28},
        {"text": "Visit nexjobs.in - 1786 Live Jobs", "start_time": 30, "end_time": 36, "position": "center", "color": "0xFFD700", "font_size": 36},
    ]
    final_path = os.path.join(OUTPUT_DIR, "nexjobs_demo_video.mp4")
    success, err = add_final_annotations(concat_path, final_path, annotations)
    if success and os.path.exists(final_path):
        print(f"  Annotations added ({os.path.getsize(final_path)} bytes)")
    else:
        print(f"  Annotation error: {err[-300:]}")
        shutil.copy2(concat_path, final_path)
        print(f"  -> Using video without annotations")

    print()
    print("=" * 60)
    print(f"  Demo video created!")
    print(f"  {final_path}")
    print(f"  Size: {os.path.getsize(final_path) / 1024 / 1024:.2f} MB")
    print("=" * 60)

    return final_path


if __name__ == "__main__":
    main()
