import os
import json
import time
import subprocess
import requests
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
REPO_NAME = os.environ.get("GITHUB_REPOSITORY")

prompt = """
Create a viral 30-second Hindi fact or motivational story for YouTube Shorts and Instagram Reels.
Return ONLY a valid JSON object in this exact format (no markdown, no backticks):
{
  "title": "Catchy Hindi title under 50 chars #shorts #facts",
  "voiceover": "Pure Hindi script of 55 to 65 words. Do NOT use emojis, hashtags, or English symbols here.",
  "caption": "Engaging Hindi caption with 5 trending hashtags",
  "image_prompts": [
    "cinematic vertical scene 1 description in english, realistic 8k",
    "cinematic vertical scene 2 description in english, realistic 8k",
    "cinematic vertical scene 3 description in english, realistic 8k",
    "cinematic vertical scene 4 description in english, realistic 8k"
  ]
}
"""

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
response = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
raw_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
clean_json = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
data = json.loads(clean_json)

with open("script.txt", "w", encoding="utf-8") as f:
    f.write(data["voiceover"])

subprocess.run([
    "edge-tts",
    "--voice", "hi-IN-MadhurNeural",
    "--rate=+5%",
    "--file", "script.txt",
    "--write-media", "voice.mp3"
], check=True)

image_files = []
for i, img_prompt in enumerate(data["image_prompts"]):
    encoded_prompt = requests.utils.quote(img_prompt)
    seed = int(time.time()) + i
    img_url = f"[https://image.pollinations.ai/prompt/](https://image.pollinations.ai/prompt/){encoded_prompt}?width=1080&height=1920&nologo=true&seed={seed}"
    for _ in range(3):
        r = requests.get(img_url, timeout=60)
        if r.status_code == 200:
            filename = f"scene_{i}.jpg"
            with open(filename, "wb") as f:
                f.write(r.content)
            image_files.append(filename)
            break
        time.sleep(3)

audio = AudioFileClip("voice.mp3")
clip_duration = audio.duration / len(image_files)

clips = [ImageClip(img).set_duration(clip_duration) for img in image_files]
final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
final_video.write_videofile("latest_reel.mp4", fps=24, codec="libx264", audio_codec="aac")

video_public_url = f"[https://raw.githubusercontent.com/](https://raw.githubusercontent.com/){REPO_NAME}/main/latest_reel.mp4?t={int(time.time())}"
payload = {
    "title": data["title"],
    "caption": data["caption"],
    "video_url": video_public_url
}
with open("post_data.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)
