# 🌍 Universal Video Transcription Validator

A powerful Python tool that validates video transcriptions by comparing original captions with AI-generated transcriptions. **Works with ANY video format and source** - from YouTube to direct video URLs to local files.

## ✨ Universal Video Support

This tool works like a **browser** and can handle:

### 📹 **Any Video Format**
- **Video files**: `.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`, `.flv`, `.wmv`, `.m4v`, `.3gp`, `.ogv`, `.ts`, `.mts`, `.m2ts`, `.vob`, `.asf`, `.rm`, `.rmvb`, `.divx`, `.xvid`, `.f4v`, `.mpg`, `.mpeg`, `.m2v`
- **Audio files**: `.mp3`, `.wav`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.wma`, `.opus`, `.aiff`, `.au`, `.ra`, `.amr`, `.ac3`, `.dts`, `.ape`, `.mka`
- **Streaming formats**: `.m3u8`, `.mpd`, `.ism`, `.f4m`

### 🌐 **Any Video Source**
- **Platform videos**: YouTube, Vimeo, Dailymotion, Twitch, Dell Support, etc.
- **Direct video URLs**: `https://example.com/video.mp4`
- **Streaming URLs**: HLS (`.m3u8`), DASH (`.mpd`), etc.
- **Local files**: Any video/audio file on your computer
- **Browser downloads**: Simulates multiple browsers for access

### 🗣️ **100+ Languages**
- **Caption extraction**: English, Spanish, French, German, Italian, Portuguese, Russian, Japanese, Korean, Chinese, Arabic, Hindi, and many more
- **AI transcription**: 100+ languages with automatic detection via OpenAI Whisper
- **Multi-language processing**: Extract captions in multiple languages simultaneously

## 🚀 Quick Start

### Installation
```bash
# Clone the repository
git clone <repository-url>
cd video_transcribe

# Install dependencies
pip install -r requirements.txt
```

### Basic Usage

#### 1. **Browser Helper (Recommended for any video format)**
```bash
python browser_helper.py
```
- Interactive interface for any video source
- Browser simulation with multiple user agents
- Direct download support for video URLs
- Universal format detection

#### 2. **Interactive Runner**
```bash
python run_transcriber.py
```
- Step-by-step guidance
- Language selection options
- Local file browser

#### 3. **Direct Script Usage**
```python
from video_transcriber import VideoTranscriber

transcriber = VideoTranscriber()

# Works with ANY of these:
url = "https://example.com/video.mp4"  # Direct video URL
url = "https://www.youtube.com/watch?v=VIDEO_ID"  # Platform video
url = "https://example.com/stream.m3u8"  # Streaming URL
url = "C:/path/to/video.mp4"  # Local video file
url = "C:/path/to/audio.mp3"  # Local audio file

# Process with auto-detection
results = transcriber.process_video(url)

# Process with specific options
results = transcriber.process_video(
    url,
    force_whisper=True,  # Force AI transcription
    target_languages=["en", "es", "fr"],  # Multiple caption languages
    whisper_language="en"  # Specific transcription language
)
```

## 🛠️ Advanced Features

### Browser-Like Download Methods
The tool uses **7 different download configurations** that simulate various browsers and devices:

1. **Desktop Browser** (Chrome/Windows) - Standard approach
2. **Mobile Browser** (Safari/iOS) - Mobile-optimized
3. **TV/Embedded Client** - Often bypasses restrictions
4. **Age-Gate Bypass** - For age-restricted content
5. **Alternative Formats** - Different quality priorities
6. **Generic Extractor** - Universal fallback
7. **Direct URL** - For simple video files

### Multi-Language Processing
```python
# Extract captions in multiple languages
results = transcriber.process_video(
    url,
    target_languages=["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh", "ar", "hi"]
)

# Force specific transcription language
results = transcriber.process_video(
    url,
    whisper_language="es"  # Spanish transcription
)

# Auto-detect language
results = transcriber.process_video(
    url,
    whisper_language=None  # Auto-detection
)
```

### Local File Processing
```python
# Video files
transcriber.process_video("C:/videos/my_video.mp4")

# Audio files  
transcriber.process_video("C:/audio/my_audio.mp3")

# Any format supported by FFmpeg
transcriber.process_video("C:/media/presentation.avi")
```

