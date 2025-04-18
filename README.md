# MCP Client

安裝 dependencies
```bash
pip install -r requirements.txt
```

建立 MCP server 設定檔 (servers_config.json)，以 GitHub Server 為例
```json
{
  "mcpServers": {
    "github": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "ghcr.io/github/github-mcp-server"
      ],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<YOUR ACCESS TOKEN>"
      }
    }
  }
}
```

## Run API Service

啟動 MCP Service
```bash
uvicorn mcp-service:app
```
- 服務會運行在 port 8000

### Client Example

參考 [mcp-client.py](./mcp-client.py)，使用 RESTful 的形式存取 MCP Service

## Run Chat Demo

- [chat-demo.py](./chat-demo.py) 是完整的 MCP 聊天應用
  - 串接 ChatGPT 3.5 和 [mcp_client](./mcp_client) 模組
- 直接使用 terminal 當作聊天介面
