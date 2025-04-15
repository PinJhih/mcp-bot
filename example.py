import json

import requests

BASE_URL = "http://localhost:8000"


def get_system_prompt():
    url = f"{BASE_URL}/system_prompt"
    response = requests.get(url)
    if response.ok:
        print("System Prompt:")
        print(response.json()["system_prompt"])
    else:
        print("Failed to get system prompt:", response.text)


def get_tools(server: str):
    url = f"{BASE_URL}/tools/{server}"
    response = requests.get(url)
    if response.ok:
        print(f"Tools of server '{server}':")
        print(response.json()["tools"])
    else:
        print(f"Failed to get tools for server '{server}':", response.text)


def execute_tool(server: str, tool: str, args: str):
    url = f"{BASE_URL}/execute/{server}/{tool}"
    args = json.loads(args)
    response = requests.post(url, json=args)
    if response.ok:
        print("Tool Execution Result:")
        print(response.json())
    else:
        print("Failed to execute tool:", response.text)


if __name__ == "__main__":
    get_system_prompt()

    server_name = "filesystem"
    get_tools(server_name)

    tool_name = "write_file"
    arguments = '{"path": "/data/test.txt", "content": "Test Message"}'
    execute_tool(server_name, tool_name, arguments)
