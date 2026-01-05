/**
 * Audit Logger for Portfolio Analysis
 * Multi-agent 포트폴리오 분석의 감사 추적을 위한 로거
 * 
 * 기능:
 * - 데이터 접근 로그
 * - 웹검색 로그
 * - 에이전트 호출 로그
 * - 추천 결과 로그
 * 
 * Usage:
 *   const { AuditLogger } = require('./audit_logger');
 *   const logger = new AuditLogger('session_123');
 *   logger.logDataAccess('fund_data.json', ['return1m', 'return3m']);
 *   logger.save();
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

class AuditLogger {
  /**
   * @param {string} sessionId - 세션 식별자
   * @param {Object} options - 옵션
   */
  constructor(sessionId, options = {}) {
    this.sessionId = sessionId || this.generateSessionId();
    this.startTime = new Date().toISOString();
    this.logDir = options.logDir || path.join(__dirname, '..', 'logs');
    this.entries = [];
    
    // 로그 디렉토리 생성
    if (!fs.existsSync(this.logDir)) {
      fs.mkdirSync(this.logDir, { recursive: true });
    }
    
    this.logPath = path.join(
      this.logDir,
      `audit_${this.sessionId}_${Date.now()}.json`
    );
    
    // 시작 로그
    this.log({
      type: 'SESSION_START',
      sessionId: this.sessionId,
      startTime: this.startTime
    });
  }
  
  /**
   * 세션 ID 생성
   */
  generateSessionId() {
    return `ses_${crypto.randomBytes(8).toString('hex')}`;
  }
  
  /**
   * 기본 로그 엔트리 추가
   * @param {Object} entry - 로그 엔트리
   */
  log(entry) {
    this.entries.push({
      timestamp: new Date().toISOString(),
      ...entry
    });
  }
  
  /**
   * 데이터 파일 접근 로그
   * @param {string} file - 파일 경로
   * @param {Array<string>} fields - 접근한 필드 목록
   */
  logDataAccess(file, fields = []) {
    this.log({
      type: 'DATA_ACCESS',
      file,
      fields,
      hash: this.hashFile(file)
    });
  }
  
  /**
   * 웹검색 로그
   * @param {string} query - 검색 쿼리
   * @param {Array<Object>} results - 검색 결과
   */
  logWebSearch(query, results = []) {
    this.log({
      type: 'WEB_SEARCH',
      query,
      resultCount: results.length,
      urls: results.map(r => r.url || r.link || 'unknown'),
      sources: results.map(r => r.source || r.domain || 'unknown')
    });
  }
  
  /**
   * 에이전트 호출 로그
   * @param {string} agent - 에이전트 이름
   * @param {string} action - 수행 동작
   * @param {Object} input - 입력 데이터 (요약)
   * @param {Object} output - 출력 데이터 (요약)
   */
  logAgentCall(agent, action, input = {}, output = {}) {
    this.log({
      type: 'AGENT_CALL',
      agent,
      action,
      input: this.summarize(input),
      output: this.summarize(output),
      duration: output.duration || null
    });
  }
  
  /**
   * 규제 준수 검증 로그
   * @param {Object} compliance - 검증 결과
   */
  logCompliance(compliance) {
    this.log({
      type: 'COMPLIANCE_CHECK',
      result: compliance.compliance ? 'PASS' : 'FAIL',
      violations: compliance.violations || [],
      warnings: compliance.warnings || [],
      summary: compliance.summary || {}
    });
  }
  
  /**
   * 출력 검증 로그
   * @param {Object} verification - 검증 결과
   */
  logVerification(verification) {
    this.log({
      type: 'OUTPUT_VERIFICATION',
      verified: verification.verified,
      confidenceScore: verification.confidence_score,
      grade: verification.grade,
      issues: verification.issues || []
    });
  }
  
  /**
   * 포트폴리오 추천 로그
   * @param {Array<Object>} portfolio - 추천 포트폴리오
   * @param {Object} metadata - 메타데이터
   */
  logRecommendation(portfolio, metadata = {}) {
    this.log({
      type: 'RECOMMENDATION',
      portfolio: portfolio.map(f => ({
        name: f.name,
        weight: f.weight,
        category: f.category || 'unknown',
        riskAsset: f.riskAsset
      })),
      riskProfile: metadata.riskProfile || 'unknown',
      totalRiskWeight: metadata.totalRiskWeight || null,
      complianceStatus: metadata.complianceStatus || null,
      version: '1.0'
    });
  }
  
  /**
   * 에러 로그
   * @param {string} source - 에러 발생 소스
   * @param {Error|string} error - 에러 객체 또는 메시지
   */
  logError(source, error) {
    this.log({
      type: 'ERROR',
      source,
      message: error.message || error,
      stack: error.stack || null
    });
  }
  
  /**
   * 세션 종료 로그
   * @param {string} status - 종료 상태 ('success', 'failure', 'partial')
   * @param {Object} summary - 최종 요약
   */
  logSessionEnd(status, summary = {}) {
    this.log({
      type: 'SESSION_END',
      status,
      endTime: new Date().toISOString(),
      duration: this.calculateDuration(),
      summary: {
        totalEntries: this.entries.length,
        dataAccesses: this.entries.filter(e => e.type === 'DATA_ACCESS').length,
        webSearches: this.entries.filter(e => e.type === 'WEB_SEARCH').length,
        agentCalls: this.entries.filter(e => e.type === 'AGENT_CALL').length,
        errors: this.entries.filter(e => e.type === 'ERROR').length,
        ...summary
      }
    });
  }
  
  /**
   * 파일 해시 계산
   * @param {string} filePath - 파일 경로
   */
  hashFile(filePath) {
    try {
      const fullPath = path.isAbsolute(filePath) 
        ? filePath 
        : path.join(__dirname, '..', filePath);
      
      if (!fs.existsSync(fullPath)) {
        return 'file_not_found';
      }
      
      const content = fs.readFileSync(fullPath);
      return crypto.createHash('sha256').update(content).digest('hex').slice(0, 16);
    } catch (e) {
      return 'hash_error';
    }
  }
  
  /**
   * 데이터 요약 (대용량 데이터 축소)
   * @param {*} data - 요약할 데이터
   */
  summarize(data) {
    if (!data) return null;
    
    if (typeof data === 'string') {
      return data.length > 500 ? data.slice(0, 500) + '...' : data;
    }
    
    if (Array.isArray(data)) {
      return {
        count: data.length,
        sample: data.slice(0, 3)
      };
    }
    
    if (typeof data === 'object') {
      const keys = Object.keys(data);
      if (keys.length > 10) {
        return {
          keyCount: keys.length,
          sampleKeys: keys.slice(0, 10)
        };
      }
      return data;
    }
    
    return data;
  }
  
  /**
   * 세션 소요 시간 계산
   */
  calculateDuration() {
    const start = new Date(this.startTime);
    const end = new Date();
    return Math.round((end - start) / 1000); // 초 단위
  }
  
  /**
   * 로그 저장
   * @returns {string} - 저장된 파일 경로
   */
  save() {
    const logData = {
      sessionId: this.sessionId,
      startTime: this.startTime,
      endTime: new Date().toISOString(),
      duration: this.calculateDuration(),
      entryCount: this.entries.length,
      entries: this.entries
    };
    
    fs.writeFileSync(
      this.logPath,
      JSON.stringify(logData, null, 2),
      'utf8'
    );
    
    console.log(`Audit log saved: ${this.logPath}`);
    return this.logPath;
  }
  
  /**
   * 로그 불러오기
   * @param {string} logPath - 로그 파일 경로
   * @returns {Object} - 로그 데이터
   */
  static load(logPath) {
    if (!fs.existsSync(logPath)) {
      throw new Error(`Log file not found: ${logPath}`);
    }
    return JSON.parse(fs.readFileSync(logPath, 'utf8'));
  }
  
  /**
   * 최근 로그 목록 조회
   * @param {number} limit - 최대 개수
   * @returns {Array<Object>} - 로그 파일 정보 목록
   */
  static listLogs(limit = 10) {
    const logDir = path.join(__dirname, '..', 'logs');
    
    if (!fs.existsSync(logDir)) {
      return [];
    }
    
    const files = fs.readdirSync(logDir)
      .filter(f => f.startsWith('audit_') && f.endsWith('.json'))
      .map(f => {
        const fullPath = path.join(logDir, f);
        const stat = fs.statSync(fullPath);
        return {
          file: f,
          path: fullPath,
          size: stat.size,
          created: stat.birthtime
        };
      })
      .sort((a, b) => b.created - a.created)
      .slice(0, limit);
    
    return files;
  }
}

