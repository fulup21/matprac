from sk import mujklic
import openai
openai.api_key=mujklic

completion = openai.chat.completions.create(model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Write a haiku about python."
        }
    ]
)

print(completion.choices[0].message.content)