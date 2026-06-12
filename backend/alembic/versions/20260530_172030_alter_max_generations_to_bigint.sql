-- 修改 evolution_tasks 表的 max_generations 字段类型为 BigInteger
-- 以支持 9999999999 这样的大数值

ALTER TABLE evolution_tasks ALTER COLUMN max_generations TYPE BIGINT;
