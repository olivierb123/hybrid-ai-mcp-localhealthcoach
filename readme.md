# Local Health Context MCP Server

This project implements a local MCP (Model Context Protocol) server that exposes a tool (`get_patient_background`) to an Azure AI Foundry hosted agent.  
It enables a cloud-based medical “specialist” agent to call into your private local LLM to fetch personal health context without sending sensitive data to the cloud.

This demonstrates a true Hybrid AI pattern:

- Sensitive data stays entirely on your machine  
- The cloud agent handles reasoning and diagnosis  
- A local LLM (via Foundry Local) provides private background  
- A Dev Tunnel exposes your MCP server securely  
- Azure AI Foundry orchestrates tool calling  

---

## Architecture Overview

User -> Cloud Agent (Azure AI Foundry) -> (MCP Tool Call) -> Dev Tunnel -> Local MCP Server -> Local GPU LLM (Foundry Local)

Workflow:

1. User reports symptoms to the cloud agent  
2. The agent calls the MCP tool to request personal background  
3. The MCP server loads your local `patient_profile.json`  
4. It sends a prompt to your local GPU LLM  
5. The anonymized summary is returned to the cloud agent  

---

## Repository Structure

```
src/
  mcp-local-health.py # MCP server + GPU inference logic
  patient_profile.json # User’s private medical history
  requirements.txt            # Python dependencies
README.md
```

---

## Setup

### 1. Create and activate a virtual environment

**Windows:**
python -m venv .venv
..venv\Scripts\activate

**macOS/Linux:**
python3 -m venv .venv
source .venv/bin/activate


### 2. Install dependencies
pip install -r requirements.txt


---

## Configure Your Local Medical Profile

Edit the file `patient_profile.json`.

Example:

```json
{
  "chronic_conditions": ["mild asthma"],
  "medications": ["albuterol inhaler"],
  "recent_labs": {
    "A1C": 5.4,
    "Vitamin D": 32
  }
}
```

This file remains local and is never transmitted.

## Run the MCP Server
python mcp-local-health.py

You should see:
[MCP] Listening at http://0.0.0.0:8081

## Expose the MCP Server Using Dev Tunnels

### Create the tunnel
devtunnel create mcp-health

### Add port 8081
devtunnel port create mcp-health -p 8081 --protocol http

### Host the tunnel
devtunnel host mcp-health

You will get a public URL such as:
https://abcd1234.usw3.devtunnels.ms:8081

## Connect the Tool in Azure AI Foundry

Open your agent → Tools → Add Tool → MCP.

Fill in:

| Setting        | Value                  |
| -------------- | ---------------------- |
| Name           | get_patient_background |
| Endpoint       | your Dev Tunnel URL    |
| Authentication | None (demo)            |

Save — the cloud agent now calls your local LLM tool.

## License
MIT License


