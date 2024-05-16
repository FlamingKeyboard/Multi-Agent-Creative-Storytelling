from groq import Groq
import random
import time
import sqlite3
import uuid
from datetime import datetime
import html
from bs4 import BeautifulSoup
import asyncio
import os

number_of_stories_per_model = 3
groq_api_key = os.environ["Groq_API_Key"]

# Connect to SQLite database (it creates the file if it does not exist)
conn = sqlite3.connect('database.db')
c = conn.cursor()
random.seed(time.time())

# Create tables
c.execute('''
CREATE TABLE IF NOT EXISTS Stories (
    story_id TEXT PRIMARY KEY,
    model TEXT,
    response TEXT,
    time_generated TEXT,
    rated INTEGER
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS Feedback (
    feedback_id TEXT PRIMARY KEY,
    story_id TEXT,
    model TEXT,
    response TEXT,
    positive_feedback TEXT,
    negative_feedback TEXT,
    ideas TEXT,
    contradictions TEXT,
    lore_changes TEXT,
    other_feedback TEXT,
    writing_score INTEGER,
    storytelling_score INTEGER,
    interest_score INTEGER,
    creativity_score INTEGER,
    fit_in_fallout_universe_score INTEGER,
    overall_score INTEGER,
    grade TEXT,
    FOREIGN KEY (story_id) REFERENCES Stories(story_id)
)
''')
client = Groq(
    api_key=groq_api_key,
)

models = ["mixtral-8x7b-32768", "gemma-7b-it", "llama3-8b-8192", "llama3-70b-8192"]#, "gemini-pro"]

async def improve_story(model, temp, story_content, feedback):
    counter = 0
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert on the entire Fallout universe. You know everything about every Fallout game in excruciating detail, down to every last bit. You will help the user by following instructions, making sure to use as much detail as possible."
                },
                {
                    "role": "user",
                    "content": f"Here is a story:\n{story_content}\n\nAnd here is the feedback for the story:\n{feedback}\n\nUsing the provided feedback, rewrite and improve the story. Respond ONLY with the new and improved story, and absolutely nothing else.",
                }
            ],
            model=model,
            temperature=temp
        )

        response = chat_completion.choices[0].message.content
        print(response)
        print("-"*50)
        print("\n")
        story_id = str(uuid.uuid4())
        time_generated = str(datetime.now().isoformat())

        data={
            'response': response,
            'model': model,
            'story_id': story_id,
            'time_generated': time_generated,
            'rated': 0
        }

        # Insert data into the table
        c.execute('''
        INSERT INTO Stories (model, response, story_id, time_generated, rated)
        VALUES (:model, :response, :story_id, :time_generated, :rated)
        ''', data)

        # Commit the transaction
        conn.commit()
    
    except:
        if counter < 5:
            counter += 1
            time.sleep(60*counter)

        else:
            raise Exception

def get_top_stories(n):
    c.execute(f'''
    SELECT 
        Stories.story_id,
        Stories.response
    FROM 
        Stories
        JOIN Feedback ON Stories.story_id = Feedback.story_id
    GROUP BY 
        Stories.story_id
    ORDER BY 
        AVG(Feedback.overall_score) DESC
    LIMIT ?;
    ''', (n,))
    return c.fetchall()

async def improve_top_stories(n_iterations):
    for i in range(n_iterations):
        print(f"Iteration {i + 1}")
        top_stories = get_top_stories(5)
        tasks = []
        for story in top_stories:
            story_id, story_content = story
            print(f"Getting {story_id}")
            c.execute('''
            SELECT feedback_id, response, positive_feedback, negative_feedback, ideas, contradictions, lore_changes, other_feedback
            FROM Feedback
            WHERE story_id = ?
            ORDER BY overall_score DESC
            ''', (story_id,))
            feedback = str(c.fetchall())

            for model in models:
                print(f"{model} improving {story_id}")                
                for j in range(0, 2):
                    temp = round(random.uniform(0.25, 1.0), 2)
                    task = asyncio.create_task(improve_story(model, temp, story_content, feedback))
                    tasks.append(task)
                    conn.commit()
                conn.commit()
            conn.commit()
        conn.commit()
        await asyncio.gather(*tasks)
        await rate_generated_stories()

