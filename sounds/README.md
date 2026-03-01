# Sound Files Directory

This directory contains ambient sound effects for the hospital voice AI system.

## Required Sound Files:

1. **typing.wav** - Keyboard typing sound effect
   - Duration: ~2 seconds
   - Format: WAV, 16-bit, 44.1kHz
   - Volume: Moderate, not too loud

2. **office_ambient.wav** - Office background ambient sound
   - Duration: ~30 seconds (loopable)
   - Format: WAV, 16-bit, 44.1kHz
   - Volume: Low/subtle background level

## Usage:

- **Keyboard typing**: Plays when agents are processing/thinking
- **Office ambient**: Plays continuously in the background during calls

## Implementation Notes:

The sound system is designed to:
1. Play keyboard typing sounds when agents are working
2. Maintain subtle office background ambiance
3. Automatically stop sounds when call ends
4. Handle errors gracefully if sound files are missing

## Adding Custom Sounds:

To add custom sounds:
1. Place WAV files in this directory
2. Update SoundManager class in main.py to reference new files
3. Ensure proper volume levels for phone call environment
