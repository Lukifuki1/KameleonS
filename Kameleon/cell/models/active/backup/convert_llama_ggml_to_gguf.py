import subprocess
from pathlib import Path

from loguru import logger


def convert_distilled_to_gguf(input_path: Path, output_dir: Path) -> bool:
    """
    Pretvori model v .distilled/.bin/.ggml formatu v .gguf format.
    """
    converter_script = Path.home() / "llama.cpp" / "convert_llama_ggml_to_gguf.py"

    if not converter_script.exists():
        logger.error(f"Konverzijska skripta ne obstaja: {converter_script}")
        return False

    if not input_path.exists():
        logger.error(f"Vhodna datoteka ne obstaja: {input_path}")
        return False

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run(
            [
                "python3",
                str(converter_script),
                "--outfile",
                str(output_dir / (input_path.stem + ".gguf")),
                str(input_path),
            ],
            check=True,
        )
        logger.success(f"Konverzija uspela: {input_path.name} → .gguf")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Napaka med konverzijo {input_path.name}: {e}")
        return False
