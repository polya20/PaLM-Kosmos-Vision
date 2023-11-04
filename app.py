import streamlit as st
import extra_streamlit_components as stx
import requests
from io import BytesIO
import replicate
from llama_index.llms.palm import PaLM
from llama_index import ServiceContext, VectorStoreIndex, Document
from llama_index.memory import ChatMemoryBuffer
import os
import datetime

# Set up the title of the application.
st.title("Image Captioning and Chat")

# Initialize the cookie manager
cookie_manager = stx.CookieManager()

# Function to get image caption via Kosmos2.
@st.cache_data
def get_image_caption(image_data):
    input_data = {
        "image": image_data,
        "description_type": "Brief"
    }
    output = replicate.run(
        "lucataco/kosmos-2:3e7b211c29c092f4bcc8853922cc986baa52efe255876b80cac2c2fbb4aff805",
        input=input_data
    )
    # Split the output string on the newline character and take the first item
    text_description = output.split('\n\n')[0]
    return text_description

# Function to create the chat engine.
@st.cache_resource
def create_chat_engine(img_desc, api_key):
    llm = PaLM(api_key=api_key)
    service_context = ServiceContext.from_defaults(llm=llm)
    doc = Document(text=img_desc)
    index = VectorStoreIndex.from_documents([doc], service_context=service_context)
    chatmemory = ChatMemoryBuffer.from_defaults(token_limit=1500)
    
    chat_engine = index.as_chat_engine(
        chat_mode="context",
        system_prompt=(
            f"You are a chatbot, able to have normal interactions, as well as talk. "
            "You always answer in great detail and are polite. Your responses always descriptive. "
            "Your job is to talk about an image the user has uploaded. Image description: {img_desc}."
        ),
        verbose=True,
        memory=chatmemory
    )
    return chat_engine

# Clear chat function
def clear_chat():
    if "messages" in st.session_state:
        del st.session_state.messages
    if "image_file" in st.session_state:
        del st.session_state.image_file

# Callback function to clear the chat when a new image is uploaded
def on_image_upload():
    clear_chat()        

# Add a clear chat button
if st.button("Clear Chat"):
    clear_chat()        

# Image upload section.
image_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"], key="uploaded_image", on_change=on_image_upload)
if image_file:
    # Display the uploaded image at a standard width.
    st.image(image_file, caption='Uploaded Image.', width=200)
    # Process the uploaded image to get a caption.
    image_data = BytesIO(image_file.getvalue())
    img_desc = get_image_caption(image_data)
    st.write(f"Image description: {img_desc}")

    # Initialize the chat engine with the image description.
    chat_engine = create_chat_engine(img_desc, os.environ["GOOGLE_API_KEY"])

# Initialize session state for messages if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle new user input
user_input = st.chat_input("Ask me about the image:", key="chat_input")
if user_input:
    # Retrieve the message count from cookies
    message_count = cookie_manager.get(cookie='message_count')
    if message_count is None:
        message_count = 0
    else:
        message_count = int(message_count)

    # Check if the message limit has been reached
    if message_count >= 20:
        st.error("Notice: The maximum message limit for this demo version has been reached.")
    else:
        # Append user message to the session state
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(user_input)

        # Call the chat engine to get the response if an image has been uploaded
        if image_file:
            # Get the response from your chat engine
            response = chat_engine.chat(user_input)

            # Append assistant message to the session state
            st.session_state.messages.append({"role": "assistant", "content": response})

            # Display the assistant message
            with st.chat_message("assistant"):
                st.markdown(response)
        
        # Increment the message count and update the cookie
        message_count += 1
        cookie_manager.set('message_count', str(message_count), expires_at=datetime.datetime.now() + datetime.timedelta(days=30))



# Set Replicate and Google API keys
os.environ['REPLICATE_API_TOKEN'] = st.secrets['REPLICATE_API_TOKEN']
os.environ["GOOGLE_API_KEY"] = st.secrets['GOOGLE_API_KEY']