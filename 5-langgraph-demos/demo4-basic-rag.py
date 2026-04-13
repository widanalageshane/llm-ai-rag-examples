import json
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_chroma import Chroma

# ─── Fictionary Creature Catalog ─────────────────────────────────────────────

CREATURES = [
    {
        "name": "Gloomfang",
        "type": "Shadow Beast",
        "habitat": "Dark Forests",
        "size": "Large",
        "abilities": ["Shadow Step", "Fear Aura", "Night Vision"],
        "diet": "Carnivore",
        "danger_level": 8,
        "description": "A wolf-like creature made of living shadow. Its fur absorbs light, making it nearly invisible at night.",
    },
    {
        "name": "Crystalwing",
        "type": "Aerial Elemental",
        "habitat": "Mountain Peaks",
        "size": "Medium",
        "abilities": ["Ice Breath", "Crystal Shield", "Blizzard Call"],
        "diet": "Omnivore",
        "danger_level": 6,
        "description": "A bird with wings made of translucent ice crystals. It soars at high altitudes and can summon blizzards.",
    },
    {
        "name": "Murkwraith",
        "type": "Swamp Spirit",
        "habitat": "Marshes and Bogs",
        "size": "Small",
        "abilities": ["Poison Mist", "Bog Sink", "Mimic Voice"],
        "diet": "Soul Eater",
        "danger_level": 7,
        "description": "A translucent spirit that floats above swamp water, luring travelers with mimicked voices before dragging them under.",
    },
    {
        "name": "Emberclaw",
        "type": "Fire Drake",
        "habitat": "Volcanic Regions",
        "size": "Huge",
        "abilities": ["Magma Breath", "Heat Aura", "Armor Melt"],
        "diet": "Carnivore",
        "danger_level": 9,
        "description": "A small dragon variant with claws that glow like molten rock. It can melt metal armor on contact.",
    },
    {
        "name": "Thornback",
        "type": "Forest Armored",
        "habitat": "Ancient Woodlands",
        "size": "Large",
        "abilities": ["Thorn Volley", "Bark Armor", "Root Grasp"],
        "diet": "Herbivore",
        "danger_level": 4,
        "description": "A tortoise-like creature covered in living thorns. Despite being herbivorous, it aggressively defends its territory.",
    },
    {
        "name": "Voidwhisper",
        "type": "Psychic Specter",
        "habitat": "Abandoned Ruins",
        "size": "Incorporeal",
        "abilities": ["Mind Read", "Memory Steal", "Illusion Cast"],
        "diet": "Memory Eater",
        "danger_level": 8,
        "description": "An invisible entity that feeds on memories. Victims often wake with no recollection of their past.",
    },
    {
        "name": "Saltmaw",
        "type": "Sea Lurker",
        "habitat": "Coastal Waters",
        "size": "Gigantic",
        "abilities": ["Tidal Pull", "Brine Spit", "Echo Roar"],
        "diet": "Piscivore",
        "danger_level": 7,
        "description": "A massive eel-like creature with rows of bioluminescent teeth, known for capsizing fishing boats.",
    },
    {
        "name": "Duskmorel",
        "type": "Fungal Wanderer",
        "habitat": "Underground Caves",
        "size": "Medium",
        "abilities": ["Spore Cloud", "Mycelium Network", "Regenerate"],
        "diet": "Decomposer",
        "danger_level": 3,
        "description": "A walking mushroom colony that releases hallucinogenic spores when threatened. Mostly harmless unless cornered.",
    },
]


# ─── ChromaDB vector store (in-memory, built at startup) ─────────────────────

embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

vector_store = Chroma.from_texts(
    texts=[json.dumps(c) for c in CREATURES],
    embedding=embeddings,
)

retriever = vector_store.as_retriever(search_kwargs={"k": 3})


# ─── State ────────────────────────────────────────────────────────────────────

class State(TypedDict, total=False):
    query: str            # user question
    context: list[str]    # retrieved creature entries
    answer: str           # final LLM response
    sources: list[str]    # creature names parsed from retrieved docs
    retry_count: int      # incremented in retrieve()


