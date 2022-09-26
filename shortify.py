from datetime import datetime
import json
import os
import time
from typing import List

import openai
from dotenv import load_dotenv
from newspaper import Article
from ratelimit import limits
from textwrap import wrap

load_dotenv()

# Load your API key from an environment variable or secret management service
openai.api_key = os.getenv("OPENAI_API_KEY")


@limits(calls=24, period=60)
def completion(prompt, stop: List[str] = None):
    # time.sleep(5.0)
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=prompt,
        max_tokens=512,
        temperature=0.7,
        top_p=0.9,
        frequency_penalty=0.5,
        presence_penalty=0.0,
        stop=stop or [],
    )
    return response.choices[0].text


def shortify_part(title, known: List[str], questions: List[str], next_part, fraction_done):
    prompt = f"""
I'm part way through reading the document named "{title}".  I've read {fraction_done*100:.0f}% of it so far and here's what I already know:
{json.dumps(known)}

I have these outstanding questions:
{json.dumps(questions)}

Here is the next part to read:
{next_part}

---

Next, answer the following questions about the new part I just read:
Q1: Do I understand the part? (boolean)
Q2: What did I learn from the part? (string)
Q3: List any question I have. (array)
Q4: List any important key points from the part.  These should make sense out of context. (array)

```json
{{
"A1":"""
    attempts = 5
    for _ in range(attempts):
        try:
            response = completion(prompt, stop=["```"])
            response = response.strip()
            if not response.endswith("}"):
                response += "}"
            response = json.loads(f"{{\"A1\": {response}")
            assert response["A2"] is not None and isinstance(response["A2"], str)
            assert response["A3"] is not None and all(isinstance(el, str) for el in response["A3"])
            assert response["A4"] is not None and all(isinstance(el, str) for el in response["A4"])
            print(f"Finished part. {fraction_done*100:.0f}% done.")
            return [
                str(response["A1"]).lower().strip() in ['true', 'yes'],
                response["A2"],
                response["A3"],
                response["A4"],
            ]
        except json.JSONDecodeError:
            print("JSONDecodeError", fraction_done)
            continue
        except AssertionError:
            print("AssertionError", fraction_done)
            continue




# title = "Text Summarizer Using Abstractive and Extractive Method"
# input = """
# To reduce length, complexity, and retaining some of the essential qualities of the original document, will go for summarizer. Titles, key words, tables-of-contents and abstracts might all be considered as the forms of summary. In a full text document, abstract of that document plays role as a summary of that particular document. They are intermediates between document‟s titles and its full text that is useful for rapid relevance and quick assessment of the document. Autosummarization is a technique generates a summary of any document, provides briefs of big documents, etc.
#
# There is an abundance of text material available on the internet. However, usually the Internet provides more information than is needed. It is very difficult for human beings to manually summarize large documents of text. Therefore, a twofold problem is encountered. Searching for relevant documents through an overwhelming number of documents available, and absorbing a large quantity of relevant information. The goal of automatic text summarization is condensing the source text into a shorter version preserving its information content and overall meaning. A good summary system should reflect the diverse topics of the document while keeping redundancy to a minimum.
#
# Microsoft Word‟s AutoSummarize function is a simple example of text summarization. Text Summarization methods can be classified into extractive and abstractive summarization. An extractive summarization [1] method consists of selecting important sentences, paragraphs etc. from the original document and concatenating them into shorter form. The importance of sentences is decided based on statistical and linguistic features of sentences. An Abstractive summarization [2] attempts to develop an understanding of the main concepts in a document and then express those concepts in clear natural language. It uses linguistic methods [3] to examine and interpret the text and then to find the new concepts and expressions to best describe it by generating a new shorter text that conveys the most important information from the original text document.
# """
questions = []
question_set = set()
known = []
known_set = set()
learned = []
understood = []


url = "https://docs.spring.io/spring-framework/docs/5.0.0.RC2/spring-framework-reference/overview.html"
article = Article(url=url)
article.download()
article.parse()
input = article.html
title = article.title


# exit()

MAX_PART_LENGTH = 4000

parts = wrap(input, MAX_PART_LENGTH)
for i, part in enumerate(parts):
    try:
        new_understood, new_learned, new_questions, new_known = shortify_part(title, list(known), list(questions), part, i / len(parts))
        for nk in new_known:
            if nk not in map(lambda k: k.strip(), known_set):
                known.append(nk)
                known_set.add(nk)
        for nq in map(lambda q: q.strip(), new_questions):
            if nq not in question_set:
                questions.append(nq)
                question_set.add(nq)
        learned.append(new_learned)
        understood.append(new_understood)
    except Exception as e:
        print(e, part)
        continue

print(known)
print(questions)
print(learned)
print(understood)

result = {
    "title": title,
    "url": url or "",
    "article": input,
    "part_lengths": [len(part) for part in parts],
    "summary": {
        "key points": list(known),
        "questions": list(questions),
        "learned": learned,
        "parts understood": understood,
    }
}

with open(f"result_{datetime.now().strftime('%Y-%m-%d %H.%M.%S')}.json", "w") as f:
    json.dump(result, f, indent=4)

exit()
# article = Article(url="https://adamtooze.substack.com/p/chartbook-153-the-south-asian-polycrisis")
# article = Article(url="https://gizmodo.com/ncis-whistleblower-military-data-broker-cymru-wyden-1849564984")
# article = Article(url="https://www.rfc-editor.org/rfc/rfc7530.html")
# article = Article(url="https://distill.pub/2017/aia/")
# article = Article(url="https://www.redhat.com/en/blog/balancing-if-it-aint-broke-dont-fix-it-vs-release-early-and-often")


article.download()
# print(article.html)
# exit()
article.parse()

# print(article.text)

paragraphs = article.text.split("\n")

parts = [[]]
MAX_PART_LENGTH = 8000
for paragraph in paragraphs:
    if sum(map(len, parts[-1])) + len(paragraph) > MAX_PART_LENGTH:
        parts[-1] = "\n".join(parts[-1])
        parts.append([])

    parts[-1].append(paragraph)

parts[-1] = "\n".join(parts[-1])

short_parts = []
for part in parts:
    try:
        short_parts.append(shortify(part))
    except openai.error.RateLimitError as e:
        print(e)
        time.sleep(60.0)
        short_parts.append(shortify(part))

if len(short_parts) == 1:
    print("\n\nFINAL VERSION:\n\n")
    print(short_parts[0])
    exit()

short_version = shortify("\n".join(short_parts))

print("\n\nFINAL VERSION:\n\n")

print(short_version)
