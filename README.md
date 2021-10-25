# bot_facebook

## Purpose

bot_facebook is a scraper, coded in Python, to parse Facebook accounts for all Post data, in a 
specific year and month given as input in the form of yearmonth, i.e. 202104. The input parameter is
parsed from **--month** argument from command line / sys.argv. 

bot_facebook expects a **UTF-8 encoded** text input file called **urls.lst** in the working
directory which contains a single account URL on each line. No validation of URLs are performed, may
or may not raise in case of a URL error.

bot_facebook requires
* **tr_TR.UTF8** LC_ALL locale to be available in your system.
* Firefox and geckodriver (version 0.30.0) to be on your PATH.
* To parse accounts requiring log in, EMAIL and PASSWORD env variables to be set
 (Though this is not possible at the moment)
* tesseract-ocr (version 4.1.1) and tesseract-ocr-tur (Turkish language data) to be installed on 
your system, to analyze screenshots. If all you need is parsing DOM, you don't have to have them.

It parses each account by 

1. Saving each account url's md5hash in a file called **url-md5.csv** in the current working 
directory, with column values [ACCOUNT_URL] and [URL_MD5_HASH].

2. Taking a .png screenshot of the account, saved in the current working directory named in the 
format bot_facebook_[URL_MD5_Hash].png, for example bot_facebook_059ac34dcc4305b54af17c27d5d50902.png

3. Parsing each matching -year and month of post time- post data in the Posts/Gönderiler page
of the account and saving it in a .csv file, in **DOM/** directory of the current working
directory, named in the format bot_facebook_[URL_MD5_HASH],
for example bot_facebook_059ac34dcc4305b54af17c27d5d50902.csv where each line has 
likes, comments and shares column values. For example: "13, 4, 5" for likes, comments and shares
respectively.

4. Taking a screenshot of each matching post, saving their reaction box in **OCR/** directory of 
the current working directory, named in the format 
bot_facebook_[YEARMONTH]_[URL_MD5_HASH]\_[PAGE_ORDER].png,
for example bot_facebook_202110_059ac34dcc4305b54af17c27d5d50902_0027.png

5. Creating a full screenshot of the matching posts in page order by assembling single post 
screenshots and saving in the name format bot_facebook_[YEARMONTH]_[URL_MD5_HASH].png, 
for example bot_facebook_202110_059ac34dcc4305b54af17c27d5d50902.png


## How to build

```
python3 -m venv venv-bot_facebook
source venv-bot_facebook/bin/activate
pip3 install -r requirements.txt 
```

## How to run
```
# To start scraping
python3 main.py --month [yearmonth]

# To analyze screenshots in OCR directory with tesseract Turkish language settings
python3 ocr.py

# To accumulate all likes, comment & share counts, recognized from tesseract outputs,
# into bot_facebook_sum.csv file in OCR
python3 summary.py --dir OCR

# To accumulate all likes, comment & share counts, parsed from page sources,
# into bot_facebook_sum.csv file in DOM
python3 summary.py --dir DOM
```