# ─── LLM ──────────────────────────────────────────────────────────────────────

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite")


# ─── Helper function for Part 3c ──────────────────────────────────────────────

def is_relevant(query: str, documents: list[str]) -> bool:
    """
    Simple heuristic relevance check.
    Returns True if at least one meaningful query word appears
    in the combined retrieved documents.
    """
    stop_words = {
        "what", "which", "who", "where", "when", "why", "how",
        "is", "are", "the", "a", "an", "of", "in", "on", "to",
        "me", "about", "tell", "and", "or", "with"
    }

    query_words = {
        word.strip("?,.!:;\"'()").lower()
        for word in query.split()
        if word.strip("?,.!:;\"'()").lower() not in stop_words
    }

    combined_docs = " ".join(documents).lower()

    match_count = sum(1 for word in query_words if word in combined_docs)
    return match_count >= 1


# ─── Nodes ────────────────────────────────────────────────────────────────────

def retrieve(state: State) -> dict:
    """Retrieve the most relevant creatures via ChromaDB similarity search."""
    docs = retriever.invoke(state["query"])

    # Debug print to inspect raw retrieved documents
    print("\n[DEBUG] Retrieved documents:")
    for i, doc in enumerate(docs, start=1):
        print(f"{i}. {doc.page_content}")

    context = [doc.page_content for doc in docs]

    sources = []
    for doc in docs:
        try:
            parsed = json.loads(doc.page_content)
            sources.append(parsed.get("name", "Unknown"))
        except json.JSONDecodeError:
            sources.append("Unknown")

    current_retry_count = state.get("retry_count", 0) + 1

    return {
        "context": context,
        "sources": sources,
        "retry_count": current_retry_count,
    }


def generate(state: State) -> dict:
    """Generate an answer grounded in the retrieved creature entries."""
    context_block = "\n\n---\n\n".join(state["context"])

    messages = [
        SystemMessage(
            content=(
                "You are a knowledgeable guide to a world of fictionary creatures. "
                "Answer the user's question using only the provided creature catalog entries. "
                "Be concise and informative."
            )
        ),
        HumanMessage(
            content=(
                f"Creature catalog entries:\n\n{context_block}\n\n"
                f"Question: {state['query']}"
            )
        ),
    ]

    response = llm.invoke(messages)
    return {"answer": response.content}


def format_answer(state: State) -> dict:
    """
    Rewrite the answer as a numbered bullet list using simple Python
    string manipulation only. No LLM call here.
    """
    raw_answer = state["answer"].strip()

    # Split by lines, remove empty lines
    lines = [line.strip(" -•\t") for line in raw_answer.splitlines() if line.strip()]

    # If the model returned one paragraph, split by sentences
    if len(lines) <= 1:
        sentences = [s.strip() for s in raw_answer.replace("\n", " ").split(".") if s.strip()]
        lines = sentences

    formatted_lines = [f"{i}. {line}" for i, line in enumerate(lines, start=1)]
    formatted_answer = "\n".join(formatted_lines)

    return {"answer": formatted_answer}


# ─── Graph ────────────────────────────────────────────────────────────────────
#
#   START → retrieve → generate → format_answer → END
#

builder = StateGraph(State)

builder.add_node("retrieve", retrieve)
builder.add_node("generate", generate)
builder.add_node("format_answer", format_answer)

builder.add_edge(START, "retrieve")
builder.add_edge("retrieve", "generate")
builder.add_edge("generate", "format_answer")
builder.add_edge("format_answer", END)

graph = builder.compile()


# ─── Demo queries ─────────────────────────────────────────────────────────────

queries = [
    "What creatures live in dark or shadowy environments?",
    "Which creature is the most dangerous and what are its abilities?",
    "Tell me about the Murkwraith",
]

for query in queries:
    print(f"\n{'=' * 60}")
    print(f"Query:  {query}")
    print("-" * 60)

    result = graph.invoke({"query": query})

    print(f"Answer:\n{result['answer']}")
    print(f"\nSources: {result['sources']}")
    print(f"Retry count: {result['retry_count']}")
    print(f"Relevant? {is_relevant(query, result['context'])}")
