import logging
import sys
from pathlib import Path

from PIL import Image
from pytesseract import pytesseract

OCR_DIR = Path("OCR")


def main():
    for file in OCR_DIR.iterdir():
        if file.match("*.png"):
            tes_text = pytesseract.image_to_string(
                Image.open(file, formats=("PNG",)), config='--psm 6', lang="tur")

            with open(file.with_suffix(".txt"), "w", encoding="utf-8") as txt:
                txt.write(tes_text)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s]: %(message)s',
                        stream=sys.stdout)
    main()
