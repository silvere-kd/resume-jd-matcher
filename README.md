# <center>**`Project Details`**</center>

#### **Purpose**:

Tis project goal is matching a resume to a job description. A poorly aligned resume can lead to missed opportunities, even when the candidate is a strong fit. The project aims to showcase how we can make use of AI agents to help applicants tailor their resumes more strategically, uncover hidden gaps, and present a stronger case to recruiters — all with minimal effort.

A [Github repo](https://github.com/vikrambhat2/MultiAgents-with-CrewAI-ResumeJDMatcher) tackling this project exist and our goal will be to improve it by seperating the **Backend** and the **Frontend** logics.

##### **Why Split**?

 - The backend will hold business logic, agent orchestration, model calls, state, data processing, API endpoints, while the frontend focuses on the UI/UX, user interaction, session management, file upload, displaying results.
 - Scalability: Backend can scale independently of UI (and can even serve other clients)
 - Security: Sensitive logic, API keys, and resource-intensive processing are kept server-side
 - Performance: Streamlit remains snappy, while heavy lifting is offloaded to backend
 
##### **Responsibilities**

  - *<u>Backend</u>*: 
    - Expose REST API endpoints:
        - `/match`: Accepts resume + JD, returns match results and insights.
        - `/enhance`: Accepts resume + JD, returns resume improvement suggestions.
        - `/cover-letter`: Accepts resume + JD, returns a cover letter.
    - Agent orchestration: All CrewAI workflows run here.
    - Input validation, error handling.
    - PDF/text parsing if desired (or can also be handled in frontend, see below).
    - Optional: Authentication, user/session management, logging, monitoring.
    - Optional: Serve as an async queue for heavy jobs if latency is an issue (using Celery/RQ, etc.).
 
 - *<u>Frontend</u>(Streamlit)*
    - UI for uploading files, entering/pasting text.
    - Visualization: Render reports, scores, enhanced resume, cover letter, etc.
    - API client: Handles all interaction with FastAPI backend.
    - Light preprocessing: E.g., local PDF parsing if you want to send plain text to backend (saves bandwidth).
    - Session/user state, feedback, download links, etc.

Here is how the system works (Flow):

 1. User uploads resume & JD (PDF or text) → Streamlit UI

 2. Frontend extracts or passes files → Sends to FastAPI (as text or file)

 3. FastAPI endpoint receives, orchestrates CrewAI agents, returns structured results

 4. Streamlit displays results, progress, suggestions, etc.

#### **Constraints**:

 - None


#### **Tools**:

 - Use local **ollama** model

#### **Requirements**:
 - Make it work as expected

#### How to run:

 1. Run the fastpi backend:
 ```
 uvicorn backend.app.main:get_app --reload
 ```

  2. Start redis:
 ```
 docker run -d -p 6379:6379 redis
 ```
  3. Start the Celery worker:
 ```
 celery -A backend.worker.worker.celery_app worker --loglevel=info
 ```
