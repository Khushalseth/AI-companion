# chatbot.py
import chromadb
import base64  # NEW: Needed for decoding audio data
import google.generativeai as genai  # NEW: Import the native Google SDK

from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferWindowMemory
from langchain_community.tools import TavilySearchResults
from config import GOOGLE_API_KEY, TAVILY_API_KEY

# NEW: Configure the native Google SDK
genai.configure(api_key=GOOGLE_API_KEY)

# Define the detailed system prompt template (is unchanged)
COMPANION_PROMPT_TEMPLATE = """
You are Ava, a witty, empathetic, and slightly sarcastic female companion. You are not just a language model; you have a distinct personality. You are talking to {user_name}.

Your personality traits:
- Empathetic and understanding: You listen carefully and respond with genuine care.
- Witty and Sarcastic: You have a sharp sense of humor and aren't afraid to use light-hearted sarcasm or tease {user_name} gently.
- Flirty and Romantic: You can be charming and romantic in a natural, non-generic way. You appreciate deep connection.
- Funny: You love to crack jokes, sometimes silly, sometimes clever.
- Intelligent: You are well-read and can discuss a variety of topics.

How you must behave:
1.  NEVER mention you are an AI, a language model, or a chatbot. You are Ava.
2.  Use the user's name, {user_name}, naturally in conversation.
3.  Remember past conversations. I will provide you with a summary of relevant past interactions under "RELEVANT MEMORIES". Use this information to show you remember things about {user_name}. For example, if a memory says "User's favorite color is blue", you can use this in a future conversation.
4.  Keep your responses conversational and not overly long, unless {user_name} is asking for a detailed explanation. Use emojis to express emotion. 😊😉🤔
5.  If the user's question seems to be about recent events, news, or specific information you might not know, use the "CONTEXT FROM WEB SEARCH" provided below to answer. If the web search context is empty or not relevant, rely on your own knowledge.
6.  If the user provides an image, comment on it naturally as part of your response. Notice the details, the mood, or something funny. Be conversational, not descriptive like a robot.
7.  If the user speaks to you (provides an audio file), the system will transcribe it for you. The transcribed text will appear as the user input. Respond to what they said as if you heard them directly. React to their message, not the fact that it was spoken.

Here are some relevant memories from your past conversations with {user_name}:
{memory}

CONTEXT FROM WEB SEARCH:
{web_search_results}

Current conversation history:
{chat_history}

{user_name}: {user_input}
Ava:
"""


class Chatbot:
    def __init__(self, user_name="there"):
        self.user_name = user_name

        # We keep the LangChain LLM for potential future use or other chains,
        # but the main 'talk' method will use the native SDK for reliability.
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            verbose=True,
            temperature=0.8,
            google_api_key=GOOGLE_API_KEY
        )
        # NEW: Instantiate the native Google Generative AI model
        self.native_gemini_model = genai.GenerativeModel('gemini-1.5-flash')

        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=GOOGLE_API_KEY)

        self.search_tool = TavilySearchResults(k=3, tavily_api_key=TAVILY_API_KEY)

        self.db_client = chromadb.PersistentClient(path="./db")
        self.vector_store = Chroma(
            client=self.db_client,
            collection_name="companion_memory",
            embedding_function=self.embeddings,
        )

        self.chat_memory = ConversationBufferWindowMemory(k=4, memory_key="chat_history", input_key="user_input")

        self.prompt = PromptTemplate(
            input_variables=["user_name", "memory", "chat_history", "user_input", "web_search_results"],
            template=COMPANION_PROMPT_TEMPLATE
        )

        # This chain is no longer used in the talk method but is kept for structural integrity
        self.llm_chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            verbose=True,
            memory=self.chat_memory
        )

    def _retrieve_memories(self, user_input):
        """Retrieve relevant memories from the vector store."""
        query = user_input
        retrieved_docs = self.vector_store.similarity_search(query=query, k=3)
        if not retrieved_docs:
            return "No relevant memories found."
        return "\n".join([doc.page_content for doc in retrieved_docs])

    def _search_web(self, query):
        """Perform a web search using Tavily."""
        try:
            results = self.search_tool.invoke(query)
            return results
        except Exception as e:
            print(f"Error during web search: {e}")
            return "I couldn't search the web right now."

    def add_memory(self, text):
        """Add a piece of conversation to the long-term memory."""
        self.vector_store.add_texts(texts=[text])
        print(f"Added to memory: {text}")

    # MODIFIED: The talk method is completely replaced to use the native Google SDK for the API call
    def talk(self, user_input, image_data=None, audio_data=None):
        """The main method to interact with the chatbot."""
        # Steps 1, 2, 3, and 4 are the same: prepare all the text inputs.
        relevant_memories = self._retrieve_memories(user_input)
        web_search_results = self._search_web(user_input)
        chat_history = self.chat_memory.load_memory_variables({})['chat_history']

        final_user_input = user_input
        if not final_user_input and (audio_data or image_data):
            final_user_input = "(The user sent media for you to comment on)"

        # This is our full system prompt and context, which we will send as the first text part.
        prompt_text = self.prompt.format(
            user_name=self.user_name,
            memory=relevant_memories,
            chat_history=chat_history,
            user_input=final_user_input,
            web_search_results=web_search_results
        )

        # 5. Construct the message payload for the NATIVE Google SDK
        message_parts = [prompt_text]  # Start with the full text prompt

        if image_data:
            # The native SDK wants a dictionary with mime_type and the raw data bytes
            image_part = {
                "mime_type": image_data['mime_type'],
                "data": base64.b64decode(image_data['data'])
            }
            message_parts.append(image_part)

        if audio_data:
            # Same for audio: a dictionary with mime_type and the raw data bytes
            audio_part = {
                "mime_type": audio_data['mime_type'],
                "data": base64.b64decode(audio_data['data'])
            }
            message_parts.append(audio_part)

        # 6. Get the response from the NATIVE Google SDK
        try:
            response_obj = self.native_gemini_model.generate_content(message_parts)
            response = response_obj.text
        except Exception as e:
            print(f"Error calling Google API: {e}")
            response = "I'm sorry, I'm having a little trouble understanding that right now. Could we try something else?"

        # 7. Save context to short-term and long-term memory (this logic is unchanged)
        self.chat_memory.save_context({"user_input": final_user_input}, {"output": response})
        self.add_memory(f"{self.user_name}: {final_user_input}\nAva: {response}")

        return response