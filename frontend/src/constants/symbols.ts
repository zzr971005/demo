// 系统规格规定的 12 个独立进化池品种（与后端 init_data.DEFAULT_SYMBOLS+EXTENDED_SYMBOLS 对齐）
// 规格: MA/RB/M/TA/FG/SR/SA/PP/AU/CU/SC/IF
// 主连合约代码格式来自后端 quant_engine/data/source.py（CZCE/CFFEX 用大写，其余小写）

export interface SymbolInfo {
  /** 品种代码，如 RB */
  value: string
  /** 中文名 */
  name: string
  /** 交易所 */
  exchange: 'SHFE' | 'DCE' | 'CZCE' | 'CFFEX' | 'INE'
  /** 天勤主连合约代码，如 KQ.m@SHFE.rb */
  contract: string
  /** 带代码的展示标签，如 螺纹钢(RB) */
  label: string
}

const make = (
  value: string,
  name: string,
  exchange: SymbolInfo['exchange'],
): SymbolInfo => {
  const code = exchange === 'CZCE' || exchange === 'CFFEX' ? value.toUpperCase() : value.toLowerCase()
  return { value, name, exchange, contract: `KQ.m@${exchange}.${code}`, label: `${name}(${value})` }
}

export const SYMBOLS: SymbolInfo[] = [
  make('MA', '甲醇', 'CZCE'),
  make('RB', '螺纹钢', 'SHFE'),
  make('M', '豆粕', 'DCE'),
  make('TA', 'PTA', 'CZCE'),
  make('FG', '玻璃', 'CZCE'),
  make('SR', '白糖', 'CZCE'),
  make('SA', '纯碱', 'CZCE'),
  make('PP', '聚丙烯', 'DCE'),
  make('AU', '黄金', 'SHFE'),
  make('CU', '沪铜', 'SHFE'),
  make('SC', '原油', 'INE'),
  make('IF', '沪深300', 'CFFEX'),
]

/** 仅代码数组，如 ['MA','RB',...] */
export const SYMBOL_CODES: string[] = SYMBOLS.map((s) => s.value)

/** 代码 -> 信息 映射 */
export const SYMBOL_MAP: Record<string, SymbolInfo> = Object.fromEntries(
  SYMBOLS.map((s) => [s.value, s]),
)

/** 主连合约下拉用：{ value: 'KQ.m@SHFE.rb', label: '螺纹钢(RB)' } */
export const SYMBOL_CONTRACT_OPTIONS = SYMBOLS.map((s) => ({ value: s.contract, label: s.label }))
