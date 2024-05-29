from openai import OpenAI
import re
import streamlit as st
from prompts import get_system_prompt
import requests

st.title("☃️ Frosty")

# Initialize the chat messages history
client = OpenAI(api_key=st.secrets.OPENAI_API_KEY)
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]

# Function to call OpenAI API
def query_chatgpt(prompt, api_key):
    url = 'https://api.openai.com/v1/chat/completions'
    data = {
        "model": "gpt-4-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100,
        "temperature": 0.5
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()

# Function to handle the button click
def on_button_click(entity_name):
    api_key = st.secrets["OPENAI_API_KEY"]
    prompt = f"Tell me something about {entity_name}, which was awarded in OSCAR"
    result = query_chatgpt(prompt, api_key)
    st.write("API Response:", result)  # Log the entire API response for debugging
    choices = result.get("choices", [])
    if choices:
        description = choices[0].get("message", {}).get("content", "No description found.")
    else:
        description = "No description found."
    st.write(f"Description of {entity_name}: {description}")

# Prompt for user input and save
prompt = st.chat_input()
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

def make_video_link(cloud_url, file_path):
    full_url = f"{cloud_url}/{file_path}"
    return f'<a href="{full_url}" target="_blank">Watch Video</a>'

def display_results_with_buttons(results):
    if 'CLOUD_FRONT_URL' in results.columns and 'MOVIE_FILE_IN_S3' in results.columns:
        results['video_link'] = results.apply(lambda row: make_video_link(row['CLOUD_FRONT_URL'], row['MOVIE_FILE_IN_S3']), axis=1)
        columns_to_show = ['ENTITY_NAME', 'video_link'] + [col for col in results.columns if col not in ['ENTITY_NAME', 'CLOUD_FRONT_URL', 'MOVIE_FILE_IN_S3', 'video_link']]
        for index, row in results.iterrows():
            st.write(f"**{row['ENTITY_NAME']}**")
            st.markdown(row['video_link'], unsafe_allow_html=True)
            # Generate a unique key by combining the index and entity name
            button_key = f"button_{index}_{row['ENTITY_NAME']}"
            if st.button(f"Search for {row['ENTITY_NAME']}", key=button_key):
                on_button_click(row['ENTITY_NAME'])
        html = results[columns_to_show].to_html(escape=False, index=False)
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.dataframe(results)

for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if "results" in message:
            display_results_with_buttons(message["results"])

def generate_response():
    response = ""
    resp_container = st.empty()
    for delta in client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
            stream=True,
    ):
        response += (delta.choices[0].delta.content or "")
        resp_container.markdown(response)

    message = {"role": "assistant", "content": response}
    st.session_state.messages.append(message)
    sql_match = re.search(r"```sql\n(.*)\n```", response, re.DOTALL)
    if sql_match:
        sql = sql_match.group(1)
        conn = st.connection("snowflake")
        message["results"] = conn.query(sql)
        display_results_with_buttons(message["results"])

generate_response() if st.session_state.messages[-1]["role"] != "assistant" else None
