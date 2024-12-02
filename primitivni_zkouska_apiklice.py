from sk import mujklic
import openai
openai.api_key=mujklic

completion = openai.chat.completions.create(model="gpt-4o-mini",
    messages=[
        {
            "role": "user",
            "content": "Oprav tento program: "
        }
    ]
)

print(completion.choices[0].message.content)