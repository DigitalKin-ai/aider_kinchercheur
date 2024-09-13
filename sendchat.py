import hashlib
import json
import time
from typing import List, Dict, Any, Optional

import backoff
import litellm
from litellm import completion, RateLimitError, APIError, APIConnectionError, ServiceUnavailableError

from aider.dump import dump  # noqa: F401

CACHE_PATH = "~/.aider.send.cache.v1"
CACHE = None

def retry_exceptions():
    return (
        APIConnectionError,
        APIError,
        RateLimitError,
        ServiceUnavailableError,
    )

def lazy_litellm_retry_decorator(func):
    def wrapper(*args, **kwargs):
        decorated_func = backoff.on_exception(
            backoff.expo,
            retry_exceptions(),
            max_time=60,
            on_backoff=lambda details: print(
                f"{details.get('exception', 'Exception')}\nRetry in {details['wait']:.1f} seconds."
            ),
        )(func)
        return decorated_func(*args, **kwargs)

    return wrapper

def send_completion(
    model_name, messages, functions, stream, temperature=0, extra_headers=None, max_tokens=None
):
    kwargs = dict(
        model=model_name,
        messages=messages,
        temperature=temperature,
        stream=stream,
    )

    if functions is not None:
        function = functions[0]
        kwargs["tools"] = [dict(type="function", function=function)]
        kwargs["tool_choice"] = {"type": "function", "function": {"name": function["name"]}}
    if extra_headers is not None:
        kwargs["extra_headers"] = extra_headers
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    key = json.dumps(kwargs, sort_keys=True).encode()

    hash_object = hashlib.sha1(key)

    if not stream and CACHE is not None and key in CACHE:
        return hash_object, CACHE[key]

    res = completion(**kwargs)

    if not stream and CACHE is not None:
        CACHE[key] = res

    return hash_object, res

@lazy_litellm_retry_decorator
def simple_send_with_retries(
    model_name: str, 
    messages: List[Dict[str, Any]], 
    extra_headers: Optional[Dict[str, str]] = None,
    **kwargs
) -> Dict[str, Any]:
    try:
        return litellm.completion(
            model=model_name,
            messages=messages,
            extra_headers=extra_headers,
            **kwargs
        )
    except Exception as e:
        if hasattr(e, 'status_code') and e.status_code == 400:
            raise ValueError("Bad Request: " + str(e))
        else:
            raise

def send_with_retries(
    model_name: str, 
    messages: List[Dict[str, Any]], 
    extra_headers: Optional[Dict[str, str]] = None,
    **kwargs
) -> str:
    max_retries = 5
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            response = completion(
                model=model_name, 
                messages=messages, 
                extra_headers=extra_headers,
                **kwargs
            )
            return response.choices[0].message.content
        except retry_exceptions() as e:
            if attempt < max_retries - 1:
                print(f"Error: {e}. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                raise

    raise Exception("Max retries reached. Unable to get a response.")
