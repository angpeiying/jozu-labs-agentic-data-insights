# Jozu Labs: Agentic Data Insights 🧠📊

Jozu is an **agentic data analytics system** built with LangGraph and LLMs.
It automatically transforms CSV/XLSX/Parquet/JSON datasets into **structured, evidence-backed insights**
with full transparency and interactive visualizations.

## ✨ Features
- Agent-based pipeline (profiling → planning → analysis → hypothesis → narration)
- Evidence-backed insights with confidence scores
- Interactive Vega-Lite charts (no notebooks required)
- Live agent execution panel (Copilot-style)
- Automatic ydata-profiling report generation
- Server-Sent Events (SSE) for real-time progress updates

## 🏗 Architecture
- Backend: FastAPI + LangGraph + Pandas
- LLM: OpenAI / Bedrock-compatible
- Frontend: Vanilla JS + Vega-Lite
- Profiling: ydata-profiling

## 🚀 Demo
1. Upload a CSV/XLSX/Parquet/JSON file
2. Watch agents execute in real time
3. Review structured insights and charts
4. Open full profiling report for deep inspection

## 🧠 Why Jozu?
Most AI analytics tools either:
- hallucinate insights, or
- require heavy manual analysis

Jozu bridges the gap by combining:
**deterministic computation + agentic reasoning + explainability**.

## 📌 Use Cases
- Exploratory data analysis
- Business reporting
- Data quality auditing
- Dataset comparison & drift detection
- Analyst productivity tooling

## ✨ Sample Screenshots
- User Interface (Light and Dark Mode)
<img width="1888" height="899" alt="image" src="https://github.com/user-attachments/assets/4c6aa1f6-59b7-4c11-b0b2-f02c713f5fc2" />
<img width="1889" height="895" alt="image" src="https://github.com/user-attachments/assets/18b7997f-cb3a-4502-bbf7-b0f15883da2c" />

- 🏗 Agents running
<img width="1889" height="898" alt="image" src="https://github.com/user-attachments/assets/537d2b71-0dec-455f-a23c-9db125b01647" />

- 📊 Sample Results
<img width="1498" height="807" alt="image" src="https://github.com/user-attachments/assets/a952c3ef-41fc-42dd-a5b2-b6d18ca5e719" />
<img width="1547" height="836" alt="image" src="https://github.com/user-attachments/assets/a6e9039a-1dd7-4aef-8ac9-28824a8e8bac" />
<img width="1456" height="818" alt="image" src="https://github.com/user-attachments/assets/ae36fdcb-e59b-4ba8-9735-2dbf307a0eef" />
<img width="1453" height="698" alt="image" src="https://github.com/user-attachments/assets/5b53c9e5-9899-46c8-8d48-1abd901a5f07" />


## 📄 License
MIT

## Setup
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# edit .env and set OPENAI_API_KEY

## Run

uvicorn tools.main:app --reload 
