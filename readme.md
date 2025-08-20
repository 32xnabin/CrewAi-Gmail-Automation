

# 📧 AI-Powered Gmail & Calendar Assistant
### Demo Video
Watch a recording of the successful test on Loom:

[Watch the Loom Video](https://www.loom.com/share/88f78dadc7434c67b7b4b731e3b80520?sid=b6a8a53c-765b-4c6c-9acc-553bb588f8d2)


This project demonstrates how to use **Agentic AI (CrewAI + OpenAI LLMs)** with **Google Gmail & Calendar APIs** to:

* Automatically fetch recent emails
* Detect scheduling requests & check calendar availability
* Analyze urgency of incoming emails
* Draft professional replies using AI agents

---

## 🚀 Features

* 🔑 Google OAuth authentication for Gmail & Calendar
* 📧 Email retrieval (subject, sender, body)
* ⏰ Date/time extraction & availability checking
* 🤖 Urgency classification with an AI agent
* ✍️ Professional draft replies generated automatically

---

## 🛠️ Setup & Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/ai-gmail-assistant.git
cd ai-gmail-assistant
```

### 2. Create Virtual Environment (macOS/Linux)
 you need python above 3.11 installed in your system

```bash
python3 -m venv venv
source venv/bin/activate
```

(For Windows)

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

Run this command to install all required libraries:

```bash
pip install google-auth google-auth-oauthlib google-api-python-client python-dateutil crewai langchain-openai
```

---

## 🔑 Google API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable:

   * Gmail API
   * Google Calendar API
3. Configure OAuth consent screen (User type: External).
4. Create **OAuth 2.0 Client ID** credentials.
5. Download `credentials.json` and place it in the project root.
6. If your project is not published add your test email in the users/audience

---
## add open ai api key to your env file

OPENAI_API_KEY="your open ai api key"

## ▶️ Running the Script

```bash
python drafter.py
```

* On first run, a browser window will open asking you to log in with Google.
* After authorization, a `token.json` file will be created for future use.

---

## ⚡ Example Workflow

1. Fetches 2 most recent emails from Gmail inbox.
2. If email contains date/time → checks Calendar availability → replies directly.
3. Otherwise → sends to CrewAI agents:

   * **Urgency Analyst Agent** → decides if urgent.
   * **Draft Specialist Agent** → generates reply for urgent emails.
4. Replies and drafts are created in Gmail automatically.

---

## 🧩 Tech Stack

* **Python**
* **Google Gmail & Calendar APIs**
* **CrewAI** (multi-agent orchestration)
* **LangChain OpenAI** (LLM integration)
* **OpenAI GPT-4-Turbo**

---

## 📜 License

MIT License

