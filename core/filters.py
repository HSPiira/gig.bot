import re
from transformers import pipeline
from core.logger import logger
from core.config import config

# Initialize the zero-shot classification pipeline
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

candidate_labels = ["freelance gig", "job offer", "advertisement", "discussion"]

def keyword_score_and_filter(text: str) -> (float, bool):
    """
    Determine a weighted keyword score for the text and whether it should be considered a potential gig.
    
    Returns:
        (float, bool): A tuple where the first element is the accumulated weighted score from configured keywords, and the second element is `True` if no negative keyword was found and the score is greater than zero, `False` otherwise.
    """
    text_lower = text.lower()
    for neg_keyword in config.negative_keywords:
        if neg_keyword.lower() in text_lower:
            logger.info(f"Skipping due to negative keyword: '{neg_keyword}'")
            return (0.0, False)

    score = 0.0
    for keyword, weight in config.weighted_keywords.items():
        if keyword.lower() in text_lower:
            score += weight
            
    if score > 0:
        return (score, True)
    
    return (0.0, False)

def extract_budget_info(text: str) -> dict:
    """
    Extracts budget amounts and currency information from freeform text.
    
    Parses currency symbols/codes and numeric amounts (supports commas, decimals, trailing 'k' for thousands and 'm' for millions), detecting either a range or a single fixed price.
    
    Returns:
        dict: Parsed budget information. Possible shapes:
            - Range: {"type": "range", "amount_min": float, "amount_max": float, "currency": str or None}
            - Fixed price: {"type": "fixed_price", "amount": float, "currency": str or None}
            - Empty dict if no amount or range is detected.
    """
    budget_info = {}
    text_lower = text.lower()

    # Enhanced Regex for currency symbols and codes
    currency_map = {
        "$": "USD", "€": "EUR", "£": "GBP", "₹": "INR", "¥": "JPY", "₽": "RUB",
        "ugx": "UGX", "ksh": "KES", "kes": "KES", "usd": "USD", "eur": "EUR", "gbp": "GBP",
        "inr": "INR", "jpy": "JPY", "rub": "RUB",
        "shs": "UGX",
    }
    # Pattern to match currency symbols/codes. Prioritize longer codes.
    sorted_currencies_keys = sorted(currency_map.keys(), key=len, reverse=True)
    currency_pattern_parts = []
    for s in sorted_currencies_keys:
        if len(s) > 1: # For multi-char codes, use word boundary
            currency_pattern_parts.append(r'\b' + re.escape(s) + r'\b')
        else: # For single char symbols, just escape
            currency_pattern_parts.append(re.escape(s))
    currency_pattern = r"(?:" + "|".join(currency_pattern_parts) + r")"

    # Regex for numerical values (with optional 'k' for thousands, 'm' for millions, and commas/decimals)
    amount_core_pattern = r"\d+(?:[.,]\d+)?"
    amount_full_pattern = rf"{amount_core_pattern}(?:[km])?"


    # Helper to parse amount strings
    def parse_amount(amount_str):
        """
        Parse a numeric amount string into a float, handling commas, decimals, and 'k'/'m' multipliers.
        
        Parameters:
            amount_str (str): String containing the amount; may include commas, a decimal point, and an optional trailing
                'k' (thousand) or 'm' (million) multiplier (case-insensitive).
        
        Returns:
            float: The parsed numeric value with multipliers applied. Returns 0.0 if parsing fails.
        """
        amount_str = amount_str.replace(',', '')
        
        multiplier = 1.0
        if amount_str.lower().endswith('k') and amount_str[:-1].replace('.', '', 1).isdigit():
            multiplier = 1000.0
            amount_str = amount_str[:-1]
        elif amount_str.lower().endswith('m') and amount_str[:-1].replace('.', '', 1).isdigit():
            multiplier = 1_000_000.0
            amount_str = amount_str[:-1]
        
        try:
            return float(amount_str) * multiplier
        except ValueError:
            return 0.0


    # --- Range Pattern (checked first) ---
    # Separator: (to|-|between X and Y)
    # Using a non-capturing group for the separator
    range_separator_pattern = r"\s*(?:to|-|between\s+(?:the\s+)?amounts?\s+of\s+|\s*and\s*)\s*" # Improved range separator
    range_regex = re.compile(
        rf"(?:({currency_pattern})\s*)?({amount_full_pattern}){range_separator_pattern}(?:({currency_pattern})\s*)?({amount_full_pattern})(?:\s*({currency_pattern}))?",
        re.IGNORECASE
    )
    range_match = range_regex.search(text_lower)

    if range_match:
        # print(f"DEBUG RANGE GROUPS: {range_match.groups()}") # DEBUG
        
        currency_found_code = None
        # Check group 1, then group 3, then group 5 for currency
        for i in [1, 3, 5]:
            if range_match.group(i):
                if range_match.group(i).lower() in currency_map:
                    currency_found_code = range_match.group(i).lower()
                    break
        # print(f"DEBUG: Potential currencies: {potential_currencies}, Chosen: {currency_found_code}") # DEBUG
            
        amount_min_str = range_match.group(2)
        amount_max_str = range_match.group(4)
        
        budget_info["amount_min"] = parse_amount(amount_min_str)
        budget_info["amount_max"] = parse_amount(amount_max_str)
        budget_info["currency"] = currency_map.get(currency_found_code, None)
        budget_info["type"] = "range"
        return budget_info

    # --- Single Amount Pattern (checked second) ---
    single_amount_regex = re.compile(
        rf"(?:({currency_pattern})\s*)?({amount_full_pattern})(?:\s*({currency_pattern}))?",
        re.IGNORECASE
    )
    single_amount_match = single_amount_regex.search(text_lower)

    if single_amount_match:
        # print(f"DEBUG SINGLE GROUPS: {single_amount_match.groups()}") # DEBUG

        currency_found_code = None
        for i in [1, 3]:
            if single_amount_match.group(i):
                if single_amount_match.group(i).lower() in currency_map:
                    currency_found_code = single_amount_match.group(i).lower()
                    break
        # print(f"DEBUG: Potential currencies: {potential_currencies}, Chosen: {currency_found_code}") # DEBUG

        amount_str = single_amount_match.group(2)
        
        budget_info["amount"] = parse_amount(amount_str)
        budget_info["currency"] = currency_map.get(currency_found_code, None)
        budget_info["type"] = "fixed_price"
        return budget_info

    return {}


