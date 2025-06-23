#!/usr/bin/env python3
"""
Interactive Video Transcriber Runner

This script provides an easy way to run the video transcriber with different sources:
- Online videos (YouTube, Dell, etc.)
- Local video files
- Local audio files

Usage: python run_transcriber.py
"""

import os
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

# Import the main transcriber
from video_transcriber import VideoTranscriber

console = Console()

def show_welcome():
    """Display welcome message and options."""
    console.print(Panel.fit(
        "[bold blue]🎥 Video Transcription Validator[/bold blue]\n\n"
        "[yellow]This tool analyzes video transcriptions by:[/yellow]\n"
        "• Extracting captions from videos\n"
        "• Transcribing audio with AI (Whisper)\n"
        "• Comparing accuracy and timing\n"
        "• Generating detailed reports\n\n"
        "[green]Supports:[/green] YouTube, Dell, Vimeo, local files",
        title="Welcome",
        border_style="blue"
    ))

def get_video_source():
    """Get video source from user."""
    console.print("\n[bold cyan]Choose your video source:[/bold cyan]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Description", style="white")
    table.add_column("Example", style="yellow")
    
    table.add_row("1", "YouTube Video", "https://www.youtube.com/watch?v=VIDEO_ID")
    table.add_row("2", "Dell Support Video", "https://www.dell.com/support/...")
    table.add_row("3", "Other Online Video", "https://vimeo.com/VIDEO_ID")
    table.add_row("4", "Local Video File", "C:/path/to/video.mp4")
    table.add_row("5", "Local Audio File", "C:/path/to/audio.mp3")
    
    console.print(table)
    
    choice = Prompt.ask("\nSelect option", choices=["1", "2", "3", "4", "5"], default="1")
    
    if choice == "1":
        url = Prompt.ask("\n[cyan]Enter YouTube URL[/cyan]")
    elif choice == "2":
        url = Prompt.ask("\n[cyan]Enter Dell support video URL[/cyan]")
    elif choice == "3":
        url = Prompt.ask("\n[cyan]Enter video URL[/cyan]")
    elif choice == "4":
        url = get_local_file("video")
    else:  # choice == "5"
        url = get_local_file("audio")
    
    return url

def get_local_file(file_type):
    """Get local file path from user."""
    console.print(f"\n[cyan]Enter path to your local {file_type} file:[/cyan]")
    
    if file_type == "video":
        extensions = "(.mp4, .avi, .mov, .mkv, .webm, etc.)"
    else:
        extensions = "(.mp3, .wav, .m4a, .aac, .ogg, .flac, etc.)"
    
    console.print(f"[yellow]Supported formats: {extensions}[/yellow]")
    
    while True:
        file_path = Prompt.ask("File path")
        
        if os.path.exists(file_path):
            return file_path
        else:
            console.print(f"[red]File not found: {file_path}[/red]")
            if not Confirm.ask("Try again?", default=True):
                sys.exit(1)

def get_processing_options():
    """Get processing options from user."""
    console.print("\n[bold cyan]Processing Options:[/bold cyan]")
    
    force_whisper = Confirm.ask(
        "Force Whisper transcription? (Skip caption extraction)", 
        default=False
    )
    
    # Language options
    console.print("\n[bold cyan]Language Options:[/bold cyan]")
    
    # Caption languages
    use_custom_languages = Confirm.ask(
        "Specify custom languages for caption extraction?", 
        default=False
    )
    
    target_languages = None
    if use_custom_languages:
        console.print("[yellow]Enter language codes separated by commas (e.g., en,es,fr,de)[/yellow]")
        console.print("[yellow]Common codes: en(English), es(Spanish), fr(French), de(German), it(Italian), pt(Portuguese), ru(Russian), ja(Japanese), ko(Korean), zh(Chinese), ar(Arabic), hi(Hindi)[/yellow]")
        lang_input = Prompt.ask("Language codes", default="en,es,fr,de")
        target_languages = [lang.strip() for lang in lang_input.split(",")]
    
    # Whisper language
    whisper_language = None
    if force_whisper or Confirm.ask("Specify language for Whisper transcription?", default=False):
        console.print("\n[yellow]Whisper Language Options:[/yellow]")
        console.print("• Leave empty for automatic detection")
        console.print("• Common codes: en, es, fr, de, it, pt, ru, ja, ko, zh, ar, hi")
        whisper_lang_input = Prompt.ask("Whisper language code (or press Enter for auto-detect)", default="")
        whisper_language = whisper_lang_input if whisper_lang_input else None
    
    return force_whisper, target_languages, whisper_language

def main():
    """Main function."""
    show_welcome()
    
    try:
        # Get video source
        url = get_video_source()
        
        # Get processing options
        force_whisper, target_languages, whisper_language = get_processing_options()
        
        # Show processing info
        console.print(f"\n[green]Processing:[/green] {url}")
        console.print(f"[green]Force Whisper:[/green] {force_whisper}")
        if target_languages:
            console.print(f"[green]Caption Languages:[/green] {', '.join(target_languages)}")
        if whisper_language:
            console.print(f"[green]Whisper Language:[/green] {whisper_language}")
        else:
            console.print(f"[green]Whisper Language:[/green] Auto-detect")
        
        if not Confirm.ask("\nProceed with transcription?", default=True):
            console.print("[yellow]Cancelled by user[/yellow]")
            return
        
        # Initialize transcriber and process
        transcriber = VideoTranscriber()
        
        console.print("\n" + "="*60)
        results = transcriber.process_video(
            url, 
            force_whisper=force_whisper,
            target_languages=target_languages,
            whisper_language=whisper_language
        )
        
        if results:
            transcriber.save_mismatches(results)
            console.print(f"\n[bold green]✅ Successfully processed {len(results)} segments![/bold green]")
            
            # Show language info if available
            if hasattr(transcriber, 'transcription_language'):
                console.print(f"[cyan]Transcription language: {transcriber.transcription_language}[/cyan]")
            if hasattr(transcriber, 'all_manual_captions') and transcriber.all_manual_captions:
                console.print(f"[cyan]Available manual caption languages: {', '.join(transcriber.all_manual_captions.keys())}[/cyan]")
            if hasattr(transcriber, 'all_auto_captions') and transcriber.all_auto_captions:
                console.print(f"[cyan]Available auto caption languages: {', '.join(transcriber.all_auto_captions.keys())}[/cyan]")
                
        else:
            console.print("\n[bold red]❌ No results generated[/bold red]")
            console.print(Panel.fit(
                "[yellow]Troubleshooting Tips:[/yellow]\n\n"
                "• Try a different video URL\n"
                "• Download the video manually and use local file\n"
                "• Check if the video is publicly accessible\n"
                "• Try with force_whisper=True option\n"
                "• Try different language settings",
                title="Help",
                border_style="yellow"
            ))
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {str(e)}[/red]")
        console.print("\n[yellow]Try using a local file if online download failed[/yellow]")
    finally:
        # Cleanup
        import shutil
        if hasattr(transcriber, 'temp_dir') and os.path.exists(transcriber.temp_dir):
            shutil.rmtree(transcriber.temp_dir)

if __name__ == "__main__":
    main() 