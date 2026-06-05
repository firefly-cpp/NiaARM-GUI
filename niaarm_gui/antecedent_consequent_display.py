import re

def clean_rule_text(rule_text):
    """Cleans the text with brackets"""
    # Removes outer brackets
    text = rule_text.strip()
    if text.startswith('[') and text.endswith(']'):
        text = text[1:-1]
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]

    # Removes inner round brackets
    text = text.replace('([', '[').replace('])', ']')

    # Rounds numbers inside brackets to 3 decimal places
    text = round_numbers_in_brackets(text)

    return text

def round_numbers_in_brackets(text):
    """Rounds the numbers to 3 decimal places, but only if they already have more than 3 decimal places"""
    def replace_number(match):
        try:
            original = match.group(0)
            number = float(original)

            # Checks for decimal point and if the number has more than 3 decimal places
            if '.' in original:
                decimal_part = original.split('.')[1]
                # Odstrani trailing zeros za pravilno štetje
                decimal_part_stripped = decimal_part.rstrip('0')

                if len(decimal_part_stripped) > 3:
                    # Zaokroži na 3 decimalna mesta
                    return f"{number:.3f}"

            return original
        except:
            return match.group(0)

    def process_bracket_content(match):
        bracket_content = match.group(1)
        rounded_content = re.sub(r'-?\d+\.?\d*', replace_number, bracket_content)
        return f"[{rounded_content}]"

    result = re.sub(r'\[([^\]]+)\]', process_bracket_content, text)
    return result

def split_attributes(text):
    """Splits the attributes in the text"""
    attributes = []
    current = ""
    depth = 0

    for char in text:
        if char == '[' or char == '(':
            depth += 1
            current += char
        elif char == ']' or char == ')':
            depth -= 1
            current += char
        elif char == ',' and depth == 0:
            if current.strip():
                attributes.append(current.strip())
            current = ""
        else:
            current += char

    if current.strip():
        attributes.append(current.strip())

    return attributes