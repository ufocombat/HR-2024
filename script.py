from openai import OpenAI
from dotenv import load_dotenv
import json
import pandas as pd
from tqdm import tqdm
import sqlite3

# получим переменные из .env
load_dotenv()
MAX_LENGTH = 2048 

client = OpenAI()

system_prompt = '''
Ты директор IT компании которая разрабатывает сайты с применением языковых моделей LLM. 
Проанализируй структуру it-отдела разработки сайтов из 15 человек и добавь наименование 10 недостающих должностей: 

Разработчик Python, 
Аналитик данных, 
Инженер по машинному обучению, 
Web-разработчик, 
Системный администратор

Для информации: Ruby мы не используем
Наш стек: Python, Django, Angular, MogoDB, Docker
'''

completion = client.chat.completions.create(
  model="gpt-4",
  messages=[
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": "Ответ дай без пояснений в виде перечня из 15 должностей:  Пример ответа: Разработчик Python,..."}
  ]
)

vacancies = list(completion.choices[0].message.content.split(","))


system_prompt_vac = '''
Ты HR специалист с IT бэкграундом в компании
которая разрабатывает сайты с применением языковых моделей LLM. 
Наш стек для програмистов: Python, Django, Angular, MogoDB, Docker
По представленному названию должности составь JSON объект:

"title": "Название вакансии." 
"description": "Краткое описание вакансии.",
"requirements": ["Требование к вакансии 1", "Требование к вакансии 2",...]

Все описания должны быть на русском языке.
'''

vacancies_data=[]

for vac in tqdm(vacancies, desc="Обработка вакансий"):
    for attempt in range(3):  # Повторять до 3 раз
        try:
            completion = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt_vac},
                    {"role": "user", "content": f"Вакансия: {vac}"}
                ]
            )
            temp_data = json.loads(completion.choices[0].message.content)
            
            # Проверка длины текста
            combined_text = temp_data["title"] + temp_data["description"] + ''.join(temp_data["requirements"])
            if len(combined_text) > MAX_LENGTH:
                raise ValueError(f"Длина текста превышает {MAX_LENGTH} символов")
            
            vacancies_data.append(temp_data)
            break  # Прервать цикл при успешном выполнении
        except Exception as e:
            print(f"Произошла ошибка: {e}. Попытка {attempt + 1} из 3.")
            if attempt == 2:  # Если это последняя попытка
                print("Не удалось обработать вакансию после 3 попыток.")

conn = sqlite3.connect('vacancies.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS vacancies (
        id INTEGER PRIMARY KEY,
        title TEXT,
        description TEXT,
        requirements TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY,
        skills TEXT,
        experience TEXT
    )
''')

for vacancy in vacancies_data:
    cursor.execute('''
        INSERT INTO vacancies (title, description, requirements)
        VALUES (?, ?, ?)
    ''', (vacancy["title"], vacancy["description"], ", ".join(vacancy["requirements"])))

cursor.execute('SELECT * FROM vacancies')
rows = cursor.fetchall()

df_vacancies = pd.DataFrame(rows, columns=['id', 'title', 'description','requirements'])
df_vacancies.to_excel('vacancies.xlsx', index=False)

conn.commit()
conn.close()

system_prompt_vac = '''
Ты специалист по подготовке данных с IT бэкграундом в компании
которая разрабатывает сайты с применением языковых моделей LLM. 
Наш стек для програмистов: Python, Django, Angular, MogoDB, Docker
По представленному названию вакансии сгенерируй резюме предполагаемого кандидата в JSON объект,
названия компаний придумывай опираясь на знание Российского it-рынка,
обязательно указывай уровень английского языка:

"skills": ["Навык 1", "Навык 2", ...], 
"experience": ["Опыт работы в компании 1", "Опыт работы в компании 2",...]

Все описания должны быть на русском языке.
'''

resume_data=[]

for vac in tqdm(vacancies, desc="Обработка резюме"):
    for attempt in range(3):  # Повторять до 3 раз
        try:
            completion = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt_vac},
                    {"role": "user", "content": f"Вакансия: {vac}"}
                ]
            )
            temp_data = json.loads(completion.choices[0].message.content)
            
            # Проверка длины текста
            combined_text =  ''.join(temp_data["skills"]) + ''.join(temp_data["experience"])
            if len(combined_text) > MAX_LENGTH:
                raise ValueError(f"Длина текста превышает {MAX_LENGTH} символов")
            
            resume_data.append(temp_data)
            break  # Прервать цикл при успешном выполнении
        except Exception as e:
            print(f"Произошла ошибка: {e}. Попытка {attempt + 1} из 3.")
            if attempt == 2:  # Если это последняя попытка
                print("Не удалось обработать резюме после 3 попыток.")


conn = sqlite3.connect('vacancies.db')
cursor = conn.cursor()

for resume in resume_data:
    cursor.execute('''
        INSERT INTO resumes (skills, experience)
        VALUES (?, ?)
    ''', ("; ".join(resume["skills"]), "; ".join(resume["experience"])))


conn = sqlite3.connect('vacancies.db')
cursor = conn.cursor()

cursor.execute('SELECT * FROM resumes')
rows = cursor.fetchall()

df_resumes = pd.DataFrame(rows, columns=['id', 'skills', 'experience'])
df_resumes.to_excel('resumes.xlsx', index=False)

conn.commit()
conn.close()


