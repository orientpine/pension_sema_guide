# Exa MCP Timeout 오류 해결 가이드

## 진단 결과

### 근본 원인
**Exa API Key 미설정**

사용자가 Exa API 키를 어디에 입력해야 하는지 모르는 상태에서 OpenCode가 Exa MCP 서버에 연결을 시도하여 인증 실패 → 타임아웃 발생.

### 증상
- OpenCode 시작 시 100% 발생
- MCP 서버 연결 타임아웃 (5초 기본값)
- Exa 검색 도구 사용 불가

---

## 해결 방법

### 방법 1: Remote MCP 사용 (권장 - 가장 간단)

Exa는 **호스팅된 Remote MCP 서버**를 제공합니다. API 키 없이도 기본 기능 사용 가능!

#### 1단계: OpenCode 설정 파일 찾기/생성

OpenCode 설정 파일 위치:
- **프로젝트별**: `{프로젝트폴더}/.opencode/opencode.jsonc`
- **전역**: `~/.opencode/opencode.jsonc`

#### 2단계: Remote Exa MCP 설정 추가

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "exa": {
      "type": "remote",
      "url": "https://mcp.exa.ai/mcp"
    }
  }
}
```

**API 키를 URL에 포함하려면** (더 높은 rate limit):
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "exa": {
      "type": "remote",
      "url": "https://mcp.exa.ai/mcp?exaApiKey=YOUR_EXA_API_KEY"
    }
  }
}
```

#### 3단계: OpenCode 재시작

---

### 방법 2: API 키 발급 및 Local MCP 설정

#### 1단계: Exa API 키 발급

1. **https://dashboard.exa.ai** 접속
2. **Google 계정으로 로그인** (또는 새 계정 생성)
3. 대시보드에서 **API Key** 복사

#### 2단계: 환경 변수 설정 (Windows)

**영구 설정** (시스템 환경 변수):
```powershell
# PowerShell (관리자 권한)
[System.Environment]::SetEnvironmentVariable("EXA_API_KEY", "your-api-key-here", "User")
```

**또는 터미널 세션에서 임시 설정**:
```powershell
$env:EXA_API_KEY = "your-api-key-here"
```

#### 3단계: Local MCP 설정

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "exa": {
      "type": "local",
      "command": ["npx", "-y", "exa-mcp-server"],
      "environment": {
        "EXA_API_KEY": "{env:EXA_API_KEY}"
      }
    }
  }
}
```

#### 4단계: OpenCode 재시작

---

### 방법 3: Exa MCP 비활성화 (임시 해결)

Exa가 필요 없다면 MCP 서버를 비활성화:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "exa": {
      "type": "remote",
      "url": "https://mcp.exa.ai/mcp",
      "enabled": false
    }
  }
}
```

또는 tools에서 비활성화:
```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "tools": {
    "exa*": false
  }
}
```

---

## 설정 확인 방법

### MCP 서버 상태 확인

```bash
opencode mcp list
```

예상 출력:
```
✓ exa connected
    https://mcp.exa.ai/mcp
```

### MCP 디버그

```bash
opencode mcp debug exa
```

---

## 타임아웃 조정

연결이 느린 경우 타임아웃 증가:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "exa": {
      "type": "remote",
      "url": "https://mcp.exa.ai/mcp",
      "timeout": 10000
    }
  }
}
```

기본값: 5000ms (5초)
권장: 10000ms (10초) 이상

---

## 대안: 다른 검색 MCP

Exa 대신 사용 가능한 MCP 서버:

### Context7 (무료, API 키 불필요)
```jsonc
{
  "mcp": {
    "context7": {
      "type": "remote",
      "url": "https://mcp.context7.com/mcp"
    }
  }
}
```

### Grep by Vercel (무료, API 키 불필요)
```jsonc
{
  "mcp": {
    "gh_grep": {
      "type": "remote",
      "url": "https://mcp.grep.app"
    }
  }
}
```

---

## 체크리스트

- [ ] Exa 대시보드에서 API 키 발급
- [ ] OpenCode 설정 파일 생성/수정
- [ ] MCP 서버 설정 추가
- [ ] OpenCode 재시작
- [ ] `opencode mcp list`로 연결 확인
- [ ] 검색 기능 테스트

---

## 참고 자료

- [Exa API 대시보드](https://dashboard.exa.ai)
- [Exa MCP 문서](https://docs.exa.ai/reference/exa-mcp)
- [OpenCode MCP 설정 문서](https://opencode.ai/docs/mcp)
- [Exa MCP GitHub](https://github.com/exa-labs/exa-mcp-server)

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|:----:|:----:|----------|
| v1.0 | 2026-01-05 | 최초 작성 |
