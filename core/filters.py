from transformers import pipeline

# Initialize the zero-shot classification pipeline
# This will download the model on the first run
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# Define the labels for classification
candidate_labels = ["freelance gig", "job offer", "advertisement", "discussion"]

def looks_like_gig(text: str) -> bool:
    """
    Uses a zero-shot classification model to determine if a text is a freelance gig.
    """
    if not text:
        return False

    # The model works best with texts that are not too long.
    # Truncate to the first 512 tokens (words/sub-words).
    # This is a reasonable length for a post.
    truncated_text = " ".join(text.split()[:300])

    try:
        result = classifier(truncated_text, candidate_labels)
        
        # Check if "freelance gig" or "job offer" is the top label with a reasonable score
        top_label = result["labels"][0]
        top_score = result["scores"][0]

        if top_label in ["freelance gig", "job offer"] and top_score > 0.4:
            print(f"✅ Classified as '{top_label}' (Score: {top_score:.2f})")
            return True
        else:
            print(f"⏩ Classified as '{top_label}' (Score: {top_score:.2f}). Skipping.")
            return False

    except Exception as e:
        print(f"🛑 NLP classification error: {e}")
        # Fallback to a simple keyword check in case of an error
        return "hiring" in text.lower() or "looking for" in text.lower()

if __name__ == '__main__':
    # For testing the filter directly
    test_text_1 = "We are hiring a Python developer for a quick project. Budget is $200."
    test_text_2 = "Check out this new course on web development!"
    test_text_3 = "Urgently looking for a graphic designer for a logo. Pays $50."

    print(f"Testing: '{test_text_1}'")
    print(f"Is it a gig? -> {looks_like_gig(test_text_1)}")
    print("-" * 20)
    print(f"Testing: '{test_text_2}'")
    print(f"Is it a gig? -> {looks_like_gig(test_text_2)}")
    print("-" * 20)
    print(f"Testing: '{test_text_3}'")
    print(f"Is it a gig? -> {looks_like_gig(test_text_3)}")