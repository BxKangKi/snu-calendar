import requests
from bs4 import BeautifulSoup as bs
import vobject
import os
import pytz
from datetime import datetime

URL = "https://www.snu.ac.kr/academics/resources/calendar"
AUTHOR = "Seoul National University<@snu.ac.kr>, Kiyeon Kang<kngky078@snu.ac.kr>"
BUILD_DIR = 'docs'
FILE_NAME = 'calendar.ics'
TIMEZONE = pytz.timezone("Asia/Seoul")


def extract_digits(text):
    return [int(ch) for ch in text if ch.isdigit()]


class Date:
    def __init__(self, year, month, day=0):
        self.year = int(year)
        self.month = int(month)
        self.day = int(day)

    def __str__(self):
        return f"{self.year}-{self.month:02d}-{self.day:02d}"


class Content:
    def __init__(self, start_date, end_date, description):
        self.start_date = start_date
        self.end_date = end_date
        self.description = description

    def print_event(self):
        print(f"{self.start_date} ~ {self.end_date}: {self.description}")


def parse_date_from_text(text, base_year, base_month):
    digits = extract_digits(text)
    # Heuristic parsing based on length of digits
    if len(digits) < 3:
        day_start = day_end = int(''.join(map(str, digits)))
        start_date = Date(base_year, base_month, day_start)
        end_date = Date(base_year, base_month, day_end)
    elif len(digits) < 5:
        day_start = int(''.join(map(str, digits[:2])))
        day_end = int(''.join(map(str, digits[2:])))
        start_date = Date(base_year, base_month, day_start)
        end_date = Date(base_year, base_month, day_end)
    elif len(digits) < 7:
        # format like DDMMDD (day, month, day)
        day_start = int(''.join(map(str, digits[:2])))
        month_end = int(''.join(map(str, digits[2:4])))
        day_end = int(''.join(map(str, digits[4:])))
        start_date = Date(base_year, base_month, day_start)
        end_date = Date(base_year, month_end, day_end)
    elif len(digits) < 11:
        # format like DDYYYYMMDD (day, year, month, day)
        day_start = int(''.join(map(str, digits[:2])))
        year_end = int(''.join(map(str, digits[2:6])))
        month_end = int(''.join(map(str, digits[6:8])))
        day_end = int(''.join(map(str, digits[8:])))
        start_date = Date(base_year, base_month, day_start)
        end_date = Date(year_end, month_end, day_end)
    else:
        # fallback
        start_date = Date(base_year, base_month)
        end_date = Date(base_year, base_month)
    return start_date, end_date


def get_date(month_text, year):
    digits = extract_digits(month_text)
    if len(digits) < 3:
        month = int(''.join(map(str, digits)))
        return Date(year, month)
    else:
        year_parsed = int(''.join(map(str, digits[:4])))
        month_parsed = int(''.join(map(str, digits[4:])))
        return Date(year_parsed, month_parsed)


def get_events_from_wrap(cal, wrap_div, base_year):
    month_text = wrap_div.select_one('span.month-text').get_text()
    base_date = get_date(month_text, base_year)
    content_divs = wrap_div.select('div.work-content')

    for content_div in content_divs:
        work_items = content_div.select('div.work')
        for work in work_items:
            desc = work.select_one('p.desc').get_text(strip=True)
            day_text = work.select_one('p.day').get_text()
            start_date, end_date = parse_date_from_text(day_text, base_date.year, base_date.month)

            # Create VEVENT
            vevent = cal.add('vevent')
            vevent.add('description').value = desc
            vevent.add('summary').value = desc

            dtstart = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0)
            dtend = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
            vevent.add('dtstart').value = TIMEZONE.localize(dtstart)
            vevent.add('dtend').value = TIMEZONE.localize(dtend)

            event_obj = Content(start_date, end_date, desc)
            event_obj.print_event()
    return cal


def main():
    cal = vobject.iCalendar()
    cal.add('prodid').value = AUTHOR
    
    try:
        resp = requests.get(URL, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return

    soup = bs(resp.text, "lxml")

    thisyear_text = soup.select_one('div.this-year').get_text(strip=True)
    thisyear = int(''.join(map(str, extract_digits(thisyear_text))))

    wrap_divs = soup.select('div.work-wrap')

    for wrap_div in wrap_divs:
        cal = get_events_from_wrap(cal, wrap_div, thisyear)

    os.makedirs(os.path.dirname(BUILD_DIR), exist_ok=True)

    with open(os.path.join(BUILD_DIR, FILE_NAME), 'wb') as file:
        file.write(cal.serialize().encode('utf-8'))

    print(f"Calendar saved to {FILE_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
