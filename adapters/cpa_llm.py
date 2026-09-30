import re
import requests
from core.ports import LLMPort

class CPALlmAdapter(LLMPort):
    """Adapter gọi LLM qua Local CPA Proxy (OpenAI compatible endpoint)"""
    def __init__(self, endpoint_url: str = "http://localhost:8317/v1/chat/completions", 
                 model_name: str = "gemini-3.5-flash-lite", 
                 temperature: float = 0.0, 
                 timeout_seconds: int = 45):
        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds

    def generate_sql(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 800
        }

        try:
            resp = requests.post(self.endpoint_url, json=payload, timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            return self._clean_sql_markdown(raw_text)
        except Exception as e:
            print(f"[CPALlmAdapter] Error calling LLM: {e}")
            return ""

    @staticmethod
    def _clean_sql_markdown(raw_text: str) -> str:
        """Hàm thuần (Pure Function): Bóc tách câu lệnh SQL từ khối markdown"""
        text = raw_text.strip()
        # Tìm khối ```sql ... ```
        match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text
