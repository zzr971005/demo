"""验证流程数据持久化服务"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, update, delete, desc
from app.db import get_session
from app.models import ValidationPipelineData


class ValidationPipelineService:
    """验证流程数据管理服务"""
    
    @staticmethod
    def update_pipeline_data(
        symbol: str,
        generation: int,
        search_input: int = 0,
        search_output: int = 0,
        search_drop: int = 0,
        replay_input: int = 0,
        replay_output: int = 0,
        replay_drop: int = 0,
        validation_input: int = 0,
        validation_output: int = 0,
        validation_drop: int = 0,
        demo_input: int = 0,
        demo_output: int = 0,
        demo_drop: int = 0,
    ) -> ValidationPipelineData:
        """更新或创建验证流程数据"""
        with get_session() as session:
            # 查询是否已存在该代的数据
            existing = session.execute(
                select(ValidationPipelineData).where(
                    ValidationPipelineData.symbol == symbol,
                    ValidationPipelineData.generation == generation
                )
            ).scalar_one_or_none()
            
            if existing:
                # 更新现有记录
                existing.search_input = search_input
                existing.search_output = search_output
                existing.search_drop = search_drop
                existing.replay_input = replay_input
                existing.replay_output = replay_output
                existing.replay_drop = replay_drop
                existing.validation_input = validation_input
                existing.validation_output = validation_output
                existing.validation_drop = validation_drop
                existing.demo_input = demo_input
                existing.demo_output = demo_output
                existing.demo_drop = demo_drop
                existing.updated_at = datetime.utcnow()
                return existing
            else:
                # 创建新记录
                new_data = ValidationPipelineData(
                    symbol=symbol,
                    generation=generation,
                    search_input=search_input,
                    search_output=search_output,
                    search_drop=search_drop,
                    replay_input=replay_input,
                    replay_output=replay_output,
                    replay_drop=replay_drop,
                    validation_input=validation_input,
                    validation_output=validation_output,
                    validation_drop=validation_drop,
                    demo_input=demo_input,
                    demo_output=demo_output,
                    demo_drop=demo_drop,
                )
                session.add(new_data)
                return new_data
    
    @staticmethod
    def get_latest_pipeline_data(symbol: str) -> Optional[ValidationPipelineData]:
        """获取指定品种最新的验证流程数据"""
        with get_session() as session:
            return session.execute(
                select(ValidationPipelineData)
                .where(ValidationPipelineData.symbol == symbol)
                .order_by(desc(ValidationPipelineData.generation))
            ).scalar_one_or_none()
    
    @staticmethod
    def get_all_latest_pipeline_data() -> List[dict]:
        """获取所有品种最新的验证流程数据"""
        with get_session() as session:
            # 使用子查询获取每个品种的最新代数
            subquery = session.execute(
                select(
                    ValidationPipelineData.symbol,
                    ValidationPipelineData.generation
                ).distinct().order_by(
                    ValidationPipelineData.symbol,
                    desc(ValidationPipelineData.generation)
                )
            ).all()
            
            # 获取每个品种的最新数据
            results = []
            for symbol, generation in subquery:
                data = session.execute(
                    select(ValidationPipelineData).where(
                        ValidationPipelineData.symbol == symbol,
                        ValidationPipelineData.generation == generation
                    )
                ).scalar_one_or_none()
                if data:
                    # 转换为字典，避免session依赖
                    results.append({
                        'symbol': data.symbol,
                        'generation': data.generation,
                        'search_input': data.search_input,
                        'search_output': data.search_output,
                        'search_drop': data.search_drop,
                        'cumulative_search_input': data.cumulative_search_input,
                        'replay_input': data.replay_input,
                        'replay_output': data.replay_output,
                        'replay_drop': data.replay_drop,
                        'cumulative_replay_input': data.cumulative_replay_input,
                        'validation_input': data.validation_input,
                        'validation_output': data.validation_output,
                        'validation_drop': data.validation_drop,
                        'cumulative_validation_input': data.cumulative_validation_input,
                        'demo_input': data.demo_input,
                        'demo_output': data.demo_output,
                        'demo_drop': data.demo_drop,
                        'cumulative_demo_input': data.cumulative_demo_input,
                        'created_at': data.created_at,
                        'updated_at': data.updated_at,
                    })
            
            return results
    
    @staticmethod
    def get_pipeline_history(symbol: str, limit: int = 10) -> List[ValidationPipelineData]:
        """获取指定品种的历史验证流程数据"""
        with get_session() as session:
            return session.execute(
                select(ValidationPipelineData)
                .where(ValidationPipelineData.symbol == symbol)
                .order_by(desc(ValidationPipelineData.generation))
                .limit(limit)
            ).scalars().all()
    
    @staticmethod
    def delete_symbol_data(symbol: str) -> int:
        """删除指定品种的所有验证流程数据"""
        with get_session() as session:
            result = session.execute(
                delete(ValidationPipelineData).where(
                    ValidationPipelineData.symbol == symbol
                )
            )
            return result.rowcount
    
    @staticmethod
    def cleanup_old_data(symbol: str, keep_generations: int = 100) -> int:
        """清理旧数据，只保留最近的指定代数"""
        with get_session() as session:
            # 获取要保留的最小代数
            min_generation = session.execute(
                select(ValidationPipelineData.generation)
                .where(ValidationPipelineData.symbol == symbol)
                .order_by(desc(ValidationPipelineData.generation))
                .offset(keep_generations - 1)
                .limit(1)
            ).scalar()
            
            if min_generation is None:
                return 0
            
            # 删除旧数据
            result = session.execute(
                delete(ValidationPipelineData).where(
                    ValidationPipelineData.symbol == symbol,
                    ValidationPipelineData.generation < min_generation
                )
            )
            return result.rowcount
