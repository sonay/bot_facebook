import argparse
import csv
import logging
import sys
from pathlib import Path

_logger = logging.getLogger(__name__)

SUMMARY_CSV_PATH = Path("bot-facebook_sum.csv")
SUMMARY_HEADERS = ["URL_MD5", "ToplamBegeni", "ToplamYorum", "ToplamPaylasim"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir",
                        help="Enter the csv source directory, either OCR or DOM")
    args = parser.parse_args()

    try:
        csv_dir = args.dir
        if csv_dir not in ["OCR", "DOM"]:
            raise ValueError()
    except ValueError:
        _logger.critical("Missing or illegal --dir parameter, use with -h for help.")
        return

    create_summary(Path(csv_dir))


def create_summary(csv_dir):
    summary_csv_path = csv_dir / SUMMARY_CSV_PATH
    write_headers(summary_csv_path)


def write_headers(csv_file):
    with csv_file.open(newline='', mode="x", encoding="utf-8") as f:
        csv.writer(f).writerow(SUMMARY_HEADERS)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s]: %(message)s',
                        stream=sys.stdout)
    main()
