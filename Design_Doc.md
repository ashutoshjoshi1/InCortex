# InCortex — Detailed Design Document

## 1. Project Name

**InCortex**

## 2. Project Tagline

**A biologically inspired, modular, self-learning cognitive architecture built from Cells to Cortex.**

## 3. Project Vision

InCortex is an open-source artificial intelligence framework inspired by biological intelligence. The project follows a layered biological development model:

**Cell → Tissue → Muscle → Organ → Cortex → Full Brain System**

The goal is to create a modular, self-improving brain-like software system that can:

* Receive input through text, voice, files, APIs, and sensors.
* Understand information using specialized intelligence modules.
* Store short-term and long-term memory.
* Reason across memory, context, and goals.
* Learn from feedback and experience.
* Speak or respond naturally like a mouth.
* Use tools safely.
* Improve its internal knowledge over time.
* Support future advanced learning methods such as fine-tuning, reinforcement learning, self-evaluation, and multi-agent collaboration.

InCortex is not designed as one giant AI model. It is designed as a **living intelligence operating system** made of small intelligent units that cooperate.

---

# 4. Core Philosophy

Biological intelligence does not appear suddenly. It grows from small units.

A living organism begins with cells. Cells combine into tissues. Tissues support muscles and organs. Organs work together under the nervous system. The brain coordinates everything.

InCortex follows the same idea in software.

## 4.1 Biological Mapping

| Biological Concept | InCortex Software Concept                         |
| ------------------ | ------------------------------------------------- |
| Cell               | Smallest intelligent processing unit              |
| Tissue             | Group of related Cells                            |
| Muscle             | Action/execution module                           |
| Organ              | Specialized intelligence subsystem                |
| Nervous System     | Message bus and communication layer               |
| Brainstem          | Runtime control and survival functions            |
| Cortex             | Higher reasoning, planning, learning              |
| Memory             | Short-term, long-term, episodic, semantic storage |
| Mouth              | Text-to-speech and response delivery              |
| Ear                | Speech-to-text and input capture                  |
| Reflex             | Fast automatic response                           |
| Learning           | Feedback, scoring, memory update, retraining      |
| Body               | Complete InCortex runtime environment             |

---

# 5. Project Goals

## 5.1 Primary Goals

InCortex should become a modular AI system that can:

1. Understand user input.
2. Store useful memory.
3. Reason through tasks.
4. Learn from feedback.
5. Speak or respond naturally.
6. Use tools safely.
7. Improve its behavior over time.
8. Support local and cloud-based AI models.
9. Allow developers to add new Cells, Tissues, Muscles, and Organs.
10. Provide a research-grade foundation for building self-learning agent systems.

## 5.2 Secondary Goals

InCortex should also support:

* Voice interaction.
* File reading.
* Code generation.
* Local knowledge base learning.
* Multi-agent communication.
* Tool/plugin integration.
* Self-debugging suggestions.
* Human-approved self-improvement.
* Visual dashboards for brain activity.
* Open-source contribution system.

---

# 6. Non-Goals

To keep the project realistic and safe, InCortex should not initially attempt to:

1. Build artificial general intelligence from scratch.
2. Train a giant language model from zero.
3. Allow uncontrolled self-modifying code.
4. Give the system unrestricted internet or computer access.
5. Make autonomous high-risk decisions.
6. Replace human approval for code changes.
7. Claim consciousness or biological awareness.
8. Store private user data without permission.

The first version should focus on **controlled self-learning through memory, feedback, and modular reasoning**.

---

# 7. High-Level System Overview

InCortex will be built as a layered cognitive system.

```text
User Input
   ↓
Input Layer
   ↓
Perception Cells
   ↓
Language Tissue
   ↓
Memory Organ
   ↓
Reasoning Organ
   ↓
Planning Organ
   ↓
Action/Muscle System
   ↓
Output/Mouth System
   ↓
Feedback and Learning Organ
   ↓
Memory Update
```

The system operates in a loop:

```text
Listen → Understand → Remember → Reason → Plan → Act → Speak → Learn
```

This loop is the foundation of the InCortex brain.

---

# 8. Main Architecture

## 8.1 Layered Architecture

InCortex should be divided into the following layers:

```text
Application Layer
API Layer
Cortex Layer
Organ Layer
Tissue Layer
Cell Layer
Memory Layer
Learning Layer
Tool/Muscle Layer
Safety Layer
Runtime Layer
Storage Layer
```

## 8.2 Architecture Diagram

