# Import necessary libraries
import streamlit as st
import PyPDF2
import docx
from gtts import gTTS
from pydub import AudioSegment
import os
from groq import Groq
import time
from tempfile import NamedTemporaryFile

# Function to extract text from a PDF resume
def extract_text_from_pdf(pdf_path):
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ''
            for page in reader.pages:
                text += page.extract_text()
        return text if text else "Unable to extract text from PDF."
    except Exception as e:
        return f"Error extracting text from PDF: {e}"

# Function to extract text from a DOCX resume
def extract_text_from_docx(docx_path):
    try:
        doc = docx.Document(docx_path)
        text = '\n'.join([para.text for para in doc.paragraphs])
        return text if text else "Unable to extract text from DOCX."
    except Exception as e:
        return f"Error extracting text from DOCX: {e}"

# Function to call Groq Llama model for generating the HR conversation
def generate_hr_conversation(resume_text, job_role, job_level):
    try:
        # Create a client instance for Groq
        client = Groq(
            api_key="YOUR_API_KEY",  # Replace with your Groq API key
        )

        # Define the prompt to pass to Llama3-8b-8192 model
        prompt = f"""
        You're two senior HR executives evaluating a candidate's resume for the role of {job_role}. It is a {job_level} level job.
        Here is the candidate's resume:

        {resume_text}

        Now, start a humorous conversation between 2 HRs talking to each other where you provide critical feedback, roast the resume, and suggest improvements.
        -Make the conversations in a communicative tone
        -Do not use markdown, emojis, or other formatting in your responses. Respond in a way easily spoken by text-to-speech software
        -Do not write anything in braces 
        -Do not use any emotions like (laughs) in your responses
        -The output should be like - "HR1: <text>\nHR2: <text>\n...."
        -Do not forget to suggest the improvements
        """

        # Call the Groq API for chat completion
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=True,
            stop=None
        )

        # Gather the output as chunks of text (streaming mode)
        hr_conversation = ""
        for chunk in completion:
            hr_conversation += chunk.choices[0].delta.content or ""

        return hr_conversation
    except Exception as e:
        return f"Error generating HR conversation: {e}"

# Function to convert HR text to audio using different voices for HR1 and HR2
def text_to_speech_mixed(hr_feedback, output_file="hr_feedback_combined.mp3"):
    # Split the feedback into lines
    lines = hr_feedback.split('\n')

    # Initialize an empty AudioSegment to store the combined audio
    combined_audio = AudioSegment.empty()

    # Loop through each line, generate audio based on HR1 or HR2, and concatenate
    for line in lines:
        if line.startswith("HR1:"):
            hr1_text = line.replace("HR1:", "").strip()
            if hr1_text:
                hr1_tts = gTTS(hr1_text, lang='en', slow=False)  # Default TTS for HR1
                hr1_tts.save("hr1_temp.mp3")
                hr1_audio = AudioSegment.from_mp3("hr1_temp.mp3")
                combined_audio += hr1_audio
        elif line.startswith("HR2:"):
            hr2_text = line.replace("HR2:", "").strip()
            if hr2_text:
                hr2_tts = gTTS(hr2_text, lang='en', tld='co.in', slow=False)  # Indian accent TTS for HR2
                hr2_tts.save("hr2_temp.mp3")
                hr2_audio = AudioSegment.from_mp3("hr2_temp.mp3")
                combined_audio += hr2_audio

    # Save the combined audio as a single output file
    combined_audio.export(output_file, format="mp3")
    print(f"Combined audio feedback saved as {output_file}")

    # Clean up temporary audio files
    if os.path.exists("hr1_temp.mp3"):
        os.remove("hr1_temp.mp3")
    if os.path.exists("hr2_temp.mp3"):
        os.remove("hr2_temp.mp3")

# Main Streamlit app
def main():
    st.title("Resume Feedback Generator")

    # File uploader for the resume
    uploaded_file = st.file_uploader("Upload your resume (PDF or DOCX)", type=["pdf", "docx"])
    
    # Input for job role and level
    job_role = st.text_input("Enter the job role:")
    job_level = st.selectbox("Select job level:", ["Beginner", "Intermediate", "Advanced"])

    if st.button("Generate Feedback"):
        if uploaded_file is not None and job_role:
            # Save the uploaded file temporarily
            with NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(uploaded_file.read())
                resume_path = temp_file.name

            start_time = time.time()
            # Determine file type and extract text
            if resume_path.endswith('.pdf'):
                resume_text = extract_text_from_pdf(resume_path)
            elif resume_path.endswith('.docx'):
                resume_text = extract_text_from_docx(resume_path)
            else:
                st.error("Unsupported file format. Please upload a PDF or DOCX file.")
                return

            if "Error" in resume_text:
                st.error(resume_text)  # Return the error message if extraction failed
                return

            # Generate HR conversation using Groq's Llama model
            hr_feedback = generate_hr_conversation(resume_text, job_role, job_level)

            if "Error" in hr_feedback:
                st.error(hr_feedback)  # Return the error message if generation failed
                return

            # Convert the HR feedback to speech with alternating voices
            text_to_speech_mixed(hr_feedback)

            end_time = time.time()
            st.success("Feedback generated successfully!")

            # Display the feedback
            st.subheader("HR Feedback:")
            st.text(hr_feedback)

            # Provide an audio player for the combined audio
            st.audio("hr_feedback_combined.mp3")

            st.write(f"Time taken for feedback generation: {end_time - start_time:.2f} seconds")
        else:
            st.error("Please upload a resume and enter the job role.")

if __name__ == "__main__":
    main()
