import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_session
from app.models import ValidationPipelineData
from sqlalchemy import select

with get_session() as session:
    result = session.execute(
        select(ValidationPipelineData).where(
            ValidationPipelineData.symbol == 'RB',
            ValidationPipelineData.generation == 30
        )
    ).scalar_one_or_none()
    
    if result:
        print(f'Generation 30:')
        print(f'  search_input={result.search_input}')
        print(f'  search_output={result.search_output}')
        print(f'  replay_output={result.replay_output}')
        print(f'  validation_output={result.validation_output}')
        print(f'  demo_output={result.demo_output}')
    else:
        print('Generation 30 not found')
