from openai import OpenAI
import re
import streamlit as st
import requests
from prompts import get_system_prompt

st.title("☃️ Frosty")

# Function to create clickable links
def make_video_link(cloud_url, file_path):
    full_url = f"{cloud_url}/{file_path}"
    return f'<a href="{full_url}" target="_blank">Watch Video</a>'

# Function to create clickable name links
def make_name_link(name):
    return f'<a href="javascript:fetchDescription(\'{name}\');">{name}</a>'

# Function to display results with video links and name links
def display_results_with_links(results):
    if 'CLOUD_FRONT_URL' in results.columns and 'MOVIE_FILE_IN_S3' in results.columns:
        results['video_link'] = results.apply(
            lambda row: make_video_link(row['CLOUD_FRONT_URL'], row['MOVIE_FILE_IN_S3']), axis=1)
        if 'ENTITY_NAME' in results.columns:
            results['ENTITY_NAME'] = results['ENTITY_NAME'].apply(make_name_link)
        else:
            results.insert(0, 'ENTITY_NAME', 'Unknown')  # Ensure ENTITY_NAME is always included
        columns_to_show = ['ENTITY_NAME', 'video_link'] + [col for col in results.columns if col not in ['ENTITY_NAME', 'CLOUD_FRONT_URL', 'MOVIE_FILE_IN_S3', 'video_link']]
        html = results[columns_to_show].to_html(escape=False, index=False)
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.dataframe(results)

def run_frosty():
    # Initialize the chat messages history if not already done
    if "client" not in st.session_state:
        st.session_state.client = OpenAI(api_key=st.secrets.OPENAI_API_KEY)
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]

    # Check if a movie was selected
    selected_movie = st.experimental_get_query_params().get('selected_movie')
    if selected_movie:
        selected_movie = int(selected_movie[0])
        movie_name = st.session_state.results.iloc[selected_movie]['ENTITY_NAME']
        st.session_state.messages.append({"role": "user", "content": f"Tell me about the movie {movie_name}"})

    # Prompt for user input and save
    prompt = st.chat_input("Your message:", key="chat_input")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

    # Display the existing chat messages
    for message in st.session_state.messages:
        if message["role"] == "system":
            continue
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if "results" in message:
                display_results_with_links(message["results"])

    # Generate a new response and handle SQL queries
    if st.session_state.messages and st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            response = ""
            resp_container = st.empty()
            for delta in st.session_state.client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                    stream=True,
            ):
                response += (delta.choices[0].delta.content or "")
                resp_container.markdown(response)

            message = {"role": "assistant", "content": response}
            st.session_state.messages.append(message)

            # Parse the response for a SQL query and execute if available
            sql_match = re.search(r"```sql\n(.*)\n```", response, re.DOTALL)
            if sql_match:
                sql = sql_match.group(1)
                conn = st.connection("snowflake")
                message["results"] = conn.query(sql)
                st.session_state.results = message["results"]
                display_results_with_links(message["results"])

# Add a button to trigger the application
if st.button('Run Frosty', key="run_frosty_button"):
    st.session_state.run_frosty_triggered = True

# Ensure the session state persists and shows the existing chat even when button is not clicked
if "run_frosty_triggered" in st.session_state:
    run_frosty()

# JavaScript to handle fetching the movie description
st.markdown("""
<script>
function fetchDescription(movieName) {
    const chatgpt_url = 'https://api.openai.com/v1/engines/davinci-codex/completions';
    const data = {
        prompt: `Tell me about the movie ${movieName}`,
        max_tokens: 100,
        temperature: 0.5
    };

    fetch(chatgpt_url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {st.secrets.OPENAI_API_KEY}'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        const description = data.choices[0].text;
        alert(`Description of ${movieName}: ${description}`);
    })
    .catch(error => console.error('Error:', error));
}
</script>
""", unsafe_allow_html=True)


