#!/usr/bin/env python3
"""
Example: Using Video Transcriber with Local Files

This example shows how to use the video transcriber when online downloads fail.
Simply update the file paths below to point to your local video or audio files.
"""

from video_transcriber import VideoTranscriber
from rich.console import Console

console = Console()

def main():
    # Initialize the transcriber
    transcriber = VideoTranscriber()
    
    # Example 1: Local video file
    # Replace this path with your actual video file
    video_file = "path/to/your/video.mp4"  # Update this path
    
    # Example 2: Local audio file  
    # Replace this path with your actual audio file
    audio_file = "path/to/your/audio.mp3"  # Update this path
    
    # Choose which file to process (uncomment one)
    # file_to_process = video_file
    # file_to_process = audio_file
    
    # For demonstration, we'll use the existing sample audio file if it exists
    import os
    sample_audio = "Update PowerEdge Drivers Using a Dell Update Package (DUP).m4a"
    
    if os.path.exists(sample_audio):
        file_to_process = sample_audio
        console.print(f"[green]Using sample file: {sample_audio}[/green]")
    else:
        console.print("[yellow]No sample file found. Please update the file paths in this script.[/yellow]")
        console.print("[yellow]Update 'video_file' or 'audio_file' variables with your local file paths.[/yellow]")
        return
    
    try:
        console.print(f"[cyan]Processing local file: {file_to_process}[/cyan]")
        
        # Process the file (force_whisper=True since we're using local files)
        results = transcriber.process_video(file_to_process, force_whisper=True)
        
        if results:
            # Save results
            transcriber.save_mismatches(results, "local_file_results.json")
            console.print(f"[bold green]✅ Successfully processed {len(results)} segments![/bold green]")
            console.print("[green]Results saved to 'local_file_results.json' and Excel file[/green]")
        else:
            console.print("[red]❌ No results generated[/red]")
            
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        console.print("[yellow]Make sure the file path is correct and the file format is supported[/yellow]")
    
    finally:
        # Cleanup
        import shutil
        if hasattr(transcriber, 'temp_dir') and os.path.exists(transcriber.temp_dir):
            shutil.rmtree(transcriber.temp_dir)

if __name__ == "__main__":
    main() 