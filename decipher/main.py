import base64
import os
import sqlite3
from dotenv import load_dotenv

import requests

load_dotenv()
DATABASE_NAME = os.getenv('DATABASE_NAME')
# OpenAI API Key
api_key = os.getenv("OPENAI_API_KEY")

# Function to encode the image
def encode_image():
  encoded_image_question_pairs = []

  with sqlite3.connect(DATABASE_NAME) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT image, question FROM captchas")
    for image_data, question in cursor.fetchall():
      encoded_image = base64.b64encode(image_data).decode('utf-8')
      encoded_image_question_pairs.append((encoded_image, question))

  return encoded_image_question_pairs


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

def main():
    data_set = encode_image()
    for i, (image, question) in enumerate(data_set):
      if i >= 3:
        break
      response = request_completion(image, question, "")
      print(response)


if __name__ == "__main__":
    main()