import os
from itertools import count

import requests
from dotenv import load_dotenv
from terminaltables import AsciiTable

PROGRAM_LANGUAGES = [
    'Python', 'Java', 'Javascript', 'Ruby', 'PHP', 'C++', 'C#', 'Go', 'C'
]


def print_ascii_table(vacancies_by_lang, title):
    table_header = [
        (
            'Язык программирования', 'Вакансий найдено',
            'Вакансий обработано', ' Средняя зарплата'
        ),
    ]
    table_rows = []
    for program_language, vacancy_stat in vacancies_by_lang.items():
        table_row = [program_language, ]
        for _, column_value in vacancy_stat.items():
            table_row.append(column_value)
        table_rows.append(table_row)

    table_instance = AsciiTable(table_header.extend(table_rows), title)
    print(table_instance.table)
    print()


def predict_salary(salary_from, salary_to):
    if salary_from and salary_to:
        return (salary_to + salary_from) / 2
    elif salary_from:
        return salary_from * 1.2
    elif salary_to:
        return salary_to * 0.8
    else:
        return None


def predict_rub_salary_hh(vacancy):
    if not vacancy['salary']:
        return None
    if vacancy['salary']['currency'] != 'RUR':
        return None
    return predict_salary(vacancy['salary']['from'], vacancy['salary']['to'])


def predict_rub_salary_sj(vacancy):
    if vacancy['currency'] != 'rub':
        return None
    return predict_salary(vacancy['payment_from'], vacancy['payment_to'])


def fetch_hh_vacancies(text, area):
    url = 'https://api.hh.ru/vacancies'
    payload = {
            'text': text,
            'area': area,
            'per_page': 100,
            'period': 30,
        }
    vacancies = []
    total_vacancies = 0
    for page in count():
        payload['page'] = page
        try:
            page_response = requests.get(url, params=payload)
            page_response.raise_for_status()

            page_payload = page_response.json()
            vacancies.extend(page_payload['items'])
            total_vacancies = page_payload['found']
            if page >= page_payload['pages']:
                break
        except requests.exceptions.HTTPError:
            if page_response.json()['description'] == (
                "you can't look up more than 2000 items in the list"
            ):
                return vacancies, total_vacancies
            page_response.raise_for_status()
    return vacancies, total_vacancies


def fetch_sj_vacancies(text, superjob_api_key):
    url = 'https://api.superjob.ru/2.0/vacancies/'
    headers = {
        'X-Api-App-Id': superjob_api_key,
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
    total_vacancies = page_payload['total']
    return vacancies, total_vacancies


def get_superjob_vacancies_stat(superjob_api_key):
    vacancies_by_lang = {}
    vacancies = []
    for program_language in PROGRAM_LANGUAGES:
        try:
            vacancies, total_vacancies = fetch_sj_vacancies(
                text=f'программист {program_language}',
                superjob_api_key=superjob_api_key,
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
        vacancies_by_lang[program_language] = {
                'vacancies_found': total_vacancies,
                'vacancies_processed': vacancies_processed,
                'average_salary': average_salary,
            }
    return vacancies_by_lang


def get_hh_vacancies_stat():
    vacancies_by_lang = {}
    vacancies = []
    for program_language in PROGRAM_LANGUAGES:
        try:
            vacancies, total_vacancies = fetch_hh_vacancies(
                text=f'программист {program_language}',
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

        vacancies_by_lang[program_language] = {
            'vacancies_found': total_vacancies,
            'vacancies_processed': vacancies_processed,
            'average_salary': average_salary,
        }
    return vacancies_by_lang


def main():
    load_dotenv()
    superjobj_stat = get_superjob_vacancies_stat(
        superjob_api_key=os.getenv('SUPERJOB_API_KEY'),
    )
    print_ascii_table(superjobj_stat, 'SuperJob Moskow')

    headhunter_stat = get_hh_vacancies_stat()
    print_ascii_table(headhunter_stat, 'HeadHunter Moskow')


if __name__ == '__main__':
    main()
