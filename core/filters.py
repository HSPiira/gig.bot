from .keywords import CHEAP_KEYWORDS, URGENCY_KEYWORDS, DEV_KEYWORDS

def looks_like_gig(text: str) -> bool:
    if not text:
        return False

    text = text.lower()
    score = 0

    for word in CHEAP_KEYWORDS:
        if word in text:
            score += 1

    for word in URGENCY_KEYWORDS:
        if word in text:
            score += 1

    for word in DEV_KEYWORDS:
        if word in text:
            score += 1

    # Adjust threshold to be more/less strict
    return score >= 2
