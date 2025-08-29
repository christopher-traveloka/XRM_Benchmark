from google import genai

client = genai.Client(
    vertexai=True, project="tvlk-shared-services-stg", location="global"
)

response = client.models.generate_content(
    model="gemini-2.5-flash", contents="Write a haiku about sunrise."
)

print(response.text)
