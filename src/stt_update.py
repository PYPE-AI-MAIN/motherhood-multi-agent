# Add this to your create_stt() function in main.py:
def create_stt():
    """Create STT instance from YAML config."""
    stt_config = config.stt_config
    provider = stt_config.get("provider", "sarvam")
    language = stt_config.get("language", "hi-IN")
    model = stt_config.get("model", "saaras:v3")
    mode = stt_config.get("mode", "codemix")

    if provider == "sarvam":
        return sarvam.STT(language=language, model=model, mode=mode)
    else:
        raise ValueError(f"Unknown STT provider: {provider}")
