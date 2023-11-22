import gradio as gr
import base64
import os
import sqlite3
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
from difflib import Differ
from openai import OpenAI
from PIL import Image
from io import BytesIO

load_dotenv()
client = OpenAI()


def encode_image(image_data):
    encoded_image = base64.b64encode(image_data).decode("utf-8")
    return encoded_image


def request_completion(image_data, question, prompt, max_token, detail):
    response = client.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{prompt} {question}"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encode_image(image_data)}",
                            "detail": detail,
                        },
                    },
                ],
            }
        ],
        max_tokens=int(max_token),
    )
    return response.choices[0].message.content


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


def fetch_data(start, end):
    data_set = []
    with sqlite3.connect(os.getenv("DATABASE_NAME")) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT image, question, answer FROM captchas WHERE answer IS NOT NULL LIMIT ?, ?",
            (start, end),
        )
        for image_data, question, answer in cursor.fetchall():
            data_set.append((image_data, question, answer))
    return data_set


def decipher_captcha(start, end, prompt, is_high_detail, max_token):
    completions = []
    data_set = fetch_data(start, end)

    for data in data_set:
        detail = "high" if is_high_detail else "low"
        response = request_completion(data[0], data[1], prompt, max_token, detail)
        completions.append(response)

    similarities, average_similarity = calculate_cosine_similarity(
        [answer for _, question, answer in data_set], completions
    )
    questions_answers = [[question, answer] for _, question, answer in data_set]

    does_contain_answer = []
    for completion, answer in zip(completions, [answer for _, _, answer in data_set]):
        does_contain_answer.append(answer in completion)

    hidden_table_result = []
    table_result = []
    for data, qa, completion, similarity, does_contain in zip(
        data_set,
        questions_answers,
        completions,
        [similarity * 100 for similarity in similarities],
        does_contain_answer,
    ):
        image_data = encode_image(data[0])
        hidden_table_result.append(qa + [completion, similarity, does_contain, image_data])
        table_result.append(qa + [completion, similarity, does_contain])

    return average_similarity * 100, hidden_table_result, table_result


def diff_texts(text1, text2):
    d = Differ()
    return [
        (token[2:], token[0] if token[0] != " " else None)
        for token in d.compare(text1, text2)
    ]


def open_image(base64_image):
    image = Image.open(BytesIO(base64.b64decode(base64_image)))
    return image


def select_table_row(evt: gr.SelectData, data):
    return diff_texts(
        data.iloc[evt.index[0]]["Answer"], data.iloc[evt.index[0]]["Completion"]
    ), open_image(data.iloc[evt.index[0]]["Image Data"])


def save_data(data):
    data.to_excel("data.xlsx")


with gr.Blocks() as demo:
    with gr.Row():
        with gr.Column():
            prompt_text = gr.Textbox(label="Prompt", lines=5)
            is_high_detail_checkbox = gr.Checkbox(label="High Detail")
            max_token_text = gr.Number(label="Max Token", value=300)
            start_number = gr.Number(label="Start Index", value=0)
            end_number = gr.Number(label="Count", value=10)
            generate_button = gr.Button("Decipher")

            gr.Examples(
                examples=[
                    "제시한 이미지를 기반으로 단답형으로 단위 없이 답만 적어주시오. 단 지역명은 ~동, ~군, ~구 등의 단위를 포함하여 적어주시오. 또한 질문에 [?]로 빈칸이 있는경우 빈칸에 대한 답만 적으시오. 몇개의 종류인지 묻는 질문의 경우 종류의 수만 적으시오."
                ],
                inputs=[prompt_text],
                label="Prompt Examples",
            )

        with gr.Column():
            average_similarity_texbox = gr.Textbox(
                label="Average Similarity", interactive=False
            )
            hidden_table = gr.Dataframe(
                headers=[
                    "Question",
                    "Answer",
                    "Completion",
                    "Similarity",
                    "Does Completion Contain Answer?",
                    "Image Data",
                ],
                datatype=["str", "str", "str", "number", "bool", "str"],
                visible=False,
            )
            table = gr.Dataframe(
                headers=[
                    "Question",
                    "Answer",
                    "Completion",
                    "Similarity",
                    "Does Completion Contain Answer?",
                ],
                datatype=["str", "str", "str", "number", "bool"],
                interactive=False,
            )

            highlighted_text = gr.HighlightedText(
                label="Diff",
                combine_adjacent=True,
                show_legend=True,
                color_map={"+": "red", "-": "green"},
            )
            img = gr.Image()
            save_button = gr.Button("Save")

        table.select(
            fn=select_table_row, inputs=[hidden_table], outputs=[highlighted_text, img]
        )

        generate_button.click(
            fn=decipher_captcha,
            inputs=[
                start_number,
                end_number,
                prompt_text,
                is_high_detail_checkbox,
                max_token_text,
            ],
            outputs=[average_similarity_texbox, hidden_table, table],
        )

        save_button.click(
            fn=save_data,
            inputs=[table],
        )

demo.launch()
