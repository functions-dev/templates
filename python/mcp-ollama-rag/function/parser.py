import requests
from urllib.parse import urlparse

def parse_data_generator(data):
    """
    Generator that yields documents one at a time.
    Handles any combination of urls and data strings.
    Can be of type str|list.
    example:
    ["<url1>","<url2>","long data string"] etc.
    """

    # STR
    if isinstance(data, str):
        content = ''
        if is_url(data):
            content = get_raw_content(data)
        else:
            content = data
        yield content.strip()

    # LIST
    elif isinstance(data, list):
        for item in data:
            if isinstance(item,str):
                if is_url(item):
                    content = get_raw_content(item)
                else:
                    content = item
                yield content.strip()
            else:
                print(f"warning: handling item {item} as a string")
                yield str(item)
    else:
        print(f"Fallback: unknown type, handling {data} as a string")
        yield str(data)

def is_url(text: str):
    """Check if text is a valid URL"""
    try:
        result = urlparse(text)
        print(f"is_url: {result}")
        return all([result.scheme, result.netloc])
    except:
        return False

# Accepts any url link which points to a raw data (*.md/text files etc.)
# example: https://raw.githubusercontent.com/knative/func/main/docs/function-templates/python.md
def get_raw_content(url: str) -> str:
    """ retrieve contents of github raw url as a text """
    response = requests.get(url)
    response.raise_for_status() # errors if bad response
    print(f"fetch '{url}' - ok")
    return response.text