async def generate_story(model, temp):
    counter = 0
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert on the entire Fallout universe. You know everything about every Fallout game in excrucating detail, down to every last bit. You will help the user by following instructions, making sure to use as much detail as possible."
                },
                {
                    "role": "user",
                    "content": "Write a brand new story about a new vault in the wasteland in the Fallout universe. Use as much detail as you possibly can. Make sure it is accurate to the Fallout universe, and add a good twist or surprise to the vault.",
                }
            ],
            model=model,
            temperature=temp
        )

        response = chat_completion.choices[0].message.content
        print(response)
        print("-"*50)
        print("\n")
        story_id = str(uuid.uuid4())
        time_generated = str(datetime.now().isoformat())

        data={
            'response': response,
            'model': model,
            'story_id': story_id,
            'time_generated': time_generated,
            'rated': 0
        }

        # Insert data into the table
        c.execute('''
        INSERT INTO Stories (model, response, story_id, time_generated, rated)
        VALUES (:model, :response, :story_id, :time_generated, :rated)
        ''', data)

        # Commit the transaction
        conn.commit()
    
    except:
        if counter < 5:
            counter += 1
            time.sleep(60*counter)

        else:
            raise Exception

async def generate_new_stories(number_of_stories_per_model=1):
    tasks = []
    for model in models:
        for i in range(0, number_of_stories_per_model):
            temp = round(random.uniform(0.25, 1.0), 2)
            print("-"*50)
            print(f"{model} at {temp}")
            print("-"*50)
            task = asyncio.create_task(generate_story(model, temp))
            tasks.append(task)

    await asyncio.gather(*tasks)

