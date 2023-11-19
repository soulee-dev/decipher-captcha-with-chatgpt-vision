import base64
import os
import sqlite3
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
import pickle

load_dotenv()
DATABASE_NAME = os.getenv("DATABASE_NAME")
# OpenAI API Key
api_key = os.getenv("OPENAI_API_KEY")


# Function to encode the image
def encode_image():
    encoded_image_question_pairs = []
    answer_list = []

    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT image, question, answer FROM captchas")
        for image_data, question, answer in cursor.fetchall():
            encoded_image = base64.b64encode(image_data).decode("utf-8")
            encoded_image_question_pairs.append((encoded_image, question))
            answer_list.append(answer)

    return encoded_image_question_pairs, answer_list


def request_completion(base64_image, question, prompt):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
    }

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{prompt} {question}"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
        "max_tokens": 300,
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
    )

    return response.json()


def calculate_cosine_similarity(text_list1, text_list2):
    combined_texts = text_list1 + text_list2

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(combined_texts)

    similarities = []
    for i in range(len(text_list1)):
        similarity = cosine_similarity(
            tfidf_matrix[i], tfidf_matrix[len(text_list1) + i]
        )
        similarities.append(similarity[0][0])

    average_similarity = sum(similarities) / len(similarities)

    return similarities, average_similarity


def save_data_with_pickle(data, filename):
    with open(filename, "wb") as file:
        pickle.dump(data, file)


def save_record(prompt, average_similarity):
    data_to_save = {"prompt": prompt, "average_similarity": average_similarity}
    file_path = "/Users/hankyuhong/PycharmProjects/decipher-captcha-with-chatgpt-vision/decipher/data"
    file_name = f"{prompt}, {round(average_similarity * 100, 4)}.pkl"
    os.makedirs(file_path, exist_ok=True)
    full_path = os.path.join(file_path, file_name)
    save_data_with_pickle(data_to_save, full_path)


def main():
    prompt = "제시한 이미지를 기반으로 단답형으로 단위 없이 답만 적어주시오. 단 지역명은 ~동, ~군, ~구 등의 단위를 포함하여 적어주시오. 또한 질문에 [?]로 빈칸이 있는경우 빈칸에 대한 답만 적으시오. 몇개의 종류인지 묻는 질문의 경우 종류의 수만 적으시오."
    response_answer_list = []
    data_set, answer_list = encode_image()
    for i, (image, question) in enumerate(data_set):
        if i >= 50:
            break
        response = request_completion(image, question, prompt)
        response_content = response["choices"][0]["message"]["content"]
        print("Response Content:", response_content)
        response_answer_list.append(response_content)
    similarities, average_similarity = calculate_cosine_similarity(
        answer_list[:50], response_answer_list
    )
    print("Answer List:", answer_list[:50])
    print("Similarities:", similarities)
    print("Average Similarity:", average_similarity)

    save_record(prompt, average_similarity)


if __name__ == "__main__":
    main()