```text
+--------------------------------------------------+
|                  User Interface                  |
|      CLI / Web App / Voice / API / Desktop App   |
+--------------------------------------------------+
                         |
                         v
+--------------------------------------------------+
|                  Input System                    |
|      Text Input / Voice Input / File Input       |
+--------------------------------------------------+
                         |
                         v
+--------------------------------------------------+
|                  InCortex Core                   |
|     Router / Scheduler / State / Message Bus     |
+--------------------------------------------------+
        |               |                |
        v               v                v
+---------------+ +---------------+ +---------------+
| Language      | | Memory        | | Reasoning     |
| Organ         | | Organ         | | Organ         |
+---------------+ +---------------+ +---------------+
        |               |                |
        v               v                v
+---------------+ +---------------+ +---------------+
| Planning      | | Learning      | | Safety        |
| Organ         | | Organ         | | Organ         |
+---------------+ +---------------+ +---------------+
        |               |                |
        v               v                v
+--------------------------------------------------+
|                  Muscle System                   |
|   Speak / Search / Code / File / API / Tools     |
+--------------------------------------------------+
                         |
                         v
+--------------------------------------------------+
|                  Output System                   |
|           Text Response / Speech / Actions       |
+--------------------------------------------------+
```

---

# 9. Core Concepts

## 9.1 Cell

A **Cell** is the smallest processing unit in InCortex.

Each Cell should have:

* Name
* Type
* Input handler
* Processing logic
* Memory access
* Output generator
* Confidence score
* Health status
* Learning hooks
* Error tracking
* Communication ability

### Example Cell Types

```text
TextCell
IntentCell
MemoryCell
ReasoningCell
PlannerCell
SpeechCell
SafetyCell
EmotionCell
FeedbackCell
ToolCell
VisionCell
CodeCell
```

## 9.2 Cell Responsibilities

A Cell should do one small job well.

Example:

| Cell          | Responsibility                 |
| ------------- | ------------------------------ |
| IntentCell    | Understand what the user wants |
| MemoryCell    | Retrieve relevant memory       |
| ReasoningCell | Think through the problem      |
| FeedbackCell  | Learn from user correction     |
| SafetyCell    | Check risk before action       |
| SpeechCell    | Convert response to voice      |
| CodeCell      | Generate or analyze code       |

## 9.3 Basic Cell Contract

Every Cell should follow the same structure:

```text
Input → Process → Output → Learn → Report Health
```

### Cell Interface

```python
class BaseCell:
    def __init__(self, name, cell_type):
        self.name = name
        self.cell_type = cell_type
        self.health = "active"
        self.confidence = 0.0

    def receive(self, message):
        raise NotImplementedError

    def process(self, message):
        raise NotImplementedError

    def emit(self):
        raise NotImplementedError

    def learn(self, feedback):
        raise NotImplementedError

    def health_check(self):
        return {
            "name": self.name,
            "type": self.cell_type,
            "health": self.health,
            "confidence": self.confidence
        }
```

---

# 10. Tissue Design

A **Tissue** is a group of Cells working together.

For example, a Language Tissue may contain:

```text
TokenizerCell
IntentCell
ContextCell
SummarizerCell
ResponseCell
```

A Memory Tissue may contain:

```text
ShortTermMemoryCell
LongTermMemoryCell
VectorMemoryCell
EpisodicMemoryCell
```

## 10.1 Tissue Responsibilities

A Tissue should:

1. Manage a group of Cells.
2. Send messages to the right Cell.
3. Combine Cell outputs.
4. Report health of all Cells.
5. Improve performance based on feedback.
6. Allow new Cells to be added easily.

### Tissue Interface

```python
class BaseTissue:
    def __init__(self, name):
        self.name = name
        self.cells = []

    def add_cell(self, cell):
        self.cells.append(cell)

    def process(self, message):
        results = []
        for cell in self.cells:
            results.append(cell.process(message))
        return self.combine(results)

    def combine(self, results):
        return results

    def health_check(self):
        return [cell.health_check() for cell in self.cells]
```

---

# 11. Muscle Design

A **Muscle** is an action system.

The brain thinks. Muscles act.

Muscles should not make deep decisions. They should execute approved actions.

## 11.1 Example Muscles

| Muscle         | Function                      |
| -------------- | ----------------------------- |
| SpeechMuscle   | Speak using text-to-speech    |
| FileMuscle     | Read/write local files        |
| SearchMuscle   | Search memory or internet     |
| CodeMuscle     | Run safe code                 |
| APIMuscle      | Call external APIs            |
| GitHubMuscle   | Create issues, PRs, commits   |
| TerminalMuscle | Execute approved commands     |
| BrowserMuscle  | Browse web pages              |
| VisionMuscle   | Process images                |
| DocumentMuscle | Read PDFs, docs, spreadsheets |

