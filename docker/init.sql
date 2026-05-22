-- PostgreSQL 初始化脚本
-- 容器首次启动时由 Docker 自动执行（仅执行一次）
-- 作用：在 sonarrule_rag 数据库中启用 pgvector 扩展，
--       使 RAG 模块可以创建 vector 类型字段并执行余弦相似度检索

CREATE EXTENSION IF NOT EXISTS vector;
