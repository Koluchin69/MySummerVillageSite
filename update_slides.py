import json
import re
import urllib.request
from bs4 import BeautifulSoup

CHANNEL = 'MSVgame'
MAX_ITEMS = 30
MAX_PAGES = 5
HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8')


def bg(el):
    if el is None:
        return None
    m = re.search(r"url\(['\"]?([^'\")]+)['\"]?\)", el.get('style', '') or '')
    return m.group(1) if m else None


def clean_link(href, fallback):
    return re.sub(r'\?single$', '', href or fallback)


def parse(html):
    soup = BeautifulSoup(html, 'html.parser')
    messages = []
    ids = []
    for msg in soup.select('.tgme_widget_message'):
        post = msg.get('data-post')
        if not post:
            continue
        ids.append(int(post.split('/')[-1]))
        post_link = 'https://t.me/' + post
        text_el = msg.select_one('.tgme_widget_message_text')
        text = ''
        if text_el:
            for br in text_el.find_all('br'):
                br.replace_with('\n')
            text = text_el.get_text().strip()
        time_el = msg.select_one('.tgme_widget_message_date time')
        date = time_el.get('datetime') if time_el else ''
        media = []
        for a in msg.select('a.tgme_widget_message_photo_wrap'):
            src = bg(a)
            if src:
                media.append({'type': 'image', 'src': src, 'link': clean_link(a.get('href'), post_link)})
        for a in msg.select('a.tgme_widget_message_video_player'):
            video = a.select_one('video')
            thumb = bg(a.select_one('.tgme_widget_message_video_thumb'))
            link = clean_link(a.get('href'), post_link)
            if video is not None and video.get('src'):
                media.append({'type': 'video', 'src': video.get('src'), 'poster': thumb or '', 'link': link})
            elif thumb:
                media.append({'type': 'video', 'src': '', 'poster': thumb, 'link': link})
        for item in media:
            item['text'] = text
            item['date'] = date
        if media:
            messages.append(media)
    return messages, ids


def main():
    pages = []
    url = 'https://t.me/s/' + CHANNEL
    for _ in range(MAX_PAGES):
        messages, ids = parse(fetch(url))
        if not messages:
            break
        pages.append(messages)
        if not ids or min(ids) <= 1:
            break
        url = 'https://t.me/s/%s?before=%d' % (CHANNEL, min(ids))
    items = []
    seen = set()
    for messages in pages:
        for media in reversed(messages):
            for item in media:
                if item['src'] in seen:
                    continue
                seen.add(item['src'])
                items.append(item)
    items = items[:MAX_ITEMS]
    if not items:
        raise SystemExit('no media found')
    with open('slides.json', 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
