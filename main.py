import os
from itertools import count

import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable

load_dotenv()

SUPERJOB_API = os.getenv('SUPERJOB_API')

POPILAR_LANG = [
    'Python', 'Java', 'Javascript', 'Ruby', 'PHP', 'C++', 'C#', 'Go', 'C'
]


def print_ascii_table(vacancies_by_lang, title):
    table_data = [
        (
            'Язык программирования', 'Вакансий найдено',
            'Вакансий обработано', ' Средняя зарплата'
        ),
    ]

    for lang in vacancies_by_lang:
        data = vacancies_by_lang[lang]
        table_data.append(
            (
                lang, data['vacancies_found'],
                data['vacancies_processed'], data['average_salary']
            )
        )

    table_instance = AsciiTable(table_data, title)
    table_instance.justify_columns[2] = 'right'
    print(table_instance.table)
    print()


def predict_salary(salary_from, salary_to):
    if salary_from and salary_to:
        return (salary_to-salary_from)/2
    return salary_from or salary_to


def predict_rub_salary_hh(vacancy):
    if vacancy['salary'] and vacancy['salary']['currency'] == 'RUR':
        return predict_salary(vacancy['salary']['from'], vacancy['salary']['to'])
    return None


def predict_rub_salary_sj(vacancy):
    if vacancy['currency'] == 'rub':
        return predict_salary(vacancy['payment_from'], vacancy['payment_to'])
    return None


def fetch_hh_vacancies(text, area):
    url = 'https://api.hh.ru/vacancies'
    payload = {
            'text': text,
            'area': area,
            'per_page': 100,
            'period': 30,
        }
    vacancies = []
    for page in count():
        payload['page'] = page
        try:
            page_response = requests.get(url, params=payload)
            page_response.raise_for_status()

            page_payload = page_response.json()
            vacancies.extend(page_payload['items'])
            if page >= page_payload['pages']:
                break
        except requests.exceptions.HTTPError:
            if page_response.json()['description'] == (
                "you can't look up more than 2000 items in the list"
            ):
                return vacancies
            page_response.raise_for_status()
    return vacancies


def fetch_sj_vacancies(text):
    url = 'https://api.superjob.ru/2.0/vacancies/'
    headers = {
        'X-Api-App-Id': SUPERJOB_API
    }
    payload = {
        'keyword': text,
        'count': 100,
        'town': 'Москва',
    }

    vacancies = []
    for page in count():
        payload['page'] = page
        page_response = requests.get(url, params=payload, headers=headers)
        page_response.raise_for_status()

        page_payload = page_response.json()
        vacancies.extend(page_payload['objects'])
        if not page_payload['objects']:
            break
    return vacancies


def get_superjob_vacancies_stat():
    vacancies_by_lang = {}
    vacancies = []
    for lang in POPILAR_LANG:
        try:
            vacancies = fetch_sj_vacancies(
                text=f'программист {lang}',
            )
        except requests.exceptions.HTTPError as error:
            print(f"Ошибка:\n{error}")
        vacancies_processed = 0
        average_salary = 0
        sum_salary = 0

        for vacancy in vacancies:
            vacancy_salary = predict_rub_salary_sj(vacancy)
            if vacancy_salary:
                sum_salary += vacancy_salary
                vacancies_processed += 1
        if vacancies_processed:
            average_salary = int(sum_salary/vacancies_processed)
        vacancies_by_lang[lang] = {
                'vacancies_found': len(vacancies),
                'vacancies_processed': vacancies_processed,
                'average_salary': average_salary,
            }
    return vacancies_by_lang


def get_hh_vacancies_stat():
    vacancies_by_lang = {}
    vacancies = []
    for lang in POPILAR_LANG:
        try:
            vacancies = fetch_hh_vacancies(
                text=f'программист {lang}',
                area=1,
            )
        except requests.exceptions.HTTPError as error:
            print(f"Ошибка:\n{error}")
        vacancies_processed = 0
        average_salary = 0
        sum_salary = 0

        for vacancy in vacancies:
            vacancy_salary = predict_rub_salary_hh(vacancy)
            if vacancy_salary:
                sum_salary += vacancy_salary
                vacancies_processed += 1
        average_salary = int(sum_salary/vacancies_processed)

        vacancies_by_lang[lang] = {
            'vacancies_found': len(vacancies),
            'vacancies_processed': vacancies_processed,
            'average_salary': average_salary,
        }
    return vacancies_by_lang


def main():
    superjobj_stat = get_superjob_vacancies_stat()
    print_ascii_table(superjobj_stat, 'SuperJob Moskow')

    headhunter_stat = get_hh_vacancies_stat()
    print_ascii_table(headhunter_stat, 'HeadHunter Moskow')


if __name__ == '__main__':
    main()