## 11.2 Muscle Safety

Every Muscle must follow permission rules.

Example:

```text
Low-risk action:
- Summarize text
- Read local memory
- Generate explanation

Medium-risk action:
- Write file
- Create GitHub issue
- Run local script

High-risk action:
- Delete file
- Push code
- Send email
- Execute shell command
- Access private credentials
```

High-risk actions require human approval.

---

# 12. Organ Design

An **Organ** is a specialized subsystem made of Tissues and Cells.

## 12.1 Core Organs

InCortex should have the following core Organs:

```text
Input Organ
Language Organ
Memory Organ
Reasoning Organ
Planning Organ
Learning Organ
Speech Organ
Safety Organ
Tool Organ
Development Organ
```

---

## 12.2 Input Organ

The Input Organ receives information from the outside world.

### Supported Input Types

```text
Text
Voice
Files
Images
Code
API events
Sensor data
System events
GitHub events
User feedback
```

### Responsibilities

* Capture input.
* Detect input type.
* Normalize input into a standard message format.
* Send message to the Cortex Core.

---

## 12.3 Language Organ

The Language Organ understands and generates language.

### Responsibilities

* Understand user intent.
* Extract entities.
* Track conversation context.
* Summarize long input.
* Generate final responses.
* Translate between internal reasoning and human-readable output.

### Internal Tissues

```text
Intent Tissue
Context Tissue
Summarization Tissue
Response Tissue
Dialogue Tissue
```

---

## 12.4 Memory Organ

The Memory Organ stores and retrieves knowledge.

### Memory Types

| Memory Type       | Purpose                         |
| ----------------- | ------------------------------- |
| Working Memory    | Current conversation/task state |
| Short-Term Memory | Recent interactions             |
| Long-Term Memory  | Durable knowledge               |
| Episodic Memory   | Past experiences/events         |
| Semantic Memory   | Facts and concepts              |
| Procedural Memory | Skills and instructions         |
| Preference Memory | User preferences                |
| Error Memory      | Past mistakes and corrections   |
| Experiment Memory | Development test results        |

### Memory Flow

```text
Input received
   ↓
Important details extracted
   ↓
Memory relevance checked
   ↓
Useful information stored
   ↓
Future tasks retrieve memory
```

### Memory Rules

The Memory Organ should only store information that is:

* Useful
* Relevant
* Allowed
* Non-sensitive or user-approved
* Properly timestamped
* Easy to update or delete

---

## 12.5 Reasoning Organ

The Reasoning Organ thinks through problems.

### Responsibilities

* Break down complex tasks.
* Compare options.
* Use memory.
* Detect contradictions.
* Estimate confidence.
* Ask for clarification only when necessary.
* Generate reasoning summaries.
* Support chain-of-thought internally without exposing private raw reasoning.

### Reasoning Modes

```text
Simple reasoning
Step-by-step task decomposition
Comparison reasoning
Debugging reasoning
Planning reasoning
Scientific reasoning
Mathematical reasoning
Code reasoning
Causal reasoning
Counterfactual reasoning
```

---

## 12.6 Planning Organ

The Planning Organ creates action plans.

### Responsibilities

* Convert goals into steps.
* Choose which Organs and Muscles to use.
* Track progress.
* Revise plans when something fails.
* Prioritize tasks.
* Estimate risk level.
* Decide when human approval is needed.

### Example Planning Flow

```text
Goal: Build a memory module

1. Check existing architecture.
2. Define memory schema.
3. Create database interface.
4. Add vector search.
5. Add memory retrieval function.
6. Add tests.
7. Update documentation.
8. Request review.
```

---

## 12.7 Learning Organ

The Learning Organ is the heart of self-improvement.

In the first version, learning should not mean uncontrolled model training. It should mean controlled improvement through:

```text
Memory updates
Feedback collection
Mistake tracking
Evaluation scoring
Prompt improvement
Skill library growth
Human-approved code improvement
Experiment tracking
```

### Learning Loop

```text
Task performed
   ↓
Output generated
   ↓
Feedback received
   ↓
Score assigned
   ↓
Mistake or success stored
   ↓
Strategy updated
   ↓
Future behavior improves
```

### Learning Types