async def rate_story(story_id, story_model, story_content, model, temp):
    counter = 0
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": '''
                    Rate this story based on the quality of writing, story telling, how interesting, most creative, and how well it fits in the fallout universe the best. Rate each on an integer scale from 0 to 100. Be a harsh, but fair critic. The objective is to craft a story that is as good as possible and your input will help in doing so. Your scores should be honest and not inflated at all. The scores are used to measure quality, so the more accurate the scores the better. I will tip $200.
                    Respond ONLY in the following XML format, making sure to conform to perfect XML format that is well-formed and properly escaped:
                    <feedback>
                    <response>(highly detailed response giving expert English PhD professor level writing suggestions on what was good, what was bad, and what needs improvement, and how to improve it)</response>
                    <positive_feedback>(highly detailed positive constructive feedback describing everything that was good and well done.)</positive_feedback>
                    <negative_feedback>(highly detailed negative constructive feedback describing everything that was not good and not well done.)</negative_feedback>
                    <ideas>(provide a numbered list of as many high quality, highly detailed ideas as possible that fit within the Fallout universe lore)</ideas>
                    <contradictions>(a detailed list of contradictions in the story, if there are any)</contradictions>
                    <lore_changes>(a detailed list of any changes that need to be made because they do not fit in the Fallout universes lore)</lore_changes>
                    <other_feedback>(highly detailed feedback that is neither negative or positive, perhaps general suggestions or ideas.)</other_feedback>
                    <writing_score>(integer 0 to 100)</writing_score>
                    <storytelling_score>(integer 0 to 100)</storytelling_score>
                    <interest_score>(integer 0 to 100)</interest_score>
                    <creativity_score>(integer 0 to 100)</creativity_score>
                    <fit_in_fallout_universe score>(integer 0 to 100)</fit_in_fallout_universe_score>
                    <overall_score>(integer 0 to 100)</overall_score>
                    <grade>(letter or letter with a symbol on the American grade scale, for reference: 97-100, A+, 93-96, A, 90-92, A-, 87-89, B+, 83-86, B, 80-82, B-, 77-79, C+, 73-76, C, 70-72, C-, 67-69, D+, 63-66, D, 60-62, D-, 0-59, F)</grade>
                    </feedback>
                    '''
                },
                {
                    "role": "user",
                    "content": '''
                    Rate this story based on the quality of writing, story telling, how interesting, most creative, and how well it fits in the fallout universe the best. Rate each on an integer scale from 0 to 100. Be a harsh, but fair critic. The objective is to craft a story that is as good as possible and your input will help in doing so. Your scores should be honest and not inflated at all. The scores are used to measure quality, so the more accurate the scores the better. I will tip $200.
                    Respond ONLY in the following XML format, making sure to conform to perfect XML format that is well-formed and properly escaped:
                    <feedback>
                    <response>(highly detailed response giving expert English PhD professor level writing suggestions on what was good, what was bad, and what needs improvement, and how to improve it)</response>
                    <positive_feedback>(highly detailed positive constructive feedback describing everything that was good and well done.)</positive_feedback>
                    <negative_feedback>(highly detailed negative constructive feedback describing everything that was not good and not well done.)</negative_feedback>
                    <ideas>(provide a numbered list of as many high quality, highly detailed ideas as possible that fit within the Fallout universe lore)</ideas>
                    <contradictions>(a detailed list of contradictions in the story, if there are any)</contradictions>
                    <lore_changes>(a detailed list of any changes that need to be made because they do not fit in the Fallout universes lore)</lore_changes>
                    <other_feedback>(highly detailed feedback that is neither negative or positive, perhaps general suggestions or ideas.)</other_feedback>
                    <writing_score>(integer 0 to 100)</writing_score>
                    <storytelling_score>(integer 0 to 100)</storytelling_score>
                    <interest_score>(integer 0 to 100)</interest_score>
                    <creativity_score>(integer 0 to 100)</creativity_score>
                    <fit_in_fallout_universe score>(integer 0 to 100)</fit_in_fallout_universe_score>
                    <overall_score>(integer 0 to 100)</overall_score>
                    <grade>(letter or letter with a symbol on the American grade scale, for reference: 97-100, A+, 93-96, A, 90-92, A-, 87-89, B+, 83-86, B, 80-82, B-, 77-79, C+, 73-76, C, 70-72, C-, 67-69, D+, 63-66, D, 60-62, D-, 0-59, F)</grade>
                    </feedback>
                    '''
                },
                {
                    "role": "user",
                    "content": story_content,
                }
            ],
            model=model,
            temperature=temp
        )

        response = chat_completion.choices[0].message.content
        print(response)
        
        try:
            # Insert data into Feedback using BeautifulSoup
            soup = BeautifulSoup(response, 'lxml')
            feedback = soup.find('feedback')

            response_text = feedback.find('response').text
            positive_feedback = feedback.find('positive_feedback').text
            negative_feedback = feedback.find('negative_feedback').text
            ideas = feedback.find('ideas').text
            contradictions = feedback.find('contradictions').text
            lore_changes = feedback.find('lore_changes').text
            other_feedback = feedback.find('other_feedback').text
            writing_score = int(feedback.find('writing_score').text)
            storytelling_score = int(feedback.find('storytelling_score').text)
            interest_score = int(feedback.find('interest_score').text)
            creativity_score = int(feedback.find('creativity_score').text)
            fit_in_fallout_universe_score = int(feedback.find('fit_in_fallout_universe_score').text)
            overall_score = int(feedback.find('overall_score').text)
            grade = feedback.find('grade').text
            feedback_id = str(uuid.uuid4())

            c.execute('''
            INSERT INTO Feedback (story_id, feedback_id, model, response, positive_feedback, negative_feedback, ideas, contradictions, lore_changes, other_feedback, writing_score, storytelling_score, interest_score, creativity_score, fit_in_fallout_universe_score, overall_score, grade)
            VALUES (:story_id, :feedback_id, :model, :response, :positive_feedback, :negative_feedback, :ideas, :contradictions, :lore_changes, :other_feedback, :writing_score, :storytelling_score, :interest_score, :creativity_score, :fit_in_fallout_universe_score, :overall_score, :grade)
            ''', {
                'story_id': story_id,
                'feedback_id': feedback_id,
                'model': model,
                'response': response_text,
                'positive_feedback': positive_feedback,
                'negative_feedback': negative_feedback,
                'ideas': ideas,
                'contradictions': contradictions,
                'lore_changes': lore_changes,
                'other_feedback': other_feedback,
                'writing_score': writing_score,
                'storytelling_score': storytelling_score,
                'interest_score': interest_score,
                'creativity_score': creativity_score,
                'fit_in_fallout_universe_score': fit_in_fallout_universe_score,
                'overall_score': overall_score,
                'grade': grade
            })

            # Update rated in Stories
            c.execute('''
            UPDATE 
                Stories
            SET 
                rated = rated + 1
            WHERE 
                story_id = :story_id
            ''', {'story_id': story_id})

            conn.commit()

        except:
            print(f"XML formatting failed on {model}.")


    except:
        if counter < 5:
            counter += 1
            time.sleep(60*counter)

        else:
            raise Exception

async def rate_generated_stories():
    c.execute('''
    SELECT 
        * 
    FROM 
        Stories 
    WHERE 
        rated <= 30 
    ORDER BY 
        time_generated 
    DESC;
    ''')

    stories = c.fetchall()

    tasks = []
    for story in stories:
        story_id = story[0]
        story_model = story[1]
        story_content = story[2]

        for model in models:
            for i in range(0, 3):
                temp = round(random.uniform(0.25, 0.75), 2)
                task = asyncio.create_task(rate_story(story_id, story_model, story_content, model, temp))
                tasks.append(task)

    await asyncio.gather(*tasks)

async def main():
    while True:
        await generate_new_stories(number_of_stories_per_model)
        await rate_generated_stories()
        await improve_top_stories(3)  # Adjust the number of iterations as needed
        await rate_generated_stories()

if __name__ == '__main__':
    asyncio.run(main())
    conn.close()