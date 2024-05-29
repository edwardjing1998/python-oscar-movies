from openai import OpenAI
import re
import streamlit as st
from prompts import get_system_prompt

st.title("☃️ Frosty")

# Initialize the chat messages history
client = OpenAI(api_key=st.secrets.OPENAI_API_KEY)
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]

# Prompt for user input and save
prompt = st.chat_input()
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

def make_video_link(cloud_url, file_path):
    full_url = f"{cloud_url}/{file_path}"
    return f'<a href="{full_url}" target="_blank">Watch Video</a>'

def make_entity_link(entity_name):
    # Generates an HTML link that triggers a search on ChatGPT for the movie description
    return f'<a href="#" onclick="triggerChatGPT(\'{entity_name}\')">{entity_name}</a>'

def triggerChatGPT(entity_name):
    # This function triggers a new ChatGPT response based on the entity name
    st.session_state.messages.append({"role": "user", "content": entity_name})
    generate_response()

def display_results_with_links(results):
    if 'CLOUD_FRONT_URL' in results.columns and 'MOVIE_FILE_IN_S3' in results.columns:
        results['video_link'] = results.apply(lambda row: make_video_link(row['CLOUD_FRONT_URL'], row['MOVIE_FILE_IN_S3']), axis=1)
        results['ENTITY_NAME'] = results['ENTITY_NAME'].apply(make_entity_link)
        if 'ENTITY_NAME' not in results.columns:
            results.insert(0, 'ENTITY_NAME', 'Unknown')  # Ensure ENTITY_NAME is always included
        columns_to_show = ['ENTITY_NAME', 'video_link'] + [col for col in results.columns if col not in ['ENTITY_NAME', 'CLOUD_FRONT_URL', 'MOVIE_FILE_IN_S3', 'video_link']]
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
            display_results_with_links(message["results"])

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
        display_results_with_links(message["results"])

generate_response() if st.session_state.messages[-1]["role"] != "assistant" else None

