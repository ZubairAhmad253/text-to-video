import re

MAX_WORDS_PER_SCENE = 16


def split_into_scenes(text: str) -> list[str]:
    """Split text into scenes: one per sentence, long sentences broken into caption-sized chunks."""
    scenes = []
    for paragraph in text.splitlines():
        paragraph = " ".join(paragraph.split())
        if not paragraph:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
            words = sentence.split()
            if not words:
                continue
            chunks = -(-len(words) // MAX_WORDS_PER_SCENE)  # ceil division
            size = -(-len(words) // chunks)                 # even chunk sizes
            for i in range(0, len(words), size):
                scenes.append(" ".join(words[i:i + size]))
    return scenes
