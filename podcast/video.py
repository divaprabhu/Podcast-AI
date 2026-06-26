import logging
import os
import subprocess

from .cache import get_cache_path

logger = logging.getLogger(__name__)


def step_generate_video(config):
    output_mp4 = get_cache_path(config, "video")
    audio_input = get_cache_path(config, "audio")
    image_input = config["output"]["album_art_file"]

    if not os.path.isfile(image_input):
        raise FileNotFoundError(f"Album art file missing or not a file: {image_input}")

    if not os.path.isfile(audio_input):
        raise FileNotFoundError(f"Audio file missing or not a file: {audio_input}")

    logger.info(
        "Creating podcast video with static visual background via FFmpeg..."
    )
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", image_input, "-i", audio_input,
        "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-shortest", output_mp4,
    ]
    logger.debug(f"Running command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    logger.info(f"Video file complete: {output_mp4}")
    return output_mp4
