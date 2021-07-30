from typing import List
from autograder.box_extractor import box_extraction
from autograder.character_predictor import predict
from autograder.spelling_corrector import fix_spellings
from autograder.text_similarity import check_similarity, get_marks

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
import numpy as np
import cv2

app = FastAPI(
    title="Auto-Grader",
    version="1.0",
    description="Automatically grades answer sheets",
)


def auto_grade(defined_answers, image_location, output_location):
    answers, coordinates = box_extraction(image_location, output_location)
    if len(answers) == 380:

        locations = []
        prev = 0
        print(
            answers.shape
        )  # 16 cells x 2 rows x 10 answers = 360 boxes x (28 x 28) pixels
        for n in range(10):  # all questions
            sentence = ""
            answer = answers[38 * n : 38 * (n + 1)]  # individual answer(2 rows)
            for i in range(38):  # boxes of a answer
                box = answer[i]
                sum_pix = 0
                for pixel in box:  #  pixel of the box
                    if pixel != 0:
                        sum_pix = sum_pix + 1
                # do nothing when char is detected in the box, counter i will increase. When and empty
                # box is detected after some character boxes, pix < 30
                if sum_pix < 30 or i == 37:
                    word_array = answer[prev:i].reshape(-1, 28, 28, 1)
                    if word_array.shape[0] > 1:
                        try:
                            pred = predict(word_array)
                            if i < 16:
                                sentence = sentence + "".join(pred) + " "
                            else:
                                sentence = "".join(pred) + " " + sentence
                        except:
                            print(word_array.shape)
                    prev = i + 1

            print(n + 1, sentence[::-1])

            new_words = []
            for answer in defined_answers[n]:
                words = answer.split()
                for word in words:
                    new_words.append(word.lower())

            query = fix_spellings(sentence[::-1].lower(), new_words)

            marks = []

            if query != "":
                print(query)
                cos_scores = check_similarity(defined_answers[n], query)
                m = get_marks(cos_scores, 5, (0.45, 0.85))
                print("Marks: ", "%.2f" % m)
                marks.append(m)
            else:
                print("Marks: ", "0.00")
                marks.append(0.0)
            return marks


@app.get("/")
async def index():
    return {"message": "Auto-Grader is online"}

class Answers(BaseModel):
    answers: List[str]

class Grade(BaseModel):
    ans_1: Answers
    ans_2: Answers
    ans_3: Answers
    ans_4: Answers
    ans_5: Answers
    ans_6: Answers
    ans_7: Answers
    ans_8: Answers
    ans_9: Answers
    ans_10: Answers


@app.post("/grade")
async def index(grade: Grade, file: UploadFile = File(...)):
    extension = file.filename.split(".")[-1] in ("jpg", "jpeg", "png", "JPG", "PNG")
    if not extension:
        raise HTTPException(
            status_code=400, detail="File must be an image, in jpg or png format!"
        )

    image = await file.read()
    nparr = np.fromstring(image, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    marks = auto_grade(grade., img)
    return {"marks": marks}
