import importlib
import os
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

aider_SITE_URL = "https://aider.chat"
aider_APP_NAME = "aider"

os.environ["OR_SITE_URL"] = aider_SITE_URL
os.environ["OR_APP_NAME"] = aider_APP_NAME

# `import litellm` takes 1.5 seconds, defer it!


class LazyLiteLLM:
    _lazy_module = None

    def __getattr__(self, name):
        if name == "_lazy_module":
            return super()
        self._load_litellm()
        return getattr(self._lazy_module, name)

    def _load_litellm(self):
        if self._lazy_module is not None:
            return

        try:
            self._lazy_module = importlib.import_module("litellm")
            self._lazy_module.suppress_debug_info = True
            self._lazy_module.set_verbose = False
            self._lazy_module.drop_params = True
        except ImportError as e:
            print(f"Erreur lors de l'importation de litellm: {e}")
            raise

    def exceptions(self):
        self._load_litellm()
        return self._lazy_module.exceptions


litellm = LazyLiteLLM()

def retry_exceptions():
    return (
        litellm.exceptions.OpenAIError,
        #litellm.exceptions.AzureOpenAIError,
        #litellm.exceptions.AnthropicError,
        litellm.exceptions.BingAIError,
        litellm.exceptions.GooglePalmError,
        litellm.exceptions.HuggingfaceError,
        litellm.exceptions.ReplicateError,
        litellm.exceptions.TogetherAIError,
        litellm.exceptions.AlephAlphaError,
        litellm.exceptions.NLPCloudError,
        litellm.exceptions.VertexAIError,
        litellm.exceptions.CohereBadRequestError,
        litellm.exceptions.AnthropicRateLimitError,
    )

__all__ = [litellm, retry_exceptions]
