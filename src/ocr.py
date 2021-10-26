import csv
import logging
import re
import sys
from operator import attrgetter
from pathlib import Path

from PIL import Image
from pytesseract import pytesseract

_logger = logging.getLogger(__name__)

OCR_DIR = Path("OCR")


def main():
    # sorted to match DOM csv's for easier diffing
    for file in sorted(OCR_DIR.iterdir(), key=attrgetter('name')):
        if file.match("*.png"):
            tes_text = pytesseract.image_to_string(
                Image.open(file, formats=("PNG",)), config='--psm 6', lang="tur")
            _logger.debug("tesseract_output:'%s'", tes_text)

            with open(file.with_suffix(".txt"), "w", encoding="utf-8") as txt:
                txt.write(tes_text)

            likes, comments, shares = (0, 0, 0)
            try:
                likes, comments, shares = TesseractOutputParser(tes_text).to_post_data()
            except ValueError as val_err:
                _logger.error("Error in %s tesseract's output: %s", file.name, val_err)
                # write zeroes anyway, for easier diff comparison with DOM csvs

            _logger.debug("Parsed tesseract output: likes:%s comments:%s shares:%s",
                          likes, comments, shares)

            parts = file.name.split("_")
            with open(f"{OCR_DIR}/{parts[0]}_{parts[1]}_{parts[3]}.csv", "a+", encoding="utf-8") \
                    as tes_out:
                csv.writer(tes_out).writerow((likes, comments, shares))


class TesseractOutputParser:
    SHARES_REGEX = re.compile(r"(\d+)\s*(Paylaşım)")

    COMMENTS_REGEX = re.compile(r"(\d+)\s*(Yorum)")

    LIKES_REGEX = re.compile(r"^\s*\d+")

    SAFEGUARD = "Beğen Yorum yap Paylaş"

    def __init__(self, text):
        self.text = text

    def to_post_data(self):
        if self.SAFEGUARD not in self.text:
            raise ValueError("Buttons' text is missing")
        safeguard_ind = self.text.index(self.SAFEGUARD)
        self.text = self.text[:safeguard_ind].strip()

        shares = self._parse_shares()
        comments = self._parse_comments()
        likes = self._parse_likes()
        return likes, comments, shares

    def _parse_shares(self):
        shares = 0
        if self.text.endswith("Paylaşım"):
            shares_match = self.SHARES_REGEX.search(self.text)

            if not shares_match:
                raise ValueError("Could not read shares count.")

            if shares_match.start(2) != len(self.text) - len("Paylaşım"):
                raise ValueError("More than one shares values.")

            shares = shares_match.group(1)
            self.text = self.text[:shares_match.start()].strip()
        return shares

    def _parse_comments(self):
        comments = 0
        if self.text.endswith("Yorum"):
            comments_match = self.COMMENTS_REGEX.search(self.text)
            if not comments_match:
                raise ValueError("Could not read comment count.")

            if comments_match.start(2) != len(self.text) - len("Yorum"):
                raise ValueError("More than one comment values.")

            comments = comments_match.group(1)
            self.text = self.text[:comments_match.start()].strip()
        return comments

    def _parse_likes(self):
        likes_match = self.LIKES_REGEX.match(self.text)
        if likes_match:
            return likes_match.group()
        raise ValueError("Unexpected characters in place of likes.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s]: %(message)s',
                        stream=sys.stdout)
    main()
