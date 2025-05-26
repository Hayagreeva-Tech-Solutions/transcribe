import os
import json
from faster_whisper import WhisperModel
import yt_dlp
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TimeRemainingColumn,
    DownloadColumn,
    TransferSpeedColumn,
)
from rich.table import Table
from pydub import AudioSegment
import tempfile
import re
from typing import List, Dict, Tuple, Optional
from difflib import SequenceMatcher
import jiwer
import webvtt
from rich.panel import Panel
from rich import box
from rich.align import Align
import re
import webvtt
import tempfile
import requests
import pandas as pd

console = Console()

CHUNK_SIZE = 30  # seconds (longer chunk for better alignment)


def clean_text(text):
    """Clean and normalize text for comparison."""
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Handle special characters and symbols
    replacements = {
        "&": "and",  # Replace ampersand
        "Â": "",  # Remove special space character
        "…": "...",  # Replace ellipsis
        "–": "-",  # Replace en dash
        "—": "-",  # Replace em dash
        "″": "",  # Remove double prime
        "′": "",  # Remove prime
        "„": "",  # Remove low double quote
        "‟": "",  # Remove high double quote
        "‚": "",  # Remove low single quote
        "‛": "",  # Remove high single quote
        "«": "",  # Remove left double angle quote
        "»": "",  # Remove right double angle quote
        "‹": "",  # Remove left single angle quote
        "›": "",  # Remove right single angle quote
        ".": " dot ",  # Replace dot with spoken form
        "/": " slash ",  # Replace slash with spoken form
        "-": " dash ",  # Replace dash with spoken form
        "_": " underscore ",  # Replace underscore with spoken form
        "@": " at ",  # Replace at symbol with spoken form
        "#": " hash ",  # Replace hash with spoken form
        "+": " plus ",  # Replace plus with spoken form
        "=": " equals ",  # Replace equals with spoken form
        "?": " question mark ",  # Replace question mark with spoken form
        "!": " exclamation mark ",  # Replace exclamation mark with spoken form
        "'": "",  # Remove single quote
        '"': "",  # Remove double quote
        ",": "",  # Remove comma
    }

    # Apply replacements
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Handle URLs and domains
    text = re.sub(r"([a-z0-9]+)\.(com|org|net)", r"\1 dot \2", text)

    # Remove any remaining special characters except alphanumeric, spaces, and 'dot' (periods are already replaced)
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove common filler words
    filler_words = {
        "um",
        "uh",
        "ah",
        "er",
        "like",
        "you know",
        "i mean",
        "well",
        "so",
        "basically",
        "actually",
        "literally",
        "just",
        "kind of",
        "sort of",
        "you see",
    }
    words = text.split()
    words = [w for w in words if w not in filler_words]

    # Final cleanup
    text = " ".join(words).strip()

    return text


def _parse_timestamps(text):
    """Parse VTT/SRT captions to get complete caption blocks with timing."""
    import re
    import webvtt
    import tempfile
    import requests

    captions = []

    try:
        # Check if the text is already VTT content (starts with WEBVTT)
        if text.strip().startswith("WEBVTT"):
            # Direct VTT content
            vtt_filename = f"temp_caption_direct.vtt"
            with open(vtt_filename, "w", encoding="utf-8") as f:
                f.write(text)
            
            try:
                for caption in webvtt.read(vtt_filename):
                    captions.append(
                        {
                            "text": caption.text.strip(),
                            "start": caption.start_in_seconds,
                            "end": caption.end_in_seconds,
                        }
                    )
            finally:
                # Clean up the temporary file
                if os.path.exists(vtt_filename):
                    os.remove(vtt_filename)
        
        else:
            # Check if it's an m3u8 playlist with VTT URLs
            vtt_urls = []
            for line in text.splitlines():
                if line.startswith("http") and ".vtt" in line:
                    vtt_urls.append(line.strip())

            # Download and parse each VTT file
            for vtt_url in vtt_urls:
                try:
                    response = requests.get(vtt_url)
                    vtt_content = response.text

                    # Create a VTT file in current directory
                    vtt_filename = f"temp_caption_{len(captions)}.vtt"
                    with open(vtt_filename, "w", encoding="utf-8") as f:
                        f.write(vtt_content)
                    
                    try:
                        for caption in webvtt.read(vtt_filename):
                            captions.append(
                                {
                                    "text": caption.text.strip(),
                                    "start": caption.start_in_seconds,
                                    "end": caption.end_in_seconds,
                                }
                            )
                    finally:
                        # Clean up the temporary file
                        if os.path.exists(vtt_filename):
                            os.remove(vtt_filename)
                except Exception as e:
                    console.print(
                        f"[yellow]Warning: Could not parse VTT file {vtt_url}: {str(e)}[/yellow]"
                    )
                    continue

    except Exception as e:
        console.print(f"[yellow]Warning: Could not parse caption text: {str(e)}[/yellow]")

    return captions


