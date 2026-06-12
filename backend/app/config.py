from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "backend" / "config" / "system.yaml"
TRADING_CONFIG_PATH = PROJECT_ROOT / "backend" / "config" / "trading_config.yaml"
SIMULATION_CONFIG_PATH = PROJECT_ROOT / "backend" / "config" / "simulation_config.yaml"
LIVE_RISK_CONFIG_PATH = PROJECT_ROOT / "backend" / "config" / "live_risk_config.yaml"


class TradingHours(BaseModel):
    day: List[str] = Field(default_factory=list)
    night: List[str] = Field(default_factory=list)


class SymbolConfig(BaseModel):
    name: str
    exchange: str
    lot: int
    margin_rate: float
    commission_rate: float
    close_today_commission_rate: Optional[float] = None
    max_margin: float
    evolution_pool: int = 300
    group: str
    trading_hours: TradingHours = Field(default_factory=TradingHours)
    if_close_today_forbidden: bool = False


class SymbolsConfig(BaseModel):
    low_margin: Dict[str, SymbolConfig] = Field(default_factory=dict)
    high_margin: Dict[str, SymbolConfig] = Field(default_factory=dict)

    @property
    def all_symbols(self) -> Dict[str, SymbolConfig]:
        return {**self.low_margin, **self.high_margin}


class EvolutionStageConfig(BaseModel):
    name: str
    max_tree_depth: Optional[int] = None
    min_ic: Optional[float] = None
    min_sharpe: Optional[float] = None
    cross_family_required: Optional[bool] = None
    min_test_sharpe: Optional[float] = None


class EvolutionConfig(BaseModel):
    main_cycle: Literal["1H", "1D", "5M"] = "1H"
    daily_evolution_time: str = "20:30"
    generations: int = 60
    population: int = 300
    crossover_rate: float = 0.7
    mutation_rate: float = 0.2
    train_months: int = 6
    validation_months: int = 6
    test_months: int = 6
    seed_reserve_gens: int = 10
    seed_reserve_ratio: float = 0.2
    template_ratio: float = 0.6
    max_tree_depth: int = 8
    stages: List[EvolutionStageConfig] = Field(default_factory=list)


class RiskConfig(BaseModel):
    max_total_margin_ratio: float = 0.8
    single_symbol_max_dd: float = 0.10
    daily_max_loss: float = 0.05
    manual_switch_required: bool = True
    if_close_today_forbidden: bool = True
    max_positions_per_symbol: int = 3
    circuit_breaker_consecutive_errors: int = 3
    max_margin_per_symbol: float = 15000.0


class FamilyConfig(BaseModel):
    weight: float
    primitives: List[str] = Field(default_factory=list)


class FamiliesConfig(BaseModel):
    momentum: FamilyConfig
    mean_reversion: FamilyConfig
    volatility: FamilyConfig
    price_volume: FamilyConfig
    term_structure: FamilyConfig
    open_interest: FamilyConfig
    microstructure: FamilyConfig
    macro_proxy: FamilyConfig


class SystemConfig(BaseModel):
    symbols: SymbolsConfig
    evolution: EvolutionConfig
    risk: RiskConfig
    families: FamiliesConfig


class TqSdkConfig(BaseModel):
    account: str
    password: str
    mode: str = "tqkq"  # tqkq: 快期模拟, tqsim: 本地模拟


class SimulationConfig(BaseModel):
    max_position_ratio: float = 0.3
    max_total_margin_ratio: float = 0.5
    strategy_selection_mode: str = "dynamic"
    strategy_evaluation_window: int = 7
    replay_enabled: bool = True
    replay_data_source: str = "database"
    live_transition_period_days: int = 30
    live_transition_min_sharpe: float = 1.5
    live_transition_max_drawdown: float = 0.1


class LiveRiskConfig(BaseModel):
    max_total_margin_ratio: float = 0.4
    daily_max_loss_ratio: float = 0.03
    max_drawdown_ratio: float = 0.08
    max_position_ratio: float = 0.2
    max_positions_per_symbol: int = 1
    single_symbol_max_dd: float = 0.05
    strategy_allocation_mode: str = "dynamic_weighted"
    allocation_method: str = "risk_parity"
    weight_update_frequency: str = "daily"
    min_weight_threshold: float = 0.05
    max_weight_threshold: float = 0.6
    ensemble_enabled: bool = True
    ensemble_method: str = "gradient_based"
    switch_cooldown_enabled: bool = True
    switch_cooldown_hours: int = 6
    switch_mode: str = "gradual"
    max_daily_weight_change: float = 0.3
    volatility_based_adjustment: bool = True
    emergency_close_all_threshold: float = 0.05
    circuit_breaker_enabled: bool = True
    circuit_breaker_level: int = 3


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "期货自动进化因子挖掘系统"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, validation_alias="DEBUG")

    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@localhost:5432/quant_db",
        validation_alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )

    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        validation_alias="CORS_ORIGINS",
    )
    ws_heartbeat_interval: int = Field(default=30, validation_alias="WS_HEARTBEAT_INTERVAL")

    tqsdk_account: str = Field(
        default="",
        validation_alias="TQSDK_ACCOUNT",
    )
    tqsdk_password: str = Field(
        default="",
        validation_alias="TQSDK_PASSWORD",
    )
    tqsdk_sim: bool = Field(
        default=True,
        validation_alias="TQSDK_SIM",
    )

    system: Optional[SystemConfig] = Field(default=None)
    tqsdk: Optional[TqSdkConfig] = Field(default=None)
    simulation: Optional[SimulationConfig] = Field(default=None)
    live_risk: Optional[LiveRiskConfig] = Field(default=None)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    def model_post_init(self, __context: Any) -> None:
        if self.system is None:
            self.system = load_system_config()
        if self.tqsdk is None:
            self.tqsdk = load_trading_config()
        if self.simulation is None:
            self.simulation = load_simulation_config()
        if self.live_risk is None:
            self.live_risk = load_live_risk_config()


def load_system_config(config_path: Optional[Path] = None) -> SystemConfig:
    path = config_path or CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"系统配置文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return SystemConfig.model_validate(raw)


def load_trading_config(config_path: Optional[Path] = None) -> TqSdkConfig:
    path = config_path or TRADING_CONFIG_PATH
    if not path.exists():
        # 返回默认配置
        return TqSdkConfig(account="", password="", mode="tqkq")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return TqSdkConfig.model_validate(raw.get("tqsdk", {}))


def load_simulation_config(config_path: Optional[Path] = None) -> SimulationConfig:
    path = config_path or SIMULATION_CONFIG_PATH
    if not path.exists():
        # 返回默认配置
        return SimulationConfig()
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return SimulationConfig.model_validate(raw.get("simulation", {}))


def load_live_risk_config(config_path: Optional[Path] = None) -> LiveRiskConfig:
    path = config_path or LIVE_RISK_CONFIG_PATH
    if not path.exists():
        # 返回默认配置
        return LiveRiskConfig()
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return LiveRiskConfig.model_validate(raw.get("live_risk", {}))


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    global _settings
    _settings = Settings()
    return _settings


def get_config() -> Settings:
    return get_settings()
