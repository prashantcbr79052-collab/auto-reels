import os
import json
import time
import subprocess
import requests
from PIL import Image
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

raw_key = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_API_KEY = raw_key.splitlines()[0].strip() if raw_key else ""
REPO_NAME = os.environ.get("GITHUB_REPOSITORY", "")

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

data = None

# 1. Google Gemini से स्क्रिप्ट लेना (अलग-अलग मॉडल ट्राय करेगा)
for model in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        r = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30)
        res_json = r.json()
        if "candidates" in res_json:
            raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
            clean_json = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(clean_json)
            print(f"Success with {model}")
            break
        else:
            print(f"{model} response:", res_json)
    except Exception as e:
        print(f"{model} error:", e)

# 2. अगर API Key में कोई भी दिक्कत हो, तो 100% फ्री बैकअप AI से स्क्रिप्ट बनाना
if not data:
    print("Using free backup AI generator...")
    try:
        r = requests.post(
            "[https://text.pollinations.ai/](https://text.pollinations.ai/)",
            json={"messages": [{"role": "user", "content": prompt}], "jsonMode": True},
            timeout=30
        )
        clean_json = r.text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(clean_json)
    except Exception as e:
        print("Backup AI fallback:", e)
        data = {
            "title": "सफलता का सबसे बड़ा रहस्य! #shorts #motivation",
            "voiceover": "क्या आप जानते हैं कि दुनिया के नब्बे प्रतिशत सफल लोग रोज़ सुबह जल्दी उठकर अपने पूरे दिन का लक्ष्य लिखते हैं। जब आप अपने लक्ष्य को कागज़ पर लिख लेते हैं, तो आपका दिमाग उसे पूरा करने के लिए दोगुनी तेज़ी से काम करने लगता है। आज ही अपनी सबसे बड़ी मंज़िल को लिखें और पहला कदम बढ़ाएं।",
            "caption": "सफलता का सबसे बड़ा रहस्य! रोज़ अपने लक्ष्य लिखें और आगे बढ़ें। #motivation #hindifacts #success #reelsindia #shorts",
            "image_prompts": [
                "cinematic sunrise over mountains inspiring golden hour vertical 8k",
                "successful person writing goals in diary morning light vertical 8k",
                "glowing human brain neural network concentration concept vertical 8k",
                "man standing on mountain peak victorious dramatic sky vertical 8k"
            ]
        }

with open("script.txt", "w", encoding="utf-8") as f:
    f.write(data["voiceover"])

# 3. हिंदी वॉइसओवर (MP3) बनाना
subprocess.run([
    "edge-tts",
    "--voice", "hi-IN-MadhurNeural",
    "--rate=+5%",
    "--file", "script.txt",
    "--write-media", "voice.mp3"
], check=True)

# 4. 4 HD तस्वीरें डाउनलोड करना
image_files = []
headers = {"User-Agent": "Mozilla/5.0"}
for i, img_prompt in enumerate(data["image_prompts"]):
    filename = f"scene_{i}.jpg"
    encoded_prompt = requests.utils.quote(img_prompt)
    seed = int(time.time()) + i
    img_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1920&nologo=true&seed={seed}"
    downloaded = False
    for _ in range(3):
        try:
            r = requests.get(img_url, headers=headers, timeout=45)
            if r.status_code == 200 and len(r.content) > 1000:
                with open(filename, "wb") as f:
                    f.write(r.content)
                Image.open(filename).verify()
                downloaded = True
                break
        except Exception:
            time.sleep(2)
    if not downloaded:
        img = Image.new("RGB", (1080, 1920), color=(20, 30, 48))
        img.save(filename)
    image_files.append(filename)

# 5. आवाज़ और तस्वीरों को जोड़कर वीडियो बनाना
audio = AudioFileClip("voice.mp3")
clip_duration = audio.duration / len(image_files)

clips = [ImageClip(img).set_duration(clip_duration) for img in image_files]
final_video = concatenate_videoclips(clips, method="compose").set_audio(audio)
final_video.write_videofile("latest_reel.mp4", fps=24, codec="libx264", audio_codec="aac")

# 6. Make.com के लिए डेटा तैयार करना
video_public_url = f"https://raw.githubusercontent.com/{REPO_NAME}/main/latest_reel.mp4?t={int(time.time())}"
payload = {
    "title": data["title"],
    "caption": data["caption"],
    "video_url": video_public_url
}
with open("post_data.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False)