class VideoTranscriber:
    def __init__(self):
        self.console = Console()
        self.model = None
        self.temp_dir = tempfile.mkdtemp()
        self.captions = []
        self.transcribed_words = []

    def load_model(self):
        self.console.print(
            "[blue]Note: Loading Whisper model as fallback for videos without captions.[/blue]"
        )
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            progress.add_task(description="Loading Whisper model...", total=None)
            self.model = WhisperModel("large-v3", device="auto", compute_type="auto")
        self.console.print("[green]✓ Whisper model loaded successfully[/green]")

    def extract_captions(self, url: str) -> Tuple[List[Dict], List[Dict]]:
        self.console.print("[yellow]Extracting captions...[/yellow]")
        
        # Multiple yt-dlp configurations to try
        ydl_configs = [
            # Configuration 1: Standard approach
            {
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en", "en-US", "en-GB"],
                "skip_download": True,
            },
            # Configuration 2: With user agent and more aggressive caption extraction
            {
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en", "en-US", "en-GB", "en-AU", "en-CA"],
                "skip_download": True,
                "http_headers": {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                },
            },
            # Configuration 3: Force auto-generated captions only
            {
                "writeautomaticsub": True,
                "subtitleslangs": ["en", "en-US", "en-GB"],
                "skip_download": True,
                "writesubtitles": False,  # Only auto-generated
                "http_headers": {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                },
            }
        ]
        
        manual_captions = []
        auto_captions = []
        
        for i, ydl_opts in enumerate(ydl_configs, 1):
            try:
                self.console.print(f"[blue]Trying caption extraction method {i}/{len(ydl_configs)}...[/blue]")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        # Extract manual subtitles
                        if "subtitles" in info and "en" in info["subtitles"]:
                            subtitle_url = info["subtitles"]["en"][0]["url"]
                            self.console.print("[green]✓ Found English manual captions[/green]")
                            response = requests.get(subtitle_url)
                            caption_text = response.text
                            manual_captions = _parse_timestamps(caption_text)
                            self.console.print(f"[bold blue]Extracted {len(manual_captions)} manual captions[/bold blue]")
                        
                        # Extract auto-generated subtitles (try multiple language variations)
                        auto_found = False
                        if "automatic_captions" in info:
                            for lang_code in ["en", "en-US", "en-GB", "en-AU", "en-CA"]:
                                if lang_code in info["automatic_captions"]:
                                    auto_subtitle_url = info["automatic_captions"][lang_code][0]["url"]
                                    self.console.print(f"[green]✓ Found English auto-generated captions ({lang_code})[/green]")
                                    response = requests.get(auto_subtitle_url)
                                    auto_caption_text = response.text
                                    auto_captions = _parse_timestamps(auto_caption_text)
                                    self.console.print(f"[bold blue]Extracted {len(auto_captions)} auto-generated captions[/bold blue]")
                                    auto_found = True
                                    break
                        
                        # If we found something, break out of the retry loop
                        if manual_captions or auto_captions:
                            break
                        
            except Exception as e:
                self.console.print(f"[yellow]Caption extraction method {i} failed: {str(e)}[/yellow]")
                continue
        
        if not manual_captions and not auto_captions:
            self.console.print("[yellow]No English captions found with any method[/yellow]")
                        
        return manual_captions, auto_captions

    def download_audio(self, url: str) -> str:
        self.console.print(f"[yellow]Downloading audio from: {url}[/yellow]")
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=True,
        )
        download_task = None

        def hook(d):
            nonlocal download_task
            if d["status"] == "downloading":
                if download_task is None:
                    total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                    download_task = progress.add_task("Downloading", total=total)
                progress.update(download_task, completed=d.get("downloaded_bytes", 0))
            elif d["status"] == "finished":
                if download_task is not None:
                    progress.update(download_task, completed=progress.tasks[0].total)

        # Multiple configurations to try in order of preference
        ydl_configs = [
            # Configuration 1: Standard approach with modern headers
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
                "outtmpl": os.path.join(self.temp_dir, "audio.%(ext)s"),
                "progress_hooks": [hook],
                "noprogress": True,
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
                "force_generic_extractor": False,
                "nooverwrites": True,
                "http_headers": {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                },
            },
            # Configuration 2: Different format and extractor args
            {
                "format": "bestaudio[ext=m4a]/bestaudio/best[height<=480]",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "128",
                    }
                ],
                "outtmpl": os.path.join(self.temp_dir, "audio.%(ext)s"),
                "progress_hooks": [hook],
                "noprogress": True,
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
                "force_generic_extractor": False,
                "nooverwrites": True,
                "http_headers": {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                },
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "web"],
                        "player_skip": ["configs", "webpage"],
                    }
                }
            },
            # Configuration 3: Lowest quality fallback
            {
                "format": "worst[ext=mp4]/worst",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "96",
                    }
                ],
                "outtmpl": os.path.join(self.temp_dir, "audio.%(ext)s"),
                "progress_hooks": [hook],
                "noprogress": True,
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
                "force_generic_extractor": False,
                "nooverwrites": True,
                "http_headers": {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36',
                },
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android"],
                    }
                }
            },
            # Configuration 4: iOS client fallback
            {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "128",
                    }
                ],
                "outtmpl": os.path.join(self.temp_dir, "audio.%(ext)s"),
                "progress_hooks": [hook],
                "noprogress": True,
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
                "force_generic_extractor": False,
                "nooverwrites": True,
                "http_headers": {
                    'User-Agent': 'com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)',
                },
                "extractor_args": {
                    "youtube": {
                        "player_client": ["ios"],
                    }
                }
            }
        ]

        last_error = None
        
        for i, ydl_opts in enumerate(ydl_configs, 1):
            try:
                self.console.print(f"[blue]Trying download method {i}/{len(ydl_configs)}...[/blue]")
                
                with progress:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                
                audio_path = os.path.join(self.temp_dir, "audio.mp3")
                if not os.path.exists(audio_path):
                    raise FileNotFoundError(f"Audio file not found at {audio_path}")
                
                self.console.print(
                    f"[green]✓ Audio downloaded successfully with method {i}[/green]"
                )
                return audio_path
                
            except Exception as e:
                last_error = e
                self.console.print(f"[yellow]Method {i} failed: {str(e)}[/yellow]")
                continue
        
        # If all methods failed
        if last_error:
            self.console.print(f"[red]All download methods failed. Last error: {str(last_error)}[/red]")
            raise last_error
        else:
            error_msg = "All download methods failed with unknown error"
            self.console.print(f"[red]{error_msg}[/red]")
            raise RuntimeError(error_msg)

    def transcribe_audio(self, audio_path: str) -> List[Dict]:
        from rich.progress import Progress, SpinnerColumn, TextColumn

        self.console.print(
            "[yellow]Transcribing audio with word timestamps...[/yellow]"
        )
        
        if not self.model:
            raise RuntimeError("Whisper model not loaded. Call load_model() first.")
            
        # Show spinner while Whisper is working
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            task = progress.add_task("Transcribing audio (Whisper)...", total=None)
            segments, _ = self.model.transcribe(
                audio_path, language="en", word_timestamps=True
            )
            segments = list(segments)  # This is the long-running part
            progress.update(task, completed=1)
        # Process segments without a progress bar
        words = []
        for segment in segments:
            if segment.words:
                for word in segment.words:
                    words.append(
                        {
                            "word": clean_text(word.word),
                            "start": word.start,
                            "end": word.end,
                        }
                    )
            else:
                words.append(
                    {
                        "word": clean_text(segment.text),
                        "start": segment.start,
                        "end": segment.end,
                    }
                )
        self.console.print(
            f"[green]✓ Transcribed {len(words)} words from audio[/green]"
        )
        return words

    def process_video(self, url: str, force_whisper: bool = False) -> List[Dict]:
        # Extract both manual and auto-generated captions (unless forcing Whisper)
        if not force_whisper:
            manual_captions, auto_captions = self.extract_captions(url)
        else:
            self.console.print("[blue]Forcing Whisper transcription (skipping caption extraction)[/blue]")
            manual_captions, auto_captions = [], []
        
        # Determine the approach based on available captions
        if manual_captions and auto_captions and not force_whisper:
            # Best case: Compare manual vs auto-generated captions
            self.console.print("[green]Found both manual and auto-generated captions - comparing them[/green]")
            reference_captions = manual_captions
            transcribed_captions = auto_captions
            comparison_type = "Manual vs Auto-Generated Captions"
            
        elif (manual_captions or auto_captions) and not force_whisper:
            # One type of caption available: Compare captions vs Whisper transcription
            available_captions = manual_captions if manual_captions else auto_captions
            caption_type = "manual" if manual_captions else "auto-generated"
            self.console.print(f"[yellow]Found only {caption_type} captions - will compare with Whisper transcription[/yellow]")
            
            # Load Whisper model and transcribe audio
            success = self._transcribe_with_whisper(url)
            if not success:
                self.console.print("[red]Failed to generate Whisper transcription. Using caption self-comparison.[/red]")
                reference_captions = available_captions
                transcribed_captions = available_captions
                comparison_type = f"{caption_type.title()} Captions Only (Whisper Failed)"
            else:
                reference_captions = available_captions
                # Convert Whisper word-level transcription to caption-like format
                transcribed_captions = self._words_to_captions(self.transcribed_words)
                comparison_type = f"{caption_type.title()} Captions vs Whisper Transcription"
            
        else:
            # No captions available or forced Whisper: Generate transcription only
            reason = "Forced Whisper mode" if force_whisper else "No captions found"
            self.console.print(f"[red]{reason} - generating Whisper transcription only[/red]")
            
            success = self._transcribe_with_whisper(url)
            if not success:
                self.console.print("[red]Failed to generate any transcription. Cannot proceed.[/red]")
                return []
            
            # Create captions from transcription for self-comparison (will show 100% accuracy)
            transcribed_captions = self._words_to_captions(self.transcribed_words)
            reference_captions = transcribed_captions
            comparison_type = "Whisper Transcription Only"
        
        self.console.print(f"[cyan]Comparison type: {comparison_type}[/cyan]")
        
        # Perform comparison analysis
        results = self._compare_captions(reference_captions, transcribed_captions, comparison_type)
        
        self.display_table(results)
        return results

    def _transcribe_with_whisper(self, url: str) -> bool:
        """Attempt to transcribe audio using Whisper. Returns True if successful."""
        try:
            if not self.model:
                self.load_model()
            
            # Download and transcribe audio
            audio_path = self.download_audio(url)
            try:
                self.transcribed_words = self.transcribe_audio(audio_path)
                return True
            finally:
                # Always delete the audio file
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                    self.console.print(f"[green]✓ Audio file deleted: {audio_path}[/green]")
                    
        except Exception as e:
            self.console.print(f"[red]Whisper transcription failed: {str(e)}[/red]")
            return False

    def _words_to_captions(self, words: List[Dict], chunk_duration: float = 5.0) -> List[Dict]:
        """Convert word-level transcription to caption chunks."""
        if not words:
            return []
        
        captions = []
        current_chunk = []
        chunk_start = words[0]["start"]
        
        for word in words:
            current_chunk.append(word["word"])
            
            # Create a new chunk if duration exceeded or at end
            if (word["end"] - chunk_start >= chunk_duration) or word == words[-1]:
                caption_text = " ".join(current_chunk).strip()
                if caption_text:  # Only add non-empty captions
                    captions.append({
                        "text": caption_text,
                        "start": chunk_start,
                        "end": word["end"]
                    })
                
                # Start new chunk
                if word != words[-1]:  # Not the last word
                    current_chunk = []
                    chunk_start = word["end"]
        
        return captions

    def _compare_captions(self, reference_captions: List[Dict], transcribed_captions: List[Dict], comparison_type: str) -> List[Dict]:
        """Compare two sets of captions and return analysis results."""
        # Create full transcribed text for comparison
        transcribed_full = " ".join([caption["text"] for caption in transcribed_captions])
        transcribed_full_norm = clean_text(transcribed_full)
        transcribed_full_words = transcribed_full_norm.split()

        results = []
        for caption in reference_captions:
            original_text = caption["text"]
            normalized_text = clean_text(original_text.lower())
            norm_words = normalized_text.split()
            n = len(norm_words)

            # Skip if no words to compare
            if n == 0:
                continue

            # Find best matching segment in transcribed captions
            best_accuracy = 0.0
            best_window = ""
            best_error = None
            best_match_caption = None
            
            # First try to find time-based match
            caption_start, caption_end = caption["start"], caption["end"]
            time_matched_captions = [
                tc for tc in transcribed_captions
                if (tc["start"] <= caption_end and tc["end"] >= caption_start)
            ]
            
            if time_matched_captions:
                # Use time-matched captions
                time_matched_text = " ".join([tc["text"] for tc in time_matched_captions])
                time_matched_norm = clean_text(time_matched_text)
                
                try:
                    error = jiwer.process_words(normalized_text, time_matched_norm)
                    total = error.hits + error.substitutions + error.deletions
                    accuracy = (error.hits / total) * 100 if total > 0 else 0.0
                    best_accuracy = accuracy
                    best_window = time_matched_norm
                    best_error = error
                    best_match_caption = time_matched_captions[0] if time_matched_captions else None
                except Exception:
                    pass
            
            # If time-based matching didn't work well, try sliding window
            if best_accuracy < 50 and len(transcribed_full_words) >= n:
                for i in range(len(transcribed_full_words) - n + 1):
                    window_words = transcribed_full_words[i : i + n]
                    window_text = " ".join(window_words)
                    try:
                        error = jiwer.process_words(normalized_text, window_text)
                        total = error.hits + error.substitutions + error.deletions
                        accuracy = (error.hits / total) * 100 if total > 0 else 0.0
                        if accuracy > best_accuracy:
                            best_accuracy = accuracy
                            best_window = window_text
                            best_error = error
                    except Exception:
                        continue

            # If still no good match, use the original text (for perfect self-comparison)
            if not best_window:
                best_window = normalized_text
                best_accuracy = 100.0
                best_error = jiwer.process_words(normalized_text, normalized_text)

            # Determine spoken timing (use matched caption timing if available)
            spoken_start = best_match_caption["start"] if best_match_caption else caption["start"]
            spoken_end = best_match_caption["end"] if best_match_caption else caption["end"]

            # Status classification
            if best_accuracy >= 95:
                status = "PERFECT"
            elif best_accuracy >= 90:
                status = "GOOD"
            elif best_accuracy >= 80:
                status = "FAIR"
            else:
                status = "POOR"

            results.append({
                "caption_start": caption["start"],
                "caption_end": caption["end"],
                "original": original_text,
                "normalized": normalized_text,
                "transcribed": best_window,
                "accuracy": best_accuracy,
                "spoken_start": spoken_start,
                "spoken_end": spoken_end,
                "offset": spoken_start - caption["start"],
                "status": status,
                "comparison_type": comparison_type,
                "errors": {
                    "substitutions": best_error.substitutions if best_error else 0,
                    "deletions": best_error.deletions if best_error else 0,
                    "insertions": best_error.insertions if best_error else 0,
                },
            })

        return results

    def display_table(self, results: List[Dict]):
        # Determine comparison type from first result
        comparison_type = results[0].get("comparison_type", "Caption Analysis") if results else "Caption Analysis"
        
        table = Table(title=f"Caption Analysis Report - {comparison_type}", show_lines=True)
        table.add_column("Caption Start", style="cyan", justify="right")
        table.add_column("Caption End", style="cyan", justify="right")
        table.add_column("Original Caption", style="yellow")
        table.add_column("Normalized Original", style="blue")
        table.add_column("Compared Text", style="magenta")
        table.add_column("Accuracy %", style="green", justify="right")
        table.add_column("Offset (s)", style="red", justify="right")
        table.add_column("Status", style="bold", justify="center")
        table.add_column("Errors", style="blue", justify="right")

        for row in results:
            # Determine color based on accuracy
            if row["accuracy"] >= 95:
                acc_color = "green"
            elif row["accuracy"] >= 90:
                acc_color = "yellow"
            else:
                acc_color = "red"

            # Format errors
            errors = row.get("errors", {})
            error_str = f"S:{errors.get('substitutions', 0)} D:{errors.get('deletions', 0)} I:{errors.get('insertions', 0)}"

            # Format offset
            offset_str = f"{row['offset']:.2f}" if row["offset"] is not None else "-"

            # Determine status color
            status_color = {
                "PERFECT": "green",
                "GOOD": "yellow",
                "FAIR": "orange",
                "POOR": "red",
            }.get(row["status"], "white")

            # Highlight mismatches in transcribed text
            transcribed = row["transcribed"]
            if row["accuracy"] < 90:  # Only highlight if accuracy is less than 90%
                transcribed = f"[red]{transcribed}[/red]"

            table.add_row(
                f"{row['caption_start']:.2f}",
                f"{row['caption_end']:.2f}",
                row["original"],  # Show original exactly as extracted
                f"[blue]{row['normalized']}[/blue]",  # Show normalized version in blue
                transcribed,  # Show transcribed with potential highlighting
                f"[{acc_color}]{row['accuracy']:.1f}[/{acc_color}]",
                offset_str,
                f"[{status_color}]{row['status']}[/{status_color}]",
                error_str,
            )
        self.console.print(table)

    def save_mismatches(self, results: List[Dict], output_file: str = "matching.json"):
        # Save as JSON
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        
        # Prepare data for Excel export
        excel_data = []
        for result in results:
            # Flatten the errors dict for easier Excel viewing
            errors = result.get("errors", {})
            row = {
                "Caption Start (s)": result["caption_start"],
                "Caption End (s)": result["caption_end"],
                "Caption Duration (s)": result["caption_end"] - result["caption_start"],
                "Original Caption": result["original"],
                "Normalized Original": result["normalized"],
                "Transcribed (Whisper)": result["transcribed"],
                "Accuracy (%)": round(result["accuracy"], 2),
                "Spoken Start (s)": result.get("spoken_start"),
                "Spoken End (s)": result.get("spoken_end"),
                "Time Offset (s)": round(result["offset"], 2) if result["offset"] is not None else None,
                "Status": result["status"],
                "Substitution Errors": errors.get("substitutions", 0),
                "Deletion Errors": errors.get("deletions", 0),
                "Insertion Errors": errors.get("insertions", 0),
                "Total Errors": errors.get("substitutions", 0) + errors.get("deletions", 0) + errors.get("insertions", 0)
            }
            excel_data.append(row)
        
        # Create DataFrame and save to Excel
        df = pd.DataFrame(excel_data)
        excel_filename = output_file.replace(".json", ".xlsx")
        
        try:
            # Save to Excel with formatting
            with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Transcription Analysis', index=False)
                
                # Get the workbook and worksheet for formatting
                workbook = writer.book
                worksheet = writer.sheets['Transcription Analysis']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            self.console.print()  # Add a blank line for spacing before
            self.console.print(
                f"[green]✓ Results saved to [bold yellow]{output_file}[/bold yellow][/green]"
            )
            self.console.print(
                f"[green]✓ Excel report saved to [bold yellow]{excel_filename}[/bold yellow][/green]"
            )
            self.console.print()  # Add a blank line for spacing after
            
        except ImportError:
            self.console.print(
                f"[yellow]Warning: openpyxl not available. Install with 'pip install openpyxl' for Excel export.[/yellow]"
            )
            self.console.print()
            self.console.print(
                f"[green]✓ Results saved to [bold yellow]{output_file}[/bold yellow][/green]"
            )
            self.console.print()
        except Exception as e:
            self.console.print(f"[red]Error saving Excel file: {str(e)}[/red]")
            self.console.print()
            self.console.print(
                f"[green]✓ Results saved to [bold yellow]{output_file}[/bold yellow][/green]"
            )
            self.console.print()


