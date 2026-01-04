/**
 * Fund Classification Generator
 * DC형 70% 위험자산 한도 자동 검증을 위한 펀드 분류 데이터 생성
 * 
 * 위험자산: 주식형, 해외주식형, 주식혼합형, 해외주식혼합형, 채권혼합형, 해외채권혼합형
 * 안전자산: 채권형, 해외채권형, 기타 (MMF, 예금, 골드, TDF 등)
 */

const fs = require('fs');
const path = require('path');

// 위험자산 카테고리
const RISK_ASSET_CATEGORIES = [
  '주식형',
  '해외주식형',
  '주식혼합형',
  '해외주식혼합형',
  '채권혼합형',
  '해외채권혼합형'
];

// 안전자산 카테고리
const SAFE_ASSET_CATEGORIES = [
  '채권형',
  '해외채권형',
  '기타'
];

// 펀드명으로 카테고리 추정 (generate_md.js 로직 기반)
function getFundCategory(fundName) {
  const name = fundName;
  
  // 1. 해외 여부 확인
  const isOverseas = /해외|글로벌|미국|차이나|인디아|베트남|일본|유럽|아시아|이머징|Global|USA|China|India|Japan|Europe|Asia|Emerging/i.test(name);
  
  // 2. 자산 유형 확인
  const hasBondMixed = /채권혼합|채권 혼합/.test(name);
  const hasStockMixed = /주식혼합|주식 혼합/.test(name);
  const hasBond = /채권|크레딧|국공채|인컴|하이일드|단기채/.test(name) && !hasBondMixed;
  const hasStock = /주식/.test(name) && !hasStockMixed && !hasBondMixed;
  
  // 3. 특수 유형 확인
  const isSpecial = /TDF|MMF|EMP|리츠|골드|부동산|원자재|금-재간접|TIF/.test(name);
  
  // 분류 결정
  if (isSpecial) {
    return '기타';
  }
  
  if (isOverseas) {
    if (hasBondMixed) return '해외채권혼합형';
    if (hasStockMixed) return '해외주식혼합형';
    if (hasBond) return '해외채권형';
    if (hasStock) return '해외주식형';
    // 기본: 해외주식형으로 추정 (대부분 해외펀드는 주식형)
    return '해외주식형';
  } else {
    if (hasBondMixed) return '채권혼합형';
    if (hasStockMixed) return '주식혼합형';
    if (hasBond) return '채권형';
    if (hasStock) return '주식형';
    return '기타';
  }
}

// 테마 추출
function extractTheme(fundName) {
  const themes = {
    'semiconductor': /반도체|필라델피아/i.test(fundName),
    'ai': /AI|인공지능|Chat AI|메타버스/i.test(fundName),
    'robot': /로봇|휴머노이드|로보틱스|로보테크/i.test(fundName),
    'healthcare': /헬스케어|바이오|헬스사이언스/i.test(fundName),
    'dividend': /배당|고배당|인컴/i.test(fundName),
    'value': /가치|밸류/i.test(fundName),
    'growth': /성장|그로스/i.test(fundName),
    'index': /인덱스|KOSPI|S&P|나스닥|KRX/i.test(fundName),
    'ev': /전기차|자율주행|모빌리티/i.test(fundName),
    'gold': /골드|금/i.test(fundName),
    'energy': /에너지|그린|클린테크/i.test(fundName),
    'reits': /리츠|부동산/i.test(fundName),
    'space': /우주항공/i.test(fundName)
  };
  
  const matched = Object.entries(themes)
    .filter(([_, match]) => match)
    .map(([theme]) => theme);
  
  return matched.length > 0 ? matched : ['general'];
}

// 지역 추출
function extractRegion(fundName) {
  if (/미국|USA|S&P|나스닥|Nasdaq/i.test(fundName)) return 'us';
  if (/차이나|중국|China/i.test(fundName)) return 'china';
  if (/인디아|인도|India/i.test(fundName)) return 'india';
  if (/일본|Japan|재팬/i.test(fundName)) return 'japan';
  if (/유럽|Europe|유로/i.test(fundName)) return 'europe';
  if (/베트남|Vietnam/i.test(fundName)) return 'vietnam';
  if (/아세안|ASEAN/i.test(fundName)) return 'asean';
  if (/아시아|Asia/i.test(fundName)) return 'asia';
  if (/브라질|Brazil/i.test(fundName)) return 'brazil';
  if (/이머징|Emerging/i.test(fundName)) return 'emerging';
  if (/글로벌|Global|월드|World/i.test(fundName)) return 'global';
  if (/코리아|한국|KOSPI|KRX|코스닥/i.test(fundName)) return 'korea';
  return 'korea'; // 기본값
}

// 환헤지 여부
function isHedged(fundName) {
  if (/\(H\)|\[H\]|H[)]|\(환헤지\)/i.test(fundName)) return true;
  if (/\(UH\)|\[UH\]|UH[)]|\(환노출\)/i.test(fundName)) return false;
  return null; // 명시되지 않음
}

// 메인 실행
function main() {
  // fund_data.json 읽기
  const fundDataPath = path.join(__dirname, '..', 'fund_data.json');
  const funds = JSON.parse(fs.readFileSync(fundDataPath, 'utf8'));
  
  // 분류 데이터 생성
  const classification = {};
  
  for (const fund of funds) {
    const category = getFundCategory(fund.name);
    const isRiskAsset = RISK_ASSET_CATEGORIES.includes(category);
    
    classification[fund.name] = {
      category: category,
      riskAsset: isRiskAsset,
      assetClass: category.includes('채권') ? 'bond' : 
                  category.includes('혼합') ? 'mixed' : 
                  category.includes('주식') ? 'equity' : 'other',
      region: extractRegion(fund.name),
      themes: extractTheme(fund.name),
      hedged: isHedged(fund.name),
      riskLevel: fund.riskLevel,
      source: 'fund_data.json + keyword classification',
      generatedAt: new Date().toISOString().split('T')[0]
    };
  }
  
  // 통계 출력
  const stats = {
    total: funds.length,
    riskAssets: Object.values(classification).filter(c => c.riskAsset).length,
    safeAssets: Object.values(classification).filter(c => !c.riskAsset).length,
    byCategory: {}
  };
  
  for (const c of Object.values(classification)) {
    stats.byCategory[c.category] = (stats.byCategory[c.category] || 0) + 1;
  }
  
  console.log('=== Fund Classification Stats ===');
  console.log(`Total funds: ${stats.total}`);
  console.log(`Risk assets: ${stats.riskAssets} (${(stats.riskAssets/stats.total*100).toFixed(1)}%)`);
  console.log(`Safe assets: ${stats.safeAssets} (${(stats.safeAssets/stats.total*100).toFixed(1)}%)`);
  console.log('\nBy category:');
  for (const [cat, count] of Object.entries(stats.byCategory).sort((a,b) => b[1]-a[1])) {
    const riskLabel = RISK_ASSET_CATEGORIES.includes(cat) ? '[RISK]' : '[SAFE]';
    console.log(`  ${cat}: ${count} ${riskLabel}`);
  }
  
  // 파일 저장
  const outputPath = path.join(__dirname, '..', 'fund_classification.json');
  fs.writeFileSync(outputPath, JSON.stringify(classification, null, 2), 'utf8');
  console.log(`\nSaved to: ${outputPath}`);
  
  return classification;
}

main();
