/**
 * Portfolio Validation Script
 * DC형 70% 위험자산 한도 검증 및 데이터 무결성 체크
 * 
 * Usage: node validate_data.js [portfolio_json]
 * 
 * Portfolio JSON format:
 * [
 *   { "name": "펀드명", "weight": 20 },
 *   ...
 * ]
 */

const fs = require('fs');
const path = require('path');

// 설정
const DC_RISK_LIMIT = 70;
const SINGLE_FUND_LIMIT = 40;

// 데이터 로드
function loadData() {
  const fundsDir = path.join(__dirname, '..');
  
  return {
    fundData: JSON.parse(fs.readFileSync(path.join(fundsDir, 'fund_data.json'), 'utf8')),
    classification: JSON.parse(fs.readFileSync(path.join(fundsDir, 'fund_classification.json'), 'utf8')),
    fees: JSON.parse(fs.readFileSync(path.join(fundsDir, 'fund_fees.json'), 'utf8')),
    depositRates: JSON.parse(fs.readFileSync(path.join(fundsDir, 'deposit_rates.json'), 'utf8'))
  };
}

/**
 * 포트폴리오 검증
 * @param {Array} portfolio - [{ name: string, weight: number }, ...]
 * @returns {Object} - { valid: boolean, errors: [], warnings: [], summary: {} }
 */
function validatePortfolio(portfolio, data) {
  const results = {
    valid: true,
    errors: [],
    warnings: [],
    summary: {
      totalWeight: 0,
      riskAssetWeight: 0,
      safeAssetWeight: 0,
      fundCount: portfolio.length,
      feesCoverage: { available: 0, missing: 0 }
    }
  };
  
  // 1. 비중 합계 검증
  const totalWeight = portfolio.reduce((sum, f) => sum + f.weight, 0);
  results.summary.totalWeight = totalWeight;
  
  if (Math.abs(totalWeight - 100) > 0.01) {
    results.valid = false;
    results.errors.push({
      rule: 'TOTAL_WEIGHT_100',
      message: `비중 합계 ${totalWeight.toFixed(2)}% (100% 필요)`,
      severity: 'error'
    });
  }
  
  // 2. 위험자산 70% 한도 검증
  let riskWeight = 0;
  let safeWeight = 0;
  
  for (const fund of portfolio) {
    const classInfo = data.classification[fund.name];
    
    if (!classInfo) {
      results.warnings.push({
        rule: 'CLASSIFICATION_MISSING',
        message: `분류 정보 없음: ${fund.name}`,
        severity: 'warning'
      });
      // 보수적으로 위험자산으로 간주
      riskWeight += fund.weight;
    } else if (classInfo.riskAsset) {
      riskWeight += fund.weight;
    } else {
      safeWeight += fund.weight;
    }
  }
  
  results.summary.riskAssetWeight = riskWeight;
  results.summary.safeAssetWeight = safeWeight;
  
  if (riskWeight > DC_RISK_LIMIT) {
    results.valid = false;
    results.errors.push({
      rule: 'DC_RISK_LIMIT_70',
      message: `위험자산 ${riskWeight.toFixed(2)}% (한도 ${DC_RISK_LIMIT}% 초과)`,
      severity: 'error',
      excess: riskWeight - DC_RISK_LIMIT
    });
  }
  
  // 3. 단일 펀드 40% 초과 검증
  for (const fund of portfolio) {
    if (fund.weight > SINGLE_FUND_LIMIT) {
      results.valid = false;
      results.errors.push({
        rule: 'SINGLE_FUND_LIMIT_40',
        message: `${fund.name}: ${fund.weight}% (한도 ${SINGLE_FUND_LIMIT}% 초과)`,
        severity: 'error'
      });
    }
  }
  
  // 4. 총보수 데이터 확인
  for (const fund of portfolio) {
    if (data.fees[fund.name]?.totalFee) {
      results.summary.feesCoverage.available++;
    } else {
      results.summary.feesCoverage.missing++;
      results.warnings.push({
        rule: 'FEE_DATA_MISSING',
        message: `총보수 미확인: ${fund.name}`,
        severity: 'warning'
      });
    }
  }
  
  // 5. 펀드 존재 여부 확인
  const fundNames = data.fundData.map(f => f.name);
  for (const fund of portfolio) {
    if (!fundNames.includes(fund.name)) {
      results.warnings.push({
        rule: 'FUND_NOT_FOUND',
        message: `펀드 데이터 없음: ${fund.name}`,
        severity: 'warning'
      });
    }
  }
  
  return results;
}

/**
 * 데이터 무결성 체크
 */
