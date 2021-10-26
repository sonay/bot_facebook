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
    for file in csv_dir.iterdir():
        if file.match("*.csv") and file != summary_csv_path:
            url_md5 = file.name[len("bot_facebook_"):-4]
            summary = summarize(file)
            save_summary(summary_csv_path, [url_md5, *summary])


def write_headers(csv_file):
    with csv_file.open(newline='', mode="w", encoding="utf-8") as f:
        csv.writer(f).writerow(SUMMARY_HEADERS)


def summarize(file):
    summary = [0, 0, 0]
    with file.open(newline='', mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            summary[0] += int(row[0])  # likes
            summary[1] += int(row[1])  # comments
            summary[2] += int(row[2])  # shares
    return tuple(summary)


def save_summary(csv_file, row):
    with csv_file.open(newline='',  mode="a+", encoding="utf-8") as f:
        csv.writer(f).writerow(row)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s]: %(message)s',
                        stream=sys.stdout)
    main()
