import asyncio
import logging
import os
import subprocess
import edge_tts

from .cache import read_cache_json, get_cache_dir, get_cache_path

logger = logging.getLogger(__name__)


async def _amake_audio(script, cache_dir, config, output_mp3):
    chunks_dir = os.path.join(cache_dir, "audio_chunks")
    os.makedirs(chunks_dir, exist_ok=True)

    file_list_path = os.path.join(cache_dir, "concat_list.txt")

    existing_up_to = -1
    for idx in range(len(script)):
        chunk_path = os.path.join(chunks_dir, f"chunk_{idx:04d}.mp3")
        if os.path.exists(chunk_path) and os.path.getsize(chunk_path) > 0:
            existing_up_to = idx
        else:
            break

    # start_idx is the first chunk that still needs to be generated.
    # existing_up_to is the last contiguous chunk that already exists,
    # so generation should begin at existing_up_to + 1.
    start_idx = existing_up_to + 1

    if start_idx > 0:
        logger.info(
            "Resuming from turn %d (chunks 0..%d already exist)",
            start_idx, existing_up_to,
        )

    timeout = (
        config.get("podcast", {}).get("voice", {}).get("tts_timeout", 120)
    )
    tts_sleep = (
        config.get("podcast", {}).get("voice", {}).get("tts_sleep", 5)
    )
    with open(file_list_path, "w") as flist:
        for idx in range(start_idx):
            chunk_file = f"chunk_{idx:04d}.mp3"
            flist.write(f"file 'audio_chunks/{chunk_file}'\n")

        for idx in range(start_idx, len(script)):
            logger.info(f"Building audio for turn {idx}")
            chunk_file = f"chunk_{idx:04d}.mp3"
            chunk_path = os.path.join(chunks_dir, chunk_file)

            turn = script[idx]
            voice_cfg = config["podcast"]["voice"]
            voice = (
                voice_cfg["male"]
                if turn["host"] == "Male"
                else voice_cfg["female"]
            )
            rate = (
                voice_cfg["male_rate"]
                if turn["host"] == "Male"
                else voice_cfg["female_rate"]
            )
            pitch = (
                voice_cfg["male_pitch"]
                if turn["host"] == "Male"
                else voice_cfg["female_pitch"]
            )

            for attempt in range(2):
                try:
                    communicate = edge_tts.Communicate(
                        turn["text"], voice, rate=rate, pitch=pitch
                    )
                    await asyncio.wait_for(
                        communicate.save(chunk_path), timeout=timeout
                    )
                    break
                except asyncio.TimeoutError:
                    if attempt == 1:
                        logger.exception(
                            "TTS timed out after %ss (2 attempts failed)",
                            timeout,
                        )
                        raise
                    logger.warning(
                        f"TTS timeout after {timeout}s "
                        f"(attempt {attempt + 1}/2). Retrying..."
                    )
                    await asyncio.sleep(tts_sleep)
                except Exception as e:
                    if attempt == 1:
                        logger.exception(
                            f"TTS generation failed after 2 attempts: {e}"
                        )
                        raise
                    logger.warning(
                        f"TTS generation error "
                        f"(attempt {attempt + 1}/2): {e}. Retrying..."
                    )
                    await asyncio.sleep(tts_sleep)

            if (
                not os.path.exists(chunk_path)
                or os.path.getsize(chunk_path) == 0
            ):
                raise RuntimeError(
                    f"TTS produced no output for turn {idx} "
                    f"(chunk: {chunk_path}). "
                    "The audio file is missing or empty."
                )

            flist.write(f"file 'audio_chunks/{chunk_file}'\n")
            await asyncio.sleep(tts_sleep)

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", file_list_path, "-c", "copy", output_mp3,
    ]
    logger.debug(f"Running command: {' '.join(cmd)}")
    subprocess.run(
        cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )


def step_generate_audio(config):
    data = read_cache_json(config)
    if not isinstance(data, dict) or "selected" not in data:
        raise KeyError("No selected paper found in cache")
    paper = data["selected"]

    if isinstance(paper, dict) and paper.get("script"):
        script = paper["script"]
    else:
        raise KeyError(
            "No script found in cache; run the 'script' step first."
        )

    cache_dir = get_cache_dir(config)
    output_mp3 = get_cache_path(config, "audio")

    if os.path.exists(output_mp3):
        logger.info("Loading audio from cache.")
        return output_mp3

    logger.info("Generating natural host audio using edge-tts...")

    try:
        asyncio.run(_amake_audio(script, cache_dir, config, output_mp3))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            _amake_audio(script, cache_dir, config, output_mp3)
        )

    logger.info(f"Audio file complete: {output_mp3}")
    return output_mp3