/**
 * 포트폴리오 분석 감사 워크플로우 예시
 */
function exampleUsage() {
  // 1. 로거 생성
  const logger = new AuditLogger();
  
  // 2. 데이터 접근 로그
  logger.logDataAccess('fund_data.json', ['name', 'return3m', 'riskLevel']);
  logger.logDataAccess('fund_classification.json', ['riskAsset', 'category']);
  logger.logDataAccess('fund_fees.json', ['totalFee']);
  
  // 3. 웹검색 로그
  logger.logWebSearch('2026 반도체 AI 전망', [
    { url: 'https://bloomberg.com/...', source: 'Bloomberg' },
    { url: 'https://reuters.com/...', source: 'Reuters' }
  ]);
  
  // 4. 에이전트 호출 로그
  logger.logAgentCall('fund-analyst', 'portfolio_recommendation', 
    { riskProfile: '공격형', constraints: ['DC형 70% 한도'] },
    { portfolioCount: 7, duration: 15000 }
  );
  
  // 5. 규제 준수 로그
  logger.logCompliance({
    compliance: true,
    violations: [],
    warnings: [{ rule: 'RISK_NEAR_LIMIT', message: '위험자산 70%' }],
    summary: { riskWeight: 70, safeWeight: 30 }
  });
  
  // 6. 출력 검증 로그
  logger.logVerification({
    verified: true,
    confidence_score: 92,
    grade: 'A',
    issues: []
  });
  
  // 7. 추천 결과 로그
  logger.logRecommendation([
    { name: '삼성글로벌반도체UH', weight: 15, riskAsset: true },
    { name: '삼성미국S&P500UH', weight: 20, riskAsset: true },
    { name: '키움더드림단기채', weight: 15, riskAsset: false }
  ], {
    riskProfile: '공격형',
    totalRiskWeight: 70,
    complianceStatus: 'PASS'
  });
  
  // 8. 세션 종료 및 저장
  logger.logSessionEnd('success', { recommendation: 'generated' });
  const logPath = logger.save();
  
  console.log('\n=== Audit Log Summary ===');
  console.log(`Session ID: ${logger.sessionId}`);
  console.log(`Log file: ${logPath}`);
  console.log(`Total entries: ${logger.entries.length}`);
}

// Export
module.exports = { AuditLogger };

// CLI 실행
if (require.main === module) {
  const args = process.argv.slice(2);
  
  if (args[0] === 'list') {
    console.log('=== Recent Audit Logs ===');
    const logs = AuditLogger.listLogs(10);
    for (const log of logs) {
      console.log(`${log.file} (${Math.round(log.size/1024)}KB) - ${log.created.toISOString()}`);
    }
  } else if (args[0] === 'example') {
    exampleUsage();
  } else if (args[0] === 'view' && args[1]) {
    const logData = AuditLogger.load(args[1]);
    console.log(JSON.stringify(logData, null, 2));
  } else {
    console.log('Usage:');
    console.log('  node audit_logger.js list     # List recent logs');
    console.log('  node audit_logger.js example  # Run example');
    console.log('  node audit_logger.js view <path>  # View log file');
  }
}
