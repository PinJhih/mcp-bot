# MCP Bot

## Setup

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

## Run

啟動 MCP API 服務
```bash
uvicorn api:app
```
- 服務會運行在 port 8000

## Client Example

參考 [example.py](./example.py)，使用 RESTful 的形式存取其他 MCP 功能
