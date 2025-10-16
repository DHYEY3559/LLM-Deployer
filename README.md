# LLM Code Deployment Project

This is the repository for my submission to the TDS Sep 2025 - Project 1.

It contains the source code for an automated application that can:
1.  Receive a project brief via a secure API endpoint.
2.  Use an LLM to generate web application code.
3.  Automatically create a GitHub repository, add an MIT License, and push the generated code.
4.  Enable GitHub Pages for deployment.
5.  Notify an evaluation server once the deployment is complete.
6.  Handle subsequent requests to revise and update the deployed application.

## Tech Stack

* **Backend:** Python 3 with FastAPI
* **LLM:** Gemini
* **GitHub Automation:** GitHub CLI (`gh`)
* **Deployment:** Render.com

## Setup & Usage

1.  Clone the repository.
2.  Install dependencies: `pip install -r requirements.txt`
3.  Create a `.env` file and populate it with your `API_SECRET`, `GITHUB_USER`, `GITHUB_TOKEN`, and `OPENAI_API_KEY`.
4.  Run the server locally: `uvicorn main:app --reload`
