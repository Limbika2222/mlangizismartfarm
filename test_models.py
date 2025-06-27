import google.generativeai as genai

# Correct API key
genai.configure(api_key="AIzaSyAMVb_p6I8nUx8VgwRPrXMl86F8RTt36xE")

# Use Gemini 1.5 model with v1
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

response = model.generate_content("What is smart farming?")
print(response.text)
