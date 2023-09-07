import requests
sess = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries = 20)
sess.mount('http://', adapter)
from urllib.request import urlopen
from bs4 import BeautifulSoup
from trafilatura import fetch_url, extract
import xml.etree.ElementTree as ET
from trafilatura import sitemaps, feeds
import json
import re

from kiwipiepy import Kiwi
kiwi = Kiwi()

from transformers import BertTokenizer
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")

def trim_zerospace(w):
    newString = (w.encode('ascii', 'ignore')).decode("utf-8")
    return newString


def intersection(lst1, lst2):
    lst3 = [value for value in lst1 if value in lst2]
    return lst3


def clean_text(input):
    output = re.sub('[-=+,#/\?:^.@*\"※~ㆍ!』‘|\(\)\[\]`\'…》\”\“\’·]', ' ', input)
    return output


def extract_news_url_list(url: str, container_select: str = '', list_select: str = '', filetype: str = 'html', relative_path: bool = False, host: str = ''):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"
    }
    origin_data = sess.get(url, headers=headers, verify=False)
    # print(host)
    if(filetype == 'xml'):
        xml = BeautifulSoup(origin_data.text, 'xml')
        url_list_container = xml.find_all(container_select)
        url_list = []
        for element in url_list_container:
            if relative_path:
                path = element.select_one(list_select).text
                url = host + path
                url_list.append(url)
            else:
                url_list.append(element.select_one(list_select).text)
        # print(url_list)

    elif(filetype == 'html'):
        html = BeautifulSoup(origin_data.text, 'html.parser')
        url_list_container = html.select_one(container_select)
        # print(url_list_container)
        url_element_list = url_list_container.select(list_select)
        url_list = []
        for element in url_element_list:
            if relative_path:
                path = element.get('href')
                url = host + path
                url_list.append(url)
            else:
                url_list.append(element.get('href'))

    return url_list


def extract_news(media: str, url: str, classes_to_remove: list = []):
    print(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36"
    }
    html = sess.get(url, headers=headers, verify=False)
    html_text = html.text
    if(len(classes_to_remove) > 0):
        soup = BeautifulSoup(html.text, "html.parser")
        for class_name in classes_to_remove:
            remove_list = soup.find_all(class_=class_name)
            for element in remove_list:
                element.decompose()
        html_text = soup.prettify()
    
    html_extract_txt = extract(html_text, include_comments=False, output_format='json')
    # print(html_extract_txt)
    html_extract_json = json.loads(html_extract_txt)
    html_extract_json["source-hostname"] = media
    html_extract_json["source"] = url
    html_extract_txt = json.dumps(html_extract_json)

    return html_extract_txt

def get_news_list(media: str, url: str, host: str, container_select: str = '', list_select: str = '', filetype: str = 'html', relative_url: bool = False, classes_to_remove: list = []):
    news_url_list = extract_news_url_list(
        url, container_select, list_select, filetype, relative_url, host)
    news_list = []
    for news_url in news_url_list:
        try:
            news = extract_news(media, news_url, classes_to_remove)
            news_list.append(news)
        except:
            print('something went wrong')

    return news_list


def main():
    ##################이곳만 수정하면 된다########################
    today = '2023-05-12'
    country = 'en' #kr or en
    ##################이곳만 수정하면 된다########################

    news_list = []

    with open(f'media_list_{country}.json', 'r', encoding='UTF-8') as f:
        media_list = json.load(f)
        for media in media_list:
            print(media['media'])
            media_news_list = get_news_list(
                media['media'],
                media['url'],
                media['host'],
                media['container_select'],
                media['list_select'],
                media['filetype'],
                (media['relative_path'] == "true"),
                media['classes_to_remove'])

            news_list = news_list + media_news_list

        # print(f'{len(news_list)}개 뉴스 수집')

    json_news_list = []

    for news in news_list:
        news_json = json.loads(news)
        if(news_json['date'] != today):
            continue

        if(any(x for x in json_news_list if x['title'] == news_json['title'])):
            continue

        if(country == 'kr'):
            token = kiwi.tokenize(clean_text(news_json['raw_text']))
            morph = [item.form for item in token if item.tag == 'NNG' or item.tag ==
                    'NNP' or item.tag == 'NNB' or item.tag == 'NR' or item.tag == 'NP' or item.tag == 'SN']
            morph = set(morph)
            news_json['token_set'] = list(morph)
            json_news_list.append(news_json)
        elif(country == 'en'):
            token = tokenizer.tokenize(clean_text(news_json['raw_text']))
            morph = set(token)
            news_json['token_set'] = list(morph)
            json_news_list.append(news_json)
        # print(news['title'])
    print(f'{len(json_news_list)}개 뉴스 수집')

    with open(f'news_list_json_new/{today}_{country}.json', 'w', encoding='UTF-8') as f:
        json.dump(json_news_list, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()