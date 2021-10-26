import argparse
import logging
import sys

_logger = logging.getLogger(__name__)


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


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s]: %(message)s',
                        stream=sys.stdout)
    main()