### Direct Video URLs
```python
# Direct video file URLs (most reliable)
transcriber.process_video("https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4")

# Streaming URLs
transcriber.process_video("https://example.com/live/stream.m3u8")

# Any direct media URL
transcriber.process_video("https://cdn.example.com/videos/demo.webm")
```

## 📊 Output Formats

The tool generates comprehensive reports in multiple formats:

### JSON Report (`results.json`)
```json
{
  "video_info": {
    "url": "video_url",
    "title": "Video Title",
    "duration": "00:15:30",
    "language": "en",
    "format": "mp4"
  },
  "mismatches": [
    {
      "timestamp": "00:01:23",
      "original": "Hello world",
      "transcription": "Hello word",
      "similarity": 0.85,
      "error_type": "substitution"
    }
  ],
  "summary": {
    "total_segments": 150,
    "mismatches": 12,
    "accuracy": 92.0,
    "languages_found": ["en", "es"]
  }
}
```

### Excel Report (`results.xlsx`)
- **Summary Sheet**: Overall statistics and language information
- **Detailed Mismatches**: Timestamp, original text, transcription, similarity scores
- **Error Analysis**: Types of errors (insertions, deletions, substitutions)
- **Language Breakdown**: Per-language accuracy if multiple languages detected

## 🔧 Troubleshooting

### When Downloads Fail

#### 1. **Use Browser Helper**
```bash
python browser_helper.py
```
- Advanced browser simulation
- Multiple user agents
- Cookie support
- Direct download capabilities

#### 2. **Try Direct Video URLs**
Instead of platform URLs, use direct video file links:
```python
# Instead of: https://www.youtube.com/watch?v=VIDEO_ID
# Try: https://example.com/video.mp4
```

#### 3. **Download Manually**
1. Download the video using your browser or download tools
2. Save it locally
3. Process the local file:
```python
transcriber.process_video("C:/Downloads/my_video.mp4")
```

#### 4. **Use Different Platforms**
- Dell support videos (usually accessible)
- Vimeo (often less restricted)
- Educational sites
- Direct video hosting services

### Common Error Solutions

| Error | Solution |
|-------|----------|
| "Sign in to confirm you're not a bot" | Use `browser_helper.py` or download manually |
| "HTTP Error 403: Forbidden" | Try direct video URLs or different platforms |
| "Video unavailable" | Check if video is public, try different source |
| Import errors | Run `pip install -r requirements.txt` |
| FFmpeg not found | Install FFmpeg system-wide |

## 🌟 Key Features

- ✅ **Universal Format Support**: Any video/audio format
- ✅ **Browser Simulation**: Multiple user agents and download methods
- ✅ **Multi-Language**: 100+ languages with auto-detection
- ✅ **Local File Support**: Process any local media file
- ✅ **Direct URLs**: Handle direct video file links
- ✅ **Streaming Support**: HLS, DASH, and other streaming formats
- ✅ **Robust Fallbacks**: 7 different download methods
- ✅ **Comprehensive Reports**: JSON and Excel output
- ✅ **Interactive Tools**: Browser helper and guided runner
- ✅ **Error Analysis**: Detailed mismatch categorization

## 📋 Requirements

- Python 3.8+
- FFmpeg (for audio processing)
- Internet connection (for online videos)
- ~2GB RAM (for Whisper model)

## 🎯 Use Cases

- **Content Creators**: Validate YouTube video captions
- **Educators**: Check educational video transcriptions
- **Accessibility**: Ensure accurate captions for accessibility
- **Quality Assurance**: Validate auto-generated captions
- **Multi-language Content**: Process videos in multiple languages
- **Local Media**: Process personal video/audio collections
- **Research**: Analyze transcription accuracy across languages

## 🔄 Workflow

1. **Input**: Any video source (URL, local file, streaming link)
2. **Detection**: Automatic format and language detection
3. **Download**: Browser-like download with multiple fallback methods
4. **Caption Extraction**: Extract existing captions in multiple languages
5. **AI Transcription**: Generate transcription using Whisper AI
6. **Comparison**: Compare captions with transcription using sliding window
7. **Analysis**: Calculate accuracy and categorize errors
8. **Output**: Generate comprehensive reports in JSON and Excel

---

**💡 Pro Tip**: Start with `browser_helper.py` for the best experience with any video format. It provides an interactive interface and handles the most complex video sources automatically! 