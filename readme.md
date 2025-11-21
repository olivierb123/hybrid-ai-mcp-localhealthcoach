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

User
↓
Cloud Agent (Azure AI Foundry)
↓ (MCP Tool Call)
Dev Tunnel
↓
Local MCP Server
↓
Local GPU LLM (Foundry Local)


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


