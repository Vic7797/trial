# AI Crew Setup

This document explains the AI components powering the automated ticket resolution system.

## Core AI Components

### 1. Classification Crew
- **Purpose**: Analyzes incoming tickets to determine criticality and category
- **Input**: Ticket title, description
- **Output**: Criticality level (low/high), category
- **Location**: `app/ai/crews/classification_crew.py`

### 2. Solution Crew
- **Purpose**: Generates responses for tickets
- **Features**:
  - Uses RAG (Retrieval Augmented Generation)
  - Searches knowledge base for relevant information
  - Generates human-like responses
- **Location**: `app/ai/crews/solution_crew.py`

### 3.Enhancement Crew
- **Purpose**: Enhances responses to make them more human-like
- **Features**:
  - Generates human-like responses
- **Location**: `app/ai/crews/enhancement_crew.py`

### 4. Analysis Crew
- **Purpose**: Processes resolved tickets to extract insights
- **Output**: Sentiment analysis, resolution quality metrics
- **Location**: `app/ai/crews/analysis_crew.py`

## Workflow

### Ticket Processing Flow

1. **Ticket Creation**
   - New ticket arrives via email/Telegram
   - System creates ticket with status `new`

2. **Classification**
   ```python
   # Example classification call
   classification = await classification_crew.classify_ticket(
       title="Login issues",
       description="Can't log in to my account"
   )
   ```

3. **Routing**
   - **Low criticality**: Auto-resolve using Solution Crew
   - **Medium/High**: Assign to human agent with AI suggestions

4. **Auto-Resolution**
   - Solution Crew generates response
   - Response sent to customer
   - Ticket marked as resolved

## Configuration

### Environment Variables
```env
# OpenAI
OPENAI_API_KEY=your_openai_key

# Vector DB
CHROMA_HOST=chroma
CHROMA_PORT=8000

# Crew Settings
MAX_TOKENS=1000
TEMPERATURE=0.7
```