def main():
    transcriber = VideoTranscriber()
    
    # The script can handle any video URL with robust fallback:
    # - Dell support videos
    # - YouTube videos  
    # - Any platform supported by yt-dlp
    # - Videos with blocked downloads (tries multiple methods)
    # - Videos without captions (auto-generates with Whisper)
    
    # Example Dell video (generally more reliable):
    url = "https://www.dell.com/support/contents/en-in/videos/videoplayer/how-to-deploy-openmanage-enterprise-on-vmware/6364425976112"
    
    
    # Example YouTube video (may be blocked):
    # url = "https://www.youtube.com/watch?v=3M0eqJLLDl0"
    
    # Example other platforms (replace VIDEO_ID with actual ID):
    # url = "https://vimeo.com/VIDEO_ID"
    
    try:
        # Try normal processing first
        results = transcriber.process_video(url)
        
        # If no results and you want to force Whisper transcription:
        if not results:
            console.print("[yellow]Retrying with forced Whisper transcription...[/yellow]")
            results = transcriber.process_video(url, force_whisper=True)
        
        if results:
            transcriber.save_mismatches(results)
        else:
            console.print("[red]Could not process video with any method[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        console.print("[yellow]You can try with force_whisper=True for difficult videos[/yellow]")
    finally:
        import shutil
        shutil.rmtree(transcriber.temp_dir)


if __name__ == "__main__":
    main()