| Learning Type          | Version | Description                               |
| ---------------------- | ------- | ----------------------------------------- |
| Memory Learning        | v0.1    | Stores useful facts and corrections       |
| Feedback Learning      | v0.1    | Learns from user ratings and corrections  |
| Error Learning         | v0.2    | Tracks repeated mistakes                  |
| Skill Learning         | v0.3    | Builds reusable task skills               |
| Self-Evaluation        | v0.4    | Scores its own outputs                    |
| Curriculum Learning    | v0.5    | Chooses what to learn next                |
| Fine-Tuning            | v1.0    | Controlled model improvement              |
| Reinforcement Learning | v1.5    | Reward-based improvement                  |
| Self-Code Improvement  | v2.0    | Suggests code changes with human approval |

---

## 12.8 Speech Organ

The Speech Organ allows InCortex to listen and speak.

### Ear System

The Ear system converts voice to text.

Possible tools:

```text
Whisper
Vosk
Deepgram
AssemblyAI
Local speech-to-text models
```

### Mouth System

The Mouth system converts text to speech.

Possible tools:

```text
pyttsx3
Coqui TTS
ElevenLabs
OpenAI TTS
Piper
System voice APIs
```

### Speech Flow

```text
User speaks
   ↓
Speech-to-text
   ↓
Language Organ
   ↓
Reasoning Organ
   ↓
Response generated
   ↓
Text-to-speech
   ↓
System speaks
```

---

## 12.9 Safety Organ

The Safety Organ protects the system, user, and environment.

### Responsibilities

* Check user requests.
* Detect unsafe actions.
* Apply permissions.
* Prevent uncontrolled self-modification.
* Prevent private data leakage.
* Require approval for risky actions.
* Log important actions.
* Block dangerous tool usage.

### Permission Levels

```text
Level 0: No action, only explanation
Level 1: Read-only actions
Level 2: Local safe write actions
Level 3: External API actions
Level 4: Code execution
Level 5: System-level actions
```

Level 4 and Level 5 actions should require approval.

---

## 12.10 Development Organ

The Development Organ helps InCortex improve its own codebase in a controlled way.

### Responsibilities

* Read project files.
* Understand GitHub issues.
* Suggest improvements.
* Generate code patches.
* Run tests.
* Write documentation.
* Create pull request drafts.
* Learn from failed tests.
* Never merge code without human approval.

### Safe Self-Development Rule

InCortex may suggest changes to itself, but it must not directly approve or merge its own changes.

Human approval is required for:

```text
Merging pull requests
Changing safety rules
Changing permissions
Deleting memory
Executing system commands
Publishing releases
```

---

# 13. Cortex Core

The **Cortex Core** is the central coordinator.

It does not do every task itself. Instead, it routes messages to the correct Organs.

## 13.1 Cortex Core Responsibilities

The Cortex Core should:

1. Receive normalized messages.
2. Identify task type.
3. Query Memory Organ.
4. Select relevant Organs.
5. Build execution plan.
6. Send tasks to Cells, Tissues, Organs, and Muscles.
7. Collect results.
8. Apply safety checks.
9. Generate final output.
10. Send results to Learning Organ.

## 13.2 Cortex Core Flow

```text
Message received
   ↓
Create task context
   ↓
Check memory
   ↓
Detect intent
   ↓
Plan response
   ↓
Route to Organs
   ↓
Execute safe actions
   ↓
Generate answer
   ↓
Collect feedback
   ↓
Update memory
```

---

# 14. Message System

All parts of InCortex should communicate through a standard message format.

## 14.1 Message Object

```python
class CortexMessage:
    def __init__(
        self,
        message_id,
        session_id,
        source,
        target,
        message_type,
        payload,
        priority="normal",
        confidence=None,
        memory_refs=None,
        permissions=None,
        created_at=None
    ):
        self.message_id = message_id
        self.session_id = session_id
        self.source = source
        self.target = target
        self.message_type = message_type
        self.payload = payload
        self.priority = priority
        self.confidence = confidence
        self.memory_refs = memory_refs or []
        self.permissions = permissions or []
        self.created_at = created_at
```

## 14.2 Message Types

```text
user_input
system_event
memory_query
memory_result
reasoning_request
reasoning_result
plan_request
plan_result
tool_request
tool_result
safety_check
feedback_event
learning_update
error_event
health_check
```

---

# 15. Memory System Design

## 15.1 Storage Layers

InCortex should use multiple storage systems.

| Storage         | Use                        |
| --------------- | -------------------------- |
| In-memory cache | Current session            |
| SQLite          | Simple local storage       |
| PostgreSQL      | Production database        |
| Vector database | Semantic search            |
| File storage    | Documents, logs, artifacts |
| Event store     | Full system history        |

