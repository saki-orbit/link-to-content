#!/usr/bin/env python3
"""Download Link2Content's speech model into the standard local model cache."""

import platform


def main() -> None:
    is_apple_silicon = platform.system() == "Darwin" and platform.machine().lower() in {
        "arm64",
        "aarch64",
    }

    if is_apple_silicon:
        from huggingface_hub import snapshot_download

        model_id = "mlx-community/whisper-large-v3-turbo"
        print(f"Downloading {model_id} into the Hugging Face cache...")
        snapshot_download(repo_id=model_id)
        return

    from faster_whisper.utils import download_model

    print("Downloading the faster-whisper large-v3-turbo model into the Hugging Face cache...")
    model_path = download_model("large-v3-turbo")
    print(f"Model ready: {model_path}")


if __name__ == "__main__":
    main()
