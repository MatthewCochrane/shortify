import os
import time

import openai
from dotenv import load_dotenv
from newspaper import Article
from ratelimit import limits

load_dotenv()

# Load your API key from an environment variable or secret management service
openai.api_key = os.getenv("OPENAI_API_KEY")


def shortify(text, max_length=512):
    prompt = f"""
My software engineering colleague asked me to summarize this article for them:
\"\"\"{text}\"\"\"

I thought it was really interesting so I summarised my takeaways for them:
\"\"\"
"""
    print(prompt)
    time.sleep(5.0)
    response = openai.Completion.create(
        engine="code-davinci-002",
        prompt=prompt,
        max_tokens=max_length,
        temperature=0.0,
        top_p=1.0,
        frequency_penalty=0.5,
        presence_penalty=0.0,
        stop=["\"\"\""],
    )
    print(response)
    return response.choices[0].text


# article = Article(url="https://adamtooze.substack.com/p/chartbook-153-the-south-asian-polycrisis")
# article = Article(url="https://gizmodo.com/ncis-whistleblower-military-data-broker-cymru-wyden-1849564984")
# article = Article(url="https://www.rfc-editor.org/rfc/rfc7530.html")
article = Article(url="https://distill.pub/2017/aia/")
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
