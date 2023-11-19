import gradio as gr
import requests
from PIL import Image
from io import BytesIO
import sqlite3


conn = sqlite3.connect("../imageDatabase.db", check_same_thread=False)
c = conn.cursor()


def load_data():
    c.execute('SELECT id, image, question FROM captchas WHERE answer IS NULL')
    row = c.fetchone()
    if row:
        _id, image, question = row
        image = Image.open(BytesIO(image))
        c.execute('SELECT COUNT(*) FROM captchas')
        total = c.fetchone()[0]
        return _id, f"{_id} / {total}", image, question
    return None, None, "No more questions"


def save_and_load_next(_id, answer):
    save_msg = save_answer(_id, answer)
    return save_msg, *load_data(), ''


def save_answer(_id, answer):
    if not answer:
        return "Please enter an answer"
    c.execute('UPDATE captchas SET answer = ? WHERE id = ?', (answer, _id))
    conn.commit()
    return f"Answer saved for {_id} as {answer}"


with gr.Blocks() as demo:
    gr.Markdown("# Label CAPTCHAs")
    with gr.Row():
        with gr.Column():
            image_display = gr.Image()
            id_value = gr.Textbox(label="ID", visible=False)
            id_box = gr.Textbox(label="Current / Total", interactive=False)
            question_box = gr.Textbox(label="Question", interactive=False)
            answer_box = gr.Textbox(label="Answer")
            submit_button = gr.Button("Submit")
        with gr.Column():
            output_box = gr.Textbox(label="Result")

    submit_button.click(fn=save_and_load_next, inputs=[id_value, answer_box],
                        outputs=[output_box, id_value, id_box, image_display, question_box, answer_box])
    demo.load(fn=load_data, inputs=[], outputs=[id_value, id_box, image_display, question_box])


if __name__ == "__main__":
    demo.launch()
