# llm_handler.py
import os
import google.generativeai as genai
import base64

# Configure the Gemini API client
try:
    # Explicitly use the key from our .env file
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not found.")
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-flash-lite-latest')
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    model = None

def decode_attachment(attachment):
    """Decodes a base64 data URI and returns its content."""
    try:
        header, encoded = attachment['url'].split(",", 1)
        data = base64.b64decode(encoded)
        return data.decode('utf-8')
    except Exception as e:
        print(f"Error decoding attachment {attachment['name']}: {e}")
        return ""

def generate_code(brief, checks, attachments):
    """Generates code using Gemini based on the project brief."""
    if not model:
        return "<html><body><h1>Error: Gemini API not configured.</h1></body></html>"
        
    # Decode attachment content
    attachment_content = ""
    if attachments:
        for attachment in attachments:
            content = decode_attachment(attachment)
            attachment_content += f"\n\n--- Attachment: {attachment['name']} ---\n{content}\n--- End Attachment ---"

    # Construct a detailed prompt for the LLM
    prompt = f"""
    You are an expert web developer. Your task is to create a complete, self-contained 'index.html' file.
    All CSS and JavaScript must be included directly within the HTML file. Do not use external files.

    **Project Brief:**
    {brief}

    **Attachments Content:**
    {attachment_content}

    **Evaluation Checks:**
    The final application will be evaluated against these checks. Make sure the generated code passes them:
    - {'\n- '.join(checks)}

    **Instructions:**
    1.  Create a single `index.html` file.
    2.  Embed all necessary JavaScript and CSS within `<script>` and `<style>` tags.
    3.  Ensure the code is clean, functional, and directly addresses the brief and checks.
    4.  The final output should ONLY be the HTML code, nothing else. Start with `<!DOCTYPE html>` and end with `</html>`.
    """

    print("Sending prompt to Gemini...")
    try:
        response = model.generate_content(prompt)
        code = response.text.strip()
        # Clean up potential markdown code fences
        if code.startswith("```html"):
            code = code[7:]
        if code.endswith("```"):
            code = code[:-3]
        return code
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return f"<html><body><h1>Error generating code: {e}</h1></body></html>"


def update_code(brief, checks, existing_code):
    """Updates existing code using Gemini based on a new brief."""
    if not model:
        return "<html><body><h1>Error: Gemini API not configured.</h1></body></html>"
        
    prompt = f"""
    You are an expert web developer. Your task is to update an existing 'index.html' file based on new requirements.
    The updated code must remain a single, self-contained HTML file.

    **New Brief / Revision Request:**
    {brief}

    **Evaluation Checks for this Revision:**
    The updated application will be evaluated against these checks. Ensure the code passes them:
    - {'\n- '.join(checks)}

    **Existing `index.html` Code:**
    ```html
    {existing_code}
    ```

    **Instructions:**
    1.  Modify the provided HTML code to meet the new requirements.
    2.  Ensure the result is still a single, self-contained `index.html` file.
    3.  The final output should ONLY be the complete, updated HTML code. Start with `<!DOCTYPE html>` and end with `</html>`.
    """
    
    print("Sending update prompt to Gemini...")
    try:
        response = model.generate_content(prompt)
        code = response.text.strip()
        if code.startswith("```html"):
            code = code[7:]
        if code.endswith("```"):
            code = code[:-3]
        return code
    except Exception as e:
        print(f"Error calling Gemini API for update: {e}")
        return f"<html><body><h1>Error updating code: {e}</h1></body></html>"