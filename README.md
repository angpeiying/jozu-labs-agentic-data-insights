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