## 15.2 Recommended MVP Storage

For the first version:

```text
SQLite for structured memory
ChromaDB or FAISS for vector memory
JSONL for event logs
Local file storage for artifacts
```

## 15.3 Memory Record

```python
class MemoryRecord:
    def __init__(
        self,
        memory_id,
        memory_type,
        content,
        source,
        importance,
        confidence,
        tags,
        created_at,
        updated_at
    ):
        self.memory_id = memory_id
        self.memory_type = memory_type
        self.content = content
        self.source = source
        self.importance = importance
        self.confidence = confidence
        self.tags = tags
        self.created_at = created_at
        self.updated_at = updated_at
```

## 15.4 Memory Importance Scoring

Each memory should be scored by:

```text
Relevance
Frequency
User confirmation
Task impact
Recency
Confidence
Uniqueness
```

Memory should not grow endlessly. The system needs memory cleanup, compression, and summarization.

---

# 16. Learning System Design

## 16.1 First-Level Learning

The first version of InCortex should learn through:

```text
User corrections
Task success/failure
Saved preferences
Repeated patterns
Evaluation scores
Manual ratings
Memory updates
```

Example:

```text
User says:
"No, I wanted a simpler explanation."

InCortex stores:
- User prefers simpler explanations for this topic.
- Previous answer was too complex.
- Future response should use easier words.
```

## 16.2 Feedback Object

```python
class FeedbackEvent:
    def __init__(
        self,
        task_id,
        rating,
        correction,
        user_comment,
        success,
        created_at
    ):
        self.task_id = task_id
        self.rating = rating
        self.correction = correction
        self.user_comment = user_comment
        self.success = success
        self.created_at = created_at
```

## 16.3 Learning Score

Each task should produce a learning score.

```text
High score:
- User accepted answer
- No correction needed
- Task completed successfully

Medium score:
- Answer useful but incomplete
- User requested changes

Low score:
- Wrong answer
- Unsafe action blocked
- Tool failed
- User corrected major mistake
```

## 16.4 Self-Learning Development Loop

During development, InCortex should learn from its own project history.

```text
Code written
   ↓
Tests run
   ↓
Errors detected
   ↓
Error patterns stored
   ↓
Fix suggested
   ↓
Human reviews
   ↓
Approved fix merged
   ↓
Learning memory updated
```

This allows the system to become better while the project is being built.

---

# 17. Brain Activity Logging

Every important action should be logged.

## 17.1 Event Log

The system should log:

```text
User input
Detected intent
Memory retrieved
Organs used
Tools used
Safety checks
Errors
Final output
Feedback
Learning updates
```

## 17.2 Why Logging Matters

Logging helps developers:

* Debug the brain.
* Understand failures.
* Improve performance.
* Build dashboards.
* Train future models.
* Track learning progress.

---

# 18. Tool and Plugin System

InCortex should support tools as controlled external abilities.

## 18.1 Tool Interface

```python
class BaseTool:
    name = "base_tool"
    risk_level = 1

    def validate(self, request):
        raise NotImplementedError

    def execute(self, request):
        raise NotImplementedError

    def result(self):
        raise NotImplementedError
```

## 18.2 Tool Registry

A Tool Registry should store available tools.

```text
Tool name
Description
Input schema
Output schema
Risk level
Permission requirement
Enabled/disabled status
```

## 18.3 Example Tools

```text
read_file
write_file
search_memory
search_web
run_python
create_github_issue
summarize_document
generate_speech
transcribe_audio
```

---

# 19. API Design

InCortex should provide an API so other apps can use the brain.

## 19.1 Suggested API Framework

Use:

```text
FastAPI
Pydantic
Uvicorn
SQLite/PostgreSQL
ChromaDB/FAISS
```

## 19.2 Core API Endpoints

```text
POST /v1/chat
POST /v1/memory/add
POST /v1/memory/search
POST /v1/feedback
GET  /v1/health
GET  /v1/organs
GET  /v1/cells
POST /v1/tools/execute
GET  /v1/logs
```

## 19.3 Chat Endpoint Example

```json
{
  "user_id": "default",
  "session_id": "session_001",
  "message": "Teach yourself what photosynthesis is.",
  "mode": "learn"
}
```

## 19.4 Response Example

