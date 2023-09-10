from bs4 import BeautifulSoup
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
from collections import Counter
import pandas as pd

import numpy as np
from kiwipiepy import Kiwi
kiwi = Kiwi(model_type='sbg')

kiwi.add_user_word("리마인더", "NNG")
kiwi.add_user_word("익스트림", "NNG")


def softmax(numpy_array):
    exp = np.exp(numpy_array)
    sum = np.sum(exp)
    y = exp / sum

    return y


def make_word_list(apps_list):
    title_total_counts = Counter()
    info_total_counts = Counter()
    for app in apps_list:
        title_total_counts += app['title_word_count']
        info_total_counts += app['info_word_count']
    
    title_words_list = [key for key, _ in title_total_counts.most_common()]
    info_words_list = [key for key, _ in info_total_counts.most_common()]

    return title_words_list, info_words_list

    


def make_word_dict(word_list):
    id_to_word_dict = {}
    word_to_id_dict = {}
    for i, word in enumerate(word_list):
        print(i)
        print(word)
        id_to_word_dict[i] = word
        word_to_id_dict[word] = i

    return id_to_word_dict, word_to_id_dict


def clean_text(input):
    output = re.sub('[-=+,#/\?:^.@*\"※~ㆍ!』‘|\(\)\[\]`\'…》\”\“\’·]', ' ', input)
    return output

def extract_apps_url_list(url: str, container_select: str = '', list_select: str = '', filetype: str = 'html', relative_path: bool = False, host: str = ''):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36",
        "Accept-Language": "ko-kr"
    }
    origin_data = sess.get(url, headers=headers, verify=False)
    html = BeautifulSoup(origin_data.text, 'html.parser')

    url_list_container = html.select_one(container_select)
    url_element_list = url_list_container.select(list_select)
    url_list = []
    for element in url_element_list[:10]: #상위 10개 추출
        if relative_path:
            url_list.append(host + element.get('href'))
        else:

            url_list.append(element.get('href'))

    return url_list

def extract_apps_detail(url: str, info_select: str = ''):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36",
        "Accept-Language": "ko-kr"
    }
    origin_data = sess.get(url, headers=headers, verify=False)
    html = BeautifulSoup(origin_data.text, 'html.parser')
    title = html.find('title').text[:-16]
    info = html.select_one(info_select).text

    return title, info

log_n = np.log([10,9,8,7,6,5,4,3,2,1])

def calc_appearance_score(keyword_matrix):
    # print(keyword_matrix)
    appear_score = np.matmul(log_n, keyword_matrix)
    return appear_score

def calc_coincide_score(keyword_matrix):
    keyword_matrix = keyword_matrix ** 0.5
    return np.average(keyword_matrix, axis=0) * 10



def main():
    # 키워드 입력
    keyword = "루틴관리"
    search_url = f"https://play.google.com/store/search?q={keyword}&c=apps"

    # 상위 앱 추출
    list_selector = ".fUEl2e"
    app_selector = ".fUEl2e > div > div > div > div:nth-child(1) > a"
    host = "https://play.google.com"
    apps_url_list = extract_apps_url_list(search_url, container_select=list_selector, list_select=app_selector, relative_path=True, host=host)

    # 앱 소개 추출
    title_selector_p = "#yDmH0d > c-wiz.SSPGKf.Czez9d > div > div > div.tU8Y5c > div.P9KVBf > div > div > c-wiz > div.hnnXjf.XcNflb.J1Igtd > div.qxNhq > div > h1 > span"
    info_selector ="#yDmH0d > c-wiz.SSPGKf.Czez9d > div > div > div.tU8Y5c > div.wkMJlb.YWi3ub > div > div.qZmL0 > div:nth-child(1) > c-wiz:nth-child(2) > div > section > div > div.bARER"

    
    apps_list = []
    for url in apps_url_list:
        print(url)
        apps_detail = extract_apps_detail(url=url, info_select=info_selector)
        title = apps_detail[0]
        info = apps_detail[1]
        app_info = {
            'title': title,
            'info': info
        }
        apps_list.append(app_info)


    # 키워드 분석

    ##키워드 카운트
    allowed_tags = {'NNG', 'NNP', 'VV'}
    for app in apps_list:
        app['title_word_count'] = Counter([x.form for x in kiwi.tokenize(clean_text(app['title'])) if x.tag in allowed_tags])
        app['info_word_count'] = Counter([x.form for x in kiwi.tokenize(clean_text(app['info'])) if x.tag in allowed_tags])
    
    ##전체 word list 및 word dictionary 생성
    title_word_list, info_word_list = make_word_list(apps_list=apps_list)
    print(title_word_list)
    title_id_to_word_dict, title_word_to_id_dict = make_word_dict(title_word_list)
    info_id_to_word_dict, info_word_to_id_dict = make_word_dict(info_word_list)

    ##numpy로 단어-app순위 matrix 생성
    print(title_word_to_id_dict)
    header = []
    for url in apps_url_list:
        header.append(url[46:])
    header.append('total score')


    ###title matrix
    title_word_score_matrix = np.zeros((10, len(title_word_list)))
    for i, app in enumerate(apps_list):
        for key, count in app['title_word_count'].most_common():
            index = title_word_to_id_dict[key]
            title_word_score_matrix[i, index] = count
        title_word_score_matrix[i] = softmax(title_word_score_matrix[i])


    ###info matrix
    info_word_score_matrix = np.zeros((10, len(info_word_list)))

    for i, app in enumerate(apps_list):
        for key, count in app['info_word_count'].most_common():
            index = info_word_to_id_dict[key]
            info_word_score_matrix[i, index] = count
        info_word_score_matrix[i] = softmax(info_word_score_matrix[i])


    ##Word Score 생성

    ###title word score
    title_appearance_score = calc_appearance_score(title_word_score_matrix)
    title_coincide_score = calc_coincide_score(title_word_score_matrix)
    total_title_word_score = title_appearance_score + title_coincide_score
    total_title_word_score = total_title_word_score.reshape(1,len(total_title_word_score))

    ###info word score 
    info_appearance_score = calc_appearance_score(info_word_score_matrix)
    info_coincide_score = calc_coincide_score(info_word_score_matrix)
    total_info_word_score = info_appearance_score + info_coincide_score
    total_info_word_score = total_info_word_score.reshape(1,len(total_info_word_score))

    
    # 분석 결과 저장

    ##title word matrix 저장
    title_index_label = [] 
    for i in range(len(title_word_list)):
        title_index_label.append(title_id_to_word_dict[i]) #word list에서의 index 위치가 word의 id 값으로 사용됨

    title_word_score_matrix = np.append(title_word_score_matrix, total_title_word_score, axis=0)
    title_word_score_matrix = title_word_score_matrix.T


    title_df = pd.DataFrame(title_word_score_matrix)
    title_df.index = title_index_label
    title_df.columns = header
    title_df.to_excel(f"{keyword}_title_word.xlsx")

    ##info word matrix 저장
    info_index_label = []
    for i in range(len(info_word_list)):
        info_index_label.append(info_id_to_word_dict[i])

    info_word_score_matrix = np.append(info_word_score_matrix, total_info_word_score, axis=0)
    info_word_score_matrix = info_word_score_matrix.T
    info_df = pd.DataFrame(info_word_score_matrix)
    info_df.index = info_index_label
    info_df.columns = header
    info_df.to_excel(f"{keyword}_info_word.xlsx")







if __name__ == "__main__":
    main()
