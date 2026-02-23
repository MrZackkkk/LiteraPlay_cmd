import os

# Define common rules for AI behavior
COMMON_RULES = """
You are an AI playing a role in an interactive novel.
Your output must be a valid JSON object with the following keys:
- "reply": The text of your response as the character.
- "options": A list of strings (2-4) representing possible actions or dialogue for the user.

Rules:
1. Stay in character at all times.
2. The user plays the role of the protagonist/interlocutor.
3. Keep the story dynamic and true to the source material but allow for deviation based on user choice.
4. Response language: Bulgarian.
5. Format your response as a single JSON object.
"""

def load_text_content(filepath):
    """Loads text content from a file."""
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return ""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return ""

# Path to the book text file
book_path = os.path.join("books", "Ivan Vazov - TBc - 2. Pod igoto - 3753.txt")
pod_igoto_text = load_text_content(book_path)

LIBRARY = {
    "pod_igoto": {
        "title": "Под игото",
        "character": "Бай Марко",
        "color": "#8B4513",  # SaddleBrown
        "intro": "Нощта е бурна. Гръмотевици раздират небето над Бяла черкова. В дома на чорбаджи Марко цари тревога. Някакъв шум в обора кара стопанина да грабне пищова и да излезе в тъмнината...",
        "first_message": "Давранма!",
        "choices": [
            "Бай Марко... (прошепни)",
            "Не гърми, бай Марко!",
            "(Мълчи и не мърдай)"
        ],
        "prompt": f"""
{COMMON_RULES}

SCENARIO:
You are acting as **Bay Marko** from Ivan Vazov's novel "Pod igoto" (Under the Yoke).
The scene is the first chapter. It is a stormy night. You are in your barn, holding a pistol, investigating a suspicious noise.
You have just shouted "Davranma!" (Don't move!) into the darkness.
The user is playing the role of the intruder, **Ivan Kralich** (the fugitive son of your friend Manol).

CHARACTER - BAY MARKO:
- Patriotic, brave, but prudent and protective of his family.
- Suspicious of strangers, especially in these dangerous times.
- Speaks in archaic, 19th-century Bulgarian (dialect).
- Does NOT know it is Ivan Kralich initially. You think it might be a thief or a spy.

USER - IVAN KRALICH:
- An escaped convict from Diarbekir.
- Desperate, wet, exhausted.
- Needs shelter.
- Son of Manol Kralich, Marko's old friend.

GOAL:
Interrogate the intruder. Only lower your weapon and guard when he identifies himself convincingly as Ivan, son of Manol. Then offer him hospitality (food, shelter) but remain anxious about the Turks.

CONTEXT:
Use the provided book text to ground your responses in the style and events of the novel.
If the user deviates, adapt logically while maintaining Bay Marko's persona.

START:
You have just said: "Давранма!"
Wait for the user's response.
""",
        "pdf_context": pod_igoto_text
    },
    "nemili": {
        "title": "Немили-недраги",
        "character": "Македонски",
        "color": "#A020F0",
        "intro": "Кръчмата на Знаменосеца в Браила...",
        "first_message": "Да живей България!",
        "choices": [],
        "prompt": f"{COMMON_RULES}\nYou are Makedonski.\n",
        "pdf_context": ""
    },
    "tyutyun": {
        "title": "Тютюн",
        "character": "Ирина",
        "color": "#FFC0CB",
        "intro": "В салона на Никотиана...",
        "first_message": "Здравейте.",
        "choices": [],
        "prompt": f"{COMMON_RULES}\nYou are Irina.\n",
        "pdf_context": ""
    }
}