function checkDataIntegrity(data) {
  const results = {
    valid: true,
    errors: [],
    warnings: [],
    summary: {}
  };
  
  // 1. fund_data.json 완전성
  const fundCount = data.fundData.length;
  results.summary.fundData = {
    count: fundCount,
    hasAllFields: data.fundData.every(f => 
      f.name && f.riskLevel !== undefined && f.company
    )
  };
  
  // 2. classification 커버리지
  const classifiedCount = Object.keys(data.classification).length;
  const uncoveredFunds = data.fundData.filter(f => !data.classification[f.name]);
  
  results.summary.classification = {
    count: classifiedCount,
    coverage: `${(classifiedCount / fundCount * 100).toFixed(1)}%`,
    uncovered: uncoveredFunds.map(f => f.name).slice(0, 5)
  };
  
  if (uncoveredFunds.length > 0) {
    results.warnings.push({
      rule: 'CLASSIFICATION_INCOMPLETE',
      message: `${uncoveredFunds.length}개 펀드 분류 누락`,
      severity: 'warning'
    });
  }
  
  // 3. fees 커버리지
  const feesCount = Object.keys(data.fees).length;
  results.summary.fees = {
    count: feesCount,
    coverage: `${(feesCount / fundCount * 100).toFixed(1)}%`,
    note: feesCount < fundCount ? '비용 분석 불완전' : '비용 분석 가능'
  };
  
  if (feesCount < 10) {
    results.warnings.push({
      rule: 'FEES_INCOMPLETE',
      message: `총보수 데이터 ${feesCount}/${fundCount}개 (비용 분석 제한)`,
      severity: 'warning'
    });
  }
  
  // 4. deposit_rates 최신성
  const lastUpdated = new Date(data.depositRates.lastUpdated);
  const now = new Date();
  const daysDiff = Math.floor((now - lastUpdated) / (1000 * 60 * 60 * 24));
  
  results.summary.depositRates = {
    lastUpdated: data.depositRates.lastUpdated,
    daysOld: daysDiff,
    baseRate: data.depositRates.rates.baseRate.value + '%'
  };
  
  if (daysDiff > 30) {
    results.warnings.push({
      rule: 'DEPOSIT_RATES_STALE',
      message: `예금 금리 데이터 ${daysDiff}일 경과 (업데이트 필요)`,
      severity: 'warning'
    });
  }
  
  return results;
}

/**
 * 결과 출력
 */
function printResults(title, results) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`  ${title}`);
  console.log(`${'='.repeat(60)}`);
  
  if (results.valid) {
    console.log('\n✅ PASSED\n');
  } else {
    console.log('\n❌ FAILED\n');
  }
  
  if (results.errors.length > 0) {
    console.log('ERRORS:');
    for (const e of results.errors) {
      console.log(`  ❌ [${e.rule}] ${e.message}`);
    }
  }
  
  if (results.warnings.length > 0) {
    console.log('\nWARNINGS:');
    for (const w of results.warnings) {
      console.log(`  ⚠️  [${w.rule}] ${w.message}`);
    }
  }
  
  console.log('\nSUMMARY:');
  console.log(JSON.stringify(results.summary, null, 2));
}

// 메인 실행
function main() {
  const data = loadData();
  
  // 1. 데이터 무결성 체크
  const integrityResults = checkDataIntegrity(data);
  printResults('Data Integrity Check', integrityResults);
  
  // 2. 예시 포트폴리오 검증 (현재 DC 포트폴리오)
  const currentPortfolio = [
    { name: "삼성글로벌반도체증권자투자신탁UH[주식]_Cpe(퇴직)", weight: 15 },
    { name: "삼성미국S&P500인덱스증권자투자신탁UH[주식] Cpe(퇴직)", weight: 20 },
    { name: "미래에셋코어테크증권자투자신탁(주식) 종류C-P2E", weight: 10 },
    { name: "삼성글로벌휴머노이드로봇증권자투자신탁UH[주식]_Cpe(퇴직연금)", weight: 5 },
    { name: "미래에셋퇴직연금배당커버드콜액티브증권자투자신탁1호(주식혼합) 종류C-P2e", weight: 20 },
    { name: "미래에셋솔로몬중장기국공채증권자투자신탁1호(채권)C-P2E(퇴직)", weight: 15 },
    { name: "미래에셋솔로몬장기국공채증권자투자신탁1호(채권) 종류 C-P2e", weight: 15 }
  ];
  
  const portfolioResults = validatePortfolio(currentPortfolio, data);
  printResults('Current Portfolio Validation', portfolioResults);
  
  // 3. CLI에서 포트폴리오 파일 전달 시 추가 검증
  const portfolioArg = process.argv[2];
  if (portfolioArg && fs.existsSync(portfolioArg)) {
    const customPortfolio = JSON.parse(fs.readFileSync(portfolioArg, 'utf8'));
    const customResults = validatePortfolio(customPortfolio, data);
    printResults('Custom Portfolio Validation', customResults);
  }
  
  // 종합 결과 반환
  return {
    integrity: integrityResults,
    portfolio: portfolioResults
  };
}

// Export for module use
module.exports = { validatePortfolio, checkDataIntegrity, loadData };

// CLI 실행
if (require.main === module) {
  main();
}
