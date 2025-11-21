#!/usr/bin/env python3
import sys
import json
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
import re

HOST = "0.0.0.0"
PORT = 8081

# ------------------- FOUNDry LOCAL CONFIG ---------------------
FOUNDRY_LOCAL_BASE_URL = "http://127.0.0.1:52403"
FOUNDRY_LOCAL_CHAT_URL = f"{FOUNDRY_LOCAL_BASE_URL}/v1/chat/completions"
FOUNDRY_LOCAL_MODEL_ID = "Phi-4-mini-instruct-cuda-gpu:5"
# --------------------------------------------------------------

### Local "memory" (your personal medical history)
LOCAL_PATIENT_PROFILE = """
Patient Profile:
- Age: 38
- Chronic conditions: Mild asthma diagnosed at age 12
- Allergies: Penicillin
- Recent labs: Elevated CRP and ESR last month
- Lifestyle: Non-smoker, exercises 3x/week
- Medications: Albuterol inhaler PRN
"""

### System prompt for the local LLM
LOCAL_BACKGROUND_SYSTEM_PROMPT = f"""
You are a personal medical context assistant running locally on the user's machine.
You know the following private long-term health background:

{LOCAL_PATIENT_PROFILE}

When given the user's symptoms, respond with structured JSON:

{{
  "relevant_background": [
      {{ "fact": "string" }},
      ...
  ],
  "reasoning_for_relevancy": "short explanation"
}}

Be concise and accurate.
"""


# ---------------------------------------------------------------
# Utility: strip ```json fences
# ---------------------------------------------------------------
def strip_code_fences(text: str) -> str:
    text = re.sub(r"^```json", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"^```", "", text.strip())
    text = re.sub(r"```$", "", text.strip())
    return text.strip()


# ---------------------------------------------------------------
# GPU Inference (Foundry Local)
# ---------------------------------------------------------------
def summarize_patient_background_locally(symptoms: str):
    """
    Calls Foundry Local (GPU) to analyze symptoms + patient background.
    """

    payload = {
        "model": FOUNDRY_LOCAL_MODEL_ID,
        "messages": [
            {"role": "system", "content": LOCAL_BACKGROUND_SYSTEM_PROMPT},
            {"role": "user", "content": symptoms},
        ],
        "max_tokens": 300,
        "temperature": 0.1,
    }

    print(f"[LOCAL] POST {FOUNDRY_LOCAL_CHAT_URL}")

    try:
        resp = requests.post(
            FOUNDRY_LOCAL_CHAT_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=60,
        )
        resp.raise_for_status()
    except Exception as e:
        print("[LOCAL] ERROR calling Foundry Local:", e)
        return None

    data = resp.json()
    content = data["choices"][0]["message"]["content"]

    if isinstance(content, list):
        content_text = "".join(part.get("text", "") for part in content)
    else:
        content_text = content

    print("[LOCAL] Raw content:")
    print(content_text)

    cleaned = strip_code_fences(content_text)

    try:
        parsed = json.loads(cleaned)
    except Exception as e:
        print("[LOCAL] Failed to parse JSON:", e)
        print("[LOCAL] Cleaned content was:\n", cleaned)
        return None

    print("[LOCAL] Parsed JSON summary:")
    print(json.dumps(parsed, indent=2))

    return parsed


# ---------------------------------------------------------------
# MCP Request Handling
# ---------------------------------------------------------------
def handle_mcp_request(req):
    method = req.get("method")
    req_id = req.get("id")

    # ========== Debug: show all inbound requests ==========
    print("=== MCP RECEIVED REQUEST ===")
    print(json.dumps(req, indent=2))
    print("================================")

    # -----------------------------------------------------
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "serverInfo": {
                    "name": "LocalPatientContextServer",
                    "version": "1.0.0",
                },
            },
        }

    # -----------------------------------------------------
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "get_patient_background",
                        "description": "Provides patient medical context relevant to the given symptoms using the local GPU model.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"symptoms": {"type": "string"}},
                            "required": ["symptoms"],
                        },
                    }
                ]
            },
        }

    # -----------------------------------------------------
    if method == "tools/call":
        params = req.get("params", {})
        tool = params.get("name")
        args = params.get("arguments", {})

        print("=== MCP RECEIVED TOOL CALL ===")
        print(json.dumps(req, indent=2))
        print("================================")

        if tool == "get_patient_background":
            symptoms = args.get("symptoms", "")

            summary = summarize_patient_background_locally(symptoms)

            print("=== LOCAL GPU MODEL OUTPUT ===")
            print(json.dumps(summary, indent=2))
            print("================================")

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(summary)}
                    ]
                },
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown tool '{tool}'"},
        }

    # -----------------------------------------------------
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method '{method}'"},
    }


# ---------------------------------------------------------------
# HTTP Handler
# ---------------------------------------------------------------
class MCPHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        self.wfile.write(b"OK")

    def do_POST(self):
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(content_len)

            print("---- RAW BODY ----")
            print(raw)
            print("-------------------")

            try:
                req = json.loads(raw.decode("utf-8"))
            except:
                self._set_headers(400)
                self.wfile.write(b'{"error":"Invalid JSON"}')
                return

            resp = handle_mcp_request(req)
            self._set_headers(200)
            self.wfile.write(json.dumps(resp).encode("utf-8"))

        except Exception as e:
            print("Exception:", e)
            self._set_headers(500)
            self.wfile.write(json.dumps({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": "Internal server error"},
            }).encode("utf-8"))


# ---------------------------------------------------------------
def main():
    print(f"[MCP] Listening at http://{HOST}:{PORT}")
    server = HTTPServer((HOST, PORT), MCPHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
