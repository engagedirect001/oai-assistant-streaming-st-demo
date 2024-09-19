
"""
app.py
"""
import streamlit as st
import os
import json
from openai import OpenAI
from openai.types.beta.assistant_stream_event import ThreadMessageDelta
from openai.types.beta.threads.text_delta_block import TextDeltaBlock
from tavily import TavilyClient

# Initialize OpenAI and Tavily clients
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
TAVILY_API_KEY = st.secrets["TAVILY_API_KEY"]
ASSISTANT_ID = st.secrets["ASSISTANT_ID"]

client = OpenAI(api_key=OPENAI_API_KEY)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)

# Function to perform Tavily search
def tavily_search(query):
    search_result = tavily_client.get_search_context(query, search_depth="advanced", max_tokens=8000)
    return search_result

# Initialise session state to store conversation history locally to display on UI
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Title
st.title("Sales Team - Co Pilot")

# Display messages in chat history
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Textbox and streaming process
if user_query := st.chat_input("Ask me a question"):

    # Create a new thread if it does not exist
    if "thread_id" not in st.session_state:
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id

    # Display the user’s query
    with st.chat_message("user"):
        st.markdown(user_query)

    # Store the user’s query into the history
    st.session_state.chat_history.append({"role": "user", "content": user_query})

    # Check if a Tavily search is needed
    if "search" in user_query.lower():
        search_result = tavily_search(user_query)
        with st.chat_message("assistant"):
            st.markdown(f"Here are the search results: {search_result}")
        st.session_state.chat_history.append({"role": "assistant", "content": f"Search Results: {search_result}"})
    else:
        # Add user query to the thread
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=user_query
        )

        # Stream the assistant’s reply
        with st.chat_message("assistant"):
            stream = client.beta.threads.runs.create(
                thread_id=st.session_state.thread_id,
                assistant_id=ASSISTANT_ID,
                stream=True
            )

            # Empty container to display the assistant’s reply
            assistant_reply_box = st.empty()

            # A blank string to store the assistant’s reply
            assistant_reply = ""

            # Iterate through the stream
            for event in stream:
                # Here, we only consider if there’s a delta text
                if isinstance(event, ThreadMessageDelta):
                    if isinstance(event.data.delta.content[0], TextDeltaBlock):
                        # empty the container
                        assistant_reply_box.empty()
                        # add the new text
                        assistant_reply += event.data.delta.content[0].text.value
                        # display the new text
                        assistant_reply_box.markdown(assistant_reply)

            # Once the stream is over, update chat history
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_reply})