def looks_like_gig(text: str) -> bool:
    """
    Determine whether a piece of text resembles a freelance gig or job offer.
    
    Parameters:
        text (str): The text of a posting or message to evaluate.
    
    Returns:
        bool: `true` if the text is considered a gig or job offer, `false` otherwise.
    
    Notes:
        - Empty or missing text is treated as not a gig.
        - The function first applies a keyword-based filter; texts filtered out there are not considered gigs.
        - For remaining texts, a zero-shot classifier is used; a top label of "freelance gig" or "job offer" with a score above 0.4 is required to classify as a gig.
        - If the classifier raises an exception, the function falls back to the keyword score and returns `true` only if that score is greater than zero.
    """
    if not text:
        return False

    keyword_strength, is_potential_gig = keyword_score_and_filter(text)
    if not is_potential_gig:
        logger.info("Skipping based on keyword filter.")
        return False

    truncated_text = " ".join(text.split()[:300])

    try:
        result = classifier(truncated_text, candidate_labels)
        
        top_label = result["labels"][0]
        top_score = result["scores"][0]

        if top_label in ["freelance gig", "job offer"] and top_score > 0.4:
            logger.info(f"✅ Classified as '{top_label}' (Score: {top_score:.2f})")
            return True
        else:
            logger.info(f"⏩ Classified as '{top_label}' (Score: {top_score:.2f}). Skipping.")
            return False

    except Exception as e:
        logger.error(f"🛑 NLP classification error: {e}")
        return keyword_strength > 0

if __name__ == '__main__':
    # For testing the filter directly
    test_text_1 = "We are hiring a Python developer for a quick project. Budget is $200."
    test_text_2 = "Check out this new course on web development! Recruitment agency post."
    test_text_3 = "Urgently looking for a graphic designer for a logo. Pays $50. Full-time position."
    test_text_4 = "Freelance opportunity for a data scientist, budget 10k-15k USD."
    test_text_5 = "Looking for a software engineer, permanent position."
    test_text_6 = "Project cost will be around 500 EUR."
    test_text_7 = "Rate is 20000 UGX per hour."
    test_text_8 = "Offering 2m KSH for the right candidate."
    test_text_9 = "Budget: 1,500 - 2,000 USD."
    test_text_10 = "Pays 50k for the job."


    logger.info(f"Testing: '{test_text_1}'")
    logger.info(f"Is it a gig? -> {looks_like_gig(test_text_1)}")
    logger.info(f"Budget Info: {extract_budget_info(test_text_1)}")
    logger.info("-" * 20)
    logger.info(f"Testing: '{test_text_2}'")
    logger.info(f"Is it a gig? -> {looks_like_gig(test_text_2)}")
    logger.info(f"Budget Info: {extract_budget_info(test_text_2)}")
    logger.info("-" * 20)
    logger.info(f"Testing: '{test_text_3}'")
    logger.info(f"Is it a gig? -> {looks_like_gig(test_text_3)}")
    logger.info(f"Budget Info: {extract_budget_info(test_text_3)}")
    logger.info("-" * 20)
    logger.info(f"Testing: '{test_text_4}'")
    logger.info(f"Is it a gig? -> {looks_like_gig(test_text_4)}")
    logger.info(f"Budget Info: {extract_budget_info(test_text_4)}")
    logger.info("-" * 20)
    logger.info(f"Testing: '{test_text_5}'")
    logger.info(f"Is it a gig? -> {looks_like_gig(test_text_5)}")
    logger.info(f"Budget Info: {extract_budget_info(test_text_5)}")
    logger.info("-" * 20)
    logger.info(f"Testing: '{test_text_6}'")
    logger.info(f"Is it a gig? -> {looks_like_gig(test_text_6)}")
    logger.info(f"Budget Info: {extract_budget_info(test_text_6)}")
    logger.info("-" * 20)
    logger.info(f"Testing: '{test_text_7}'")
    logger.info(f"Is it a gig? -> {looks_like_gig(test_text_7)}")
    logger.info(f"Budget Info: {extract_budget_info(test_text_7)}")
    logger.info("-" * 20)
    logger.info(f"Testing: '{test_text_8}'")
    logger.info(f"Is it a gig? -> {looks_like_gig(test_text_8)}")
    logger.info(f"Budget Info: {extract_budget_info(test_text_8)}")
    logger.info("-" * 20)
    logger.info(f"Testing: '{test_text_9}'")
    logger.info(f"Is it a gig? -> {looks_like_gig(test_text_9)}")
    logger.info(f"Budget Info: {extract_budget_info(test_text_9)}")
    logger.info("-" * 20)
    logger.info(f"Testing: '{test_text_10}'")
    logger.info(f"Is it a gig? -> {looks_like_gig(test_text_10)}")
    logger.info(f"Budget Info: {extract_budget_info(test_text_10)}")
    logger.info("-" * 20)