```json
{
  "response": "Photosynthesis is how plants make food using sunlight, water, and carbon dioxide.",
  "memory_updated": true,
  "organs_used": ["LanguageOrgan", "MemoryOrgan", "ReasoningOrgan"],
  "confidence": 0.91,
  "feedback_requested": true
}
```

---

# 20. GitHub Repository Structure

Recommended repository name:

```text
incortex
```

Recommended structure:

```text
incortex/
│
├── README.md
├── ROADMAP.md
├── CONTRIBUTING.md
├── LICENSE
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── pyproject.toml
├── .gitignore
├── .env.example
│
├── docs/
│   ├── architecture.md
│   ├── biological_model.md
│   ├── memory_system.md
│   ├── learning_system.md
│   ├── safety_model.md
│   ├── api_reference.md
│   └── development_phases.md
│
├── incortex/
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── cortex.py
│   │   ├── router.py
│   │   ├── scheduler.py
│   │   ├── message.py
│   │   ├── state.py
│   │   └── config.py
│   │
│   ├── cells/
│   │   ├── base_cell.py
│   │   ├── text_cell.py
│   │   ├── intent_cell.py
│   │   ├── memory_cell.py
│   │   ├── reasoning_cell.py
│   │   ├── planner_cell.py
│   │   ├── feedback_cell.py
│   │   └── safety_cell.py
│   │
│   ├── tissues/
│   │   ├── base_tissue.py
│   │   ├── language_tissue.py
│   │   ├── memory_tissue.py
│   │   ├── reasoning_tissue.py
│   │   └── learning_tissue.py
│   │
│   ├── organs/
│   │   ├── base_organ.py
│   │   ├── input_organ.py
│   │   ├── language_organ.py
│   │   ├── memory_organ.py
│   │   ├── reasoning_organ.py
│   │   ├── planning_organ.py
│   │   ├── learning_organ.py
│   │   ├── speech_organ.py
│   │   ├── safety_organ.py
│   │   └── tool_organ.py
│   │
│   ├── muscles/
│   │   ├── base_muscle.py
│   │   ├── speech_muscle.py
│   │   ├── file_muscle.py
│   │   ├── code_muscle.py
│   │   ├── search_muscle.py
│   │   └── api_muscle.py
│   │
│   ├── memory/
│   │   ├── memory_record.py
│   │   ├── short_term.py
│   │   ├── long_term.py
│   │   ├── vector_memory.py
│   │   ├── episodic_memory.py
│   │   └── memory_manager.py
│   │
│   ├── learning/
│   │   ├── feedback.py
│   │   ├── evaluator.py
│   │   ├── learning_loop.py
│   │   ├── mistake_tracker.py
│   │   └── skill_builder.py
│   │
│   ├── safety/
│   │   ├── permissions.py
│   │   ├── risk.py
│   │   ├── policy.py
│   │   └── approval.py
│   │
│   ├── tools/
│   │   ├── base_tool.py
│   │   ├── tool_registry.py
│   │   ├── file_tools.py
│   │   ├── python_tool.py
│   │   └── github_tool.py
│   │
│   ├── api/
│   │   ├── main.py
│   │   ├── routes_chat.py
│   │   ├── routes_memory.py
│   │   ├── routes_feedback.py
│   │   └── schemas.py
│   │
│   └── interfaces/
│       ├── cli.py
│       ├── web.py
│       └── voice.py
│
├── examples/
│   ├── basic_chat.py
│   ├── memory_demo.py
│   ├── feedback_demo.py
│   └── voice_demo.py
│
├── tests/
│   ├── test_cells.py
│   ├── test_tissues.py
│   ├── test_organs.py
│   ├── test_memory.py
│   ├── test_learning.py
│   └── test_safety.py
│
└── scripts/
    ├── init_db.py
    ├── run_cli.py
    ├── run_api.py
    └── seed_memory.py
```

---

# 21. Development Phases

## Phase 0: Project Foundation

### Goal

Create the GitHub repository and basic project structure.

### Deliverables

```text
README.md
ROADMAP.md
CONTRIBUTING.md
LICENSE
Basic Python package
CLI starter
Project documentation
```

### Success Criteria

The project can be installed locally and run with:

```bash
python scripts/run_cli.py
```

---

## Phase 1: Cell System

### Goal

Build the smallest unit of intelligence.

### Deliverables

```text
BaseCell
TextCell
IntentCell
MemoryCell
FeedbackCell
Cell health checks
Unit tests
```

### Success Criteria

A Cell can:

```text
Receive input
Process input
Return output
Store simple learning feedback
Report health
```

---

## Phase 2: Tissue System

### Goal

Group Cells into cooperative units.

