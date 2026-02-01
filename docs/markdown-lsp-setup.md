# Markdown LSP 설정 가이드 (OpenCode)

## 1. Marksman 설치

```bash
# Linux
curl -L https://github.com/artempyanykh/marksman/releases/latest/download/marksman-linux-x64 -o ~/.local/bin/marksman && chmod +x ~/.local/bin/marksman

# macOS (Intel)
curl -L https://github.com/artempyanykh/marksman/releases/latest/download/marksman-macos -o ~/.local/bin/marksman && chmod +x ~/.local/bin/marksman

# macOS (Apple Silicon)
curl -L https://github.com/artempyanykh/marksman/releases/latest/download/marksman-macos-arm -o ~/.local/bin/marksman && chmod +x ~/.local/bin/marksman
```

## 2. 설치 확인

```bash
~/.local/bin/marksman --version
```

## 3. OpenCode 설정

`~/.config/opencode/oh-my-opencode.json`에 추가:

```json
{
  "lsp": {
    "marksman": {
      "command": ["/home/YOUR_USERNAME/.local/bin/marksman", "server"],
      "extensions": [".md"]
    }
  }
}
```

> ⚠️ `YOUR_USERNAME`을 실제 사용자명으로 변경하거나, `$HOME` 대신 절대 경로 사용

## 4. 테스트

OpenCode 재시작 후 아무 `.md` 파일에서 LSP 기능 확인.
