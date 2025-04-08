# MCP Bot

## Setup

在專案的最上層建立 .env 設定檔，加入 Open Router 的 API Key
```bash
OPEN_ROUTER_API_KEY=<YOUR_KEY>
```

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

在 Terminal 中聊天
```
python3 run.py
```