### Deliverables

```text
BaseTissue
LanguageTissue
MemoryTissue
LearningTissue
Message passing between Cells
```

### Success Criteria

Multiple Cells can work together on one task.

Example:

```text
User input → IntentCell → MemoryCell → ResponseCell
```

---

## Phase 3: Organ System

### Goal

Create specialized brain-like subsystems.

### Deliverables

```text
LanguageOrgan
MemoryOrgan
ReasoningOrgan
LearningOrgan
SafetyOrgan
```

### Success Criteria

A full task can pass through multiple Organs.

---

## Phase 4: Cortex Core

### Goal

Build the central brain coordinator.

### Deliverables

```text
CortexCore
Router
Scheduler
MessageBus
TaskContext
SystemState
```

### Success Criteria

The Cortex Core can route a user request through the right Organs and generate a response.

---

## Phase 5: Memory and Learning

### Goal

Make InCortex remember and improve.

### Deliverables

```text
Short-term memory
Long-term memory
Vector memory
Feedback system
Mistake tracker
Learning log
```

### Success Criteria

The system can remember a topic and use it later.

Example:

```text
User: Learn that my favorite explanation style is simple English.
Later:
User: Explain neural networks.
InCortex responds in simple English.
```

---

## Phase 6: Voice System

### Goal

Add Ear and Mouth.

### Deliverables

```text
Speech-to-text module
Text-to-speech module
Voice interface
Conversation loop
```

### Success Criteria

User can speak to InCortex and hear a spoken response.

---

## Phase 7: Tool/Muscle System

### Goal

Allow InCortex to perform actions safely.

### Deliverables

```text
Tool registry
File tools
Search tools
Code tools
API tools
Permission system
Approval system
```

### Success Criteria

InCortex can use tools only after safety approval.

---

## Phase 8: Development Organ

### Goal

Allow InCortex to help develop itself safely.

### Deliverables

```text
Codebase reader
Issue analyzer
Test runner
Patch suggester
Documentation writer
GitHub integration
```

### Success Criteria

InCortex can suggest code changes and create draft pull requests, but cannot merge without human approval.

---

## Phase 9: Advanced Learning

### Goal

Move toward deeper self-learning.

### Deliverables

```text
Self-evaluation
Skill library
Curriculum learning
Experiment tracking
Fine-tuning pipeline
Model comparison
```

### Success Criteria

The system can test multiple strategies, compare performance, and improve future behavior.

---

# 22. MVP Definition

The first public MVP should be simple but impressive.

## MVP Name

**InCortex v0.1 — Cell Genesis**

## MVP Features

```text
CLI chat interface
Base Cell system
Language Tissue
Memory Organ
Learning Organ
Simple Cortex Core
SQLite memory
Feedback collection
Event logs
Basic tests
Documentation
```

## MVP Demo

User:

```text
Teach yourself what photosynthesis is.
```

InCortex:

```text
I have learned that photosynthesis is the process plants use to make food from sunlight, water, and carbon dioxide.
```

User:

```text
Remember that I like very simple explanations.
```

InCortex:

```text
Got it. I will explain future topics in simple English.
```

Later:

```text
Explain neural networks.
```

InCortex:

```text
A neural network is a computer system that learns patterns, like how your brain learns from examples.
```

This demo proves:

```text
Input understanding
Memory storage
Memory retrieval
Response generation
Feedback learning
Personalization
```

---

# 23. Technology Stack

## 23.1 MVP Stack

```text
Python 3.11+
FastAPI
SQLite
Pydantic
ChromaDB or FAISS
pytest
Typer or Click for CLI
Uvicorn
```

## 23.2 Later Stack

```text
PostgreSQL
Redis
Docker
React or Next.js dashboard
PyTorch
Transformers
Whisper
Coqui TTS or Piper
LangGraph-style orchestration
GitHub Actions
OpenTelemetry
Kubernetes
```

---

# 24. Configuration Design

InCortex should use a config file.

Example:

```yaml
project:
  name: InCortex
  version: 0.1.0

memory:
  provider: sqlite
  vector_provider: chromadb
  max_short_term_items: 100

learning:
  feedback_enabled: true
  auto_memory_enabled: true
  self_code_changes: false

safety:
  require_approval_for_tools: true
  max_permission_level: 2

models:
  language_model: local
  embedding_model: sentence-transformers
  speech_to_text: disabled
  text_to_speech: disabled
```

---

# 25. Safety and Ethics

InCortex should be open-source but responsible.

## 25.1 Safety Principles

