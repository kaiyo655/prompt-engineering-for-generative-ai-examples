import asyncio
from langchain.chat_models.openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter
from content_collection import collect_serp_data_and_extract_text_from_webpages
from custom_summarize_chain import create_all_summaries, DocumentSummary
from expert_interview_agent import AgentSetup
from article_outline_generation import BlogOutlineGenerator
from article_generation import ContentGenerator
import gradio as gr
import os

os.environ["SERPAPI_API_KEY"] = "SET_THIS_API_KEY"


def get_summary(topic):
    # Create a new event loop for this task
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)

    # Now run the asynchronous function until completion
    try:
        result = new_loop.run_until_complete(async_get_summary(topic))
    finally:
        new_loop.close()

    return result


async def async_get_summary(topic):
    # Extract content from webpages into LangChain documents:
    text_documents = collect_serp_data_and_extract_text_from_webpages(topic=topic)

    # Create summaries using LLM:
    llm = ChatOpenAI(temperature=0)
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=1500, chunk_overlap=400
    )
    parser = PydanticOutputParser(pydantic_object=DocumentSummary)
    summaries = await create_all_summaries(text_documents, parser, llm, text_splitter)

    # Expert Interview Questions:
    agent = AgentSetup(topic=topic)
    document_summaries_message = (
        f"document_summaries: {[s.dict() for s in summaries]}"
        f"topic: {topic}"
        f"---"
        f"Use the above to make interview questions, then I want to answer them."
    )
    interview_questions = agent.run(document_summaries_message)

    return text_documents, summaries, interview_questions


def generate_content(
    topic,
    text_documents,
    summaries,
):
    # General Article Outline:
    blog_outline_generator = BlogOutlineGenerator(topic=topic)
    questions_and_answers = blog_outline_generator.questions_and_answers
    outline_result = blog_outline_generator.generate_outline(summaries)

    # Article Text Generation:
    content_gen = ContentGenerator(
        topic=topic, outline=outline_result, questions_and_answers=questions_and_answers
    )
    content_gen.split_and_vectorize_documents(text_documents)
    generated_text = content_gen.generate_blog_post()

    # Placeholder for image and prompt generation:
    generated_image = None
    generated_prompt = None

    return generated_text, generated_image, generated_prompt


with gr.Blocks() as demo:
    with gr.Row():
        topic = gr.Textbox(label="Topic", scale=85, value="Memetics")
        summarize_btn = gr.Button("Summarize", scale=15)

    with gr.Row():
        summaries = gr.Textbox(label="Summary", lines=10)

    with gr.Row():
        interview_questions = gr.Textbox(label="Questions", lines=20)
        interview_answers = gr.Textbox(label="Answers", lines=20)
        text_documents = gr.Textbox(label="Text Documents", lines=20)

    with gr.Row():
        summarize_btn.click(
            fn=get_summary,
            inputs=[topic],
            outputs=[summaries, interview_questions, text_documents],
        )

        clear_btn = gr.Button("Clear", scale=15)
        generate_btn = gr.Button("Generate", scale=30)

    with gr.Row():
        with gr.Column():
            generated_content = gr.Textbox(label="Content", lines=50)
            generated_image = gr.Image(shape=(1200, 630))
            generated_prompt = gr.Textbox(label="Prompt")

        generate_btn.click(
            fn=generate_content,
            inputs=[topic, summaries, text_documents],  # Changed from 'summary_text'
            outputs=[generated_content, generated_image, generated_prompt],
        )

        # Reset the UI elements to default
        clear_btn.click(
            fn=lambda: ("", "", "", "", "", "", None, ""),  # Matching the output count
            inputs=[],
            outputs=[
                topic,
                summaries,
                text_documents,
                interview_questions,
                interview_answers,
                generated_content,
                generated_image,
                generated_prompt,
            ],
        )

demo.launch()