```text
Human control first
Clear permissions
No hidden actions
No uncontrolled self-modification
No unsafe tool execution
No private data storage without permission
Transparent logs
Reversible memory
```

## 25.2 Human Approval Required For

```text
Running shell commands
Deleting files
Sending messages
Publishing code
Merging pull requests
Changing safety policy
Accessing private credentials
Training on private data
```

## 25.3 Memory Privacy

Users should be able to:

```text
View memory
Edit memory
Delete memory
Disable memory
Export memory
```

---

# 26. Testing Strategy

## 26.1 Unit Tests

Test each Cell, Tissue, Organ, Memory module, and Safety rule.

## 26.2 Integration Tests

Test full flows:

```text
User input → Memory → Reasoning → Response
User feedback → Learning update
Tool request → Safety check → Tool execution
```

## 26.3 Safety Tests

Test that dangerous actions are blocked.

Example:

```text
Delete all files → blocked
Run unknown shell command → requires approval
Send email → requires approval
Change safety policy → blocked
```

## 26.4 Learning Tests

Test whether feedback changes future behavior.

Example:

```text
User says: Use simpler words.
Future answer should become simpler.
```

---

# 27. Metrics

InCortex should track performance.

## 27.1 Intelligence Metrics

```text
Task success rate
Answer quality score
Memory retrieval accuracy
User feedback score
Reasoning confidence
Tool success rate
Repeated mistake count
```

## 27.2 System Metrics

```text
Response time
Memory size
Error rate
Cell health
Organ health
Tool failure rate
API latency
```

## 27.3 Learning Metrics

```text
Feedback accepted
Corrections stored
Mistakes reduced
Skills created
Memory reuse count
Improvement over time
```

---

# 28. Open Source Strategy

## 28.1 GitHub Positioning

Do not describe InCortex as “we are building AGI.”

Better positioning:

```text
InCortex is an open-source biologically inspired cognitive architecture for modular AI memory, reasoning, tool use, and self-improvement.
```

## 28.2 Good First Issues

```text
Create a new Cell type
Improve memory search
Add unit tests
Improve CLI output
Write documentation
Add speech support
Build dashboard UI
Add examples
```

## 28.3 Community Contribution Areas

```text
Core architecture
Memory systems
Learning algorithms
Speech
Tool integrations
Safety
Visualization
Documentation
Testing
Research experiments
```

---

# 29. README Opening Draft

# InCortex

InCortex is an open-source biologically inspired cognitive architecture for building modular self-learning AI systems.

The project grows intelligence from the smallest unit, called a Cell, into larger structures such as Tissues, Muscles, Organs, and finally a Cortex.

The goal is to create a safe, extensible, self-improving brain framework that can understand, remember, reason, speak, use tools, and learn from feedback.

InCortex is not one giant model. It is a living system of connected intelligence modules.

## Biological Development Model

```text
Cell → Tissue → Muscle → Organ → Cortex → Brain
```

## First Milestone

The first milestone is to build a working Cell system with memory, feedback, and a simple command-line chat interface.

---

# 30. Example First Development Task

## Task

Create the first Cell.

## File

```text
incortex/cells/base_cell.py
```

## Requirements

The BaseCell should:

```text
Have a name
Have a type
Receive a message
Process a message
Return output
Accept feedback
Report health
```

## Acceptance Criteria

```text
A test can create a Cell.
The Cell can receive input.
The Cell can return output.
The Cell can report health.
The Cell can store basic feedback.
```

---

# 31. Future Vision

In the long term, InCortex can become:

```text
A local AI brain
A personal learning assistant
A research platform for cognitive architectures
A modular agent operating system
A voice-based self-learning assistant
A safe self-improving development partner
A foundation for robotics, automation, and personal AI systems
```

The system can eventually support:

```text
Vision
Speech
Memory
Reasoning
Planning
Robotics
Sensors
Self-training
Multi-agent brains
Personal AI companions
Research simulations
```

---

# 32. Final Design Principle

InCortex should always follow this rule:

```text
Small intelligent parts first.
Clear communication between parts.
Memory at every level.
Learning after every action.
Human approval for risky behavior.
```

The correct development path is:

```text
Do not build the full brain first.

Build one Cell.
Make it work.
Make it remember.
Make it communicate.
Make many Cells.
Group them into Tissues.
Group Tissues into Organs.
Connect Organs through the Cortex.
Then let the system learn safely over time.
```

InCortex should grow like biology:

```text
Simple → Connected → Specialized → Coordinated → Adaptive → Self-improving
```
